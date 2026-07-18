# Work Order: Build Topics From the Filled Sources

**For a fresh Claude session (or a script). Goal: assign every filled source
page a `topics:` value from the existing candidate registry, interlink
sources that share a topic or are semantically close, and create a topic
page per cluster that has enough members. Read `topics.md` first — it is
the candidate-topic authority (grouped by cluster, ~90 candidates already
named and described). This file tells you the process.**

Written 2026-07-13. Vault root: `C:\path\to\Akira`.

---

## 0. Prerequisite

`grep -rl "TODO" source-drafts sources-zotero` must be empty (or close to
it) before this is worth running — topic assignment needs the real summary
and Key ideas, not the `TODO` placeholder. If pages are still mid-fill,
finish `FILL-SOURCES.md` first, or run this only over the folders that are
already done.

## 1. Tools to reuse (don't rebuild them)

- **`lm.py`** (repo root) — the calling pattern for one-shot LM Studio chat:
  `pick_model()` (auto-picks the first loaded non-embedding model) and
  `ask(prompt, system=None)` (POSTs `/v1/chat/completions`). Reuse this
  shape for topic classification calls.
- **`scripts/rag_utils.py`** — reuse directly, no `settings/core/rag.toml`
  needed for this task:
  - `parse_frontmatter(text)` → `(meta_dict, body)`.
  - `embed_texts(texts, cfg, prefix)` → normalized `np.ndarray`; build `cfg`
    inline, e.g. `{"lmstudio": {"base_url": "http://localhost:1234/v1",
    "embedding_model": "text-embedding-nomic-embed-text-v1.5"}}` (check
    `curl http://localhost:1234/v1/models` for the exact loaded ID first —
    it currently also has `jina-embeddings-v5-text-small-retrieval` loaded;
    pick whichever is running).
  - `WIKILINK_RE` — for detecting existing inline links so you don't
    duplicate a Connection that's already wikilinked.
- The process below is self-contained for `source-drafts/` +
  `sources-zotero/` — no other script is involved.

## 2. Process

1. **Load candidates.** Parse `topics.md` into `{topic_stem: description}`.
   It has ~90 entries across clusters (Museo MARCO/FEMSA, music movements,
   engineering, philosophy, urbanism, etc.) — most sources should map onto
   an existing one. Only propose a new topic if nothing fits (see §4).

2. **Build one embedding text per source.** For each finished page in
   `source-drafts/` and `sources-zotero/`: concatenate `title` + the
   summary paragraph + the Key ideas bullets. Skip the Quotes/Cited In
   sections (noise for topic similarity).

3. **Embed sources and topic descriptions together** with
   `rag_utils.embed_texts()` (same embedding model for both sides so cosine
   similarity is meaningful).

4. **Classify each source.** For each source, compute cosine similarity
   against every candidate topic's embedded description; take the top 1-2
   above a similarity floor (start around 0.4, tune by eyeballing a sample).
   For low-confidence or borderline cases, use `lm.py`-style `ask()`: give
   the model the source's summary + the shortlist of candidate topic names
   with descriptions, ask it to pick the best fit(s) or say "none fit."
   Never invent a topic name that isn't in the registry at this step.

5. **Write `topics:` frontmatter.** Add the chosen topic stem(s) to each
   source's `topics:` list (max stays sane — 1-2 topics per source, per
   `relations.md`'s semantic-hierarchy intent, not a tag dump).

6. **Interconnect sources.** Within each topic cluster, compute pairwise
   cosine similarity between member sources' embeddings. For pairs above a
   higher threshold (start ~0.6), add each other's stem to `related:`
   frontmatter (dedup; don't exceed ~5 related entries — pick the strongest
   matches, not everything above threshold). This is what makes the graph
   traversable instead of just topic-tagged.

7. **Create topic pages.** For every topic with >=2 assigned sources and no
   existing page in `topics/` (create the folder if absent), write a page:
   frontmatter (`type: topic`, `title`, `tags` — 3-10, from
   `settings/core/tags.md` only, inherited from the dominant tags across
   members rather than re-derived from scratch) + a synthesis paragraph
   (written by you/the model from the member sources' summaries — not just
   a list) + a `## Sources` section wikilinking every member. Follow the
   concept-page shape in `AKIRA-V3.md` §3.3 for the frontmatter/section
   pattern. A new tag may only be proposed (registry-first, same session)
   if it will genuinely apply to 3+ pages — see `settings/core/tags.md`'s
   rule 3.

8. **Log.** Append one line per run to `TOPIC-LOG.md` (create it next to
   this file): `YYYY-MM-DD | sources processed | topics touched | topic
   pages created`.

## 3. Quality bar

- No source gets a topic it doesn't actually fit just to hit a quota —
  "no good match" is a valid outcome; leave `topics: []` and flag it for
  human review rather than forcing one from the registry.
- `related:` links must be justified by real content overlap, not just
  embedding proximity — spot-check a sample of the pairs the script
  proposes before writing them in bulk.
- Topic pages are synthesis, not a bibliography. If you can't write a
  coherent paragraph about what unifies the cluster, the cluster is
  probably wrong (too broad, or an artifact of the similarity threshold) —
  fix the threshold or split it, don't force a page.
- New topics require registry-first (`topics.md` updated, matching
  AKIRA-V3.md §4.1's tags-then-registry ordering) before a page exists for
  them or any source cites them.

## 4. When nothing in the registry fits

Rare, but: propose the new topic name + one-line description, append it to
the correct cluster section in `topics.md` (matching the existing format),
*then* proceed with steps 5-7 for it. Don't create the topic page first and
backfill the registry — same ordering rule as tags in AKIRA-V3.md §4.

## 5. Boundaries

- Never touch `path\to\ZoteroData` or `path\to\zotero-inbox` — this task only
  reads already-extracted summaries out of the finished source pages, not
  the original PDFs again.
- Don't rename or move source pages. Topic assignment is additive
  frontmatter + new pages under `topics/`, not a reorganization.
- Don't run this concurrently with `night_worker.py` / `local_night_worker.py`
  editing the same source files — read-then-write races are possible if a
  fill session and a topic-assignment pass touch the same page's
  frontmatter at once. Run topic-building on folders that are already fully
  filled (no `TODO`).
