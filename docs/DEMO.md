# 4-minute recording script

No recording is included in this repository. Record and host the video manually before submission. Use https://veritas-research-agent.vercel.app. The browser-origin approval was declined during this task, so test the page visually when recording. Do not display API keys or account details.

## Script

### 0:00–0:30 — Problem and scope

“Veritas is a bounded read-only research agent. It adapts tool searches to the question, links claims to retrieved passages, and shows what it could not verify. This is a single-agent assignment prototype, not an autonomous production research service.”

### 0:30–1:00 — Architecture and orchestration

Open Architecture. Point out the intent planner, Tavily search and selective extraction, GitHub/Wikipedia routing, passage index, separate claim review, coverage matrix and one bounded recovery pass. Show the per-run trace and mention the caps: five searches, one extraction batch and five model calls. Explain that rate limits stop further model calls.

### 1:00–2:15 — Live happy-path candidate

Choose Live mode and run: “Research the pros and cons of using a multi-agent architecture for customer support automation.” Show the complete status, medium heuristic confidence, benefit/risk coverage, cited claims and one source passage. Open Plan and Trace to show actual searches, review, source IDs, token use and latency. Say: “This is the best complete live run in the bounded sample. Confidence is a workflow label, not probability. Model review does not prove truth; manual spot-check found one case-study result was generalized and another claim adds an unsupported misrouting risk, which I documented.”

### 2:15–3:05 — Failure handling

Switch to Demo mode and run the total retrieval outage scenario. Show insufficient evidence, zero factual claims and the bounded trace. Explain this is an offline deterministic simulation and consumes no live search quota.

### 3:05–4:00 — Evaluation and tradeoffs

Open Evaluation and show 72 regression tests and 11 offline scenarios. Briefly point to the partial memory and unseen samples: the system withholds unsupported claims and reports missing criteria. Close: “The take-home is functional and deployed, but vector tradeoffs and HR eligibility remain incomplete, and the live unseen comparison still lacks REST evidence. The recording is the remaining submission step.”

## Recording checklist

- Keep the finished video between 3 and 5 minutes.
- Show a fresh live run if provider quotas allow; otherwise use the committed report and say it is saved evidence.
- Show at least one source and its supporting passage, plus the plan/trace.
- Show a clearly labeled simulated outage.
- State the partial research gaps and heuristic confidence caveat.
- Publish the real recording and add its viewable link to the submission package.
