# Medium Publishing — Format Rules

**Applies to**: every article in `articles/` that gets published on Medium.
**Enforcement**: manual for now; future CI lint welcome.

Medium's editor does NOT render Markdown cleanly. Pasting a `.md` written for GitHub into Medium produces broken tables, missing code languages, and formatting that loses the reader. This doc captures the rules so drafts are publishable on first paste.

---

## The hard rules (must follow)

### 1. No Markdown tables

Medium strips Markdown table syntax. The result is a run-on paragraph of pipe characters.

**Instead of a table, use:**
- **Bullet list with bolded keys** — best for most comparisons
- **Inline prose** — best for 2–3 row comparisons
- **Screenshot / PNG image** — best when the table is visually dense and you want to preserve alignment (treat it like a diagram; render to PNG, upload as image)

Example — staleness defaults table. DO NOT write:

```
| Source type | Stale after | Archive after | Frequency |
|---|---|---|---|
| Confluence | 90 days | 180 days | daily |
```

Instead, write:

> Confluence pages age out after **90 days** and archive at **180**, checked daily. GitHub docs are similar (60 / 180, daily). Runbooks decay slower (120 / 365, weekly). Incidents stay readable for a year before going stale, two before archive.

Or as a bullet list:

- **Confluence** — stale at 90 days, archived at 180, checked daily
- **GitHub docs** — stale at 60 days, archived at 180, checked daily
- **Runbooks** — stale at 120 days, archived at 365, checked weekly
- **Incidents** — stale at 365 days, archived at 730, checked weekly

### 2. Keep paragraphs tight

Medium readers scan more than read. Rules:

- Paragraphs max 3–4 sentences
- No paragraphs longer than ~70 words
- Split any sentence that has more than two clauses separated by em-dashes
- One idea per paragraph

### 3. Replace stale framing

Every time a draft says:

- "I wrote this" → "Here is"
- "It's worth noting that X" → "X."
- "You could say that X" → "X."
- "This article will cover X" → just cover X

Cut filler. Every sentence must earn its space.

### 4. Front-load the pull quote

Medium readers decide to keep reading within two paragraphs. Put the sharpest quotable line in the first 200 words.

### 5. Code blocks

Medium does render fenced code blocks. Keep them:

- **Short** — 5 to 15 lines max; longer blocks lose readers
- **Language-tagged** — `yaml` / `json` / `bash` / `python` at the top
- **Self-explanatory** — a code block that requires 3 paragraphs to understand shouldn't be in the article; move to the repo

### 6. Images

- Every major section can have a supporting image
- Feature image must be **1600×900** (Medium's 16:9 hero aspect)
- Inline diagrams must be **1600×900 or wider** so they stay sharp on retina
- Always provide alt text for accessibility + SEO

### 7. No employer-specific names in body copy

Per `docs/OSS_HYGIENE.md`, employer names (acme-corp / a large tech company / a large e-commerce company / etc.) stay out of the body. Byline at the bottom can carry them as author credentials.

### 8. Section structure

Default Medium-friendly structure:

1. **Title** (under 70 chars, benefit-framed)
2. **Subtitle** (one italic sentence — the "why this matters")
3. **Feature image** (1600×900)
4. **The problem** (what hurts, in specific terms)
5. **The insight** (one sentence that turns the article)
6. **The architecture / solution** (with one PNG diagram)
7. **Implementation highlights** (no more than 3 short code blocks)
8. **Results** (numbers, specific)
9. **Try it yourself** (links + bash quickstart)
10. **What's next** (teaser for the next article in the series)
11. **Byline + tags**

### 9. Tags

Medium allows up to 5 tags. Pick ones with real search volume:

- General: `AI`, `SRE`, `DevOps`, `Open Source`, `LLM`
- Topical: `RAG`, `Knowledge Management`, `MCP`, `Privacy`, `Compliance`
- Avoid: niche or acronym-only tags with no audience

### 10. Copy-paste workflow (the test)

Before publishing any article:

1. Paste the full `.md` into a blank Medium draft
2. Preview
3. Find every section that got mangled (tables, unusual markdown, code)
4. Fix in the source `.md` (not only in Medium) so the draft is permanent
5. Re-paste into the same draft to verify

If a draft needs manual fix-up after every paste, the draft is not Medium-ready. Update it until "paste works" is one step.

---

## Architect's rule

> **When I build the HTML preview for an article, I am not just rendering a styled version — I am simulating what Medium will show. If the preview has tables or other Markdown features that won't survive Medium's paste, the draft is wrong and I fix the draft.**

This applies every time a new article is drafted. Do not ship a draft whose tables will break.

---

## Related

- `docs/OSS_HYGIENE.md` — employer names / emails / AWS IDs out of source
- `articles/PUBLISHING.md` — the cadence + per-article checklist
- Memory: `feedback_medium_publishing.md` — assistant's version of these rules
