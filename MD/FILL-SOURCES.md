# Work Order: Complete Every Source Page

**For a fresh Claude session. Goal: every draft becomes a complete, individually usable source file — one page per document, filled to the quality bar below. Read `SOURCES.md` first; it is the format authority. This file tells you what to do and how thorough to be.**

Written 2026-07-12. Vault root: `C:\path\to\Akira`.

---

## 1. What exists and where

| Set | Location | Count | State |
|---|---|---|---|
| Inbox drafts | `source-drafts/` (mirrors topic folders) | 115 pages | Frontmatter + written summary; Key ideas / Quotes / Connections are `TODO` |
| Zotero-item drafts | `sources-zotero/` (by collection) | 83 pages | Same state; these have real `zotero-key` / `item-key` |

Both sets follow the template in `SOURCES.md` §4. A page is **unfinished** while it contains the string `TODO`.

Folder structure is final — do not move, rename, or merge pages. It mirrors the Zotero collections and `path\to\zotero-inbox` exactly.

## 2. Where the text comes from (in this order)

1. **`.zotero-ft-cache`** — for any attachment inside `C:\path\to\ZoteroData\storage\{KEY}\`, read the `.zotero-ft-cache` file next to it (plain UTF-8, already extracted, works for PDFs *and* HTML snapshots). The `zotero-key` frontmatter field gives you `{KEY}`.
2. **The `attachment:` path directly** — `source-drafts/` pages point into `path\to\zotero-inbox\...`; extract with `pdftotext` (installed) or `pymupdf` (installed). Some pages list two paths separated by ` | ` (duplicate copies of the same work) — read one, mention nothing.
3. **Visual reading** — for image-only PDFs (no text layer), Read the PDF pages directly as images. Do NOT skip these; they take longer, that's all. If a PDF is too big for the Read tool (>20MB or its per-request page cap), split it first: `python scripts/split_pdf.py "path/to/big.pdf"` writes `_partNN-of-MM.pdf` chunks next to the source and prints each chunk's page range — Read those one at a time. Image-only PDFs are flagged in their drafts as "visual read required".
4. **The URL** — for web items whose snapshot is junk (the Netflix *Social Dilemma* page, Facebook/Instagram/X captures), fetch the live URL if available; otherwise write from the title + context and say so in the page.

## 3. The quality bar (what "filled" means, per page)

Every page must end up with:

- **Summary paragraph** (already drafted — verify it against the actual text and correct it if the draft guessed wrong; the drafts were written from 500-char samples).
- **Key ideas: 3–8 bullets** — each one a specific claim, finding, or fact **in your own words**, precise enough that a topic page can cite it without reopening the source. Not chapter summaries, not "discusses X". For a 300-page book: the load-bearing arguments. For a 2-page datasheet: see §4.
- **Quotes: 0–5, page-referenced** — original language, short, only quotes worth citing verbatim later. `(p. 42)` where the source has pages; omit the section entirely only for sources with nothing quotable (datasheets, product pages).
- **Connections: 2+ real links** — name existing vault topics/concepts this source supports, extends, or contradicts (the draft's summary already names candidates). If it contradicts another source, note the pair explicitly — `challenges`/`challenged-by` frontmatter goes on **both** pages, same session.
- **Frontmatter finished**: remove `status: draft` when done (leave `status: stub` ONLY if the text was truly unreachable); fix `apa7` if the text reveals better metadata (real year, publisher, authors); replace `(s.f.)`/"Year TODO" wherever the document itself shows a year.
- **Tags: 3–10, registry-only** — read `settings/core/tags.md` first and pick from it; never invent a tag inline. If nothing in the registry genuinely fits, propose a new one, add it to `tags.md` with a definition (registry-first, same session), *then* use it - but only if you're confident it'll apply to at least 3 pages total (a one-off tag gets pruned later per the registry's rule 3). Most specific tag only, never a parent group name.
- **No `TODO` string anywhere in the file.**

Thoroughness rule: the page must be usable **instead of** the document for vault purposes — someone writing a topic page should almost never need to open the PDF again. When in doubt, one more Key idea, not one less.

## 4. Per-type depth

| source-type | Key ideas should capture |
|---|---|
| book | Central thesis + the 4–8 arguments/concepts the vault will actually cite; the named concepts get their own bullet each |
| article / chapter / report / thesis | Research question, method (one line), findings with numbers where they exist, limitation if stated |
| datasheet / standard | **Operative facts**: ranges, voltages, accuracies, clause numbers, ratings — the numbers an engineering page would cite. Quotes section usually empty |
| webpage / blog-post / forum-post | The claims/facts worth keeping; compress freely, ≥1 Key idea minimum; always verify `url` + `accessed` present |
| video | What it demonstrates/explains, from the title + any transcript; note if unwatched |
| guide (museum material) | Artist bio facts, exhibition thesis, thematic axes, named works — these feed entity and exhibition pages directly |
| presentation / course-slides | The framework/method taught, its steps or categories, definitions introduced |
| student-work / personal-document | 2–3 bullets on what it contains and which sources it used; these are provenance records, not knowledge sources |

## 5. Process (per session)

1. Pick unfinished pages: `grep -rl "TODO" source-drafts sources-zotero` — work through them **one at a time, completely**. Prefer finishing a folder before starting another.
2. Extract text (§2) → fill the page (§3–4) → remove `status: draft`.
3. After each folder is finished, append one line to `FILL-LOG.md` (create it next to this file): `YYYY-MM-DD | folder | pages done | notes`.
4. Batch commits are fine if the folder is a git repo; otherwise just save files.

Don't trust draft frontmatter over the document itself: fix wrong item types (books typed as `journalArticle`), wrong titles, and duplicate-title collisions whenever you touch a page.

## 5.1 Before ending the session: self-review the page

Re-read the page you just filled and verify every line of this checklist. Fix on the spot — do not end the session with a known miss:

- [ ] No `TODO` string anywhere in the file.
- [ ] `status: draft` line **deleted** from the frontmatter (not edited — removed).
- [ ] Every Key idea is a specific, citable claim — if a bullet could describe any document of this type ("discusses depression screening"), rewrite it with the concrete fact (items, numbers, names, clauses).
- [ ] Limits of the document stated honestly (missing scoring norms, no year, wrong metadata) instead of papered over.
- [ ] Quotes carry page references where the source has pages; none invented.
- [ ] `related:`/Connections point at real vault pages or clearly named future ones; `challenges` pairs written on **both** pages if used.
- [ ] Frontmatter years/`apa7` updated with anything the full text revealed.
- [ ] 3–10 tags, all from `settings/core/tags.md`, most-specific-only.

The BDI-2 page (`source-drafts/reference-misc-2026-tec/beck-bdi2-inventario-depresion.md`) is the reviewed reference example of an accepted page — match its level of specificity and honesty.

## 6. Boundaries

- Never edit `zotero.sqlite` or anything in `path\to\ZoteroData` — read-only (`mode=ro&immutable=1` if you open the DB).
- Never move/rename pages or folders; never touch `path\to\zotero-inbox`.
- Do not invent quotes, page numbers, years, or findings — if the text doesn't support it, leave it out. A shorter honest page beats a padded one.
- `citekey: PENDING` stays PENDING (Better BibTeX isn't set up yet); `zotero-key: PENDING` in `source-drafts/` also stays — a later sync script resolves both.
