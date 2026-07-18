# Work Order: Build Concept Pages From a Topic

**For a fresh Claude session (or night_worker.py). Goal: given ONE topic
page, write the concept page(s) for the distinct ideas/theories/frameworks
that topic's member sources actually develop. Read `AKIRA-V3.md` §3.3 first
- it has the authoritative concept-page shape. This file tells you the
process and the boundaries.**

Written 2026-07-17. Vault root: `C:\path\to\Akira`.

---

## 1. Input

You are given one topic stem, e.g. `posthumanism`. Read:

- `akira/topics/{topic}.md` - the synthesis paragraph and the `## Sources`
  section (its member source pages).
- Each wikilinked source under `## Sources` - specifically the Key ideas
  and summary, not the whole document again.
- `akira/templates/concept.md` - the exact frontmatter/section shape.
- `akira/concepts/` - skim existing concept stems so you don't duplicate one
  that already exists (e.g. don't recreate `hyperreality` if it's there).
- `settings/core/tags.md` - the tag registry. Pick 3-10 tags from it, most
  specific only. A new tag may only be proposed if it will genuinely apply
  to 3+ pages (registry-first: add it there with a definition, same
  session, before using it) - see the registry's own rule 3.

## 2. What counts as a concept

A concept is a **named, citable idea, theory, or framework** - not a
restatement of the topic itself and not a source summary. Ask: "would a
future page need to link `[[this-idea]]` on its own, separate from any one
source?" If yes, it's a concept. Examples of a real concept vs. not:

- Topic `posthumanism` -> concepts `posthuman-subjectivity`,
  `nomadic-ethics` (Braidotti's specific framework). NOT a concept: a page
  that just re-describes "posthumanism" as a movement (that's the topic
  page's job).
- Topic `innovation-design` -> concept `blue-ocean-strategy` (already
  exists - skip it), maybe `value-innovation` if it's developed distinctly
  enough to deserve its own page rather than being folded into
  `blue-ocean-strategy`'s Key ideas.

**1-3 concept pages per topic session, not a quota.** A topic whose sources
are all empirical/descriptive (a datasheet cluster, an exhibition-guide
cluster) may legitimately yield zero concepts - say so and stop, don't force
one.

## 3. Writing the page

Follow `akira/templates/concept.md` exactly:

```yaml
---
title: Display Title
type: concept
tags: []            # 3-10, from settings/core/tags.md registry only
topics: [this-topic-stem]
related: [source-stems, other-concept-stems]
challenges: []
challenged-by: []
lang: es            # only if the concept is Spanish-primary
status: stub        # omit entirely once the page is genuinely complete
---
```

Body: `# Title`, then a lead paragraph naming who developed the idea and in
which source (wikilinked), then `## Key ideas` (the core claims, precise,
in your own words - see the `hyperreality` example in `AKIRA-V3.md` §3.3),
then `## Connections` (real links to sources/topics/other concepts this one
grounds, extends, or contradicts - `challenges`/`challenged-by` go on both
pages, same session, per `AKIRA-V3.md` §3.3).

Stem: kebab-case, English unless culturally untranslatable (same rule as
topics/sources, `AKIRA-V3.md` §3.2).

## 4. Quality bar

- Every claim in Key ideas traces to something the source pages actually
  say - do not invent theory beyond what's in the vault's source material.
- `related:` must point at real existing pages (sources, topics, other
  concepts) - check the stem exists before linking it.
- No `TODO` string anywhere in a finished page.
- Prefer fewer, well-developed concept pages over many thin ones.

## 5. Logging

Append one line per session to `CONCEPT-LOG.md` (create it next to this
file if absent), **even if zero concepts were written**:

`YYYY-MM-DD | topic | concept stems created | notes`

Example: `2026-07-17 | posthumanism | posthuman-subjectivity, nomadic-ethics | `
or `2026-07-17 | coleccion-femsa | (none) | all member sources are exhibition guides, no distinct framework to name`

This line is the only signal an orchestrating script has that this topic
was processed - always write it before ending the session, whether or not
you created any pages.

## 6. Boundaries

- Never touch `source-drafts/`, `sources-zotero/`, or files under
  `path\to\ZoteroData`/`path\to\zotero-inbox` - read-only for this task.
- Don't edit the topic page itself beyond adding a wikilink to a new
  concept page in its body prose, if natural - don't restructure it.
- Don't rename or move any existing page.
- One topic per session. Don't wander into other topics' sources.
