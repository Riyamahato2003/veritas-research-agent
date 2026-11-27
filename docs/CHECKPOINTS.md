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
