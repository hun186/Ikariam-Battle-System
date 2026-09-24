# Known Issues

| ID | Severity | Issue | Mitigation |
| --- | --- | --- | --- |
| KI-001 | High | Agent GitHub/Gameforge network remains unavailable. | Store reviewer verification explicitly; do not claim Codex network verification. |
| KI-002 | High | Kill/rounding/SR/IR/chronology/accuracy/transfer/mixed rows/secondary/healing/morale remain unknown. | Strict inconclusive; separate named experimental policies. |
| KI-003 | High | Only `land-mini` geometry is operational. | Reject reserved larger land and naval IDs. |
| KI-004 | High | Town walls and garrison-limit battlefield escalation are not modeled. | Treat current scope as unit-vs-unit Phase A; track accepted follow-up BL-002. |
| KI-005 | Medium | Exact pre-round timing when a scenario starts with no main-line force is not established, and both sides losing it together has no verified outcome. | Fallback-required and both-zero boundaries are inconclusive; experimental one-sided definite termination names `EXP-BATTLE-END-ROUND-BOUNDARY-001`. |
