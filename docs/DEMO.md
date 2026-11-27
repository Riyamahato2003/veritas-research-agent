# 3–5 minute recording guide

No recording is included in this repository. Record and host the video manually before submission. Use the live site at https://veritas-research-agent.vercel.app and avoid displaying API keys, browser developer secrets, or personal account information.

## Suggested 4-minute run

### 0:00–0:30 — Problem and scope

“Veritas is a bounded research agent. It turns a question into a plan, uses read-only search tools, filters evidence, and returns claims linked to source passages. It is a focused single-agent prototype, not a general production platform.”

### 0:30–1:00 — Architecture

Open the Architecture tab. Point out intent planning, Tavily search and selective extraction, GitHub/Wikipedia routing, passage indexing, separate claim review, coverage accounting, and bounded recovery. Mention that live calls are capped and rate-limit errors stop further model calls.

### 1:00–2:20 — Live research

Select Live mode and run: “Compare the top 3 open-source vector databases for a startup building RAG products.” Show the returned short answer, confidence, candidate/criterion coverage, limitations, citations, and one supporting passage. Open Plan and Trace to show the actual queries, rejected claims, recovery decision, provider health, latency, and token use. Explain that “medium/low” is a transparent heuristic, not a probability, and that a model-reviewed citation is not proof of truth. Use the committed live sample only if provider quota temporarily blocks a fresh run, and label it as a saved observation.

### 2:20–3:10 — Failure handling

Switch to Demo mode, choose the total outage simulation, and run a vector-database question. Show the insufficient-evidence response and trace. Explain that the deterministic fault lab uses authored fixtures and does not consume provider credits.

### 3:10–4:00 — Evaluation and limits

Open Evaluation and show the 68 regression tests and 11 offline scenario checks (update counts if they change). Point to the evaluation report for live runs and known failures. Close by noting that the live sample shows incomplete research; more human-reviewed evidence and repeated live evaluations are needed before relying on answers.

## Recording checklist

- Keep the finished video between 3 and 5 minutes.
- Show both a live request and a simulated failure, clearly labeled.
- Show at least one source URL and its supporting passage.
- Show confidence separately from evidence/coverage metrics.
- Do not describe a partial answer as a successful complete comparison.
- Publish the real recording and add its viewable link to the submission package.
