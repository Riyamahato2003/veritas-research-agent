# Development checkpoints

| Checkpoint | Status | Evidence |
|---|---|---|
| CP1 Contracts and architecture | Complete | `veritas/contracts.py`, README |
| CP2 Planner and tool selection | Complete | `veritas/planner.py` |
| CP3 Research adapters | Implemented; live blocked | `veritas/tools.py`, `fixtures.json`, live-network-check.json |
| CP4 Synthesis and citation gate | Complete offline/mock | `veritas/model.py`, `agent.py` |
| CP5 Reliability and tracing | Complete within scope | bounded retries, malformed result handling, fault lab, trace |
| CP6 Evaluation | Complete offline | 23 unit/adapter tests, 11 scenarios, baseline |
| CP7 CLI and outputs | Complete | `python -m veritas`, 3 generated reports |
| CP8 Docs and demo | Complete local files | README, evaluation, script; separate MP4 |
| CP9 Repository | Local Git repository complete; remote pending | Git history and bundle; external GitHub repository creation/push and demo hosting pending |

Actual Git commits represent grouped checkpoints, not fictional historical milestones. No external services were deployed.

## CP11 — Groq migration and public live mode

Replaced the model API with Groq's Chat Completions endpoint; default `openai/gpt-oss-120b` is served by Groq, not OpenAI API. Removed the access-code gate and UI input at the user's request. Added provider-contract and public-live regression tests. Live calls remain unverified until credentials are configured. Public usage is bounded per run but has no distributed rate limit; configure provider limits before sharing widely.

## CP12 — Tavily web search

Replaced Brave with Tavily basic search using `TAVILY_API_KEY`. Retained the `web` tool identity, planner, fixtures, and evidence validation. Automatic search-depth selection and provider-generated answers are disabled. Added request-contract, missing-key, and malformed-response tests.

## CP13 — Live answer coverage and comparative synthesis

User-reported vector-database run returned two definitions for a requested three-way comparison. Preserve full live web query intent, use the existing single recovery budget for comparison-focused evidence, supplement sparse model selections with exact passages, and expose separately labeled source-linked AI analysis with structural citation and lexical checks. This is not semantic entailment verification or a guarantee of distinct entity coverage. Added mocked regression cases; re-run live research to assess quality.

## CP14 — Reject unsupported synthesis and retrieve candidate-specific evidence

User-reported CP13 output cited Qdrant passages for Milvus/Chroma claims. Replace lexical-only synthesis with verbatim-only excerpts; use bounded candidate-specific web follow-up for vector comparisons and render per-entity/criterion evidence with missing fields explicitly marked. Candidate names are retrieval hints, not facts or rankings. Max six retrieval steps (12 attempts) in this specialized live path; original demo budget unchanged. No claim of independent semantic verification.

## CP15 — General structured research and claim review

Four user-reported live queries exposed incomplete lists, irrelevant repository results and quotation-only comparisons. Replace the active specialized candidate path with topic-independent sections and complementary retrieval. Each proposed claim needs an exact source span; a separate conservative Groq review must affirm its support and relevance. Count reviewed labels/categories separately from sources. Withhold synthesis if review fails, and retain exact excerpts as evidence. The same-model reviewer is fallible; entity identity and eligibility still need human verification. New mocked tests cover unseen entities, cross-entity citations, rejection, duplicate verdicts, and verifier outages.
