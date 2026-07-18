"""Build/update the Akira RAG store (SQLite: pages, edges, chunks).

Dry-run by default; --live to write. Spec: settings/rag-minimal-mcp-design.md
Usage:
    python scripts/rag_index.py            # dry run: report what would change
    python scripts/rag_index.py --live     # incremental build
    python scripts/rag_index.py --rebuild --live
"""
import argparse
from datetime import datetime, timezone

import rag_utils as U

RELATION_FIELDS = {
    "related": "related_to",
    "challenges": "challenges",
    "challenged-by": "challenged_by",
}
SKIP_DIRS = {".obsidian", "indexes", "templates"}


def scan_pages(vault, include_folders):
    for folder in include_folders:
        base = vault / folder
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.md")):
            if any(part in SKIP_DIRS for part in path.relative_to(vault).parts):
                continue
            yield path


def page_type(meta, rel_path):
    t = meta.get("type")
    if t:
        return str(t)
    top = rel_path.parts[0]
    return top[:-1] if top.endswith("s") else top


def as_list(value):
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return [str(v) for v in value]


def index_vault(cfg, live: bool, rebuild: bool, embed_fn=None) -> dict:
    embed_fn = embed_fn or U.embed_texts
    vault = U.resolve_vault_path(cfg)
    con = U.open_db(cfg)
    model = cfg["lmstudio"]["embedding_model"]
    stored_model = dict(con.execute("SELECT key, value FROM meta")).get("embedding_model")
    if stored_model and stored_model != model and not rebuild:
        raise SystemExit(f"Embedding model changed ({stored_model} -> {model}); rerun with --rebuild --live")
    if rebuild and live:
        con.executescript("DELETE FROM pages; DELETE FROM edges; DELETE FROM chunks; DELETE FROM meta;")

    known = dict(con.execute("SELECT stem, content_hash FROM pages"))
    max_chars = cfg["index"]["chunk_max_chars"]
    overlap = cfg["index"]["chunk_overlap_chars"]
    prefix = cfg["lmstudio"].get("passage_prefix", "passage: ")
    stats = {"scanned": 0, "changed": 0, "deleted": 0, "chunks": 0}
    seen = set()

    for path in scan_pages(vault, cfg["index"]["include_folders"]):
        stats["scanned"] += 1
        stem = path.stem
        seen.add(stem)
        raw = path.read_text(encoding="utf-8", errors="replace")
        h = U.content_hash(raw)
        if known.get(stem) == h:
            continue
        stats["changed"] += 1
        if not live:
            print(f"would index: {path.relative_to(vault)}")
            continue

        meta, body = U.parse_frontmatter(raw)
        rel_path = path.relative_to(vault)
        title = next((l[2:].strip() for l in body.splitlines() if l.startswith("# ")), stem)
        tags = ",".join(as_list(meta.get("tags")))

        con.execute("DELETE FROM edges WHERE from_stem=?", (stem,))
        con.execute("DELETE FROM chunks WHERE page_stem=?", (stem,))
        con.execute(
            "INSERT OR REPLACE INTO pages(stem,path,type,title,tags,status,lang,content_hash,last_indexed)"
            " VALUES(?,?,?,?,?,?,?,?,?)",
            (stem, str(rel_path).replace("\\", "/"), page_type(meta, rel_path), title, tags,
             str(meta.get("status") or ""), str(meta.get("lang") or ""), h,
             datetime.now(timezone.utc).isoformat()))

        for field, rel in RELATION_FIELDS.items():
            for target in as_list(meta.get(field)):
                con.execute("INSERT OR IGNORE INTO edges VALUES(?,?,?,?)", (stem, target, rel, field))
        for target in U.extract_wikilinks(body):
            con.execute("INSERT OR IGNORE INTO edges VALUES(?,?,?,?)", (stem, target, "wikilinks_to", "body"))

        pieces = []  # (section, chunk_index, text)
        for section, text in U.split_sections(body):
            for i, chunk in enumerate(U.chunk_text(text, max_chars, overlap)):
                pieces.append((section, i, chunk))
        if pieces:
            vecs = embed_fn([p[2] for p in pieces], cfg, prefix)
            con.execute("INSERT OR REPLACE INTO meta VALUES('embedding_model',?)", (model,))
            con.execute("INSERT OR REPLACE INTO meta VALUES('embedding_dim',?)", (str(vecs.shape[1]),))
            for (section, i, chunk), vec in zip(pieces, vecs):
                con.execute(
                    "INSERT OR REPLACE INTO chunks VALUES(?,?,?,?,?,?,?)",
                    (f"{stem}|{section}|{i}", stem, str(rel_path).replace("\\", "/"),
                     section, i, chunk, vec.tobytes()))
            stats["chunks"] += len(pieces)
        con.commit()

    for stem in set(known) - seen:
        stats["deleted"] += 1
        if live:
            con.execute("DELETE FROM pages WHERE stem=?", (stem,))
            con.execute("DELETE FROM edges WHERE from_stem=?", (stem,))
            con.execute("DELETE FROM chunks WHERE page_stem=?", (stem,))
    con.commit()
    print(f"scanned={stats['scanned']} changed={stats['changed']} "
          f"deleted={stats['deleted']} new_chunks={stats['chunks']} live={live}")
    return stats


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Build/update the Akira RAG store")
    ap.add_argument("--live", action="store_true", help="actually write (default: dry run)")
    ap.add_argument("--rebuild", action="store_true", help="drop and rebuild everything")
    args = ap.parse_args()
    index_vault(U.load_config(), live=args.live, rebuild=args.rebuild)
