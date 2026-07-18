"""One-command runner for the LM Studio rewrite pipeline — v2 with live progress.

  python scripts/lmstudio-v2-run.py                      # 1 batch of 25 concepts
  python scripts/lmstudio-v2-run.py --dir entities
  python scripts/lmstudio-v2-run.py --batches 0          # run until nothing left
  python scripts/lmstudio-v2-run.py --next 10 --batches 3

Same loop as lmstudio_run.py (rewrite --live -> verify -> commit, auto-revert
on regression) but streams progress live: [page i/N] with per-page seconds,
batch ETA, and overall fail-hard countdown with a finish estimate.
"""
# ponytail: subprocess glue around existing scripts, no parallelism, stop on first failure
import argparse, json, re, subprocess, sys, time, urllib.request
from pathlib import Path

from rag_utils import load_config, resolve_vault_path

ROOT = Path(__file__).resolve().parent.parent
VAULT_REL = resolve_vault_path(load_config()).relative_to(ROOT).as_posix()
PY = sys.executable


def pick_model(preset):
    """List models loaded in LM Studio and ask which to use (skip with --model)."""
    if preset:
        return preset
    with urllib.request.urlopen("http://127.0.0.1:1234/v1/models", timeout=10) as r:
        ids = [m["id"] for m in json.load(r)["data"] if "embed" not in m["id"]]
    if not ids:
        sys.exit("no chat models loaded in LM Studio")
    for i, mid in enumerate(ids, 1):
        print(f"  {i}. {mid}")
    choice = input(f"model to use [1-{len(ids)}, Enter=1]: ").strip()
    return ids[int(choice) - 1] if choice.isdigit() and 1 <= int(choice) <= len(ids) else ids[0]


def run(*args, **kw):
    return subprocess.run([PY, *args], cwd=ROOT, capture_output=True,
                          text=True, encoding="utf-8", errors="replace", **kw)


def fmt(sec):
    sec = int(sec)
    return f"{sec // 3600}h{sec % 3600 // 60:02d}m" if sec >= 3600 else f"{sec // 60}m{sec % 60:02d}s"


def dead_links():
    out = run("scripts/find_missing_pages.py").stdout
    m = re.search(r"Done: (\d+) missing pages", out)
    return int(m.group(1)) if m else sys.exit("could not parse find_missing_pages output")


def fail_hard(dir_name):
    out = run("scripts/audit_page_quality.py", "--dir", dir_name).stdout
    m = re.search(r"fail-hard=(\d+)", out)
    return int(m.group(1)) if m else 0


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def stream_rewrite(dir_name, n, model):
    """Run lmstudio_rewrite.py --live, echoing progress per page as it happens."""
    proc = subprocess.Popen(
        [PY, "scripts/lmstudio_rewrite.py", "--from-audit", dir_name,
         "--next", str(n), "--live", "--model", model],
        cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace", bufsize=1)
    written, count, t0, t_page = [], 0, time.time(), time.time()
    for line in proc.stdout:
        line = line.rstrip()
        if line.startswith("-> "):
            count += 1
            t_page = time.time()
            stem = Path(line[3:].rstrip(" .")).stem
            done = len(written)
            eta = f", batch ETA ~{fmt((time.time() - t0) / done * (n - done))}" if done else ""
            print(f"  [{count}/{n}] {stem} ...{eta}", flush=True)
        elif "wrote" in line:
            written.append(Path(line.split("wrote", 1)[1].strip()).stem)
            print(f"        done in {fmt(time.time() - t_page)}", flush=True)
        elif line:
            print(f"  {line}", flush=True)
    proc.wait()
    return written, proc.returncode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="concepts", choices=["concepts", "entities"])
    ap.add_argument("--next", type=int, default=25, help="pages per batch")
    ap.add_argument("--batches", type=int, default=1, help="0 = until nothing left")
    ap.add_argument("--model", help="LM Studio model id (skips the interactive picker)")
    args = ap.parse_args()
    scope = f"{VAULT_REL}/{args.dir}"
    model = pick_model(args.model)
    print(f"using model: {model}")

    if any(l for l in git("status", "--porcelain", scope).stdout.splitlines() if l.strip()):
        sys.exit(f"{scope} has uncommitted changes -- commit or revert them first "
                 f"(the runner needs a clean scope to auto-revert failed batches).")

    baseline = dead_links()
    total_hard = fail_hard(args.dir)
    print(f"baseline dead links: {baseline} | fail-hard remaining in {args.dir}: {total_hard}")
    batch, pages_done, t_start = 0, 0, time.time()
    while args.batches == 0 or batch < args.batches:
        batch += 1
        print(f"\n=== batch {batch} ({args.dir}, {args.next} pages) ===")
        written, rc = stream_rewrite(args.dir, args.next, model)
        if not written:
            if rc != 0:
                sys.exit("server error before any page was written -- "
                         "check LM Studio is running, then rerun.")
            print("nothing left to process (all remaining pages deferred/reserved). done.")
            break

        print("  verifying ...", flush=True)
        links = dead_links()
        if links > baseline:
            print(f"VERIFY FAILED (dead links {baseline}->{links})")
            git("checkout", "--", scope)
            sys.exit("batch reverted, stopping. Investigate before rerunning.")
        baseline = links

        remaining = fail_hard(args.dir)  # also refreshes the worklist for the next pick
        # pages still fail-hard after their rewrite go to a skip list so the
        # picker never loops on them -- Claude finishes those by hand
        worklist = (ROOT / "settings/pending/prompts/quality-worklist.md").read_text(encoding="utf-8")
        hard_now = worklist.split("## fail-hard")[1].split("##")[0] if "## fail-hard" in worklist else ""
        stuck = [s for s in written if f"/{s}.md`" in hard_now]
        if stuck:
            with open(ROOT / "settings/pending/lmstudio-out/still-failing.md", "a", encoding="utf-8") as f:
                f.write("\n".join(stuck) + "\n")
            print(f"  {len(stuck)} pages still fail-hard after rewrite, "
                  f"skip-listed for Claude: {', '.join(stuck)}")
        git("add", "-A", scope)
        msg = (f"migrate(topics): lmstudio batch -- {written[0]}"
               + (f"-{written[-1]}" if len(written) > 1 else "")
               + f" ({len(written)} {args.dir})")
        git("commit", "-m", msg)
        pages_done += len(written)
        rate = (time.time() - t_start) / pages_done
        print(f"committed: {msg}")
        print(f"progress: {pages_done} pages this run at {fmt(rate)}/page | "
              f"fail-hard {total_hard} -> {remaining} | "
              f"~{fmt(rate * remaining)} to clear {args.dir} at this pace")
        if rc != 0:
            sys.exit("server error mid-batch -- written pages are committed; "
                     "check LM Studio is running, then rerun.")
    print("\nrun finished. Deferred items for Claude: settings/pending/lmstudio-out/deferred.md")


if __name__ == "__main__":
    main()
