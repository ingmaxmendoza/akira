# Work Order: MARCO 2026 Exhibition and Piece Pages

**Goal: promote the 7 MARCO 2026 exhibitions currently tracked only at the
source level into `entity/exhibition` pages, and create a `concept` (piece
variant) page for every named artwork in them with real descriptive content.
Templates already built: `templates/exhibition.md`, `templates/piece.md`.
AKIRA-V3.md §3.1 updated 2026-07-17 to add both categories.**

Written 2026-07-17.

---

## 0. Scope — the 7 exhibitions

| Exhibition | Source(s) | Artist(s) | Existing topic |
|---|---|---|---|
| ¿Cómo salimos? | `marco-teresa-margolles-como-salimos`, `marco-teresa-margolles-material-de-estudio` | Teresa Margolles | `teresa-margolles-como-salimos` |
| La Petite Mort | `marco-2026-gabriel-de-la-mora-la-petite-mort` | Gabriel de la Mora | `museo-marco` |
| Aquí Empieza la Patria | `marco-carlos-vielma-aqui-empieza-la-patria` | Carlos Vielma | `museo-marco` |
| Gerda Gruber: Entre verde y agua | `marco-gerda-gruber` | Gerda Gruber | `museo-marco` |
| Convergencias/Divergencias | `marco-maldonado-convergencias-divergencias` | group/collection (~25+ artists + Ye'kwana basketry) | `museo-marco` |
| Los cuervos vuelan hacia el norte | `marco-wendy-cabrera-los-cuervos` | Wendy Cabrera Rubio | `museo-marco` |
| En el hilo de la noche, la trama del mundo | `marco-en-el-hilo-de-la-noche` | Lucía Vidales, Amor Muñoz, Daniel Guzmán (group show) | `museo-marco` |

Out of scope: the institutional/education sources (`marco-arquitectura-e-historia`,
`marco-guia-arquitectonica`, `marco-percibir-muse`) and the FEMSA collection
sources — these aren't exhibitions.

## 1. Reading order per exhibition

For each row above, **read both** the source page(s) already in `sources/`
*and* the original PDF at the source's `attachment:` path (under
`path\to\zotero-inbox\museo-marco-2026-tec\...`) before writing anything —
the source.md summarizes and selects; the PDF has the full per-work catalogue
text the piece pages need (medium, year, dimensions, room placement, wall
text) that didn't make it into the source page's Key ideas bullets.

Convergencias/Divergencias's guide is explicitly a student-made document
(not official museum text, no exhibition dates given) — note that in the
exhibition page's Key facts rather than treating it as equivalent-authority
to the others.

## 2. Per-exhibition steps

1. **Artist stub(s).** If the artist doesn't already have an `entities/people/`
   page (none currently exist for these 7 shows' artists), create one:
   `type: entity/person`, `status: stub` if bio is thin, filled from the
   source's biographical paragraph. Skip for group/collection shows with no
   single-artist bio to write (Maldonado, En el hilo de la noche gets one
   stub per artist only if each has real individual bio content, not just a
   name).
2. **Exhibition page.** `entities/exhibitions/{slug}-2026.md` from
   `templates/exhibition.md`. Curator, dates, venue, thematic axes go in Key
   facts (leave blank/omit rather than guessing what the source doesn't
   state — Maldonado's guide states no dates, don't invent them). Link
   `related:` to the source(s), the artist(s), and the topic.
3. **Piece pages.** One `concepts/{piece-slug}-{artist-slug}.md` per named
   work with real descriptive content (a sentence or more beyond just a
   title) — per the source list, that's roughly: ~10 for Margolles, several
   each for De la Mora, Vielma, Gruber, Cabrera, and the group show; a
   smaller curated subset for Maldonado given it's ~25+ artists and the
   guide organizes by formal axis rather than per-work entries (write pieces
   only for works the guide actually gives individual treatment to, not
   every name in a checklist). Fill `artist`, `exhibition`, `medium`, `year`
   frontmatter where the source states them; leave blank otherwise, never
   guess.
4. **Link back.** Add each piece to the exhibition page's `## Works` list
   (one-line description). Add `topics:` on the exhibition page (and pieces,
   if genuinely distinct) from the existing registry — don't invent new
   topics for this pass.
5. **Cross-check companions.** Margolles has two sources covering overlapping
   works (`como-salimos` per-work entries vs `material-de-estudio`'s
   thematic essay) — merge into one piece page per work rather than
   duplicating; cite both sources in Connections where both discuss a piece.

## 3. Quality bar

- A piece page needs actual content from the source — a bare name in a
  checklist (e.g. Maldonado's ~25 background artists) doesn't get a page.
  "No page" is a valid outcome; don't pad.
- Don't invent dates, dimensions, or curator names the source doesn't state.
- `related:`/Connections links must point at real pages (existing or
  created this pass) — no dangling links to invented stems.
- Follow existing tag registry (`settings/core/tags.md`) only; no new tags
  without registry-first addition (AKIRA-V3.md §4).

## 4. Log

Append one line per session to `EXHIBITION-LOG.md` (create it next to this
file): `YYYY-MM-DD | exhibitions processed | pieces created | artist stubs
created`.
