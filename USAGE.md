# Usage Guide

Two halves: **deterministic scripts** (this file, first part) and **agent workflows**
(second part). The rule from the spec: scripts do everything mechanical; agents only write
prose and make judgment calls.

Conventions shared by most scripts:

- **Dry-run by default, `--live` to write.** Run without flags first, read the report, then rerun with `--live`.
- All paths come from `settings/core/rag.toml` — configure that once.
- Run from the repo root: `python scripts/<name>.py`.

## Scripts

### Ingest (Zotero → vault)

| Script | What it does |
|---|---|
| `zotero_sync.py` | The **only** source ingest path. Reads the Better BibTeX JSON auto-export (`[zotero] export_path` in `rag.toml`), skips items already in the bridge ledger, writes a source stub per new item and logs it. Metadata only — agents read the actual PDFs/snapshots straight from Zotero's storage folder during filling (see README, "How the Zotero integration works"). |

### Graph maintenance

| Script | What it does |
|---|---|
| `find_missing_pages.py` | Lists wikilinks that point to no existing file. |
| `audit_page_quality.py` | Audits every page against the Page Standard; writes a tiered worklist (fail-hard / fail-soft / stub / pass). Feeds the LM Studio batch runners below. |

### RAG (local search)

| Script | What it does |
|---|---|
| `rag_index.py` | Builds/updates the SQLite RAG store (pages, edges, chunks + embeddings). `--live` incremental, `--rebuild --live` from scratch. |
| `rag_search.py` | Hybrid retrieval: vector + lexical + 1-hop graph. `-k N`, `--show-scores`, `--self-test`. |
| `rag_utils.py` | Shared library (config loading, chunking, LM Studio client). Not run directly. |
| `akira_mcp.py` | MCP server exposing search/read over the vault to LM Studio (or any MCP client). Only write path is saving query pages to `queries/`. |

### Local-model helpers (LM Studio)

| Script | What it does |
|---|---|
| `lm.py` | One-shot prompt to LM Studio: `python scripts/lm.py "prompt"` or pipe a file in. |
| `split_pdf.py` | Splits a big PDF into chunks that fit Claude's Read tool limits (20MB / 20 pages) — `python scripts/split_pdf.py "big.pdf"` writes `_partNN-of-MM.pdf` files next to the source. Used during source filling when an attachment is too large to read whole. Needs `pypdf`. |
| `lmstudio_rewrite.py` | Rewrites pages to the Page Standard with a local model — `--from-audit DIR` picks batches from `audit_page_quality.py`'s worklist, or pass `--files` / `--list`. **You must supply `settings/lmstudio-rewrite-prompt.md`** (not shipped): a markdown file with a `## SYSTEM PROMPT` heading followed by a fenced code block holding the rewrite system prompt. |
| `lmstudio_run.py` / `lmstudio-v2-run.py` | One-command batch runners: rewrite → verify → repeat. v2 adds live progress. |

## Agent workflow (Claude Code)

The `MD/` files are **work orders**: self-contained instructions a fresh Claude Code session
executes. The pattern — start a session in the repo root and say
*"Read MD/FILL-SOURCES.md and execute it"* (or BUILD-TOPICS, BUILD-CONCEPTS,
BUILD-EXHIBITIONS). Each order tells the agent which spec sections to read, what the page
shape is, and where the boundaries are. `MD/AKIRA-V3.md` is the canonical spec everything
defers to.

The build sequence for a new vault:

1. **FILL-SOURCES** — turn each Zotero stub into a full source page (summary, key ideas). The agent reads Zotero's storage folder directly — `.zotero-ft-cache` full text first, visual PDF reading for image-only scans — no export involved in this phase.
2. **BUILD-TOPICS** — cluster sources into topic pages with a synthesis paragraph.
3. **BUILD-CONCEPTS** — per topic, write concept pages for the distinct ideas its sources actually develop. One topic per session.
4. **BUILD-PEOPLE / BUILD-ORGANIZATIONS / BUILD-PLACES** — per topic, write the entity pages its sources actually ground: people, organizations, places. Same session shape as BUILD-CONCEPTS; all three log to `MD/ENTITY-LOG.md`.
5. **BUILD-EXHIBITIONS** — curated trails through the graph.

After any agent session, run the maintenance loop:
`find_missing_pages.py` → `rag_index.py --live`.

### Unattended overnight runs (`workers/`)

| Worker | What it does |
|---|---|
| `night_worker.py` | Launches Claude Code sessions back-to-back: phase 1 fills TODO sources, phase 2 builds concepts one topic per session. Parses Claude's rate-limit message and sleeps until reset instead of dying. Runs with `--dangerously-skip-permissions` — only use on a machine/repo you fully trust, since all approval gates are off. |
| `local_night_worker.py` | Same phase-1 work but via a local LM Studio model — no Claude usage consumed. Skips image-only PDFs (they need visual reading, left for Claude). |
| `worker_common.py` | File-lock library (`.claims/`, one lock file per page stem) so both workers can run simultaneously without redoing each other's pages. |

Stop any worker with **Ctrl+C** or by creating a file named `STOP` in the repo root
(checked between sessions and during rate-limit waits). A crashed worker leaves its claim
file behind — delete stale files in `.claims/` before restarting.
