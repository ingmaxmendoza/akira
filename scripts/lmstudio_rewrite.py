"""Feed vault pages through a local LM Studio model for Page Standard rewrite.

Usage:
  python scripts/lmstudio_rewrite.py --from-audit concepts --next 25   # auto-pick batch
  python scripts/lmstudio_rewrite.py --files akira/concepts/gaia-hypothesis.md ...
  python scripts/lmstudio_rewrite.py --list batch.txt          # one path per line
  ... add --live to any of the above to write results

--from-audit DIR runs audit_page_quality.py --dir DIR, takes the first N
fail-hard pages (alphabetical), skipping any stem listed in
settings/pending/lmstudio-out/claude-only.md (twin clusters and other
judgment cases reserved for Claude — one stem per line, # comments ok).

Dry-run (default) writes proposed rewrites to settings/pending/lmstudio-out/
for review. --live overwrites the originals IN PLACE (git is the undo).
Pages missing `topics:` are skipped to the deferred list — Claude handles those.

Full loop per batch: run with --live, then
  python scripts/audit_page_quality.py --dir DIR   (fail-hard must drop by ~N)
  python scripts/find_missing_pages.py             (no new dead links)
  git add -A <vault>/DIR && git commit -m "migrate(topics): lmstudio batch — <range>"
Anything in deferred.md goes to Claude later, in one cheap message.
"""
# ponytail: stdlib urllib, sequential, no retries — rerun the command on failure
import argparse, json, re, subprocess, sys, urllib.request
from datetime import date
from pathlib import Path

from rag_utils import load_config, resolve_vault_path

ROOT = Path(__file__).resolve().parent.parent
VAULT = resolve_vault_path(load_config())
PROMPT_FILE = ROOT / "settings" / "lmstudio-rewrite-prompt.md"
OUT_DIR = ROOT / "settings" / "pending" / "lmstudio-out"
API = "http://127.0.0.1:1234/v1/chat/completions"
MODEL = "qwen3-vl-8b-instruct"  # default; override with --model


def system_prompt():
    text = PROMPT_FILE.read_text(encoding="utf-8")
    m = re.search(r"## SYSTEM PROMPT.*?```\n(.*?)\n```", text, re.S)
    if not m:
        sys.exit("could not extract system prompt from " + str(PROMPT_FILE))
    return m.group(1)


def category_of(path: Path, content: str):
    if "type: concept" in content:
        return "concept"
    m = re.search(r"^category:\s*(\w+)", content, re.M)
    sub = m.group(1) if m else path.parent.name
    return f"entity/{sub}"


def call_model(system, user):
    body = json.dumps({
        "model": MODEL,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "temperature": 0.4,
        "max_tokens": 4000,
    }).encode()
    req = urllib.request.Request(API, body, {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        out = json.load(r)["choices"][0]["message"]["content"]
    # strip a stray code fence if the model added one anyway
    out = re.sub(r"^```[a-z]*\n|\n```$", "", out.strip())
    # models add trailing spaces (markdown line breaks) which break the
    # audit's exact section-heading match -- normalize every line
    return "\n".join(l.rstrip() for l in out.strip().splitlines()) + "\n"


def sanity(original: str, rewritten: str):
    """Reject obviously broken output; real gate is audit_page_quality.py."""
    if not rewritten.startswith("---"):
        return "output does not start with frontmatter"
    if len(rewritten) < 0.5 * len(original):
        return "output suspiciously short vs input"
    return None


def keep_original_frontmatter(original: str, rewritten: str):
    """Small models mangle YAML (invent topics, dead related: stems) — keep the
    input page's frontmatter verbatim, bump last_updated, take only the model's body."""
    orig_fm = original.split("---", 2)[1]
    orig_fm = re.sub(r"^last_updated:.*$", f"last_updated: {date.today()}",
                     orig_fm, flags=re.M)
    body = rewritten.split("---", 2)[2] if rewritten.count("---") >= 2 else rewritten
    return f"---{orig_fm}---\n{body.lstrip()}"


def strip_invented_links(original: str, rewritten: str):
    """Small models invent [[wikilinks]]; de-link any target not in the input
    (unless the page actually exists in the vault) instead of rejecting."""
    orig_links = set(re.findall(r"\[\[([^\]|]+)", original))

    def fix(m):
        stem, disp = m.group(1), m.group(2)
        if stem in orig_links or list(VAULT.rglob(stem + ".md")):
            return m.group(0)
        return disp or stem

    return re.sub(r"\[\[([^\]|]+)\|?([^\]]*)\]\]", fix, rewritten)


def pick_from_audit(dir_name: str, n: int):
    subprocess.run([sys.executable, str(ROOT / "scripts" / "audit_page_quality.py"),
                    "--dir", dir_name], capture_output=True)
    worklist = (ROOT / "settings" / "pending" / "prompts" / "quality-worklist.md"
                ).read_text(encoding="utf-8")
    hard = worklist.split("## fail-hard")[1].split("##")[0]
    skip = set()
    for name in ("claude-only.md", "still-failing.md"):
        f = OUT_DIR / name
        if f.exists():
            skip |= {l.strip() for l in f.read_text().splitlines()
                     if l.strip() and not l.startswith("#")}
    picked, no_topics = [], 0
    for rel in re.findall(r"- `([^`]+)`", hard):
        if Path(rel).stem in skip:
            continue
        p = VAULT / rel
        # pages without topics: need Claude, not the local model
        if not re.search(r"^topics:\s*\[?[^\]\s]", p.read_text(encoding="utf-8"), re.M):
            no_topics += 1
            continue
        picked.append(p)
        if len(picked) == n:
            break
    if no_topics:
        print(f"skipped {no_topics} fail-hard pages lacking topics: -- "
              f"assign topics: first (Claude)")
    return picked


def main():
    global MODEL
    ap = argparse.ArgumentParser()
    ap.add_argument("--files", nargs="*", default=[])
    ap.add_argument("--list", help="file with one page path per line")
    ap.add_argument("--from-audit", metavar="DIR",
                    help="pick next fail-hard pages from audit of this dir")
    ap.add_argument("--next", type=int, default=25, help="batch size for --from-audit")
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--model", default=MODEL, help="LM Studio model id")
    args = ap.parse_args()
    MODEL = args.model

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    paths = [Path(f) for f in args.files]
    if args.list:
        paths += [Path(l.strip()) for l in Path(args.list).read_text().splitlines() if l.strip()]
    if args.from_audit:
        paths += pick_from_audit(args.from_audit, args.next)
    if not paths:
        sys.exit("no files given")

    sys_prompt = system_prompt()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    deferred = []

    for p in paths:
        content = p.read_text(encoding="utf-8")
        if not re.search(r"^topics:\s*\[?[^\]\s]", content, re.M):
            deferred.append(f"{p} | missing topics: — needs Claude")
            print(f"DEFER {p} (no topics:)")
            continue
        user = f"Date: {date.today()}\nCategory: {category_of(p, content)}\n\n{content}"
        print(f"-> {p} ...", flush=True)
        try:
            result = call_model(sys_prompt, user)
        except OSError as e:
            sys.exit(f"LM Studio not reachable at {API} ({e}) -- "
                     f"start the server (a model loaded as LLM, with system prompt support) and rerun.")
        err = sanity(content, result)
        if err:
            deferred.append(f"{p} | {err}")
            print(f"DEFER {p} ({err})")
            continue
        result = strip_invented_links(content, result)
        result = keep_original_frontmatter(content, result)
        target = p if args.live else OUT_DIR / p.name
        target.write_text(result, encoding="utf-8")
        print(f"  wrote {target}")

    if deferred:
        (OUT_DIR / "deferred.md").write_text("\n".join(deferred) + "\n", encoding="utf-8")
        print(f"\n{len(deferred)} deferred -> {OUT_DIR / 'deferred.md'}")
    if not args.live:
        print(f"\nDry-run: review {OUT_DIR}, then rerun with --live, "
              f"then: python scripts/audit_page_quality.py")


if __name__ == "__main__":
    main()
