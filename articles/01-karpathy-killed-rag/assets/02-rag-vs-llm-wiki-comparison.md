| Dimension | Traditional RAG (Pinecone + Voyage) | LLM Wiki (Obsidian + Claude Haiku) |
|---|---|---|
| **Storage** | Managed vector DB, proprietary | Local markdown + git |
| **Cost** | $30-100/mo baseline + per-query | $0.50-2/mo synthesis + ~free queries |
| **Staleness handling** | None built-in; bolt-on metadata | First-class `freshness` field |
| **Contradictions** | Ignored — returns all matches | Detected, flagged, escalated |
| **Human editability** | Rebuild index after edit | Edit the markdown file |
| **Portability** | Locked to vendor | Markdown + git, anywhere |
| **Portfolio value** | Opaque vector blob | Public GitHub repo |
| **Review workflow** | None | PRs, diff, blame, comments |
| **On-call experience** | "Why did it say that?" | Read the page |
