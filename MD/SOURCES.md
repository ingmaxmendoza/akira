# Akira V3 — Sourcing Specification

**This document is the authority for how sources enter the vault and how source pages are written. It extends §5 of [AKIRA-V3.md] and supersedes it where they differ (page depth, Zotero read method).**

Written: 2026-07-11. Originally validated against a live ~200-item library (PDFs, HTML snapshots, images).

---

## 1. Principles

1. **Zotero is the only pipeline.** A source that isn't in Zotero doesn't exist yet. No raw-PDF inbox, no ad-hoc URL stubs. PDFs and snapshots live in Zotero storage — never in the vault or repo.
2. **Full page at birth.** Source pages are NOT thin stubs. Every readable source is created with a summary, key ideas, and notable quotes drawn from its extracted full text. `status: stub` is reserved for the rare source whose text cannot be extracted yet.
3. **Read Zotero directly.** Scripts read `zotero.sqlite` **read-only** (`file:...?mode=ro&immutable=1`) for metadata, attachment paths, collections, and tags — safe while Zotero runs, no export step. Better BibTeX supplies citekeys via its auto-export; that is all the export is for.

---

## 2. Reading the library

### 2.1 Locations

| What | Where |
|---|---|
| Zotero data dir | `C:\path\to\ZoteroData` (NOT `~/Zotero`, which is empty; NOT the stale path in Zotero's prefs.js) |
| Metadata DB | `{data}\zotero.sqlite` — open read-only immutable only |
| Attachments | `{data}\storage\{KEY}\` — one 8-char key folder per attachment |
| Extracted full text | `{data}\storage\{KEY}\.zotero-ft-cache` — plain UTF-8, written by Zotero itself |
| Citekeys | Better BibTeX auto-export (JSON), path set in `settings/core/rag.toml` |

### 2.2 Text extraction — order of preference

1. **`.zotero-ft-cache`** — first choice, always. Zotero's own extraction; covers PDFs *and* HTML snapshots with one code path, and recovers text from PDFs `pdftotext` fails on. In practice nearly every indexed PDF and snapshot has one.
2. **`pymupdf` (installed)** — fallback when the cache file is missing or stale (Zotero hasn't indexed the item yet).
3. **Visual read (AI)** — for image-only PDFs with no text layer (scans). These get pages written from visual reading; until then they may carry `status: stub`.

For HTML snapshots, prefer the ft-cache over parsing the `.html` (the cache is already boilerplate-free text).

### 2.3 Metadata query shape

One join gives everything a source page needs (validated):

```sql
-- items + title + attachment path + storage key; extend with creators,
-- date, itemDataValues fields as needed
SELECT it.typeName, idv.value AS title, ia.path, att.key AS zotero_key
FROM items i
JOIN itemTypes it  ON i.itemTypeID = it.itemTypeID
JOIN itemData id   ON i.itemID = id.itemID
   AND id.fieldID = (SELECT fieldID FROM fields WHERE fieldName='title')
JOIN itemDataValues idv ON id.valueID = idv.valueID
LEFT JOIN itemAttachments ia ON ia.parentItemID = i.itemID
LEFT JOIN items att ON ia.itemID = att.itemID
WHERE it.typeName NOT IN ('attachment','note','annotation');
```

`ia.path` is `storage:filename.ext` → resolve to `{data}\storage\{zotero_key}\filename.ext`.

---

## 3. Stems

All stems: lowercase kebab-case, ASCII only (strip accents: `morán` → `moran`), English slug unless culturally untranslatable.

| Source kind | Stem format | Example |
|---|---|---|
| Authored work (book, paper, standard, datasheet) | `author-year-slug` | `baudrillard-1970-sociedad-de-consumo` |
| Web item with no author/year | `site-year-slug` — publisher or site name + best-known year | `reddit-2024-colonias-caminables`, `milenio-2025-indio-mexologia` |
| Standard/datasheet with corporate author | `org-year-slug` or `org-partnumber` | `iso-2010-12100`, `ti-opt3002` |

- The year is the publication year; if genuinely unknown, use the Zotero *date added* year.
- Spanish-language sources keep the Spanish slug and carry `lang: es`.
- The stem should match (or be derivable from) the Better BibTeX citekey where possible; where BBT generates something unusable (`anonymous2024trafico`), the stem wins and the citekey is recorded in frontmatter regardless.

---

## 4. The source page template

Lives at `settings/core/templates/source.md` in the repo; reproduced here as the authority.

```markdown
---
title: La sociedad de consumo        # display title, original language
type: source
source-type: book                    # book | article | chapter | standard |
                                     # datasheet | webpage | forum-post | video | patent
tags: [consumption, critical-theory] # 3-10, registry only (settings/core/tags.md)
topics: [philosophy-consumption-modernity]
related: [jean-baudrillard, hyperreality]
challenges: []                       # pair-added same session, never deferred
challenged-by: []
lang: es                             # only if the source itself is Spanish-primary
zotero-key: DX4IZK6Q                 # storage key of the PRIMARY attachment — required
citekey: baudrillard1970sociedad     # Better BibTeX citekey
attachment: C:\path\to\ZoteroData\storage\DX4IZK6Q\Baudrillard - La sociedad de consumo.pdf
apa7: "Baudrillard, J. (1970). La société de consommation. Denoël."
zotero-uri: zotero://select/items/@baudrillard1970sociedad
url:                                 # original URL — required for web sources, omit otherwise
accessed:                            # YYYY-MM-DD — web sources only
---

# La sociedad de consumo

One-paragraph summary: what this source is, what it argues, and why it is
in the vault — written from the extracted full text, not from the abstract
alone. Name the vault pages it speaks to: [[jean-baudrillard]],
[[consumer-culture]].

## Key ideas

- 3–8 bullets. Each bullet is one claim or finding IN YOUR OWN WORDS,
  specific enough to cite from another page without reopening the PDF.
- Link concepts as they appear: consumption as a system of
  [[sign-value|signs]], not needs.
- For datasheets/standards: the operative facts instead (ranges, clauses,
  ratings that the engineering pages will cite).

## Quotes

> "Direct quotation in the original language, kept short and citable."
> (p. 42)

- 0–5 quotes, page-referenced where the source has pages. Only quotes
  worth citing verbatim later; this is not a highlights dump.

## Connections

- How this source relates to what the vault already holds: supports,
  extends, or contradicts which pages. If it contradicts, the
  challenges/challenged-by pair is added NOW, on both pages.

## Cited In

<!-- script-maintained — never hand-edit -->
```

### 4.1 Field rules

- **`zotero-key`** — the storage key of the primary attachment (the PDF, or the snapshot for web items). Required; there is no `none` value. Items with multiple attachments: key of the one the page was written from.
- **`source-type`** — drives which body sections matter: `book/article/chapter` emphasize Key ideas + Quotes; `datasheet/standard` emphasize operative facts and rarely quote; `forum-post/webpage/video` may compress Key ideas and Quotes into fewer bullets but never skip the summary.
- **`attachment`** — absolute path from the sqlite join. It is a pointer, not a promise: tools must fail soft if the file moved.
- **`apa7`** — full APA 7 citation string. Web sources include retrieval info per APA 7.
- **`url` / `accessed`** — mandatory for `webpage/forum-post/video`, omitted for others.
- **Section headings are load-bearing** — `##` boundaries are the RAG chunk boundaries; keep the four canonical sections in order.

### 4.2 Quality bar (what "full page at birth" means)

A new source page is done when:

1. Summary paragraph exists and was written from the extracted text.
2. ≥3 Key ideas bullets (≥1 for very thin web items).
3. Tags (registry-only, 3-10) and ≥1 `topics:` value assigned.
4. Linked from at least one existing page (no orphans) and links out to at least one vault page inline.
5. `challenges`/`challenged-by` pairs added on both sides if applicable.
6. Bridge ledger row appended (§5).

Only image-only PDFs awaiting visual reading may carry `status: stub`.

---

## 5. Ingest flow

1. **Collect in Zotero** — connector or manual entry; attachment lives there; file into a collection.
2. **Sync** — `zotero_sync.py` reads `zotero.sqlite` (ro/immutable) + the BBT auto-export; for every item whose citekey is not in `settings/core/zotero-bridge.md` it:
   - resolves stem per §3,
   - emits the frontmatter skeleton with all Zotero-derived fields filled,
   - pulls the full text (`.zotero-ft-cache` → `pymupdf`) into the working context for the writer,
   - appends `citekey | vault-stem | imported-date` to the bridge ledger and a row to `settings/log/ingest.md`.
   Dry-run by default; `--live` to write.
3. **Write** — the writer (AI drafting, human reviewing) fills summary/Key ideas/Quotes/Connections from the extracted text, assigns tags + topics, links it into the graph.
4. **Commit** — `ingest(sources): ...`, then reindex (`rag_index.py --live`).

The bridge ledger is the dedup authority: one Zotero item → one vault page, forever.

---

## 6. Worked example (web snapshot)

```markdown
---
title: "¿Cuáles son las colonias/zonas más caminables de la ciudad?"
type: source
source-type: forum-post
tags: [urbanism, mexican-art]
topics: [urban-health-and-mobility]
related: [walkability, monterrey]
challenges: []
challenged-by: []
lang: es
zotero-key: TFKLBQBQ
citekey: reddit2024colonias
attachment: C:\path\to\ZoteroData\storage\TFKLBQBQ\cuáles_son_las_coloniaszonas_más_caminables_de_la.html
apa7: "[deleted]. (2024). ¿Cuáles son las colonias/zonas más caminables de la ciudad? [Online forum post]. Reddit. https://reddit.com/r/Monterrey/..."
zotero-uri: zotero://select/items/@reddit2024colonias
url: https://reddit.com/r/Monterrey/...
accessed: 2025-11-02
---

# ¿Cuáles son las colonias/zonas más caminables de la ciudad?

Reddit thread surveying which Monterrey neighborhoods residents consider
walkable; primary-source evidence of lived [[walkability]] perception used
by [[urban-health-and-mobility]].

## Key ideas

- Residents converge on Centro, [[barrio-antiguo]], and San Pedro's Casco
  as the only consistently walkable zones.
- Heat and missing shade are cited as often as sidewalk quality — climate
  is a walkability variable, not just infrastructure.

## Quotes

> "Caminable en Monterrey significa que hay banqueta y sombra, y eso ya
> es mucho pedir."

## Connections

- Grounds the anecdotal layer of [[urban-health-and-mobility]]; pairs with
  formal mobility data sources when they arrive.

## Cited In

<!-- script-maintained -->
```

Stem: `reddit-2024-colonias-caminables`.

---

## 7. Invariants (source-specific)

1. No source page without a real `zotero-key`.
2. No PDFs/snapshots in the repo — paths point into Zotero storage.
3. One Zotero item = one source page; the bridge ledger enforces it.
4. Pages are born full (§4.2); `status: stub` only for unextractable text, tracked and burned down.
5. `Cited In` is script-owned.
6. Web sources always carry `url` + `accessed`.
7. Everything else in AKIRA-V3.md §8 applies unchanged.
