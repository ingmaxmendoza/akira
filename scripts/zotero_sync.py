"""Zotero -> vault source-stub sync. The ONLY source ingest path (AKIRA-V3.md §5).

Reads a Better BibTeX JSON export (has citation keys, item keys, and PDF
attachment paths — plain CSL JSON has none of those), skips items already in
settings/core/zotero-bridge.md, and for each new item:
  - writes a stub to <vault>/sources/{author-year-slug}.md
  - appends a row to the bridge ledger
  - appends a line to settings/log/ingest.md

Dry-run by default; --live to write.
Usage:
    python scripts/zotero_sync.py                       # export path from rag.toml [zotero]
    python scripts/zotero_sync.py --export path.json --live
    python scripts/zotero_sync.py --self-test
"""
import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

import rag_utils as U

BRIDGE_REL = Path("settings/core/zotero-bridge.md")
INGEST_LOG_REL = Path("settings/log/ingest.md")


def load_export(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(data, list):
        sys.exit("This looks like a plain CSL JSON export — it has no Zotero keys or "
                 "PDF paths. Re-export from Zotero as 'Better BibTeX JSON'.")
    return data["items"]


def ledger_citekeys(bridge_path: Path) -> set[str]:
    if not bridge_path.is_file():
        return set()
    keys = set()
    for line in bridge_path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\|\s*([^|]+?)\s*\|", line)
        if m and m.group(1) not in ("citekey", "---"):
            keys.add(m.group(1))
    return keys


def first_author(item: dict) -> str:
    for c in item.get("creators", []):
        if c.get("creatorType") in (None, "author", "editor"):
            return c.get("lastName") or c.get("name") or ""
    return ""


def item_year(item: dict) -> str:
    m = re.search(r"\d{4}", str(item.get("date", "")))
    return m.group(0) if m else "n.d."


def make_stem(item: dict) -> str:
    author = U.slugify(first_author(item)) or "anon"
    title_slug = "-".join(U.slugify(item.get("title", "untitled")).split("-")[:4])
    return f"{author}-{item_year(item)}-{title_slug}".strip("-")


def find_pdf(item: dict) -> tuple[str, str]:
    """Return (pdf_path, storage_key). Empty strings when the item has no PDF."""
    for att in item.get("attachments", []):
        p = att.get("path", "")
        if p.lower().endswith(".pdf"):
            # ponytail: storage key = the PDF's parent folder name when it lives
            # in Zotero storage; falls back to the item key otherwise.
            parent = Path(p).parent.name
            key = parent if re.fullmatch(r"[A-Z0-9]{8}", parent) else item.get("itemKey", "")
            return p, key
    return "", item.get("itemKey", "")


def apa7(item: dict) -> str:
    # ponytail: minimal APA7 — authors (Family, I.), (year), title, container/publisher.
    # Upgrade path: citeproc-py if edge cases (editors, editions, DOIs) start to matter.
    names = []
    for c in item.get("creators", []):
        if c.get("creatorType") not in (None, "author"):
            continue
        if c.get("name"):
            names.append(c["name"])
        elif c.get("lastName"):
            initials = " ".join(f"{p[0]}." for p in (c.get("firstName") or "").split() if p)
            names.append(f"{c['lastName']}, {initials}".rstrip(", "))
    authors = ", ".join(names[:-1]) + (", & " if len(names) > 1 else "") + names[-1] if names else "Anon"
    tail = item.get("publicationTitle") or item.get("publisher") or ""
    apa = f"{authors} ({item_year(item)}). {item.get('title', 'Untitled')}."
    return f"{apa} {tail}." if tail else apa


def build_stub(item: dict, stem: str) -> str:
    pdf, zkey = find_pdf(item)
    citekey = item.get("citationKey", "")
    fm = [
        f"title: {json.dumps(item.get('title', 'Untitled'))}",
        "type: source",
        "tags: []",
        "related: []",
        "status: stub",
        f"zotero-key: {zkey}",
        f"citekey: {citekey}",
        f"pdf: {json.dumps(pdf) if pdf else '\"\"'}",
        f"apa7: {json.dumps(apa7(item))}",
        f"zotero-uri: zotero://select/items/@{citekey}",
    ]
    return ("---\n" + "\n".join(fm) + "\n---\n\n"
            f"# {item.get('title', 'Untitled')}\n\n"
            "## Summary\n\n*Stub — summary pending.*\n")


def sync(export_path: Path, live: bool) -> int:
    root = U.repo_root()
    cfg = U.load_config(root)
    vault = U.resolve_vault_path(cfg)
    sources = vault / "sources"
    bridge = root / BRIDGE_REL
    log = root / INGEST_LOG_REL
    known = ledger_citekeys(bridge)
    today = date.today().isoformat()
    new = 0
    for item in load_export(export_path):
        citekey = item.get("citationKey")
        if not citekey or citekey in known:
            continue
        stem = make_stem(item)
        if (sources / f"{stem}.md").exists():
            print(f"SKIP {citekey}: sources/{stem}.md already exists (not in ledger — reconcile)")
            continue
        new += 1
        print(f"{'WRITE' if live else 'WOULD WRITE'} sources/{stem}.md  ({citekey})")
        if live:
            (sources / f"{stem}.md").write_text(build_stub(item, stem), encoding="utf-8")
            with open(bridge, "a", encoding="utf-8") as f:
                f.write(f"| {citekey} | {stem} | {today} |\n")
            with open(log, "a", encoding="utf-8") as f:
                f.write(f"{today} | ingest | {stem} | zotero:{citekey}\n")
    print(f"{new} new item(s)" + ("" if live else " — dry run, use --live to write"))
    return new


def self_test():
    item = {
        "citationKey": "baudrillard1981simulacra", "itemKey": "ZZ99ZZ99",
        "title": "Simulacra and Simulation", "date": "1981", "publisher": "Galilée",
        "creators": [{"creatorType": "author", "lastName": "Baudrillard", "firstName": "Jean"}],
        "attachments": [{"path": r"C:\Zotero\storage\AB12CD34\baudrillard.pdf"}],
    }
    assert make_stem(item) == "baudrillard-1981-simulacra-and-simulation"
    assert find_pdf(item) == (r"C:\Zotero\storage\AB12CD34\baudrillard.pdf", "AB12CD34")
    assert apa7(item) == "Baudrillard, J. (1981). Simulacra and Simulation. Galilée."
    stub = build_stub(item, make_stem(item))
    assert "zotero-key: AB12CD34" in stub and "status: stub" in stub
    assert ledger_citekeys(Path("nonexistent")) == set()
    print("self-test OK")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--export", type=Path, help="Better BibTeX JSON export (default: rag.toml [zotero] export_path)")
    ap.add_argument("--live", action="store_true", help="write stubs, ledger, and log (default: dry run)")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        self_test()
        sys.exit(0)
    export = args.export or Path(U.load_config().get("zotero", {}).get("export_path", ""))
    if not export or not export.is_file():
        sys.exit("No export file: pass --export or set [zotero] export_path in settings/core/rag.toml")
    sync(export, args.live)
