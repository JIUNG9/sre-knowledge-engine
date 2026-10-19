# Aegis v4.0 — Publishing Checklist

Master publishing plan for the eleven-part Medium series and accompanying LinkedIn campaign. Audience: June. Goal: spread eleven articles across roughly five months, drive GitHub stars and interview conversations, build a durable content asset. Articles #9, #10, #11 are the Layer 0 safety arc added 2026-04-21 — they come late in the sequence because Layers 0.1–0.8 must ship as code before the articles are truthful.

---

## 1. Ordering and cadence

Two to three articles per month. Start with the two articles that are strongest on their own (#1 and #3). End with #8 as the capstone. The three Layer 0 articles (#9, #10, #11) cluster together as a "safety arc" late in the series so they reinforce each other.

| Slot | Article | Why this slot |
|------|---------|---------------|
| 1 | #1 Karpathy Killed RAG | Strongest thesis, sharpest hook. Opens the series with a claim. |
| 2 | #3 Self-Maintaining KB | Showcases the live vault at aegis-wiki. Portfolio proof. |
| 3 | #5 Claude + MCP Pager | Concrete cost and workflow. Appeals to SREs evaluating the whole loop. |
| 4 | #4 Automation Ladder | Safety thesis. Pairs with #5 to show you thought about risk. |
| 5 | #2 AI Is Lying | The practical follow-up to #1. Ships the reconciliation tools. |
| 6 | #6 Monday Patterns | Specific-number viral hook. Good standalone. |
| 7 | #7 Multi-Account Guardrails | AWS-focused, deepest technical piece. Targets infra managers. |
| 8 | #9 PII Proxy for Claude | Opens the Layer 0 safety arc. Technical + unique (nobody's published this pattern). |
| 9 | #10 Honey Tokens + Kill Switches | Middle of the safety arc. Builds on #9. |
| 10 | #11 PIPA Case Study (Tier C Deployment) | Closes the safety arc. Career-defining piece for Canadian recruiters. Pin for 2 weeks. |
| 11 | #8 Open-Sourcing Aegis | Capstone of the architecture story. |
| 12 | #12 From Investigator to Operator — Wiring the Self-Healing Executor | Phase 2 capstone. The leap from "agent describes the fix" to "agent runs the fix under the 4-stage ladder." Documents Layer 4 executor (P2.5). |

---

## 2. Suggested publish schedule (Mondays + Thursdays)

Mondays are peak LinkedIn traffic. Thursdays catch weekly recap posts. Spread releases so each article has a full week of momentum before the next lands.

| Date | Day | Article |
|------|-----|---------|
| 2026-05-04 | Mon | #1 Karpathy Killed RAG |
| 2026-05-14 | Thu | #3 Self-Maintaining KB |
| 2026-06-01 | Mon | #5 Claude + MCP Pager |
| 2026-06-18 | Thu | #4 Automation Ladder |
| 2026-07-06 | Mon | #2 AI Is Lying |
| 2026-07-23 | Thu | #6 Monday Patterns |
| 2026-08-10 | Mon | #7 Multi-Account Guardrails |
| 2026-08-27 | Thu | #9 PII Proxy for Claude (Layer 0 arc start) |
| 2026-09-10 | Thu | #10 Honey Tokens + Kill Switches |
| 2026-09-28 | Mon | #11 PIPA Case Study (Tier C, pinned for 2 weeks) |
| 2026-10-19 | Mon | #8 Open-Sourcing Aegis (capstone) |

Dates can slide by up to a week if there is a personal or infra conflict. Do not double up two articles inside the same week — momentum depends on each article having its own cycle.

---

## 3. Pre-publish checklist (per article)

Run through this for every single article before hitting publish on Medium. Do not skip steps. The sanitizer pass has caught a leaking account ID every time it has been run — assume the next article has one too.

### Content pass

- [ ] Proofread the article end to end, aloud, once
- [ ] Every claim with a number has a source in the text (a runbook, a metric, a commit)
- [ ] Every code block compiles or would compile — no pseudo-syntax
- [ ] Every link is clicked and returns 200
- [ ] Images are embedded with alt text
- [ ] Screenshots use the dark theme and the large-component density (consistent visual brand)
- [ ] Author byline at the bottom, role only, no employer names: "June Gu is a Site Reliability Engineer. [LinkedIn] [GitHub] [Aegis]."

### Sanitization grep

The patterns live in a local file outside the repo, not here. Keep your real AWS account IDs, internal incident ids, hostnames, realm names and employer names in `~/.config/aegis/leak-patterns.txt`, one extended regex per line. Never commit that file and never paste its contents into this repo.

```
mkdir -p ~/.config/aegis && touch ~/.config/aegis/leak-patterns.txt   # once; then fill it in
grep -iEf ~/.config/aegis/leak-patterns.txt article.md
```

Zero matches required. Two gotchas: a blank line in the patterns file matches every line, so keep it free of empty lines; and if the file is missing grep exits 2 with an error instead of printing nothing, which is not a pass.

Also check for:

- [ ] No real AWS account IDs anywhere (only placeholder 000000000001 through 000000000005)
- [ ] No private Confluence space keys (use `EXAMPLE-SPACE` or abstracted names)
- [ ] No real internal service codenames (use `auth-service`, `gateway`, `signaling`)
- [ ] No real Slack channel names (use `#incidents`, `#on-call`)
- [ ] No personal names other than "June Gu" and public figures (Karpathy, etc.)
- [ ] No employer-confidential incident narratives — abstract the pattern, remove the specifics

### Medium preview

- [ ] Paste the markdown into Medium's editor
- [ ] Verify every code fence renders (triple-backtick with language tag)
- [ ] Verify every Mermaid diagram renders — if not, convert to image
- [ ] Set two or three Medium tags (AI, SRE, DevOps, Open Source, Platform Engineering — rotate per article)
- [ ] Set the subtitle — one sentence, concrete claim
- [ ] Set the featured image — a dark-theme screenshot or diagram
- [ ] Schedule or publish — never save-and-forget

### Cross-reference pass

- [ ] The article links back to the Aegis repo at least once
- [ ] The article links to at least one code path (e.g. `apps/ai-engine/wiki/synthesizer.py`)
- [ ] If the article references another article in the series, the link points to the Medium version (or the in-repo file if not yet published)
- [ ] README on the main repo has been updated to mark this article as "published" in the Series table

---

## 4. Post-publish checklist (per article)

### Within the first hour

- [ ] Verify the Medium URL is canonical and does not 404
- [ ] Verify the published version matches the preview — Medium has been known to silently drop embedded images on publish
- [ ] Pin the article to the top of your Medium profile
- [ ] Add the article to your LinkedIn Featured section (bump off the oldest)
- [ ] Update the Aegis repo: replace the in-repo article link with the Medium link in the README Series table

### Within 24 hours

- [ ] Post the selected LinkedIn variant from `articles/0X-<slug>/linkedin-post.md`
- [ ] Include the Medium URL at the end of the post, not at the start (LinkedIn algorithm penalizes early external links)
- [ ] Reply to every comment within four hours on day one
- [ ] DM up to five SRE or platform engineers you know personally with a "thought you might find this interesting"

### Within 72 hours

- [ ] Cross-post to DEV.to (canonical link back to Medium)
- [ ] Cross-post to Hashnode if the article is deeply technical (#2, #5, #7)
- [ ] Submit to Hacker News on Monday or Tuesday morning PT (peak traffic)
- [ ] Submit to subreddits — matched per article:
  - #1, #2 → r/LocalLLaMA, r/LangChain, r/MachineLearning
  - #3 → r/ObsidianMD, r/selfhosted
  - #4, #7 → r/devops, r/kubernetes, r/aws
  - #5 → r/sre, r/devops
  - #6 → r/sre, r/dataisbeautiful
  - #8 → r/opensource, r/cscareerquestions
- [ ] Submit to Infoq queue if the article is infrastructure-focused (#4, #7, #8)

### Within the first week

- [ ] Record metrics snapshot at 24h, 72h, and 7d (see Section 6)
- [ ] If the article is underperforming on Medium, publish the LinkedIn variant C (hot take) as a standalone post to drive fresh traffic
- [ ] Note lessons learned in a `_meta/post-mortem-<article-slug>.md` for the next release

---

## 5. Contingency — if a tech outlet picks it up

If Hacker News lands on the front page, DEV.to features the article, or Infoq picks it up:

- [ ] Do not rewrite. The version on Medium is canonical.
- [ ] Reply to the HN thread with the author flag. Do not argue. Answer questions with facts and links.
- [ ] Watch GitHub for a star burst — respond to any issues opened in the next 48 hours within the hour. First impressions on a repo are irreversible.
- [ ] If a tech blog reaches out for syndication, allow it with a canonical link back to Medium. Do not publish exclusive content on anyone else's platform.
- [ ] If a recruiter reaches out on LinkedIn citing the article, respond within 12 hours — this is the target outcome of the entire series. Keep a log of which article prompted which recruiter message; future articles should be optimized for the audience that converts.

---

## 6. Metrics to track

Per-article metrics snapshot at 24h, 72h, and 7d post-publish. Keep a running spreadsheet.

### Medium

- Views
- Reads (longer than 30 seconds)
- Read ratio (reads / views) — target above 40% for a technical piece
- Claps
- Highlights
- Followers gained in the 24h window after publish

### LinkedIn

- Impressions on each variant
- Reactions (break down like / insightful / etc.)
- Comments (quantity and quality)
- Reposts
- Profile views in the 24h window after posting
- Connection requests from the 24h window

### GitHub (Aegis and Aegis-Wiki)

- Star count before publish vs. 24h vs. 7d
- Unique clones (available in Insights → Traffic)
- Unique visitors
- Forks
- Issues opened in the 7d window (these are the highest-signal readers)
- Referrer breakdown (Medium, LinkedIn, HN, DEV.to)

### Career signals (the real metric)

- Recruiter InMails mentioning the article or the repo
- Interview requests directly linked to Aegis
- Speaking invitations — meetups, conferences, podcasts
- Open-source contributors — the first external PR is a milestone

---

## 7. Variant selection guide for LinkedIn

Each article ships with three LinkedIn variants in `articles/0X-<slug>/linkedin-post.md`:

| Variant | Audience | When to use |
|---------|----------|-------------|
| A — Technical | Senior engineers, SREs, platform leads | Default for articles with heavy architecture (#1, #2, #4, #5, #7) |
| B — Career | Recruiters, hiring managers, managers | Use when you want to drive inbound recruiter messages (#3, #6, #8) |
| C — Hot take | Broad reach, algorithm-friendly | Use when an article is slow on Medium and you want a fresh spike. Limit to two Variant C posts per quarter to avoid brand drift. |

Only post one variant per article on the day of publish. Hold the other two for a four-to-six-week "re-run" if the article needs a second spike, or for reposting on adjacent topics.

---

## 8. Repository housekeeping

After each publish:

- [ ] Update `articles/PUBLISHING.md` (this file) with actual publish date and any schedule drift
- [ ] Update the Aegis main README Series table — replace "in progress" with "published (Medium link)"
- [ ] Tag the release in the Aegis repo: `git tag series/article-0X && git push origin series/article-0X`
- [ ] Add the article to the Aegis-Wiki vault under `concepts/` or `_meta/articles.md`

---

## 9. Protection rules

- Never publish before the grep scrub returns zero matches
- Never schedule two articles in the same week
- Never post to Hacker News more than once per article (HN treats resubmits as spam)
- Never publish exclusive content on DEV.to, Hashnode, or Infoq — Medium is canonical
- Never remove an article after publish. If something is wrong, issue a correction at the bottom of the article and link to it from the top.

---

## 10. End state

Successful completion of this publishing plan produces:

- Eight Medium articles, each with traffic well into four figures
- Twenty-four LinkedIn posts (one variant per article, two held in reserve)
- One open-source repo at github.com/JIUNG9/aegis with meaningful star count and at least one external contributor
- One live portfolio vault at github.com/JIUNG9/aegis-wiki
- A durable content asset that continues to drive recruiter inbound for two-plus years
- Demonstrable platform engineering work for Canadian SRE hiring conversations in 2027

The goal is not any single article. The goal is the compound effect across all eight.
