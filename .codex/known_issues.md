# Known Issues

| ID | Severity | Issue | Mitigation |
| --- | --- | --- | --- |
| KI-001 | High | Agent GitHub/Gameforge network remains unavailable. | Store reviewer verification explicitly; do not claim Codex network verification. |
| KI-002 | High | General kill-type selection, rounding selector, SR/IR triggers, accuracy, RR slot-internal individual allocation, secondary-weapon triggers, healing allocation, and morale remain unknown. | Strict inconclusive where required; keep separate named experimental policies. Formation chronology, class-level target transfer, and mixed-source Attacking Matrix row/column addressing are implemented and are not part of this issue. |
| KI-003 | High | Naval geometry remains unsupported; land size cannot be inferred or transitioned automatically. | Require an explicit executable land ID and reject reserved naval IDs. |
| KI-004 | High | Town walls and garrison-limit battlefield escalation are not modeled. | Treat current scope as unit-vs-unit Phase A; track accepted follow-up BL-002. |
| KI-005 | Medium | Exact pre-round timing when a scenario starts with no main-line force is not established, and both sides losing it together has no verified outcome. | Fallback-required and both-zero boundaries are inconclusive; experimental one-sided definite termination names `EXP-BATTLE-END-ROUND-BOUNDARY-001`. |
