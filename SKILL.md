---
description: Create ReshapeX Internal Brief presentations in Google Slides on any topic. Enforces the ReshapeX visual format while adapting content and slide count to whatever the user provides. Always outputs a real Google Slides file — never markdown in chat.
---

# ReshapeX Brief — Skill

When this skill is invoked, you MUST call the `create_reshapex_brief` MCP tool and return the URL. Never output a markdown presentation — always create the actual Google Slides file.

## Your job

1. Read the user's content (topic, raw data, table, description — anything).
2. Decide how many slides to use (1–5) and which layouts fit the content.
3. Write all the text for every element of every slide.
4. Call `create_reshapex_brief` with the full content.
5. Return the Google Slides URL.

---

## Slide layouts available

The template has 5 slots. Cover is always included. The other four are optional — omit any that don't serve the content.

### Cover (always)
- **badge** — `INTERNAL BRIEF · [MONTH YEAR]` in caps. Use current month/year.
- **main_title** — concise noun phrase identifying the subject.
- **subtitle_label** — one-word category: `Overview`, `Strategy`, `Analysis`, `Capabilities`, `Audit`, etc.
- **subtitle_desc** — one sentence describing what this deck covers.
- **client_name** — company or team name.

### slide2 — Card grid (3×2, up to 6 cards)
Use for: inventories, audits, capability assessments, data source maps, tool comparisons.

Each card: `title` + `badge` + `description` + `details`
- **badge values**: `STRONG` / `PARTIAL` / `GAP` / `HTML ONLY` / `UI ONLY` / `FALLBACK` / `DONE` / `PENDING` / `RISK` — pick what fits. Keep consistent within the slide.
- **details**: endpoint paths, bullet lines, or technical specifics.

### slide3 — Icon-item list (3×2, up to 6 items)
Use for: capabilities, features, process steps, what the system can do.

Each item: `icon` + `title` + `description` + `source`
- **icon**: single character symbol. Use varied symbols — no two the same per slide. Examples: `Q` (search), `=` (catalog), `v` (download), `+` (accessories), `?` (Q&A), `@` (email/contact), `>` (redirect), `o` (circular/API)
- **source**: `→ [endpoint, owner, or data origin]`

### slide4 — Numbered asks (2×2, up to 4 asks)
Use for: recommendations, requirements, next steps, what to request from a partner.

Each ask: `title` + `description` + optional `example` + `unlocks`
- **example**: `Example: GET /api/v2/products/{sku}` — only include if there's a concrete example.
- **unlocks**: outcome that becomes possible if this ask is fulfilled. Write it concisely without repeating "UNLOCKS" — the server adds that prefix.

### slide5 — Week plan (2 columns, exactly 2 weeks)
Use for: demo plans, sprints, phased rollouts.

Each week: `label` (W1/W2) + `phase` (e.g. `WEEK 1 · BUILD`) + `title` + `description` + `bullets`
- **bullets**: lines prefixed with `—` (em-dash)

---

## Narrative arcs (adapt to any topic)

**Agent / integration brief**: What we have → What we can do → What to ask for → Demo plan
**Strategy or proposal**: Where we are → Where we're going → How we get there → What we need
**Audit or review**: What we found → What's working → What needs fixing → Actions
**Project update**: What we set out to do → What we built → What's left → Timeline
**Any other**: Context → Current state → Findings / Capabilities → Gaps / Next steps → Plan

If the content naturally fits fewer than 4 content slides, use fewer. A 3-slide brief (cover + 2 content) is fine. Do not pad with content that doesn't exist.

---

## Writing rules (apply everywhere)

- Short sentences. Active voice. No filler.
- Concrete and specific: real names, real numbers, real endpoints.
- No superlatives: no "powerful", "seamless", "robust", "amazing".
- The reader is a peer — no hand-holding.
- If content is missing for a required field, invent the closest reasonable placeholder and flag it to the user after creating the file.

---

## tagline field

The tagline spans two visual lines in the template. Use `\n` to control the break:
```
"tagline": "Thirteen tools.\nFour data layers."
```
If no split is needed, write it as one line (the second line will be blank).

Pattern options:
- `[Descriptor phrase].`
- `[Thing A] — not [Thing B].`
- `[N] [things] that [outcome].`
- `[Short punchline]\n[contrast or continuation].`

---

## Example call (for the ImagingSource agent content)

```json
{
  "title": "ImagingSource Agent — Internal Brief",
  "cover": {
    "badge": "INTERNAL BRIEF · JUNE 2026",
    "main_title": "ImagingSource Agent",
    "subtitle_label": "Capabilities",
    "subtitle_desc": "Thirteen tools across four data layers — what we have, what we built, and what would make it stronger.",
    "client_name": "The Imaging Source"
  },
  "slide2": {
    "section_label": "What we have",
    "tagline": "Four data layers.\nTwo meaningful gaps.",
    "sub_description": "The accessible surfaces cover search, feeds, and product specs. Pricing and structured images are missing entirely.",
    "cards": [
      { "title": "Search API", "badge": "STRONG", "description": "Two autocomplete endpoints with JSON output.", "details": "- /api/v1/search/autocomplete/\n- /api/v2/search/autocomplete/" },
      ...
    ]
  }
}
```

---

## After creating

Return only:
1. The Google Slides URL (clickable link)
2. One sentence describing what was created and how many slides
3. Any fields where you had to guess or placeholder — flag those explicitly
