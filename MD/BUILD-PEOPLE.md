# Work Order: Build Person Pages From a Topic

**For a fresh Claude session (or night_worker.py). Goal: given ONE topic
page, write the `entity/person` page(s) for the people that topic's member
sources actually develop — theorists, artists, musicians, practitioners.
Read `AKIRA-V3.md` §3.1 first for the entity rules and the
person-vs-concept disambiguation. This file tells you the process and the
boundaries.**

Written 2026-07-17. Vault root: the repo's `akira/` folder — resolve paths
from `settings/core/rag.toml`, never guess.

---

## 1. Input

You are given one topic stem, e.g. `posthumanism`. Read:

- `akira/topics/{topic}.md` — the synthesis paragraph and the `## Sources`
  section (its member source pages).
- Each wikilinked source under `## Sources` — specifically who wrote it and
  who it is *about*, from the Key ideas and summary.
- `akira/templates/person.md` — the exact frontmatter/section shape.
- `akira/entities/people/` — skim existing stems so you don't duplicate one
  that already exists.
- `settings/core/tags.md` — the tag registry. 3–10 tags, most specific
  only; registry-first rule applies for any new tag.

## 2. What counts as a person page

A person qualifies when the vault **tracks them**, not merely cites them:
they authored or are the subject of ≥1 member source, or multiple pages
would want to link `[[their-name]]`. Ask: "does a reader of this topic need
to know who this is, beyond one citation line?"

- **Theorist whose *ideas* matter** → concept page for the idea + person
  page for the person (bio, career, influences). The person page never
  duplicates the idea's explanation — it links to the concept page.
- **Practitioner (artist/musician) whose *work* matters** → one person page
  usually covers both the person and the work.
- NOT a person page: a translator, an editor, a name dropped once in
  passing. A source's author gets a page only if the topic genuinely turns
  on who they are.

**1–3 person pages per topic session, not a quota.** A topic whose sources
are institutional/anonymous (datasheets, agency reports) may legitimately
yield zero — say so and stop, don't force one.

## 3. Writing the page

Follow `akira/templates/person.md` exactly: `type: entity/person`, filed
under `entities/people/`, stem `firstname-lastname` (kebab-case, e.g.
`rosi-braidotti`). Body: `# Full Name`, a lead paragraph saying who they
are and why the vault tracks them, then `## Key facts` (only facts that
place them — not a full biography), then `## Connections` (concepts they
originated, the vault's sources by/about them, topics their work feeds).

## 4. Quality bar

- Every fact traces to the vault's source pages — don't import biography
  the sources don't support.
- `related:` must point at real existing stems — check before linking.
- No `TODO` string anywhere in a finished page.
- Prefer fewer, well-grounded person pages over many thin ones.

## 5. Logging

Append one line per session to `ENTITY-LOG.md` (create it next to this
file if absent), **even if zero pages were written**:

`YYYY-MM-DD | people | topic | stems created | notes`

This line is the only signal an orchestrating script has that this topic
was processed for people — always write it before ending the session.

## 6. Boundaries

- Never touch `source-drafts/`, `sources-zotero/`, or Zotero storage —
  read-only for this task.
- Don't edit the topic page beyond adding a natural wikilink to a new
  person page in its prose.
- Don't rename or move any existing page.
- One topic per session; one category (people) per session.
