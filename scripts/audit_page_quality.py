"""Audit vault pages against the Page Standard (re-order.md B).

Phase 0.6 of settings/re-order.md. Read-only; writes the tiered worklist to
settings/pending/prompts/quality-worklist.md (always — it is a report, not a
vault mutation). Tiers: fail-hard / fail-soft / stub / pass.

fail-hard: Spanish body without lang: es, missing required section,
           missing/malformed bold thesis.
fail-soft: word-floor failures, misordered sections, unresolvable typed stems.
stub:      frontmatter status: stub (legal, counted).
"""
import argparse
import re
import sys
from pathlib import Path

from rag_utils import WIKILINK_RE, load_config, parse_frontmatter, repo_root, resolve_vault_path

VAULT = resolve_vault_path(load_config())
OUT = repo_root() / "settings" / "pending" / "prompts" / "quality-worklist.md"

SPANISH_STOPWORDS = {
    "el", "la", "los", "las", "del", "una", "un", "unos", "unas", "que",
    "para", "como", "más", "mas", "según", "segun", "entre", "con", "por",
    "sus", "esta", "este", "estos", "estas", "sobre", "también", "tambien",
    "pero", "muy", "ser", "es", "son", "fue", "fueron", "hacia", "donde",
    "cuando", "porque", "desde", "hasta", "sin", "está", "están", "tiene",
    "tienen", "hay", "años", "año", "través", "cada", "todo", "todos",
}

# category -> ordered required H2 sections (B.3)
REQUIRED_SECTIONS = {
    "concept": ["Overview", "Key arguments", "Applications in this vault", "Sources"],
    "entity": ["Who / What", "Relevance to this vault"],
    "exhibition": ["Overview", "Works & artists", "Concepts at play", "Sources"],
    "source": ["Key concepts"],
    "topic": ["Overview", "Open questions"],
}

THESIS_FLOORS = {"concept": (15, 40), "entity": (15, 40), "exhibition": (15, 40),
                 "source": (20, 50), "topic": (15, 40)}

# (category, section) -> minimum word count (B.4, prose floors only)
SECTION_FLOORS = {
    ("concept", "Overview"): 120,
    ("concept", "Applications in this vault"): 40,
    ("entity", "Who / What"): 80,
    ("entity", "Relevance to this vault"): 60,
    ("exhibition", "Overview"): 80,
    ("topic", "Overview"): 150,
}

TYPED_FIELDS = ("topics", "authors", "developed-by", "derived-from")
H2_RE = re.compile(r"^##\s+(.+?)\s*$", re.M)
BOLD_RE = re.compile(r"\*\*(.+?)\*\*", re.S)


def words(text: str) -> list[str]:
    text = WIKILINK_RE.sub(lambda m: m.group(1).split("|")[-1], text)
    text = re.sub(r"^#+ .*$", "", text, flags=re.M)
    return re.findall(r"[\wáéíóúñü'-]+", text.lower())


def page_kind(path: Path, meta: dict) -> str | None:
    top = path.relative_to(VAULT).parts[0]
    if top == "topics":
        return "topic"
    if top == "sources":
        return "source"
    if top == "concepts":
        return "concept"
    if top == "entities":
        return "exhibition" if "exhibition" in (meta.get("tags") or []) else "entity"
    return None


def sections_of(body: str) -> list[tuple[str, str]]:
    parts = H2_RE.split(body)
    out = []
    for i in range(1, len(parts), 2):
        out.append((parts[i], parts[i + 1] if i + 1 < len(parts) else ""))
    return out


def audit(path: Path, all_stems: set) -> tuple[str, list[str]]:
    """Return (tier, issues)."""
    meta, body = parse_frontmatter(path.read_text(encoding="utf-8", errors="ignore"))
    kind = page_kind(path, meta)
    if kind is None:
        return "pass", []
    hard, soft = [], []

    if not meta:
        hard.append("no frontmatter")

    # B.1.1 language
    toks = words(body)
    if toks and meta.get("lang") != "es":
        ratio = sum(1 for t in toks if t in SPANISH_STOPWORDS) / len(toks)
        if ratio > 0.15:
            hard.append(f"spanish body ({ratio:.0%} stopwords, no lang: es)")

    # thesis: first bold run before the first H2
    intro = body.split("\n## ", 1)[0]
    m = BOLD_RE.search(intro)
    lo, hi = THESIS_FLOORS[kind]
    if not m:
        hard.append("missing bold thesis")
    else:
        n = len(words(m.group(1)))
        if not (lo <= n <= hi):
            soft.append(f"thesis {n} words (floor {lo}-{hi})")

    # B.3 sections present + ordered
    secs = sections_of(body)
    names = [s for s, _ in secs]
    req = REQUIRED_SECTIONS[kind]
    missing = [s for s in req if s not in names]
    if kind == "topic" and "<!-- generated -->" not in body:
        missing.append("<!-- generated --> marker")
    if missing:
        hard.append(f"missing sections: {', '.join(missing)}")
    else:
        idx = [names.index(s) for s in req if s in names]
        if idx != sorted(idx):
            soft.append("required sections out of order")

    # B.4 word floors per section
    for (k, sec), floor in SECTION_FLOORS.items():
        if k != kind:
            continue
        for name, text in secs:
            if name == sec and len(words(text)) < floor:
                soft.append(f"'{sec}' {len(words(text))} words (floor {floor})")

    # typed stems resolve
    for field in TYPED_FIELDS:
        vals = meta.get(field) or []
        if isinstance(vals, str):
            vals = [vals]
        bad = [str(v) for v in vals if str(v).strip() not in all_stems]
        if bad:
            soft.append(f"unresolvable {field}: {', '.join(bad)}")

    if meta.get("status") == "stub":
        return "stub", hard + soft
    if hard:
        return "fail-hard", hard + soft
    if soft:
        return "fail-soft", soft
    return "pass", []


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", help="vault subdir to audit (default: all content dirs)")
    args = ap.parse_args()

    dirs = [args.dir.strip("/")] if args.dir else ["concepts", "entities", "sources", "topics"]
    all_stems = {f.stem for d in ("concepts", "entities", "sources", "topics", "notes", "queries")
                 for f in (VAULT / d).rglob("*.md") if (VAULT / d).is_dir()}

    tiers = {"fail-hard": [], "fail-soft": [], "stub": [], "pass": []}
    for d in dirs:
        for f in sorted((VAULT / d).rglob("*.md")):
            tier, issues = audit(f, all_stems)
            tiers[tier].append((f.relative_to(VAULT).as_posix(), issues))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# Quality Worklist\n\nScope: {', '.join(dirs)}. "
             f"hard={len(tiers['fail-hard'])} soft={len(tiers['fail-soft'])} "
             f"stub={len(tiers['stub'])} pass={len(tiers['pass'])}\n"]
    for tier in ("fail-hard", "fail-soft", "stub"):
        lines.append(f"\n## {tier}\n")
        for rel, issues in tiers[tier]:
            lines.append(f"- `{rel}` — {'; '.join(issues) or '(declared stub)'}")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    print(f"fail-hard={len(tiers['fail-hard'])} fail-soft={len(tiers['fail-soft'])} "
          f"stub={len(tiers['stub'])} pass={len(tiers['pass'])} -> {OUT}")
    sys.exit(1 if tiers["fail-hard"] else 0)


if __name__ == "__main__":
    main()
