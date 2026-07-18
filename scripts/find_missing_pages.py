"""Find wikilinks that have no corresponding .md file in the vault."""
import re
from pathlib import Path

VAULT = Path(__file__).parent.parent / "akira"
OUT = Path(__file__).parent.parent / "akira" / "indexes" / "missing-pages.md"
SKIP_DIRS = {".obsidian", "indexes", "templates"}  # match rag_index.py's SKIP_DIRS

link_re = re.compile(r"\[\[([^\]|#]+)(?:\|[^\]]*)?\]\]")


def slug(name: str) -> str:
    return name.strip().lower().replace(" ", "-")


def main():
    md_files = [
        f for f in VAULT.rglob("*.md")
        if not any(p.name.startswith(".") or p.name in SKIP_DIRS for p in f.parents)
        and f != OUT
    ]

    # existing pages: stem as-is and lowercased slug
    existing = set()
    for f in md_files:
        existing.add(f.stem)
        existing.add(f.stem.lower())
        existing.add(slug(f.stem))

    missing: dict[str, list[str]] = {}  # target -> [source files]

    print(f"Scanning {len(md_files)} files…", flush=True)
    for i, f in enumerate(md_files, 1):
        if i % 200 == 0:
            print(f"  {i}/{len(md_files)} scanned…", flush=True)
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for m in link_re.finditer(text):
            target = m.group(1).strip()
            target_slug = slug(target)
            if target_slug not in existing and target not in existing:
                missing.setdefault(target_slug, []).append(f.name)

    # write report
    OUT.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Missing Pages\n",
        f"_Generated from {len(md_files)} files — {len(missing)} unresolved links_\n\n",
        "| Page | Referenced in |\n",
        "|------|---------------|\n",
    ]
    for target in sorted(missing):
        sources = ", ".join(f"[[{s[:-3]}]]" for s in sorted(set(missing[target])))
        lines.append(f"| [[{target}]] | {sources} |\n")

    OUT.write_text("".join(lines), encoding="utf-8")
    print(f"Done: {len(missing)} missing pages -> {OUT}")


if __name__ == "__main__":
    main()
