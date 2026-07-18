"""Local night worker: fills Akira source pages using a local LM Studio
model instead of a Claude Code session. Companion to night_worker.py - no
Claude account/usage-limit involved, runs fully offline against whatever
chat model LM Studio has loaded.

Only handles pages with extractable text (pdftotext/pymupdf/.zotero-ft-cache
or HTML). Image-only PDFs needing visual reading are skipped and left for
night_worker.py (Claude Code can Read PDF pages as images; this script does
not, since it goes through the plain /v1/chat/completions text endpoint -
wiring qwen3-vl for that is a possible upgrade, not done here).

Safe to run at the same time as night_worker.py: both claim a page via
worker_common before starting it, so they never redo each other's work.

Stop with Ctrl+C or by creating a file named STOP_LOCAL next to this script
(kept separate from night_worker.py's STOP file on purpose).
"""
import datetime
import json
import pathlib
import re
import subprocess
import sys
import time
import urllib.request

import worker_common as W

AKIRA = pathlib.Path(__file__).resolve().parent.parent  # workers/ -> repo root
LOGS = AKIRA / "logs"
LOGS.mkdir(exist_ok=True)
STOP = AKIRA / "STOP_LOCAL"
LOG = LOGS / "local_night_worker.log"
ROOTS = ["source-drafts", "sources-zotero"]
ZOTERO_STORAGE = pathlib.Path(r"C:\path\to\ZoteroData\storage")  # TEMPLATE: set to your Zotero data dir's storage/ folder
LM_BASE = "http://localhost:1234/v1"
MAX_SOURCE_CHARS = 45000  # ponytail: crude context cap; raise if the loaded model's window allows more
PAUSE_BETWEEN_PAGES = 5  # seconds


def log(msg):
    line = f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} | {msg}"
    print(line)
    with open(LOG, "a", encoding="utf8") as f:
        f.write(line + "\n")


# --- LM Studio calls, same shape as lm.py ---

def pick_model():
    with urllib.request.urlopen(f"{LM_BASE}/models", timeout=10) as r:
        ids = [m["id"] for m in json.load(r)["data"]]
    return next(i for i in ids if "embed" not in i)


def ask(prompt, system=None, timeout=900):
    messages = ([{"role": "system", "content": system}] if system else []) + \
               [{"role": "user", "content": prompt}]
    body = json.dumps({"model": pick_model(), "messages": messages, "temperature": 0.2}).encode()
    req = urllib.request.Request(f"{LM_BASE}/chat/completions", body, {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)["choices"][0]["message"]["content"]


# --- page selection, same logic as night_worker.py ---

def has_todo(path: pathlib.Path) -> bool:
    return "TODO" in path.read_text(encoding="utf8", errors="ignore")


def next_claimed_page(skip):
    for root in ROOTS:
        for p in sorted((AKIRA / root).rglob("*.md")):
            if p in skip or not has_todo(p):
                continue
            if W.claim(p.stem):
                return p
    return None


def frontmatter_field(text, key):
    m = re.search(rf"^{key}:\s*(.+)$", text, re.MULTILINE)
    return m.group(1).strip().strip('"') if m else None


# --- text extraction, per SOURCES.md/FILL-SOURCES.md order (minus visual read) ---

def extract_text(page_text):
    zkey = frontmatter_field(page_text, "zotero-key")
    if zkey and zkey != "PENDING":
        cache = ZOTERO_STORAGE / zkey / ".zotero-ft-cache"
        if cache.is_file():
            text = cache.read_text(encoding="utf8", errors="ignore")
            if text.strip():
                return text

    attachment = frontmatter_field(page_text, "attachment")
    if not attachment:
        return None
    path = pathlib.Path(attachment.split(" | ")[0].strip())
    if not path.exists():
        return None

    if path.suffix.lower() == ".pdf":
        try:
            out = subprocess.run(["pdftotext", "-layout", str(path), "-"],
                                  capture_output=True, timeout=120, text=True, errors="ignore")
            if out.returncode == 0 and out.stdout.strip():
                return out.stdout
        except Exception:
            pass
        try:
            import fitz  # pymupdf
            doc = fitz.open(path)
            text = "\n".join(p.get_text() for p in doc)
            if text.strip():
                return text
        except Exception:
            pass
        return None  # image-only or unreadable -> leave for the Claude/visual worker

    if path.suffix.lower() in (".html", ".htm"):
        raw = path.read_text(encoding="utf8", errors="ignore")
        return re.sub("<[^>]+>", " ", raw)

    return None


SYSTEM_PROMPT = (
    "You fill in Akira vault source pages per MD/SOURCES.md / MD/FILL-SOURCES.md. "
    "Quality bar: Key ideas are 3-8 specific, citable claims in your own words "
    "(never chapter summaries or 'discusses X'); Quotes are 0-5, page-referenced "
    "where the source has pages, omit the section if nothing is quotable; "
    "Connections name >=2 real links this source supports/extends/contradicts. "
    "Never invent facts, quotes, or page numbers not present in the source text. "
    "A shorter honest page beats a padded one."
)


def build_prompt(page_text, source_text):
    return (
        "Fill this Akira vault source page draft. Return ONLY the complete "
        "replacement file content (frontmatter + body) - no commentary, no "
        "markdown code fences.\n\n"
        "Rules:\n"
        "- Replace the 'TODO' bullets under Key ideas / Connections with real content.\n"
        "- Delete the 'status: draft' frontmatter line entirely.\n"
        "- Keep title/tags/other frontmatter fields as-is unless clearly wrong.\n"
        "- No 'TODO' string may remain anywhere in your output.\n\n"
        f"CURRENT PAGE (draft):\n---\n{page_text}\n---\n\n"
        f"EXTRACTED SOURCE TEXT (truncated to {MAX_SOURCE_CHARS} chars):\n---\n"
        f"{source_text[:MAX_SOURCE_CHARS]}\n---\n"
    )


def looks_valid(text):
    return (text.strip().startswith("---")
            and "## Key ideas" in text
            and "TODO" not in text
            and "status: draft" not in text)


def strip_fences(text):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n|\n```$", "", text).strip()
    return text


n = 0
skip = set()  # pages this run couldn't extract text for or that failed sanity - don't loop forever
while not STOP.exists():
    page = next_claimed_page(skip)
    if page is None:
        STOP.write_text("all pages done, or all remaining need visual/Claude reading\n")
        break

    n += 1
    rel = page.relative_to(AKIRA)
    page_text = page.read_text(encoding="utf8", errors="ignore")
    log(f"[{n}] {rel} - extracting text")

    try:
        source_text = extract_text(page_text)
        if not source_text or len(source_text.strip()) < 200:
            log(f"[{n}] {rel} - no usable text (image-only PDF or missing attachment) - skipping for this run")
            skip.add(page)
            continue

        try:
            reply = strip_fences(ask(build_prompt(page_text, source_text), system=SYSTEM_PROMPT))
        except Exception as e:
            log(f"[{n}] {rel} - LM Studio call failed: {e} - skipping for this run")
            skip.add(page)
            time.sleep(PAUSE_BETWEEN_PAGES)
            continue

        if not looks_valid(reply):
            log(f"[{n}] {rel} - model output failed sanity check, leaving file untouched")
            skip.add(page)
            continue

        page.write_text(reply, encoding="utf8")
        log(f"[{n}] {rel} - DONE")
    finally:
        W.release(page.stem)
    time.sleep(PAUSE_BETWEEN_PAGES)

log(f"local night worker done: {n} pages attempted, "
    f"stop={'STOP_LOCAL file' if STOP.exists() else 'loop ended'}")
