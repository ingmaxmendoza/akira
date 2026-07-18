# Akira — an Obsidian-based Second Brain, maintained by AI agents

Akira is a template for an **Obsidian-based Second Brain** with **RAG and Zotero
integration**: a plain-markdown vault built and maintained by **local and cloud AI agents**
(Claude Code sessions and local LM Studio models) plus **deterministic Python scripts that
handle everything mechanical — minimizing token requirements** by reserving the LLM for
judgment calls only. The vault is queryable locally via a RAG store (SQLite + LM Studio
embeddings, exposed as an MCP server), and Zotero is the sole source-ingest pipeline.

<img width="1286" height="781" alt="image_2026-07-17_233204670" src="https://github.com/user-attachments/assets/e010ac74-4821-4af2-b809-01a004cf04ac" />


Three principles (full spec in [`MD/AKIRA-V3.md`](MD/AKIRA-V3.md)):

1. **Script-first** — anything mechanical (scanning, linking, indexing, auditing) is a script
   in `scripts/`. AI is used only where judgment is irreducible: writing prose, deciding
   merges, evaluating scope.
2. **Zotero-only sourcing** — Zotero is the sole ingest path for source material
   (`scripts/zotero_sync.py`).
3. **RAG store as first-class citizen** — the vault is locally searchable
   (vector + lexical + graph) and the index is rebuilt as part of normal maintenance.

## Repository layout

```
├── MD/            ← spec + agent work orders (the "prompts" agents run from)
│   ├── AKIRA-V3.md        ← canonical spec: page shapes, folder rules, everything
│   ├── SOURCES.md         ← sourcing spec (Zotero pipeline)
│   ├── FILL-SOURCES.md    ← work order: fill source stubs into full pages
│   ├── BUILD-TOPICS.md    ← work order: cluster sources into topic pages
│   ├── BUILD-CONCEPTS.md  ← work order: write concept pages from a topic
│   ├── BUILD-PEOPLE.md    ← work orders: entity pages (people/organizations/places)
│   ├── BUILD-ORGANIZATIONS.md
│   ├── BUILD-PLACES.md
│   └── BUILD-EXHIBITIONS.md
├── scripts/       ← deterministic tooling (see USAGE.md)
├── workers/       ← unattended overnight agent loops
├── settings/
│   └── core/rag.toml      ← THE config: vault paths, LM Studio models, chunking
├── akira/         ← the vault itself (gitignored; concepts/ entities/ sources/ topics/ …)
└── rag_store/     ← SQLite RAG index (gitignored, rebuilt by rag_index.py)
```

## Quick start

1. Clone, then create the vault skeleton:
   `mkdir akira akira/concepts akira/entities akira/sources akira/topics akira/notes akira/queries akira/indexes`
   and open `akira/` (the inner folder, not the repo root) in Obsidian.
2. Edit **`settings/core/rag.toml`** — set `repo_path`/`vault_path` to your clone, and the
   LM Studio embedding/chat models to what you have loaded. Every tool reads paths from this
   file; a few older scripts and the `MD/` work orders still contain absolute paths from the
   original machine — search for `C:\Users\` and replace with yours.
3. In Zotero, set up a **Better BibTeX auto-export** (JSON) once — it self-updates from
   then on. Point `[zotero] export_path` in `rag.toml` at it, then
   `python scripts/zotero_sync.py --live` to create source stubs.
4. Fill sources: run a Claude Code session with the `MD/FILL-SOURCES.md` work order — or let
   `workers/night_worker.py` do it unattended overnight.
5. Build the graph: `BUILD-TOPICS.md` → `BUILD-CONCEPTS.md`, with
   `scripts/find_missing_pages.py` catching broken wikilinks.
6. Index and search: `python scripts/rag_index.py --live`, then
   `python scripts/rag_search.py "your question"`. Hook `scripts/akira_mcp.py` into LM Studio
   for chat-with-your-vault.

## How the Zotero integration works

Two phases touch Zotero differently:

1. **Ingest (metadata → stubs), scripted, zero tokens.** `zotero_sync.py` reads the Better
   BibTeX JSON auto-export and writes one stub page per library item — citekey-based
   filename, Zotero storage key, attachment path, APA 7 citation — plus a ledger so reruns
   skip existing items. The export exists because BBT citekeys live in Better BibTeX's own
   database, not in `zotero.sqlite`; the auto-export is a one-time setup, not a per-run
   chore.
2. **Fill (content → full pages), agents read Zotero directly.** The agent takes the
   `zotero-key` from a stub's frontmatter and reads Zotero's own data folder — first the
   `.zotero-ft-cache` full-text extract inside `storage/{KEY}/` (covers PDFs and HTML
   snapshots), falling back to `pymupdf` extraction, and finally visual page reading for
   image-only scans (`split_pdf.py` chunks oversized ones). No export or API involved.

**Requirements:** Python 3.11+, [Claude Code](https://claude.com/claude-code),
[LM Studio](https://lmstudio.ai) with an embedding model, [Zotero](https://zotero.org) +
Better BibTeX, [Obsidian](https://obsidian.md) for browsing.

See **[USAGE.md](USAGE.md)** for the full script reference and the agent workflow.
