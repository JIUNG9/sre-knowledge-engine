# Article #10 — Honey Tokens and Kill Switches

Second Layer 0 safety article. Companion to Article #9 (PII proxy). Walks through the detection layer (honey tokens in the vault + outbound scanner) and the response layer (`aegis panic` CLI + Redis-backed kill switch).

## Files

| File | Purpose |
|------|---------|
| `article.md` | Canonical Medium markdown |
| `article.html` | Standalone dark-theme HTML preview |
| `linkedin-post.md` | LinkedIn announcement (3 variants) |
| `assets/` | Diagrams + screenshots |

## Where to publish

**Medium** — June Gu's profile.

**Tags (5):** `AI`, `SRE`, `Security`, `LLM`, `Open Source`.

Additional body tags: `DevOps`, `MCP`, `Claude`, `AI Safety`, `Canary Tokens`.

## Publishing checklist

- [ ] Proofread desktop + mobile
- [ ] Verify GitHub links resolve to `apps/ai-engine/honeytokens/` and `apps/ai-engine/killswitch/`
- [ ] Confirm code blocks render correctly (Python syntax highlighting)
- [ ] Copy the `aegis panic` terminal block into a styled "code screenshot" for feature image
- [ ] Pick 2 pull quotes for Medium blockquote styling
- [ ] Schedule Tue or Wed 9 AM ET (Canadian recruiter peak)
- [ ] Crosspost LinkedIn within 1 hour
- [ ] Pin LinkedIn for 1 week

## Cross-references

- Predecessor: Article #9 (PII proxy). This piece assumes the reader has skimmed that one.
- Successor: Article #11 (PIPA case study). Teased in the closing section.
- Source code references:
  - `apps/ai-engine/honeytokens/` — generator, registry, scanner, seeder
  - `apps/ai-engine/killswitch/` — switch, gate, aws_revoke, panic CLI
  - `apps/ai-engine/cli/panic.py` — Typer CLI

## Notes

- Sanitized — no real org names in code examples beyond the already-public "Aegis" branding.
- The `aegis-honey-root-7f3a91b8c4` examples are illustrative strings, NOT real tokens from the registry.
- Terminal mock for `aegis panic` uses account ID `123456789012` (AWS docs placeholder).
