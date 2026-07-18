"""Hybrid retrieval over the Akira RAG store: vector + lexical + 1-hop graph.

Usage:
    python scripts/rag_search.py "How does Braidotti connect to posthumanism?"
    python scripts/rag_search.py "query" -k 10 --show-scores
    python scripts/rag_search.py --self-test
"""
import argparse
import re
import sys

import numpy as np

import rag_utils as U

_CACHE: dict = {}

STEM_BOOST = 0.35
TAG_BOOST = 0.15
STUB_PENALTY = 0.10
GRAPH_FACTOR = 0.6
EXPAND_TOP_PAGES = 5


def _load(cfg):
    key = cfg["vault"]["repo_path"]
    if key not in _CACHE:
        con = U.open_db(cfg)
        rows = con.execute(
            "SELECT c.chunk_id, c.page_stem, c.path, c.section, c.chunk_index, c.text,"
            "       c.embedding, p.type, p.status, p.tags, p.title"
            " FROM chunks c JOIN pages p ON p.stem = c.page_stem").fetchall()
        if not rows:
            sys.exit("RAG store is empty — run: python scripts/rag_index.py --live")
        dim = int(dict(con.execute("SELECT key, value FROM meta"))["embedding_dim"])
        mat = np.frombuffer(b"".join(r[6] for r in rows), dtype=np.float32).reshape(len(rows), dim)
        _CACHE[key] = (con, rows, mat)
    return _CACHE[key]


def _tokens(text):
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def search(query, cfg, k=10, embed_fn=None):
    embed_fn = embed_fn or U.embed_texts
    con, rows, mat = _load(cfg)
    qvec = embed_fn([query], cfg, cfg["lmstudio"].get("query_prefix", "query: "))[0]
    sims = mat @ qvec
    qtok = _tokens(query)

    scored = []
    for i, r in enumerate(rows):
        (chunk_id, stem, path, section, ci, text, _,
         ptype, status, tags, title) = r
        score, via = float(sims[i]), "vector"
        stem_toks = _tokens(stem.replace("-", " "))
        if stem_toks and stem_toks <= qtok:
            score += STEM_BOOST
            via = "lexical"
        if tags and _tokens(tags.replace(",", " ")) & qtok:
            score += TAG_BOOST
        if status == "stub":
            score -= STUB_PENALTY
        scored.append({"stem": stem, "path": path, "type": ptype, "section": section,
                       "status": status, "text": text, "score": score, "via": via,
                       "chunk_index": ci})
    scored.sort(key=lambda d: d["score"], reverse=True)

    # one chunk per (stem, section)
    seen, primary = set(), []
    for d in scored:
        key = (d["stem"], d["section"])
        if key not in seen:
            seen.add(key)
            primary.append(d)

    # 1-hop graph expansion from top pages
    top_pages, page_scores = [], {}
    for d in primary:
        if d["stem"] not in page_scores:
            page_scores[d["stem"]] = d["score"]
            top_pages.append(d["stem"])
        if len(top_pages) >= EXPAND_TOP_PAGES:
            break
    have = {d["stem"] for d in primary[:k]}
    expanded = []
    for stem in top_pages:
        for col, where in (("to_stem", "from_stem"), ("from_stem", "to_stem")):
            q = f"SELECT DISTINCT {col} FROM edges WHERE {where}=?"
            for (nb,) in con.execute(q, (stem,)):
                if nb in have:
                    continue
                row = con.execute(
                    "SELECT c.text, c.path, p.type, p.status FROM chunks c"
                    " JOIN pages p ON p.stem=c.page_stem"
                    " WHERE c.page_stem=? AND c.section='intro' AND c.chunk_index=0", (nb,)).fetchone()
                if row:
                    have.add(nb)
                    expanded.append({"stem": nb, "path": row[1], "type": row[2],
                                     "section": "intro", "status": row[3], "text": row[0],
                                     "score": page_scores[stem] * GRAPH_FACTOR,
                                     "via": "graph", "chunk_index": 0})
    merged = sorted(primary[:k] + expanded, key=lambda d: d["score"], reverse=True)
    return merged[:k]


def neighbors(stem, cfg):
    con, _, _ = _load(cfg)
    out = [{"stem": t, "relation": r} for t, r in con.execute(
        "SELECT DISTINCT to_stem, relation_type FROM edges WHERE from_stem=?", (stem,))]
    inn = [{"stem": f, "relation": r} for f, r in con.execute(
        "SELECT DISTINCT from_stem, relation_type FROM edges WHERE to_stem=?", (stem,))]
    return {"outbound": out, "inbound": inn}


SELF_TEST = {
    "What is posthumanism?": "posthumanism",
    "Who is Rosi Braidotti?": "rosi-braidotti",
    "Tell me about Museo Marco": "museo-marco",
}


def self_test(cfg):
    failures = []
    for q, expected in SELF_TEST.items():
        stems = [d["stem"] for d in search(q, cfg, k=5)]
        ok = expected in stems
        print(f"{'PASS' if ok else 'FAIL'}  {q!r} -> expected {expected}, got {stems}")
        if not ok:
            failures.append(q)
    if failures:
        sys.exit(f"{len(failures)} self-test question(s) failed")
    print("self-test: all passed")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Search the Akira RAG store")
    ap.add_argument("query", nargs="?", help="question text")
    ap.add_argument("-k", type=int, default=10)
    ap.add_argument("--show-scores", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    config = U.load_config()
    if args.self_test:
        self_test(config)
    elif args.query:
        for d in search(args.query, config, k=args.k):
            score = f"  [{d['score']:.3f} {d['via']}]" if args.show_scores else ""
            print(f"- {d['path']} :: {d['section']}{score}")
            print(f"  {d['text'][:200].replace(chr(10), ' ')}")
    else:
        ap.print_help()
