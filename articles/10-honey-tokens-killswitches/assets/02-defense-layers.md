| Layer | Catches | Misses | Response time |
|---|---|---|---|
| **PII proxy** (Article #9) | Pattern-matchable PII, secrets, hostnames | Paraphrased summaries, novel formats | 0ms (prevention) |
| **Honey tokens** (this article) | Anything that leaks verbatim, including unseen patterns | Paraphrased or re-keyed content | ~1ms per scan (detection) |
| **Kill switch** (this article) | Active misbehavior, runaway tool calls | Past leaks (cannot un-send) | ~5ms check, ~2s to fully halt |
