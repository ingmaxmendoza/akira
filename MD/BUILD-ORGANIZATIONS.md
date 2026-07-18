# Work Order: Build Organization Pages From a Topic

**For a fresh Claude session (or night_worker.py). Goal: given ONE topic
page, write the `entity/organization` page(s) for the organizations that
topic's member sources actually document — museums, labels, collectives,
brands, NGOs, institutions. Read `AKIRA-V3.md` §3.1 first for the entity
rules. This file tells you the process and the boundaries.**

Written 2026-07-17. Vault root: the repo's `akira/` folder — resolve paths
from `settings/core/rag.toml`, never guess.

---

## 1. Input

You are given one topic stem, e.g. `coleccion-femsa`. Read:

- `akira/topics/{topic}.md` — the synthesis paragraph and the `## Sources`
  section (its member source pages).
- Each wikilinked source under `## Sources` — which organizations it
  documents, from the Key ideas and summary.
- `akira/templates/organization.md` — the exact frontmatter/section shape.
- `akira/entities/organizations/` — skim existing stems so you don't
  duplicate one that already exists.
- `settings/core/tags.md` — the tag registry. 3–10 tags, most specific
  only; registry-first rule applies for any new tag.

## 2. What counts as an organization page

An organization qualifies when the sources document **what it does**, not
just that it exists: it runs the exhibitions, publishes the material, or is
itself the object of a source's argument. Ask: "would multiple pages link
`[[this-org]]`, and does the vault know something about it beyond its name?"

- **Exhibitions/biennials/campaigns are NOT organizations** — they get
  their own category (`entity/exhibition`, `entities/exhibitions/`, via
  `templates/exhibition.md` and the `BUILD-EXHIBITIONS.md` work order).
  The organization page is for the museum/collective *behind* them.
- Ambiguous person-vs-organization (a solo practice with a studio name):
  file by what the vault actually tracks about them (§3.1).
- NOT an organization page: a publisher on a citation line, a university
  affiliation, any org mentioned once in passing.

**1–3 organization pages per topic session, not a quota.** Zero is a
legitimate outcome — say so and stop, don't force one.

## 3. Writing the page

Follow `akira/templates/organization.md` exactly: `type:
entity/organization`, filed under `entities/organizations/`, stem
`org-name` (kebab-case, e.g. `museo-jumex`). Body: `# Organization Name`,
a lead paragraph saying what it is, where, and why the vault tracks it,
then `## Key facts` (founding/history facts relevant to the vault), then
`## Connections` (the sources documenting it, the topics its work feeds,
key people — founders, curators).

## 4. Quality bar

- Every fact traces to the vault's source pages — no imported institutional
  history the sources don't support.
- `related:` must point at real existing stems — check before linking.
- No `TODO` string anywhere in a finished page.
- Prefer fewer, well-grounded organization pages over many thin ones.

## 5. Logging

Append one line per session to `ENTITY-LOG.md` (create it next to this
file if absent), **even if zero pages were written**:

`YYYY-MM-DD | organizations | topic | stems created | notes`

This line is the only signal an orchestrating script has that this topic
was processed for organizations — always write it before ending the
session.

## 6. Boundaries

- Never touch `source-drafts/`, `sources-zotero/`, or Zotero storage —
  read-only for this task.
- Don't edit the topic page beyond adding a natural wikilink to a new
  organization page in its prose.
- Don't rename or move any existing page.
- One topic per session; one category (organizations) per session.
