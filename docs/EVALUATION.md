# Veritas evaluation

## Method

This report separates deterministic contract/failure tests from live-provider research. Fixture outputs are authored examples; they are not evidence of real-world factual accuracy. Live runs were made against the public API on 2026-11-27 with Tavily and Groq configured. No keys were retrieved or logged. Live response JSON and evidence snapshots are saved under `samples/` when they come from the final deployed revision.

## Automated checks

Final local Python 3.13 run: **72/72 unit and adapter tests passed**; **11/11 scenario checks passed**; baseline comparison completed. Final GitHub CI passed on Python 3.10 and 3.13. Reproduce from the repository root:

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

The first correction release required candidate-specific citations to name the candidate in every cited passage or its title, and showed low confidence for incomplete coverage. A repeat vector run found a different cross-entity error: one source passage named Qdrant, Milvus and Weaviate together, then assigned the high-availability caveat specifically to Milvus; the model attached that caveat to Qdrant. That run was partial with low confidence, covered 7/9 criterion slots, fully covered 1/3 candidates, accepted 7/17 proposals, used 4 searches plus 1 extract estimate, reported 12,657 tokens, and took 9.36 s. All 5 model calls succeeded. This demonstrated that passage-level co-mention checks are not enough.

The next correction requires every candidate claim to repeat its subject and rejects claims whose feature wording overlaps a different candidate's explicitly named possessive or verb-owned clause in the same passage. This remains a conservative lexical heuristic: it can reject relevant evidence and does not prove entailment or source accuracy. The final deployed live evaluations against the second correction release are recorded below.



## CP31 second-correction live evaluation (2026-11-27)

These two calls ran against the public production alias after the second CP31 correction (runtime reports `cp30-prototype`; source commit `d2d26b3`) but before the CP32 recovery refinements. Raw API responses are preserved as `samples/live-vector.json` and `samples/live-hr.json`. Provider calls succeeded and citation IDs resolved in both; these are single-run observations, not a benchmark.

| Question | Expected behavior | Observed result | What worked | What failed / limitations |
|---|---|---|---|---|
| Compare the top 3 open-source vector databases for a startup building RAG products | Three defensible candidates, comparable dimensions, grounded claims, no unsupported ranking | Partial, low confidence; Chroma, Milvus and Qdrant discovered/reviewed; 6/9 criterion facets, 0/3 fully covered; 10/17 claims accepted; 11,925 reported tokens; 4 searches + 1 extract estimate; 8.74 s | All 5 Groq calls succeeded; no provider errors; citations intact. Recovery claim validation explicitly rejected one multi-entity feature attribution as `feature_owned_by_other_entity`. Final output did not repeat the previously observed Milvus high-availability caveat as a Qdrant claim. | The response still lacks a full comparison and does not validate a “top” ranking. The owner rejection is one targeted regression observation, not proof the heuristic catches all attribution errors. Some accepted claims are promotional or broad; source quality and current product/license details need human review. |
| Find 5 Indian B2B SaaS startups in HR tech and summarize their positioning | Five eligible companies, each with independently supported eligibility and positioning | Partial, low confidence; five names discovered and reviewed (Zimyo, Workline, Darwinbox, sumHR, Leena AI); 5/10 facets, 0/5 fully covered; 10/20 claims accepted; 12,868 reported tokens; 4 searches + 1 extract estimate; 11.24 s | All 5 Groq calls succeeded; no provider errors; five cited positioning snippets/claims are present, and the system correctly marks incomplete coverage low confidence. | It does **not** establish all five are Indian B2B SaaS startups: eligibility facets are missing for every candidate, and some evidence is secondary or directory-like. Do not treat the list as verified. |

The live rerun therefore confirms the confidence downgrade and catches the specific cross-entity clause seen after the first fix, while the HR eligibility and complete-comparison requirements remain unmet. These outputs should be presented as partial research with visible gaps, not successful completion of either request. No confidential credentials were fetched or included in the reports.

## Remaining evaluation limits

- The live sample is small, with no human-labeled reference set or statistical accuracy estimate.
- Model review is fallible and shares the model family's limitations; citation linkage is not factual validation.
- Search snippets and selective extraction may omit context, source dates, or material qualifications.
- Startup status, headquarters/geography, open-source licensing, product claims and “top” rankings need primary-source checks.
- The current confidence field is a coarse low/medium workflow heuristic, not a calibrated probability. High is not assigned by the live engine.
- Search-credit counts are estimates, token counts are provider-reported, and latency is from individual runs.
- The original assignment document was not present in the repository or connected Drive search; this evaluation follows the full requirements in the supplied project brief.

## Evaluation boundary

This take-home closes with a small set of assignment and unseen live queries plus deterministic offline tests. A 50-question benchmark is outside scope. Before real use, manually review a representative set of claims and sources, then calibrate confidence and measure latency/cost across a larger held-out set.

## Bounded final release validation (2026-11-27)

The final coverage refinements are in production commit `ef7a822d643d42705e367cfdcff6c600396298cc` (`cp30-prototype`). PRs #4–#6 passed GitHub Actions on Python 3.10 and 3.13. Local checks: **72/72 unit tests**, **11/11 offline scenarios**, baseline comparison completed, and `git diff --check` clean. Representative reports contain every mandatory response field: question, short answer, findings, sources, confidence, limitations, assumptions, suggested next steps, plan, trace and metrics. Static UI inspection confirms the report renderer displays confidence, coverage, evidence links/passages, limitations, assumptions, next steps, plan and trace. Direct visual browser verification was blocked by the user declining the browser origin approval; it was not retried by another route.

| Live query | Observed outcome | What worked | Remaining gap |
|---|---|---|---|
| `Research the pros and cons of using a multi-agent architecture for customer support automation.` | Complete, medium heuristic confidence; benefits and risks covered (2/2 facets); 4/4 claims accepted; 5 source records; 3 model calls, 2 Tavily searches + 1 extraction estimate; 4,951 tokens; 3.35 s | Best available live happy-path candidate: relevant support-automation framing, linked passages, both sides, no provider errors. Raw report: [`live-success-multiagent.json`](../samples/live-success-multiagent.json). | Manual spot-check found one benefit claim generalizes a vendor case-study result and one risk claim adds “misrouting” beyond the cited passage. Treat this as workflow success with a visible source-quality caveat, not independently verified factual truth. The source mix includes vendor and secondary material. |
| `Compare different approaches to adding memory in an AI support agent.` | Partial, low confidence; 5 proposed approaches, 0/8 facets reviewed; 25 claims rejected (`entity_not_in_evidence` 12, `claim_subject_missing` 13); 5 model calls, 3 Tavily searches + 1 extraction estimate; 7,994 tokens; 7.76 s | The system withheld unsupported claims and exposed the rejection stage. Raw report: [`live-partial-memory.json`](../samples/live-partial-memory.json). | Retrieved passages described memory generically but did not identify the proposed approach labels in the cited evidence. Planner also generated four requirements for an open-ended approaches question. Primary observed issue: claim/evidence attribution and proposal quality, not provider availability. |
| `Compare REST APIs, GraphQL and gRPC for communication between microservices in a production environment.` | Final deployed run: partial, low confidence; all 3 explicit alternatives tracked; 4/12 facets covered; GraphQL and gRPC reviewed, REST unresolved; 4 claims accepted, 12 proposed, 8 rejected; 4 searches + 1 extraction estimate; 11,067 tokens; 11.38 s | The target parser retained all three names; bounded recovery queried the named alternatives rather than substitutes. Citation linkage was intact and provider health was OK. Raw report: [`live-partial-unseen.json`](../samples/live-partial-unseen.json). | REST evidence remained insufficient. An earlier attempt returned a 429 at synthesis; after respecting `retry-after: 2`, one retry succeeded. No repeated retry loop was used. This demonstrates partial generalization with explicit gaps, not a complete comparison. |
| `Summarize how PostgreSQL documentation describes MVCC and its role in concurrent reads and writes.` | Partial, low confidence; 0/2 facets covered; 4 claim proposals rejected for `claim_subject_missing`; 3 model calls, 4 Tavily searches + 1 extraction estimate; 6,515 tokens; 6.17 s | Retrieved official PostgreSQL documentation alongside secondary explanations and exposed the validation failure. | The synthesizer emitted candidate-style claims without explicit subjects for a general explanatory question. The engine withheld them. This is a live failure observation, not a success. |
| Simulated total retrieval outage | Insufficient, low confidence; no factual claims; 8 bounded simulated attempts | Safe structured abstention and failure trace; no provider credits used. Raw output: [`failure-simulated-outage.json`](../samples/failure-simulated-outage.json). | Offline deterministic simulation, not a live outage. |

The complete multi-agent report was generated on commit `307616969de1d79bd39192cc41289e13f4142a9a`. PRs #5 and #6 only changed explicit named-comparison parsing and recovery, so this tradeoff-query path was unaffected. It remains the best live complete-path demonstration, with its manual claim-quality caveat stated above.

### Root causes and corrections

- **Vector database query:** initial searches emphasized general RAG capabilities; the recovery trace targeted only Chroma and Milvus and repeated a generic “practical tradeoff or limitation” phrase. The remaining R3 facet had no accepted candidate-specific claim. One multi-entity feature was correctly rejected (`feature_owned_by_other_entity`); no broad passage-selection failure is established. The primary observed causes were incomplete criterion-focused recovery and weak candidate-owned tradeoff evidence; facet classification also drifted once. The final code batches missing criteria across candidates within the existing two-search budget and deduplicates after reviewer classification. The vector query was not rerun after this refinement, so improvement is covered by deterministic regressions, not a fresh live claim.
- **HR-tech query:** discovery returned five names, but retained passages were mostly secondary lists/directories and did not prove Indian B2B SaaS/startup eligibility for any candidate. The reviewer accepted positioning claims but rejected all five recovery eligibility claims as `not_entailed`. Generic eligibility wording and recovery searches for only two candidates compounded the evidence gap. The final rubric and recovery terms now express the India/HR/SaaS constraint explicitly and batch affected candidates; the HR query was not rerun after the final refinement.
- **Memory comparison:** 25 proposals were rejected because the cited text did not name the synthesized approach or the statement omitted its subject. This is primarily claim/evidence alignment. No content was forced through validation.
- **Unseen comparison:** the first parser used target 2 and omitted a third explicit name when the planner returned an empty `named` list. A small comma/“and” parser now preserves explicit alternatives. The deployed run tracked all three, then recovery targeted the named options; REST still lacked reviewed evidence.

### Response contract check

Static contract inspection and representative exported reports confirmed `question`, `short_answer`, `key_findings`, `sources_used`, `confidence`, `limitations`, `assumptions`, `suggested_next_steps`, `status`, `plan`, `trace`, and `metrics`. The complete, partial, unseen and failure samples contain these fields; accepted claim source IDs resolve to entries in `sources_used`. Browser-origin approval prevented direct visual verification of the deployed UI. Vercel reports the production deployment READY and public live API requests were exercised; perform the visual UI check during the manual recording.

The original assignment document was read from the supplied pasted text; it is not included in the repository. The provider returned a rate-limit response during one unseen-query attempt; after respecting its `retry-after` value, one retry succeeded. No repeated retry loop was used.

### Manual deployment-protection cleanup

A temporary Vercel **Protection Bypass for Automation** secret was created during protected-preview diagnostics. It remains to be revoked. The earlier Vercel dashboard browser-origin approval was declined, and no alternate access route was used. Manually remove it in **Project Settings → Deployment Protection → Protection Bypass for Automation → revoke/delete secret**. No provider credentials were changed.
