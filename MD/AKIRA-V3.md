# Akira V3 — Canonical Specification

**This document is the single source of truth for the Akira V3 vault: how it works, its structures, its tooling, and its rules.**

Written: 2026-07-08. Revised 2026-07-14 after the first real build pass (198
sources filled and promoted, 17 topics, first concept/entity pages) — several
sections below were originally aspirational and are now corrected against
what was actually built. Sections marked **[NOT YET BUILT]** describe design
intent that hasn't been implemented.

---

## 1. What Akira Is

Akira is a **personal knowledge wiki**: a plain-markdown vault curated by the User, maintained with Claude Code plus deterministic Python scripts, and browsed in Obsidian. There is **no central research topic** — the vault is deliberately a mixed corpus. The value is the **graph of wikilinks between all of it**.

**Language policy:** vault and tooling are English-only. Spanish appears only in culturally-untranslatable stems (`corrido-tumbado`), pages marked `lang: es`, and direct quotations inside "".

Three principles govern everything in V3:

1. **Script-first** — anything mechanical (scanning, matching, linking, indexing, auditing) is done by a script in `scripts/`. AI is used only where judgment is irreducible: writing prose, deciding merges, evaluating scope. If a needed operation has no script, write one and keep it.
2. **Zotero-only sourcing** — Zotero is the **sole method of source collection and the only place sources are ingested from**. See §5. There is no other inbox for source material.
3. **The RAG store is a first-class citizen** — the vault is queryable locally (vector + lexical + graph retrieval) via LM Studio, and the index is rebuilt as part of normal maintenance. See §6.

---

## 2. Repository Layout

The git repo root and the vault are **separate levels**: Obsidian opens the inner folder only, and **every tool must read the vault path from `settings/core/rag.toml`, never guess it**.

```
Akira/                      ← git repo root
├── MD/                        ← all top-level docs, incl. this file
│   ├── AKIRA-V3.md               ← this file (canonical doc)
│   ├── SOURCES.md                ← sourcing spec (§5 supersedes AKIRA-V3.md where they differ)
│   ├── FILL-SOURCES.md           ← the source-filling work order (98% complete as of 2026-07-14)
│   ├── FILL-LOG.md               ← append-only log of fill sessions
│   ├── BUILD-TOPICS.md           ← the topic-building work order (superseded by the folder-derived
│   │                                promotion approach - kept as historical process notes)
│   └── topics.md                 ← SUPERSEDED, kept for reference only. Do NOT use as the topic
│                                    authority (§4.1) - topics are derived from source folder
│                                    structure during promotion, not from this file.
├── akira/                     ← THE VAULT (open this folder in Obsidian)
│   ├── concepts/              ← abstract ideas, theories, frameworks
│   ├── entities/
│   │   ├── people/            ← artists, theorists, musicians, practitioners
│   │   ├── organizations/     ← museums, labels, collectives
│   │   ├── exhibitions/       ← exhibitions/biennials/campaigns, own category (§3.1)
│   │   └── places/            ← venues, cities, regions
│   ├── sources/               ← one page per promoted source (flat, no subfolders)
│   ├── topics/                ← broad thematic clusters, one per source-folder cluster (§4.1)
│   ├── notes/                 ← personal notes (class, meeting, reflection, research,
│   │                            brainstorm, idea) — stem YYYY-MM-DD-slug
│   ├── queries/               ← RAG answer digests written by the MCP save_query tool
│   │                            (the ONLY machine-written content folder) [NOT YET BUILT: no
│   │                            akira_mcp.py session has run against this vault yet]
│   ├── templates/             ← one template per category: source, topic, concept, person,
│   │                            organization, place, exhibition, piece (concept-schema
│   │                            variant), query, note-{brainstorm,class,idea,
│   │                            meeting,reflection,research}
│   ├── indexes/               ← GENERATED — scripts own this folder, never hand-edit
│   │   └── missing-pages.md   ← dead-wikilink tracker (find_missing_pages.py); by-tag/
│   │                            by-category/by-topic/master.md are NOT YET BUILT
│   └── .obsidian/
├── workers/                   ← unattended fill-orchestration (not part of the original design;
│   │                            built to get the 198-source fill work order done)
│   ├── night_worker.py           ← loops spawning `claude -p` sessions, one page per session;
│   │                                handles rate-limit detection, session timeouts, and
│   │                                coordinates with local_night_worker.py via worker_common
│   ├── local_night_worker.py     ← same loop, but calls LM Studio directly instead of Claude -
│   │                                text-only, skips image-only PDFs (left for night_worker.py)
│   └── worker_common.py          ← shared claim/release file-lock (.claims/) so both workers can
│                                    run simultaneously without redoing each other's pages
├── settings/
│   └── core/
│       ├── rag.toml           ← vault paths, LM Studio endpoint, chunking/retrieval params
│       └── tags.md            ← the tag registry (§4) - built 2026-07-17
│                                 (relations.md, zotero-bridge.md, dup-whitelist.md, pending/,
│                                 log/, archive/ are all still [NOT YET BUILT])
├── rag_store/
│   └── akira.sqlite           ← RAG index (pages, edges, chunks) — regenerable, gitignored
├── logs/                      ← night_worker.log, local_night_worker.log, per-session out logs
├── .claims/                   ← worker_common's page-lock files (transient, empty when idle)
├── scripts/                   ← Python maintenance layer (§7)
└── lm.py                      ← one-shot LM Studio prompt offload helper
```

There is deliberately nothing else beyond `workers/`: no manager app, no server, no file inbox.
`workers/` is scaffolding for one-time unattended catch-up work, not a permanent service.

---

## 3. Data Model

### 3.1 Page categories

Every page belongs to **exactly one category**, filed by the TYPE of thing, not the subject:

| Category | Folder | Stem format | Example |
|---|---|---|---|
| concept | `concepts/` | `kebab-case` | `hyperreality` |
| entity/person | `entities/people/` | `firstname-lastname` | `rosi-braidotti` |
| entity/organization | `entities/organizations/` | `org-name` | `museo-jumex` |
| entity/place | `entities/places/` | `place-name` | `barrio-antiguo` |
| entity/exhibition | `entities/exhibitions/` | `{slug}-{year}` | `teresa-margolles-como-salimos-2026` |
| source | `sources/` | `author-year-slug` (from Zotero citekey) | `baudrillard-1981-simulacra` |
| topic | `topics/` | `topic-slug` | `posthumanism-and-technology` |
| note | `notes/` | `YYYY-MM-DD-slug` | `2026-07-08-marco-visit` |
| query | `queries/` | `YYYY-MM-DD-slug` | machine-written only |

Exhibitions/biennials/campaigns get their **own category**, `entity/exhibition`, filed under `entities/exhibitions/` (not `organizations/` — revised 2026-07-17; originally specified as an organization subtype, split out once the vault started building individual piece pages that needed a clean parent to link to). Tag with `exhibition`/`biennial`/`group-show`/`solo-show`/`institutional` as appropriate.

Individual artworks/pieces within an exhibition get a **concept-schema variant** page (`type: concept`, `templates/piece.md`, filed in `concepts/`, stem `{piece-slug}-{artist-slug}` for disambiguation, e.g. `la-promesa-margolles`) — an artwork is a concrete made thing rather than an abstract idea, but reuses the `concept` category rather than adding a new top-level one. `piece.md` adds optional frontmatter (`artist`, `exhibition`, `medium`, `year`) that other concept pages don't carry.

Disambiguation: theorist's *ideas* → concept page for the idea + entity page for the person. Practitioner → one entity page covers the work. Ambiguous person-vs-organization → file by what the vault actually tracks about them.

### 3.2 Stems and naming

- Lowercase kebab-case; no spaces, accents, or special characters.
- English unless culturally untranslatable (`corrido-tumbado`, `nueva-cancion`). Spanish-primary pages carry `lang: es` and can be displayed bilingually via alias: `[[braidotti-2013-posthumano|Lo Posthumano]]`.
- Source stems derive from the Zotero citekey (`author-year-slug`). Spanish-language sources keep the Spanish slug.

### 3.3 Frontmatter (the machine-readable layer)

`settings/core/relations.md` is the single authority for the full per-category schema. Fields every tool must handle:

```yaml
---
title: Hyperreality            # display title
type: concept                  # matches folder category
tags: [semiotics, critical-theory]  # 3-10, all from the registry
topics: [philosophy-of-aesthetics] # topic membership (semantic hierarchy)
related: [simulacra, jean-baudrillard]  # graph backbone beyond inline wikilinks
challenges: []                 # contradiction tracking — always added in pairs,
challenged-by: []              #   same session, never deferred
lang: es                       # only on Spanish-primary pages
status: stub                   # stub | (absent = full) | archived
---
```

Source pages additionally carry:

```yaml
zotero-key: ABC123XY           # Zotero storage key — REQUIRED, no `none` value
citekey: baudrillard1981       # Better BibTeX citekey
pdf: C:\...\Zotero\storage\ABC123XY\file.pdf  # from the Zotero export
apa7: "Baudrillard, J. (1981). ..."           # formatted citation
zotero-uri: zotero://select/items/@baudrillard1981
```

Archived pages: `status: archived`, `archived: YYYY-MM-DD`, `archive-reason:`, `replaced-by:`.

A complete concept page, for reference:

```markdown
---
title: Hyperreality
type: concept
tags: [semiotics, media-theory]
topics: [philosophy-of-aesthetics]
related: [simulacra, jean-baudrillard, consumer-culture]
challenged-by: [eco-1986-travels]
---

# Hyperreality

A condition in which the simulation of reality becomes more real than
reality itself, developed by [[jean-baudrillard]] in
[[baudrillard-1981-simulacra]].

## Key ideas

- The map precedes the territory ...

## Connections

- Grounds the reading of [[la-petite-mort-2024]]'s staged mourning ...
```

Every page follows this shape: frontmatter → `# Title` → `##` sections with inline `[[wikilinks]]`. The `##` sections matter mechanically — they are the RAG chunk boundaries (§6).

### 3.4 Page anatomy

- `##` sections structure the body; the RAG chunker splits on them.
- Bare mentions of existing pages become `[[wikilinks]]`.
- Source pages carry a script-maintained **"Cited In"** section — never hand-edited.
- Stub pages (`status: stub`) are allowed but tracked; the health checker grades them down and the RAG layer penalizes and labels them in results.

---

## 4. Tags

`settings/core/tags.md` is the **single authority** — built 2026-07-17 from an earlier vault's registry, adapted to this vault's `type:`/`status:` frontmatter (which made a few old tags redundant) and to what the current 227-page corpus actually needed after a full bulk-tagging pass.

- **7 parent groups**: `art`, `music`, `theory`, `culture`, `geography`, `methodology`, `engineering`, plus a small `exhibition-type` group for the entity-tagging case in §3.1; **66 child tags** as of the 2026-07-17 pass (down from an initial ~70 candidates — a few were dropped for redundancy or for false-matching unrelated vocabulary, see tags.md's own notes). Machine-readable format: `## parent` headings, then `- child: definition` lines — scripts parse it directly.
- **Rules:**
  1. A tag not in the registry is a violation — no undeclared tags, ever.
  2. **Max 10 tags per page**, minimum 3 where the page's content genuinely supports it (thin pages may honestly carry fewer — never pad to hit the floor).
  3. **A tag must be used on at least 3 pages to remain in the registry** — a tag that lands under 3 after tagging gets folded into a broader tag or dropped, not kept as a one-off. Checked whenever a bulk pass or new-tag proposal runs.
  4. Use the most specific tag; never parent + child together.
  5. Tags describe *category, not content* (a page about a corrido is tagged `corrido`, not restated in tags).
  6. Geography tags signal cultural context, not mere location.
  7. A brand-new tag may only be added if it will genuinely apply to 3+ existing pages — propose it, add it to the registry with a definition first, *then* tag the pages, same session (registry-first ordering, same principle as topic naming in §4.1).
- Adding a tag = editing the registry first (with definition), then tagging pages, then regenerating `indexes/by-tag/`.
- The **tag → topic map** (in `relations.md`) links registry tags to topic pages so `topics:` frontmatter can be assigned/audited by script.
- **Bulk tagging method**: embed each page's title+intro+key-ideas against every registry tag's definition (LM Studio, same approach as topic assignment in §4.1), then rank by *per-tag z-score* rather than raw cosine similarity — raw cosine alone is nearly flat across a ~70-tag registry (most tags clear a low floor for every page), so z-score corrects for tags that sit in a generically "central" region of embedding space. Dry-run by default; `--live` writes. Even after tuning, expect a modest error rate on thin/edge-case pages (entity stubs, admin notes) — spot-check a sample before trusting a bulk run wholesale, the same way the 2026-07-17 pass needed manual correction on the entity pages and on two tags (`ambient`, `listening-practice`) that turned out to be lexical-collision magnets.

### 4.1 Topic registry — CORRECTED, differs from the original design

**`MD/topics.md` is NOT the topic authority.** The original design (a curated
candidate-topic registry, edited by hand before any topic page could exist)
never matched how sources actually arrived: they came in pre-organized by
Zotero collection / inbox folder (`{cluster-name}-2026-tec/`), and that
folder structure IS the real topic boundary — reusing it is simpler and more
accurate than maintaining a parallel abstract list. `MD/topics.md` is kept
only as a historical snapshot of early candidate-topic brainstorming; treat
it as dead.

**The real mechanism**, implemented in the promotion step:

1. `FOLDER_TOPIC` maps each source-drafts/sources-zotero top-level folder to
   a topic stem (stripping course-code suffixes like `-2026-tec`; merging
   language variants, e.g. `posthumanismo-2026-tec` → `posthumanism`).
2. One folder (`museo-marco-2026-tec`) has real per-exhibition subfolders;
   `topic_for()` special-cases it to use the subfolder (one topic per
   exhibition) instead of the top-level folder, plus a general `museo-marco`
   umbrella topic a source can *also* carry alongside its specific exhibition
   topic (multi-topic membership is normal, not an error).
3. Two folders (`personal-work-2026-tec`, `reference-misc-2026-tec`) are
   deliberately **not** mapped — provenance/reference material (a CV, a
   soldering report, a depression inventory) isn't a real synthesis topic;
   forcing one manufactures fake coherence. Those sources carry `topics: []`.
4. A cluster needs **≥2 member sources** to get a topic page
   (`MIN_TOPIC_SIZE`) — a single source is a source, not a cluster. Below
   that threshold, `topics:` is cleared rather than forcing a one-member
   "synthesis."
5. Topic page synthesis paragraphs are **written by hand (Claude), not by
   any model** — an earlier version called LM Studio for this and it proved
   unreliable, silently clobbering good prose with `(LM Studio call failed:
   timed out)` on every rerun since the script originally regenerated every
   topic page unconditionally. Current behavior: a new topic gets a `TODO`
   placeholder page (synthesis written by hand from there); an existing
   topic's `## Sources` list is refreshed in place on rerun, but its
   synthesis paragraph is never touched.

New topics found by other means (not tied to a source-drafts folder) still
follow the tags ordering principle: name it, create the page, then assign
`topics:` — the promotion mechanism is specific to the fill-work
pipeline, not the only legal way to add a topic.

---

## 5. Sources — Zotero Is the Only Pipeline

**Zotero is the ONLY method of collecting sources and the ONLY place sources are ingested from.** No raw-PDF inbox, no drag-a-file-into-the-repo, no ad-hoc source stubs from URLs. If something deserves to be a source, it goes into Zotero first (with its PDF/snapshot attached there); the vault only ever mirrors Zotero.

### 5.1 Division of responsibility

| Concern | Owner |
|---|---|
| PDFs, snapshots, attachments | Zotero storage — **never in the vault or repo** |
| Bibliographic metadata | Zotero (exported as **Better BibTeX JSON** — it carries citekeys, item keys, and PDF paths; never committed) |
| Citekeys | Better BibTeX in Zotero |
| Vault representation | One thin metadata stub per item in `sources/` |
| Dedup ledger | `settings/core/zotero-bridge.md` — `citekey \| vault-stem \| imported-date`, script-written, prevents double import |

### 5.2 Ingest flow (the only source workflow)

1. **Collect in Zotero** — save the item via the Zotero connector / manual entry; attach the PDF there; file it in a collection.
2. **Export** — Better BibTeX JSON export of the library (or collection, ideally as a BBT auto-export) to a gitignored path the scripts read (`[zotero] export_path` in `rag.toml`, or `--export`).
3. **Sync stubs** — `zotero_sync.py` reads the export and, for each item whose citekey is not in `zotero-bridge.md`: creates the `sources/` stub with full frontmatter (`zotero-key`, `citekey`, `apa7`, `pdf`, `zotero-uri`, `status: stub`), appends the bridge ledger row, and appends to `settings/log/ingest.md`. Dry-run by default; `--live` to write.
4. **Connect** — the human/AI-writer links the new stub from at least one existing page (`related:` or inline), adds `challenges`/`challenged-by` pairs if the source critiques something already in the vault, assigns tags and topics.
5. **Commit** — `ingest(sources): ...`.

Consequences of Zotero-only:

- Every source page has a real `zotero-key`; there is no `zotero-key: none` escape hatch. A source that isn't in Zotero doesn't exist yet.
- There is no PDF-"matching" step: the stub is born with its `pdf:` path from the export.
- Professor handouts, exhibition catalogs, scanned documents — all enter through Zotero (manual item + attachment), or they are not sources. Material that isn't a source (photos, personal files) simply doesn't enter the repo.

**Known deviation (as of 2026-07-14):** the first 198-page fill batch went
through a different, ad-hoc pipeline (`MD/FILL-SOURCES.md`): a manual
`path\to\zotero-inbox\{cluster}\` staging area, split into `source-drafts/`
(no real Zotero item yet, `zotero-key: PENDING`) and `sources-zotero/` (real
Zotero items with real keys), filled by `workers/night_worker.py` and
`workers/local_night_worker.py`, then promoted into `akira/sources/`.
**Many promoted source pages still carry
`zotero-key: PENDING`**, which technically violates invariant §8.5. This is
tracked debt, not resolved: `zotero_sync.py`'s real `zotero.sqlite`-reading
flow (per §5.2 above) was never actually run against this vault. A future
session should reconcile the PENDING sources against the real Zotero
library and backfill real keys.

---

## 6. The RAG Layer

The vault is locally queryable through a hybrid retrieval stack served to LM Studio via MCP. Everything runs offline; no cloud calls.

### 6.1 Components

| Piece | File | Role |
|---|---|---|
| Config | `settings/core/rag.toml` | Vault paths (**the** path authority), LM Studio endpoint, embedding + chat model names, nomic task prefixes, chunking and retrieval parameters |
| Store | `rag_store/akira.sqlite` | Three tables — `pages` (stem, type, status, tags, title), `edges` (typed relations: `related_to`, `challenges`, `challenged_by`, plus wikilinks), `chunks` (text + embedding blob per `##` section, max 1600 chars, 200 overlap) — plus `meta` (embedding dim etc.). Fully regenerable; gitignored. |
| Indexer | `scripts/rag_index.py` | Scans `concepts, entities, sources, topics, notes, queries` (skips `.obsidian`, `indexes`, `templates`), parses frontmatter, chunks by section, embeds via LM Studio `/v1/embeddings`. Incremental by content hash; dry-run default, `--live` to write, `--rebuild` for full re-embed. |
| Retriever | `scripts/rag_search.py` | Hybrid scoring: vector similarity (24 initial candidates) + lexical stem/tag boosts (+0.35 stem, +0.15 tag) + 1-hop graph expansion over `edges` (×0.6 factor) − stub penalty (−0.10); returns top 10. Also a CLI (`--show-scores`, `--self-test`). |
| Shared lib | `scripts/rag_utils.py` | Config loading, **vault-path sanity check** (refuses to run if the path doesn't contain `concepts/` — the nested-path guard), frontmatter/wikilink parsing, DB and embedding helpers. |
| MCP server | `scripts/akira_mcp.py` | Exposes to LM Studio: `search_akira` (retrieval with stub labels + an instruction to log the query), `read_page` (full page by stem), `save_query` (writes an answer digest to `queries/`). **`save_query` is the ONLY write path; knowledge pages are read-only by construction.** **[UNVERIFIED]** — never actually connected to LM Studio's `mcp.json` and run against this vault; `queries/` is empty. |
| PDF splitter | `scripts/split_pdf.py` | Splits oversized PDF attachments into `_partNN-of-MM.pdf` chunks that fit Claude's Read tool limits (20MB / 20 pages), for the fill pipeline's visual-reading path (`pypdf`). |
| Ad-hoc helper | `lm.py` (repo root) | One-shot prompt offload to whatever chat model LM Studio has loaded; used by batch-rewrite tooling. |

### 6.2 Operational rules

- LM Studio must have a properly-typed **embeddings** model loaded (`text-embedding-nomic-embed-text-v1.5`; jina v5 is typed `llm` and breaks `/v1/embeddings`). Chat model is independent (`qwen3-vl-8b-instruct` currently).
- **Reindex after every content batch**: `python scripts/rag_index.py --live` joins the maintenance loop next to index regeneration. Changing embedding model = edit `rag.toml` + `--rebuild --live`.
- MCP `mcp.json` paths use forward slashes (LM Studio gotcha).
- `queries/` pages are normal vault pages (indexed, linkable) but are machine-written; humans curate or archive them, they don't hand-write there.

---

## 7. The Script Layer

All scripts live in `scripts/`, are Python 3, and share a contract: **dry-run by default with an explicit `--live`/`--write` flag for anything destructive; argparse flags; plain-line streamed output.** `rag_utils.py` is the shared library. Every script resolves the vault path via `rag.toml`, never by guessing.

### 7.1 Health & audit (read-only)

| Script | Does |
|---|---|
| `find_missing_pages.py` | Scans dead wikilinks → regenerates `indexes/missing-pages.md` |
| `audit_page_quality.py` | Per-page quality audit against the Page Standard; writes the tiered worklist that feeds the LM Studio rewrite runners (§7.5) |

### 7.2 Fix & maintain (dry-run → `--live`)

| Script | Does |
|---|---|
| `zotero_sync.py` | The Zotero ingest pipeline of §5.2: Better BibTeX JSON → stubs + bridge ledger + log (`--self-test` available). **[UNVERIFIED against this vault]** — see the known deviation note in §5.2. |

### 7.5 LLM offload

| Script | Does |
|---|---|
| `lmstudio_rewrite.py` / `lmstudio_run.py` / `lmstudio-v2-run.py` | Batch page processing on the local LM Studio model, for bulk work over many pages. Claude handles only judgment calls and commits |
| `rag_index.py` / `rag_search.py` / `akira_mcp.py` | §6 |

### 7.7 Unattended fill orchestration (`workers/`)

Not part of the original design — built to get the 198-page `MD/FILL-SOURCES.md`
work order done without a human babysitting every page. One-time catch-up
scaffolding, not a permanent service; a future session can delete `workers/`
once there's no large backlog to burn through.

| Script | Does |
|---|---|
| `night_worker.py` | Loops spawning `claude --dangerously-skip-permissions -p "..."` sessions, one unfinished page per session. Detects Claude usage-limit rate-limiting (429/"session limit" text) and stops cleanly instead of burning the rest of its session budget on instant failures; kills and skips any session that hangs past a 20-min timeout. |
| `local_night_worker.py` | Same loop, but calls LM Studio directly (`/v1/chat/completions`) instead of spawning Claude sessions — no usage limit, fully offline. Text-only: image-only PDFs it can't extract text from are left with `TODO` for `night_worker.py` (Claude can visually read PDF pages) to pick up. |
| `worker_common.py` | Shared claim/release file-lock (one `.claims/{stem}.lock` per page) so both workers can run **simultaneously** against the same folder pool without redoing each other's pages. |

Both workers independently pick "the first page still containing `TODO`,"
claim it, and release it when done (success, failure, or timeout) — so
either one dying mid-run just means the other picks up the slack next pass.

### 7.8 How they interact

```
Zotero (Better BibTeX JSON export)          path\to\zotero-inbox\{cluster}\ (manual staging,
      │                                      §5.2 known-deviation pipeline)
      ▼                                            │
zotero_sync.py ──writes──► sources/*.md            ▼
      │  [unverified            ▲          source-drafts/ + sources-zotero/ (TODO-marked drafts)
      │   this vault]            │                 │
      ▼                          │          workers/night_worker.py ◄─┐ claim/release via
zotero-bridge.md                 │          workers/local_night_worker.py ─┘ worker_common.py
log/ingest.md                    │                 │ (fills TODO → real content)
                                  │                 ▼
                                  └── promotion into sources/ (topics: derived from
                                       source-folder structure, §4.1)
                                                     │
                                                     ▼
        find_missing_pages.py (dead-link audit)      rag_index.py --live ──► rag_store/
                                                      │
                                             rag_search.py ◄── akira_mcp.py ◄── LM Studio
                                                      │ [unverified this vault]
                                             queries/*.md (save_query)
```

---

## 8. Governance Invariants

Non-negotiable rules any tool or session must preserve:

1. **Registry-only tags** — 3-10 per page, all from `settings/core/tags.md`; a tag under 3 real uses gets pruned/merged (§4).
2. **No dead links** — every `[[wikilink]]` resolves to an existing page or one in `settings/pending/staged/`; unresolved links are tracked in `indexes/missing-pages.md`.
3. **No orphans** — every new page is linked from at least one existing page.
4. **No duplicates** — check stems, staged pages, and missing-pages before creating; merge instead of double-creating (`dup-whitelist.md` lists intentional exceptions).
5. **Zotero-only sources** — no source page without a `zotero-key`; no PDFs in the repo; the bridge ledger is the dedup authority.
6. **Generated content is never hand-edited** — `indexes/`, "Cited In" sections, `zotero-bridge.md`, `rag_store/`.
7. **Contradiction pairs same-session** — `challenges`/`challenged-by` added together when the critique is ingested, never deferred.
8. **Archive, never delete** — retired pages → `settings/archive/{category}/` with archive frontmatter, inbound links rewritten first, logged to `ops.md`.
9. **Append-only logs** — `settings/log/ingest.md` and `ops.md`: `YYYY-MM-DD | action | target | detail`.
10. **Git hygiene** — commit per completed batch, `type(category): description` (e.g. `ingest(sources): add 3 Braidotti stubs`, `merge: anthropocene ← antropoceno`). Never commit: Zotero exports, `rag_store/`, `settings/session.md`.
11. **Session continuity** — multi-step tasks write `settings/session.md` (gitignored); new sessions read it first.
12. **Reindex discipline** — after any content batch: regenerate affected `indexes/`, rerun `find_missing_pages.py`, run `rag_index.py --live`.
13. **Vault path from config** — every tool resolves the vault via `rag.toml`; `rag_utils.resolve_vault_path` refuses paths without `concepts/` inside.
14. **No new files at repo root if a folder exists for that content type.** Docs go in `MD/` (never a loose `.md` at root), Python tooling goes in `scripts/` (maintenance layer) or `workers/` (fill-orchestration), logs go in `logs/`. `lm.py` is the one deliberate exception — see §2's layout, it's called out there by name. Before creating anything at root, check whether an existing folder already owns that file type; if one does, the file goes there, full stop.

---

## 9. Workflows

**Source ingest** — §5.2. Zotero → export → `zotero_sync.py --live` → connect + tag → commit.

**Page creation** — duplicate check (vault, staged, missing-pages) → draft in `settings/pending/staged/` → promote to the correct category folder → link from ≥1 existing page → registry tags + topics → commit → reindex.

**Maintenance loop** — health/audit scripts → fix batches with fix-scripts (dry-run first) → regenerate indexes → `rag_index.py --live` → commit per batch. Dead links are worked from `indexes/missing-pages.md`: create the page, rewrite the link, or petition a merge.

**Merge** — assemble both pages into a petition file in `settings/pending/prompts/`; human (or AI-as-writer, reviewed) resolves; losing stem archived with `replaced-by:`, inbound links rewritten, logged.

**RAG query session** — LM Studio + MCP: model calls `search_akira`/`read_page`, answers, then `save_query` writes the digest to `queries/`; digests get picked up by the next reindex and become part of the corpus.

**Bulk rewrites** — batched through `lmstudio_rewrite.py` on the local model; Claude reviews edge cases and commits.

---

## 10. AI Boundaries

- **AI is writer-only, and shrinking.** It drafts prose, resolves merges as files for human review in `settings/pending/`, and evaluates scope. It never auto-writes knowledge pages, never invents tags, never bypasses the staged→promote flow.
- The MCP server enforces this in code: `save_query` → `queries/` is the only machine write path into the vault.
- Nothing in the core loop (ingest, index, link, audit) requires an LLM to function.

---

## 11. Prerequisites & Setup

What a fresh machine needs to run the full system:

| Component | Requirement |
|---|---|
| Python | 3.11+ (3.13 in use; `tomllib` requires ≥3.11). Third-party packages: `numpy`, `requests`, `pyyaml`, `mcp`, `pypdf` |
| Obsidian | Any recent version; open the **inner** vault folder, not the repo root |
| Zotero | Desktop app + **Better BibTeX** plugin (citekeys + JSON export). Storage stays at its default location; the vault only stores paths into it |
| LM Studio | Local server on `127.0.0.1:1234` with two models loaded: an **embeddings**-typed model (`text-embedding-nomic-embed-text-v1.5`) and any chat model. Only needed for RAG/rewrite work — the vault, scripts, and ingest pipeline all function without it |
| Git | Standard; no LFS (no binaries in the repo) |

First-run order: clone → set both paths in `settings/core/rag.toml` → `python scripts/rag_index.py --live` (builds the RAG store from scratch; it is gitignored, so every clone starts empty).

Windows notes: script paths in configs use forward slashes for LM Studio's `mcp.json`; beware the doubled folder name (`...\Akira\Akira`) when setting paths — `rag_utils.resolve_vault_path` will refuse a wrong level, trust it.

---

## 12. Quick Reference

| Need | Where |
|---|---|
| Vault content | `akira/` (nested) — open in Obsidian |
| Canonical paths | `settings/core/rag.toml` |
| Topic derivation | source-folder structure, NOT `MD/topics.md` (§4.1) |
| Tag registry | `settings/core/tags.md` — built 2026-07-17 |
| Frontmatter schema | `settings/core/relations.md` — **[NOT YET BUILT]**; `akira/templates/*.md` are the working reference in the meantime |
| Docs | `MD/` — this file, `SOURCES.md`, `FILL-SOURCES.md`, `FILL-LOG.md`, `BUILD-TOPICS.md`, `BUILD-CONCEPTS.md`, `CONCEPT-LOG.md`, `topics.md` (superseded) |
| Source ingest (designed) | Zotero → Better BibTeX JSON export → `scripts/zotero_sync.py --live` — **[unverified against this vault]** |
| Source ingest (actually used) | `MD/FILL-SOURCES.md`'s pipeline → `workers/night_worker.py` + `workers/local_night_worker.py` → promotion into `akira/sources/` |
| Dedup ledger | `settings/core/zotero-bridge.md` — **[NOT YET BUILT]** |
| Dead links | `akira/indexes/missing-pages.md` ← `python scripts/find_missing_pages.py` |
| RAG reindex | `python scripts/rag_index.py --live` |
| RAG query CLI | `python scripts/rag_search.py "question"` |
| MCP server | `scripts/akira_mcp.py` — **[unverified against this vault]**; `queries/` is empty |
| Logs | `logs/night_worker.log`, `logs/local_night_worker.log`; `settings/log/` — **[NOT YET BUILT]** |
| Commit format | `type(category): description` |
