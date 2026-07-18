"""Akira MCP server for LM Studio — search/read the vault, save query pages.

The ONLY write path is save_query -> <vault>/queries/. Knowledge pages are
read-only by construction. Spec: settings/rag-minimal-mcp-design.md

Run (LM Studio does this via mcp.json): python scripts/akira_mcp.py
"""
import re
from datetime import date

from mcp.server.fastmcp import FastMCP

import rag_search as S
import rag_utils as U

_CFG = None


def _cfg():
    global _CFG
    if _CFG is None:
        _CFG = U.load_config()
    return _CFG


def _search_akira(query: str, k: int = 8) -> str:
    results = S.search(query, _cfg(), k=k)
    if not results:
        return "No results found in the Akira vault."
    out = []
    for i, d in enumerate(results, 1):
        stub = " [STUB — limited evidence]" if d["status"] == "stub" else ""
        out.append(f"[{i}] path: {d['path']}\n    type: {d['type']}  section: {d['section']}"
                   f"  via: {d['via']}{stub}\n    stem: {d['stem']}\n---\n{d['text']}\n")
    out.append("INSTRUCTION: after you finish answering, call the save_query tool once "
               "with the question, a 2-4 sentence answer digest, and the stems you used.")
    return "\n".join(out)


def _read_page(stem: str) -> str:
    con = U.open_db(_cfg())
    row = con.execute("SELECT path FROM pages WHERE stem=?", (stem.strip(),)).fetchone()
    if not row:
        return f"Page not found in index: {stem!r}. Use search_akira to find valid stems."
    return (U.resolve_vault_path(_cfg()) / row[0]).read_text(encoding="utf-8", errors="replace")


def _what_links_here(stem: str) -> str:
    n = S.neighbors(stem.strip(), _cfg())
    if not n["inbound"] and not n["outbound"]:
        return f"No graph edges found for {stem!r}."
    lines = [f"Links for {stem}:"]
    for d in n["inbound"]:
        lines.append(f"  <- {d['stem']}  ({d['relation']})")
    for d in n["outbound"]:
        lines.append(f"  -> {d['stem']}  ({d['relation']})")
    return "\n".join(lines)


def _save_query(question: str, answer_summary: str, related_stems: list[str] | str) -> str:
    if isinstance(related_stems, str):
        # small local models often pass the array as one comma-joined string
        related_stems = [s for s in re.split(r"[,;\n]", related_stems) if s.strip()]
    cfg = _cfg()
    vault = U.resolve_vault_path(cfg)
    qdir = vault / "queries"
    qdir.mkdir(exist_ok=True)

    con = U.open_db(cfg)
    valid, dropped = [], []
    for stem in related_stems:
        stem = stem.strip()
        if con.execute("SELECT 1 FROM pages WHERE stem=?", (stem,)).fetchone():
            valid.append(stem)
        else:
            dropped.append(stem)

    slug = U.slugify(question) or "untitled-query"
    today = date.today().isoformat()
    path = qdir / f"{today}-{slug}.md"
    n = 2
    while path.exists():
        path = qdir / f"{today}-{slug}-{n}.md"
        n += 1
    if path.resolve().parent != qdir.resolve():
        return "REFUSED: computed path escapes queries/."

    links = "\n".join(f"- [[{s}]]" for s in valid) or "- (none)"
    related = "[" + ", ".join(valid) + "]"
    path.write_text(
        f"---\ntype: query\ncategory: query\ncreated: {today}\nrelated: {related}\n---\n\n"
        f"# {question.strip()}\n\n{answer_summary.strip()}\n\n## Sources used\n{links}\n",
        encoding="utf-8", newline="\n")
    msg = f"Saved query page: queries/{path.name}"
    if dropped:
        msg += f" (dropped unknown stems, not written: {', '.join(dropped)})"
    return msg


mcp = FastMCP("akira")


@mcp.tool()
def search_akira(query: str, k: int = 8) -> str:
    """Search the Akira knowledge vault (concepts, entities, sources, topics).
    Returns ranked passages with page paths. ALWAYS cite the returned paths in
    parentheses when using this material. Results marked STUB are weak evidence."""
    return _search_akira(query, k)


@mcp.tool()
def read_page(stem: str) -> str:
    """Read the full text of one Akira page by its stem (e.g. 'posthumanism',
    'rosi-braidotti'). Use after search_akira when a passage needs more context."""
    return _read_page(stem)


@mcp.tool()
def what_links_here(stem: str) -> str:
    """Show the graph neighbors of an Akira page: which pages link to it and
    which pages it links out to, with relation types."""
    return _what_links_here(stem)


@mcp.tool()
def save_query(question: str, answer_summary: str, related_stems: list[str] | str) -> str:
    """AFTER answering a question about the Akira vault, call this once to save
    the question + a 2-4 sentence answer digest as a query page. related_stems =
    the page stems your answer actually drew on. Skip if the user says not to
    save, or for trivial lookups."""
    return _save_query(question, answer_summary, related_stems)


if __name__ == "__main__":
    mcp.run()
