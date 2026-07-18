"""File-lock shared by night_worker.py and local_night_worker.py so both can
run against the same source-drafts/sources-zotero pool at once without
redoing each other's pages. One lock file per page stem in .claims/;
atomic create is the mutex, no real distributed-lock machinery needed for
two local processes on the same filesystem.

ponytail: a crashed worker leaves its claim behind (no expiry/heartbeat) -
if a page seems stuck, delete its .claims/{stem}.lock by hand. Not worth
building staleness detection for two manually-supervised processes.
"""
import pathlib

REPO = pathlib.Path(__file__).resolve().parent.parent  # workers/ -> repo root
CLAIMS_DIR = REPO / ".claims"


def claim(stem: str) -> bool:
    """Atomically claim a page by stem. True if claimed here, False if
    another worker already holds it."""
    CLAIMS_DIR.mkdir(exist_ok=True)
    try:
        (CLAIMS_DIR / f"{stem}.lock").open("x").close()
        return True
    except FileExistsError:
        return False


def release(stem: str):
    (CLAIMS_DIR / f"{stem}.lock").unlink(missing_ok=True)
