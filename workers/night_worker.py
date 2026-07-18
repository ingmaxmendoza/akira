"""Night worker: launches Claude Code sessions in path/to/Akira one after
another so vault work continues unattended.

Two phases, run in order: (1) fill source pages that still have TODO, (2)
once sources are TODO-free, build concept pages out of the topic pages
(MD/BUILD-CONCEPTS.md), one topic per session. Falls through to phase 2
automatically - no separate invocation needed.

Safe to run at the same time as local_night_worker.py: both claim a page
via worker_common before starting it, so they never redo each other's work
(local_night_worker.py only ever does phase 1).

Claude Code has no scriptable API for the live 5-hour session-limit
percentage (checked --help/--debug/`/usage`), so rate limiting is handled
reactively: when a session's output contains the exact "hit your session
limit" message, the reset time is parsed out of it and the worker sleeps
until then instead of stopping for good - see wait_for_reset().

The user has explicitly authorized --dangerously-skip-permissions for these
sessions (all approval gates off). Stop the loop with Ctrl+C or by creating
a file named STOP next to this script (checked between sessions and during
any rate-limit wait).
"""
import re, subprocess, time, datetime, pathlib, sys

import worker_common as W

AKIRA = pathlib.Path(__file__).resolve().parent.parent  # workers/ -> repo root
LOGS = AKIRA / "logs"
LOGS.mkdir(exist_ok=True)
STOP = AKIRA / "STOP"
LOG = LOGS / "night_worker.log"
PAUSE_BETWEEN_SESSIONS = 30  # seconds
SESSION_TIMEOUT = 20 * 60  # seconds; a hung session gets killed, not left open
MAX_SESSIONS = int(sys.argv[1]) if len(sys.argv) > 1 else 50
ROOTS = ["source-drafts", "sources-zotero"]
TOPICS_DIR = AKIRA / "akira" / "topics"
CONCEPT_LOG = AKIRA / "MD" / "CONCEPT-LOG.md"
RATE_LIMIT_WAIT_FALLBACK = 30 * 60  # seconds; used if the reset time can't be parsed
RATE_LIMIT_WAIT_BUFFER = 2 * 60  # seconds past the parsed reset time, before retrying

SOURCE_PROMPT_TMPL = (
    "You are working unattended on the Akira vault sources. "
    "Read MD/FILL-SOURCES.md first and follow it exactly - it defines the text "
    "extraction order, the quality bar, and the boundaries. "
    "Your ONLY task this session is to completely fill this ONE page: {page} "
    "Do not touch any other page. When done, stop."
)

CONCEPT_PROMPT_TMPL = (
    "You are working unattended on the Akira vault. "
    "Read MD/BUILD-CONCEPTS.md first and follow it exactly - it defines what "
    "counts as a concept, the page shape, and the boundaries. "
    "Your ONLY task this session is to process this ONE topic: {topic} "
    "(topic page: akira/topics/{topic}.md). Write the concept page(s) it "
    "warrants (zero is a valid outcome), then append your line to "
    "MD/CONCEPT-LOG.md as instructed. Do not touch any other topic. When done, stop."
)


def log(msg):
    line = f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} | {msg}"
    print(line)
    with open(LOG, "a", encoding="utf8") as f:
        f.write(line + "\n")


def has_todo(path: pathlib.Path) -> bool:
    return "TODO" in path.read_text(encoding="utf8", errors="ignore")


def next_claimed_page(skip):
    # ponytail: naive first-match scan, fine at this file count. Claim is
    # attempted per candidate so a page held by local_night_worker.py gets
    # skipped in favor of the next one, not blocked on.
    for root in ROOTS:
        for p in sorted((AKIRA / root).rglob("*.md")):
            if p in skip or not has_todo(p):
                continue
            if W.claim(p.stem):
                return p
    return None


def any_todo_left(skip) -> bool:
    """True if a TODO page exists anywhere, even if currently claimed by
    the other worker - distinguishes "genuinely done" from "just locked"."""
    for root in ROOTS:
        for p in sorted((AKIRA / root).rglob("*.md")):
            if p not in skip and has_todo(p):
                return True
    return False


def logged_concept_topics() -> set:
    """Topic stems already processed, per CONCEPT-LOG.md's first column."""
    if not CONCEPT_LOG.exists():
        return set()
    done = set()
    for line in CONCEPT_LOG.read_text(encoding="utf8", errors="ignore").splitlines():
        parts = line.split("|")
        if len(parts) >= 2 and parts[0].strip()[:4].isdigit():  # a YYYY-... log line
            done.add(parts[1].strip())
    return done


def next_claimed_topic(skip, done):
    for p in sorted(TOPICS_DIR.glob("*.md")):
        if p in skip or p.stem in done:
            continue
        if W.claim(f"concept-{p.stem}"):
            return p
    return None


def any_topics_left(skip, done) -> bool:
    return any(p not in skip and p.stem not in done for p in sorted(TOPICS_DIR.glob("*.md")))


RATE_LIMIT_MARKERS = ("session limit", "rate_limit", "\"apiErrorStatus\":429")
RESET_TIME_RE = re.compile(r"resets\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)", re.IGNORECASE)


def wait_for_reset(out_text: str):
    """Sleep until the session limit resets (parsed from the CLI's own
    "resets 9pm (...)" message), or a fixed fallback if that can't be
    parsed. Polls in short chunks so STOP still works during the wait."""
    m = RESET_TIME_RE.search(out_text)
    if not m:
        log(f"rate limited but couldn't parse a reset time - waiting {RATE_LIMIT_WAIT_FALLBACK // 60} min and retrying")
        target = datetime.datetime.now() + datetime.timedelta(seconds=RATE_LIMIT_WAIT_FALLBACK)
    else:
        hour, minute, ampm = int(m.group(1)), int(m.group(2) or 0), m.group(3).lower()
        hour = (hour % 12) + (12 if ampm == "pm" else 0)
        now = datetime.datetime.now()
        target = now.replace(hour=hour % 24, minute=minute, second=0, microsecond=0)
        if target <= now:
            target += datetime.timedelta(days=1)
        target += datetime.timedelta(seconds=RATE_LIMIT_WAIT_BUFFER)
        log(f"rate limited - session resets {m.group(0)}, sleeping until {target:%Y-%m-%d %H:%M:%S}")

    while datetime.datetime.now() < target and not STOP.exists():
        time.sleep(min(120, max(1, (target - datetime.datetime.now()).total_seconds())))
    if STOP.exists():
        log("STOP file appeared during rate-limit wait - honoring it")
    else:
        log("rate-limit wait over - resuming")


def run_session(n, label, out_name, prompt):
    """Launches one Claude Code session, blocks until it exits or times
    out, returns (out_text, rate_limited, timed_out)."""
    out_file = LOGS / out_name
    log(f"session {n} starting | {label}")

    # ponytail: new visible console per session; /wait blocks until claude exits;
    # output is teed to a file too so we can detect rate-limit responses.
    proc = subprocess.Popen(
        f'start "Akira night session {n} - {label}" /wait cmd /c '
        f'claude --dangerously-skip-permissions --model sonnet -p '
        f'"{prompt}" 1^> "{out_file}" 2^>^&1',
        shell=True, cwd=AKIRA,
    )
    try:
        proc.wait(timeout=SESSION_TIMEOUT)
        exit_code = proc.returncode
        timed_out = False
    except subprocess.TimeoutExpired:
        subprocess.run(f"taskkill /PID {proc.pid} /T /F", shell=True,
                        capture_output=True)
        proc.wait()
        exit_code = "killed (timeout)"
        timed_out = True

    out_text = out_file.read_text(encoding="utf8", errors="ignore") if out_file.exists() else ""
    rate_limited = any(m.lower() in out_text.lower() for m in RATE_LIMIT_MARKERS)
    return out_text, rate_limited, timed_out, exit_code


def main():
    n = 0
    skip_pages = set()  # source pages that timed out this run - don't retry forever in one go
    skip_topics = set()  # same, for the concept phase
    while n < MAX_SESSIONS and not STOP.exists():
        page = next_claimed_page(skip_pages)
        if page is not None:
            n += 1
            rel = page.relative_to(AKIRA)
            out_text, rate_limited, timed_out, exit_code = run_session(
                n, f"page: {rel}", f"night_worker_session_{n}.out.log",
                SOURCE_PROMPT_TMPL.format(page=rel),
            )
            if timed_out:
                skip_pages.add(page)
            done = not has_todo(page)
            status = "RATE LIMITED" if rate_limited else "DONE" if done else "TIMEOUT - SKIPPED" if timed_out else "STILL HAS TODO"
            log(f"session {n} ended | page: {rel} | exit {exit_code} | {status}")
            W.release(page.stem)
            if rate_limited:
                wait_for_reset(out_text)
            else:
                time.sleep(PAUSE_BETWEEN_SESSIONS)
            continue

        if any_todo_left(skip_pages):
            log("no page claimable right now (locked by local_night_worker.py) - waiting")
            time.sleep(PAUSE_BETWEEN_SESSIONS)
            continue

        # source phase exhausted - fall through to concept building
        done_topics = logged_concept_topics()
        topic = next_claimed_topic(skip_topics, done_topics)
        if topic is not None:
            n += 1
            out_text, rate_limited, timed_out, exit_code = run_session(
                n, f"topic: {topic.stem}", f"night_worker_session_{n}.out.log",
                CONCEPT_PROMPT_TMPL.format(topic=topic.stem),
            )
            if timed_out:
                skip_topics.add(topic)
            logged = topic.stem in logged_concept_topics()
            status = "RATE LIMITED" if rate_limited else "LOGGED" if logged else "TIMEOUT - SKIPPED" if timed_out else "DID NOT LOG - SKIPPED"
            if not logged and not rate_limited:
                skip_topics.add(topic)  # ponytail: no log line = session didn't finish the work order, don't retry it this run
            log(f"session {n} ended | topic: {topic.stem} | exit {exit_code} | {status}")
            W.release(f"concept-{topic.stem}")
            if rate_limited:
                wait_for_reset(out_text)
            else:
                time.sleep(PAUSE_BETWEEN_SESSIONS)
            continue

        if any_topics_left(skip_topics, done_topics):
            log("no topic claimable right now - waiting")
            time.sleep(PAUSE_BETWEEN_SESSIONS)
            continue

        STOP.write_text("all pages and topics done\n")
        break

    log(f"night worker done: {n} sessions, stop={'STOP file' if STOP.exists() else 'max reached'}")


if __name__ == "__main__":
    main()
