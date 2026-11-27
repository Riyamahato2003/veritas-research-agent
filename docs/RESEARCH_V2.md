# Passage-indexed research engine (CP17–23)

## Why
CP16 measured 7/9 HR claims rejected for quote-copy mismatch; 2/8 in a second architecture run. These are historical observed traces, not a model benchmark. V2 never requests model-generated quotations.

## Implementation
- CP17: deterministic request shape + optional model-decomposed facets and targeted queries. Explicit numbered targets remain deterministic; model facets are bounded and validated.
- CP18: basic Tavily search with provider scores, query overlap, source-quality hints and explicit rejected titles. Selective Tavily Extract of up to three discovered HTTPS pages via fixed endpoint. No arbitrary server URL fetch.
- CP19: content-addressed source and passage IDs; original normalized text retained. Validation requires known passage IDs and explicit named entity context; no quote-copy failures by design.
- CP20: per-candidate requirement matrix; all required facets need approved claims before a candidate counts. Tradeoff benefit and risk criteria are separately tracked. Multi-source claims can cite up to three passages.
- CP21: one recovery round from missing requirements/discovered labels; bounded by time and provider call caps. Reviewed claims preserved across rounds.
- CP22: deterministic ID/number checks plus separate Groq reviewer with reason codes and fail-closed publication. Same-model review is fallible; source authority heuristic is not proof, eligibility is not independently verified, alias detection is lexical.
- CP23: frozen artificial evidence tests and live smoke test procedure. Offline tests demonstrate behavior, not external factual accuracy. Use human review of exact passages for factual assessment.

## Budget
At most 5 basic web searches, one extraction batch (up to 3 pages), initial background tool, at most 5 Groq requests (intent, initial draft/review, recovery draft/review), 48-second soft execution budget. Network calls have socket timeouts, not cancellable strict wall deadlines. Live requests do not retry 429 blindly. Demo retains original retry/failure scenarios. Estimated credits = basic searches attempted + extraction batch (conservative estimate for basic extraction, not provider invoice). Provider limits may differ.

## Observability
Every live report has engine version, run ID, chronological offsets, stage times, provider attempts/errors, Groq reported token counts, claim rejection reasons, per-entity coverage, and recovery decisions. Opt-in diagnostic trace includes the passage snapshot and selected IDs; it is returned to the requesting client only. Vercel receives a JSON aggregate run summary (no question, source text, URLs, API keys or prompts); retention depends on Vercel plan. There is no durable metrics store, alerting, or distributed rate limit.

## Real-world acceptance
Check five assignment/unseen questions; inspect citations and eligibility for each candidate. Do not interpret complete as proof of truth. Compare CP16's quote-copy rejections to V2 ID failures; evaluate useful entity coverage, claims accepted/rejected, p50/p95 latency, token and search usage, and fallback behavior across repeated runs. A handful of live smoke tests are not statistical accuracy evidence.

A frozen artificial evidence replay asserts that a punctuation-altered legacy quote fails while the same supported claim with a stable passage ID passes structural validation. This isolates quote-copy failure without claiming semantic accuracy. Authentication/rate-limit model errors suppress subsequent Groq calls in the same run; skip events are not counted as attempts.

## Quota-aware revision (live audit)
The initial CP17–23 production smoke reproduced Groq 429 on three queries. The HR-tech request used 6,600 tokens before review. Compact request-local passage handles map back to immutable backend IDs; context is capped at 32 passages and 8,500 passage characters, review input deduplicates cited evidence, and smaller completion caps are used. Default task routing uses GPT-OSS 120B for synthesis and GPT-OSS 20B for planning/review; override `GROQ_MODEL` and `GROQ_AUX_MODEL` independently. Role assignment is not an automatic model-switch retry on quota failures. Quota headers and per-model usage are logged, not secrets. Actual quotas are account-specific and concurrent use can still exhaust them.

## CP25 — coverage accounting and evidence scope
The quota-aware production HR-tech audit (run `92e46471b1274b53963b51840a74f5aa`) completed five model calls without HTTP 429 and returned 16 reviewed claims, but coverage was wrongly reported as zero because the planner supplied generic category phrases as mandatory named candidates. Corrected list intent handling, added conservative qualifier checks and duplicate suppression, prioritized near-complete candidates and reserved discovery capacity, and exported every model-selected passage in diagnostic mode. The audit exposed remaining semantic-review errors; reviewer approval is not proof of factual correctness.

## CP26–30 — prototype finish
Separate evidence linkage/review from completeness and provider health. Count partially reviewed candidates and individual criterion slots alongside fully covered candidates. Do not append redundant mandatory facets to numbered lists. The existing review call may correct a claim's criterion using a valid ID; it cannot rewrite a statement or add citations. The short answer represents distinct candidates; the UI explains partial outcomes and displays human-readable missing criteria. A claim may have model-reviewed evidence and still be part of a partial answer. No claim of factual verification, calibrated confidence, enterprise infrastructure or guaranteed coverage.

## CP31 — live attribution and confidence correction
Live inspection first found a Qdrant claim citing a contextless “It indexes…” passage from a page section about LanceDB. Candidate claims now repeat their candidate name, and structural validation requires every cited passage or its title to name that candidate. A subsequent live run exposed a subtler case: a passage named Qdrant, Milvus and Weaviate together, then assigned a high-availability caveat specifically to Milvus; the model placed that caveat under Qdrant. Validation now rejects feature text that overlaps with another named candidate's possessive/verb-owned clause. This rule catches the observed structure but is heuristic, may reject valid comparative evidence, and is not general entailment. Confidence is now `medium` only when reviewed coverage is complete, provider health is good, and at least two sources are cited; otherwise it is `low`. The UI displays confidence alongside evidence and coverage indicators.


Final CP31 production check: the vector run rejected one feature-owner mismatch and kept confidence low with 6/9 facets; the HR run found five candidates but had no eligibility coverage (5/10 facets). Neither query met its requested coverage. Raw reports and details are in `docs/EVALUATION.md`.

## Final CP32 closeout

List eligibility facets now retain the question's explicit geography/product constraints. The single recovery pass groups missing requirements across candidates within the existing search budget. Candidate claims are deduplicated only after semantic review can correct their requirement IDs. A deterministic parser preserves explicit comma/“and”-separated compare alternatives if model planning omits names; named alternatives with no reviewed evidence are coverage gaps, not a prompt to discover substitutes. Live evaluation still found incomplete HR eligibility, memory attribution and REST evidence; see `docs/EVALUATION.md` and the representative raw reports.
