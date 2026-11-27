# Evaluation notes

## Scope and method

Run `python -m unittest discover -s tests -v`, `python evaluate.py`, and `python baseline.py` from the root. The deterministic corpus contains authored example records with reference URLs; it is not collected live and must not be used as factual gold evidence. Assertions check orchestration, result coverage, citation integrity, fallback and safety behavior. All four assignment example questions are included; the fifth is a deliberately unknown query. Six additional fault scenarios use the vector database question. The model and provider adapters have mock contract tests. The build used Python 3.13.5.

## Results

23/23 automated tests and 11/11 scenario checks passed on the final local run. See `test-results.txt` and `evaluation-results.json` for actual outputs and timings.

| Query/scenario | Expected behavior | Observed | Result |
|---|---|---|---|
| Compare top 3 open-source vector databases for RAG | Find Qdrant, Milvus, Weaviate; no unsupported ranking | 6 evidence records, partial, medium | Pass |
| Find 5 Indian B2B SaaS startups in HR tech | Web-first routing and 5 positioning records | 5 records, complete, medium | Pass |
| Multi-agent architecture for customer support | At least 2 relevant sources | 3 records, complete, medium | Pass |
| Approaches to adding agent memory | At least 2 relevant sources; exclude unrelated multi-agent result | 3 records, complete, medium | Pass |
| Explain xenoflux quorbanic tessellation | One recovery step then abstain | 0 records, insufficient, low | Pass |
| Vector query, GitHub timeout | 2 GitHub attempts; partial answer | 4 records, partial, low | Pass |
| Vector query, all providers unavailable | No fabricated answer; bounded attempts | 0 records, insufficient, low | Pass |
| Vector query, malformed GitHub output | Reject schema, continue | 4 records, partial, low | Pass |
| Vector query, suspicious instructions | Reject injection-like result | 6 clean records, partial | Pass |
| Vector query, irrelevant sports result | Reject unrelated result | 6 clean records, partial | Pass |
| Vector query, transient timeout | Successful second attempt | 6 records, 6 attempts | Pass |

## Baseline

The baseline uses only the first GitHub lookup, with no retry, fallback or multi-provider selection. On the same vector query, it returns 3 records normally, 0 during GitHub timeout, and 0 during total outage. Veritas uses 6, 4, and 0 respectively, with 3, 4, and 8 retrieval attempts. This demonstrates recovery and broader evidence coverage at the cost of more tool calls; it does not measure factual quality or show that more sources always improve answers. See `baseline-results.json`.

## What broke and what changed

The initial scenario run was 10/11: the HR filter dropped one relevant record because its vocabulary did not overlap the query. The memory and architecture scenario initially admitted off-topic results based only on generic terms such as agent. Tightened topic anchors, revised fixture descriptions to make the authored example semantics explicit, and added assertions excluding unrelated framework records. The changes improve these regressions but may reduce recall for synonyms or unfamiliar domains. This is not evidence of improved live retrieval quality.

## What worked well

- Explicit route selection, bounded retry and recovery, and traces make failures reproducible.
- Exact-span validation rejects invented citations and invalid model proposals, with deterministic fallback.
- Offline scenarios and mock adapters run without credentials and no network dependency.

## What did not / not established

- Live public API requests failed DNS resolution in this environment. Actual GitHub, Wikipedia and Brave integration success is unverified; the historical live network check correctly abstained. The original model provider was OpenAI; CP11 migrated to Groq with mocked contract tests. No live Groq or Brave credentialed test has been completed. Live mode is not silently replaced by demo mode.
- Source content is authored fixture material rather than a verified snapshot; no claim of factual accuracy, company startup status, source freshness, market rankings, or benchmark performance is justified. Lexical relevance and simple injection matching are imperfect. Source count is a proxy, not proof of requested entity count.
- The optional LLM selects spans rather than producing rich free-form analytical synthesis. This trades fluency for verifiability. No end-to-end LLM quality, semantic entailment, calibration, load or cost benchmark has been measured.
- Local elapsed times do not measure production network latency. Socket timeout is not a global deadline.

## Next evaluation iteration

Collect 50–100 human-labeled queries across domains, including ambiguous, multilingual, conflicting, adversarial, and time-sensitive requests. Measure retrieval recall@k, source relevance, claim-level support, coverage of requested entities, answer correctness, abstention precision/recall and injection attack success; compare against the same model without retrieval and against the single-tool baseline. Run live smoke tests, fault tests with real HTTP mock servers and rate-limit stress, and track p50/p95 latency, tokens, cost and provider errors. Calibrate confidence against held-out judgments. Report quality by query class and disclose uncertainty.
