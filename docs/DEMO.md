# 3–5 minute walkthrough script

1. Introduce the goal: a bounded research agent, not a chat wrapper. Explain the planner, parallel tools, filter, optional LLM, verification and abstention.
2. Run `python -m veritas "Find 5 Indian B2B SaaS startups in HR tech and summarize their positioning."` Show demo mode, web-first plan, five findings, source IDs, limitations and trace. Explain the corpus is authored and not current evidence.
3. Run `python -m veritas "Compare the top 3 open-source vector databases for a startup building RAG products." --fault timeout`. Show two GitHub timeout attempts, continued retrieval, partial status and low confidence. Explain the recovery bound.
4. Run the same command with `--fault outage`. Point out the replan event, eight attempts and zero findings. Discuss why abstention matters in production.
5. Run `python -m unittest discover -s tests -v` and `python evaluate.py`. Show 23/23 and 11/11. Explain the actual initial relevance regression, baseline, and why these are not factual-quality metrics.
6. Close with limitations: live DNS blocked, live model not tested, exact span does not establish truth, no global timeout, no calibrated confidence. Next steps: live smoke test, semantic validation, human evals, production telemetry.
