# Development checkpoints

| Checkpoint | Status | Evidence |
|---|---|---|
| CP1–7 Core agent | Implemented | Contracts, planner, bounded tools, offline demo and fault lab |
| CP8 Docs and demo | Script prepared; recording pending | README, evaluation, manual recording guide; no MP4 is included |
| CP9 Repository and deployment | Existing public GitHub repo and Vercel app verified | Live site/API checked on 2026-11-27; final change deployment is tracked separately below |
| CP10–30 Research iterations | Historical checkpoints retained | See sections below and `docs/RESEARCH_V2.md` |

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

CP15 regression correction: the first CI run exposed singular/plural mismatches in the stricter relevance filter; corrected without changing the existing tests. Live coverage uses reviewed labels rather than number of source URLs.

## CP16 — Observability-only diagnostic audit

An isolated public-endpoint audit reproduced 2/5 HR-tech coverage (15 accepted web rows, 10 retained, two claims reached review; both approved) and 0/2 multi-agent coverage (19 accepted rows, 16 retained, first model call failed). Add bounded per-query retrieval counts, raw proposal/validation rejection reasons, provider error categories, model finish reason/token usage, and opt-in retained evidence snapshots in the response trace. No API keys, raw provider error bodies, or server-side question logging. No change to search or answer-selection policy. Audit workflow: https://github.com/Riyamahato2003/veritas-research-agent/actions/runs/45959543108.

## CP17–23 — Passage-indexed, coverage-driven live engine

New live pipeline with intent decomposition, provider-score ranking, bounded Tavily extraction, immutable passage IDs, explicit per-candidate requirements, missing-coverage recovery, fail-closed claim review, and privacy-minimized correlated run telemetry. The original demo remains unchanged. See `docs/RESEARCH_V2.md`; provider credentials and live acceptance are separate from CI.

## CP26–30 — prototype reporting and quality polish
Separate citation linkage, evidence review status, candidate discovery/review, facet coverage and provider health. Correct requirement assignment in the existing review pass, simplify numbered-list rubric, prefer atomic claims, and explain partial answers directly in the UI. Preserve the original demo and provider budgets. No production infrastructure expansion.

## CP31 — Live audit, entity attribution and confidence
On 2026-11-27, verified that the deployed `cp30-prototype` API and both providers were available. A live vector database run discovered three candidates but covered only 5/9 requested criterion slots; zero candidates were fully covered. Manual passage inspection found that a Qdrant claim cited an anaphoric “It indexes…” passage from a source section about LanceDB. A separate HR-tech run found four candidates with reviewed claims out of five, three fully covered, and only four entities in its short answer. Provider calls succeeded in both runs. Added a deterministic per-passage candidate attribution gate, a confidence heuristic that stays low when coverage is incomplete or provider health is degraded, and a visible confidence metric in the UI. These checks reduce one observed attribution failure but do not establish general semantic entailment or factual accuracy.
