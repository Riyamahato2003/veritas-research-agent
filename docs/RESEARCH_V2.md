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
