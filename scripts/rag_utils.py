"""Shared utilities for the Akira RAG layer.

Spec: settings/rag-minimal-mcp-design.md
"""
import hashlib
import re
import sqlite3
import sys
import tomllib
from pathlib import Path

import numpy as np
import requests
import yaml

WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]")
SECTION_RE = re.compile(r"^##\s+(.+)")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_config(root: Path | None = None) -> dict:
    root = root or repo_root()
    with open(root / "settings" / "core" / "rag.toml", "rb") as f:
        return tomllib.load(f)


def resolve_vault_path(cfg: dict) -> Path:
    vault = Path(cfg["vault"]["vault_path"])
    if not (vault / "concepts").is_dir():
        sys.exit(f"REFUSING: {vault} does not look like the Akira vault "
                 "(no concepts/ inside). Check settings/core/rag.toml — "
                 "the vault is NESTED one level below the repo root.")
    return vault


def parse_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    try:
        meta = yaml.safe_load(parts[1]) or {}
        if not isinstance(meta, dict):
            meta = {}
    except yaml.YAMLError:
        meta = {}
    return meta, parts[2]


def extract_wikilinks(body: str) -> list[str]:
    seen, out = set(), []
    for m in WIKILINK_RE.finditer(body):
        stem = m.group(1).strip()
        if stem and stem not in seen:
            seen.add(stem)
            out.append(stem)
    return out


def split_sections(body: str) -> list[tuple[str, str]]:
    sections, current, name = [], [], "intro"
    for line in body.splitlines():
        m = SECTION_RE.match(line)
        if m:
            text = "\n".join(current).strip()
            if text:
                sections.append((name, text))
            name, current = m.group(1).strip(), []
        else:
            current.append(line)
    text = "\n".join(current).strip()
    if text:
        sections.append((name, text))
    return sections


def chunk_text(text: str, max_chars: int, overlap: int) -> list[str]:
    if len(text) <= max_chars:
        return [text] if text.strip() else []
    chunks, start = [], 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        if end < len(text):
            cut = text.rfind("\n", start, end)
            if cut > start + max_chars // 2:
                end = cut
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return chunks


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower().encode("ascii", "ignore").decode()).strip("-")
    return s[:60].rstrip("-")


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def embed_texts(texts: list[str], cfg: dict, prefix: str) -> np.ndarray:
    url = cfg["lmstudio"]["base_url"].rstrip("/") + "/embeddings"
    model = cfg["lmstudio"]["embedding_model"]
    out = []
    batch_size = 32
    for i in range(0, len(texts), batch_size):
        batch = [prefix + t for t in texts[i:i + batch_size]]
        r = requests.post(url, json={"model": model, "input": batch}, timeout=300)
        r.raise_for_status()
        data = sorted(r.json()["data"], key=lambda d: d["index"])
        out.extend(d["embedding"] for d in data)
    arr = np.asarray(out, dtype=np.float32)
    arr /= (np.linalg.norm(arr, axis=1, keepdims=True) + 1e-9)
    return arr


SCHEMA = """
CREATE TABLE IF NOT EXISTS pages(
    stem TEXT PRIMARY KEY, path TEXT NOT NULL, type TEXT, title TEXT,
    tags TEXT, status TEXT, lang TEXT, content_hash TEXT, last_indexed TEXT);
CREATE TABLE IF NOT EXISTS edges(
    from_stem TEXT NOT NULL, to_stem TEXT NOT NULL,
    relation_type TEXT NOT NULL, source_field TEXT NOT NULL,
    UNIQUE(from_stem, to_stem, relation_type, source_field));
CREATE TABLE IF NOT EXISTS chunks(
    chunk_id TEXT PRIMARY KEY, page_stem TEXT NOT NULL, path TEXT NOT NULL,
    section TEXT, chunk_index INTEGER, text TEXT NOT NULL, embedding BLOB);
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT);
CREATE INDEX IF NOT EXISTS idx_edges_from ON edges(from_stem);
CREATE INDEX IF NOT EXISTS idx_edges_to ON edges(to_stem);
CREATE INDEX IF NOT EXISTS idx_chunks_page ON chunks(page_stem);
"""


def open_db(cfg: dict) -> sqlite3.Connection:
    db_path = Path(cfg["vault"]["repo_path"]) / cfg["index"]["store_path"]
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    con.executescript(SCHEMA)
    return con
