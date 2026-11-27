# Veritas evaluation

## Method

This report separates deterministic contract/failure tests from live-provider research. Fixture outputs are authored examples; they are not evidence of real-world factual accuracy. Live runs were made against the public API on 2026-11-27 with Tavily and Groq configured. No keys were retrieved or logged. Live response JSON and evidence snapshots are saved under `samples/` when they come from the final deployed revision.

## Automated checks

Local Python 3.13 run: **67/67 unit and adapter tests passed**; **11/11 scenario checks passed**; baseline comparison completed. Reproduce from the repository root:

```bash
python -m unittest discover -s tests -v
python evaluate.py
python baseline.py
```

The tests cover input and response contracts, routing, citation IDs, candidate attribution, requirement coverage, unsupported numbers/qualifiers, malformed tool responses, injection filtering, timeouts, transient errors, total outage, provider rate-limit handling, log redaction, and recovery. Provider integrations are mocked in tests. The scenario corpus uses local records and simulated faults. `docs/evaluation-results.json`, `docs/baseline-results.json`, `docs/test-results.txt`, and the Evaluation page are generated/check-in artifacts; no scenario score is a live factual-quality metric.

| Test query/scenario | Expected behavior | Observed fixture result | What worked / did not |
|---|---|---|---|
| Compare top 3 open-source vector databases for RAG | Three distinct candidates; ranking withheld | Partial, low confidence; 6 source records | Candidate labels and citations exist; fixture coverage is intentionally incomplete, and no ranking is established. |
| Find 5 Indian B2B SaaS HR-tech startups | Five eligible companies with positioning | Complete, medium; 5 records | Demonstrates web-first routing only. Authored fixture records do not establish real eligibility. |
| Multi-agent architecture for customer support | Explain pros and cons with sources | Complete; 3 records | Fixture relevance/structure check passed; no live claim validation. |
| Memory approaches for an AI support agent | Compare distinct approaches | Complete; 3 records | Fixture scenario passed; not evidence that the descriptions are accurate or current. |
| Invented “xenoflux quorbanic tessellation” | Abstain when evidence is absent | Insufficient; 0 sources | Deterministic abstention and recovery path passed. |
| Total retrieval outage | Structured answer without fabricated facts | Insufficient; 0 sources; 8 bounded simulated attempts | Failure trace and safe abstention passed. |
| Prompt-injection record | Treat retrieved instructions as untrusted data | Suspicious record rejected; clean records retained | Heuristic filter passed this fixture; it is not a general prompt-injection defense. |

The baseline asks one GitHub lookup. On the fixture vector query it returned 3 records normally, 0 during simulated GitHub timeout, and 0 during total outage. The agent returned 6, 4, and 0, using 3, 4, and 8 attempts. This demonstrates tool fallback and bounded retries, not answer quality.

## Live baseline before CP31 corrections

These two calls ran on deployed `cp30-prototype`, before the candidate-attribution and confidence changes. They are preserved as diagnostic evidence of the defect; they are **not** final sample outputs.

| Question | Expected behavior | Observed result | What worked | What failed / limitations |
|---|---|---|---|---|
| Compare the top 3 open-source vector databases for a startup building RAG products | Three defensible candidates, comparable technical/practical tradeoffs, citations for each claim, no absolute ranking without a method | Partial; Qdrant, Weaviate, Milvus discovered; 3/3 candidates had some reviewed claim; 5/9 criterion slots; 0/3 fully covered; 8/18 claims accepted; 12,888 reported tokens; 4 searches + 1 extract estimate; 8.85 s | Retrieval and all 5 Groq calls succeeded; citations resolved; provider health was OK; rejected 10 proposed claims | The short answer made a claim about Qdrant hybrid search/reranking using a passage whose source context was about LanceDB. The reviewer accepted the cross-entity attribution. It also reported medium confidence with incomplete coverage. No absolute ranking or complete comparison was established. |
| Find 5 Indian B2B SaaS startups in HR tech and summarize positioning | Five distinct companies with explicit supported eligibility and positioning | Partial; 5 candidates discovered, 4 had reviewed claims, 3/5 fully covered, 7/20 claims accepted; 11,693 reported tokens; 4 searches + 1 extract estimate; 8.77 s | Web search, extraction and all 5 model calls succeeded; four companies received cited positioning claims; 13 claims were rejected | Only four entities appeared in the short answer; Darwinbox had no accepted claim. Eligibility and startup status were not independently established; retrieved pages included secondary lists and broad SaaS material. Medium confidence overstated the incomplete result. |

The 2026-11-27 corrections require candidate-specific citations to name the candidate in every cited passage or its title, and show low confidence for incomplete coverage or degraded provider health. The rule is intentionally conservative and can reject useful generic evidence. It cannot prove entailment, establish startup eligibility, or guarantee source truth. Final deployed observations are recorded below after release verification.

## Remaining evaluation limits

- The live sample is small, with no human-labeled reference set or statistical accuracy estimate.
- Model review is fallible and shares the model family's limitations; citation linkage is not factual validation.
- Search snippets and selective extraction may omit context, source dates, or material qualifications.
- Startup status, headquarters/geography, open-source licensing, product claims and “top” rankings need primary-source checks.
- The current confidence field is a coarse low/medium workflow heuristic, not a calibrated probability. High is not assigned by the live engine.
- Search-credit counts are estimates, token counts are provider-reported, and latency is from individual runs.
- The original assignment document was not present in the repository or connected Drive search; this evaluation follows the full requirements in the supplied project brief.

## Next evaluation iteration

Human-review at least 50 diverse questions, including multilingual, conflicting, temporal, adversarial and entity-list queries. Score source relevance, entity eligibility, claim-level support, citation correctness, criterion coverage, unsupported-assertion rate, safe abstention, latency, token use and provider costs. Compare the same frozen evidence through previous and revised synthesis where available. Calibrate confidence only after collecting held-out human judgments.
