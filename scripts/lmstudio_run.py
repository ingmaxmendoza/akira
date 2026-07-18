"""One-command runner for the LM Studio rewrite pipeline.

  python scripts/lmstudio_run.py                      # 1 batch of 25 concepts
  python scripts/lmstudio_run.py --dir entities
  python scripts/lmstudio_run.py --batches 0          # run until nothing left
  python scripts/lmstudio_run.py --next 10 --batches 3

Per batch: rewrite N pages in place (lmstudio_rewrite.py --live) -> verify
(find_missing_pages no regression) -> commit.
On any regression: git-revert the scope and stop. Ctrl+C anytime; committed
batches stay, the in-flight one is simply uncommitted.
"""
# ponytail: subprocess glue around existing scripts, no parallelism, stop on first failure
import argparse, re, subprocess, sys
from pathlib import Path

from rag_utils import load_config, resolve_vault_path

ROOT = Path(__file__).resolve().parent.parent
VAULT_REL = resolve_vault_path(load_config()).relative_to(ROOT).as_posix()
PY = sys.executable


def run(*args, **kw):
    return subprocess.run([PY, *args], cwd=ROOT, capture_output=True,
                          text=True, encoding="utf-8", errors="replace", **kw)


def dead_links():
    out = run("scripts/find_missing_pages.py").stdout
    m = re.search(r"Done: (\d+) missing pages", out)
    return int(m.group(1)) if m else sys.exit("could not parse find_missing_pages output")


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="concepts", choices=["concepts", "entities"])
    ap.add_argument("--next", type=int, default=25, help="pages per batch")
    ap.add_argument("--batches", type=int, default=1, help="0 = until nothing left")
    args = ap.parse_args()
    scope = f"{VAULT_REL}/{args.dir}"

    if any(l for l in git("status", "--porcelain", scope).stdout.splitlines() if l.strip()):
        sys.exit(f"{scope} has uncommitted changes -- commit or revert them first "
                 f"(the runner needs a clean scope to auto-revert failed batches).")

    baseline = dead_links()
    print(f"baseline dead links: {baseline}")
    batch = 0
    while args.batches == 0 or batch < args.batches:
        batch += 1
        print(f"\n=== batch {batch} ({args.dir}, {args.next} pages) ===")
        out = run("scripts/lmstudio_rewrite.py", "--from-audit", args.dir,
                  "--next", str(args.next), "--live").stdout
        print(out.strip())
        written = re.findall(r"wrote .*[\\/](.+)\.md", out)
        if not written:
            print("nothing left to process (all remaining pages deferred/reserved). done.")
            break

        links = dead_links()
        if links > baseline:
            print(f"VERIFY FAILED (dead links {baseline}->{links})")
            git("checkout", "--", scope)
            sys.exit("batch reverted, stopping. Investigate before rerunning.")
        baseline = links

        run("scripts/audit_page_quality.py", "--dir", args.dir)  # refresh worklist for next pick
        git("add", "-A", scope)
        msg = (f"migrate(topics): lmstudio batch -- {written[0]}"
               + (f"-{written[-1]}" if len(written) > 1 else "")
               + f" ({len(written)} {args.dir})")
        git("commit", "-m", msg)
        print(f"committed: {msg} (dead links {links})")
    print("\nrun finished. Deferred items for Claude: settings/pending/lmstudio-out/deferred.md")


if __name__ == "__main__":
    main()
