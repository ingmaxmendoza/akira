# Work Order: Build Place Pages From a Topic

**For a fresh Claude session (or night_worker.py). Goal: given ONE topic
page, write the `entity/place` page(s) for the places that topic's member
sources actually depend on — venues, neighborhoods, cities, regions. Read
`AKIRA-V3.md` §3.1 first for the entity rules. This file tells you the
process and the boundaries.**

Written 2026-07-17. Vault root: the repo's `akira/` folder — resolve paths
from `settings/core/rag.toml`, never guess.

---

## 1. Input

You are given one topic stem, e.g. `sierra-picachos`. Read:

- `akira/topics/{topic}.md` — the synthesis paragraph and the `## Sources`
  section (its member source pages).
- Each wikilinked source under `## Sources` — which geography its argument
  actually depends on, from the Key ideas and summary.
- `akira/templates/place.md` — the exact frontmatter/section shape.
- `akira/entities/places/` — skim existing stems so you don't duplicate
  one that already exists.
- `settings/core/tags.md` — the tag registry. 3–10 tags, most specific
  only; geography tags signal *cultural context*, not mere location
  (`AKIRA-V3.md` §4). Registry-first rule applies for any new tag.

## 2. What counts as a place page

A place qualifies when a source's **argument depends on the geography** —
not when a location is merely mentioned. Ask: "if this place were swapped
for another, would the source's claim change?" If yes, it's a place page.

- A mobility study of a specific city, an ecology survey of a specific
  sierra, a scene rooted in a specific neighborhood → place pages.
- NOT a place page: where a book was published, where a conference
  happened, a city on a byline.
- Scale: use the level the sources argue at (neighborhood vs. city vs.
  region) — don't create both `barrio-antiguo` and `monterrey` unless
  sources genuinely work at both levels.

**1–3 place pages per topic session, not a quota.** Zero is a legitimate
outcome — say so and stop, don't force one.

## 3. Writing the page

Follow `akira/templates/place.md` exactly: `type: entity/place`, filed
under `entities/places/`, stem `place-name` (kebab-case, e.g.
`barrio-antiguo`). Body: `# Place Name`, a lead paragraph saying what/where
it is and why the vault tracks it, then `## Key facts`
(geographic/administrative facts plus what specifically happens here that
the sources document), then `## Connections` (the sources about it, the
topics it feeds, organizations based or operating there).

## 4. Quality bar

- Every fact traces to the vault's source pages — no imported geography
  trivia the sources don't support.
- `related:` must point at real existing stems — check before linking.
- No `TODO` string anywhere in a finished page.
- Prefer fewer, well-grounded place pages over many thin ones.

## 5. Logging

Append one line per session to `ENTITY-LOG.md` (create it next to this
file if absent), **even if zero pages were written**:

`YYYY-MM-DD | places | topic | stems created | notes`

This line is the only signal an orchestrating script has that this topic
was processed for places — always write it before ending the session.

## 6. Boundaries

- Never touch `source-drafts/`, `sources-zotero/`, or Zotero storage —
  read-only for this task.
- Don't edit the topic page beyond adding a natural wikilink to a new
  place page in its prose.
- Don't rename or move any existing page.
- One topic per session; one category (places) per session.
