# Technical Decisions

## Active Decision Index
| ID | Decision | Status | Date |
| --- | --- | --- | --- |
| ADR-0001 | Separate evidence confidence and strict/experimental execution | Accepted | 2026-09-23 |

## ADR-0001
The PDF is empirical and contains explicit open problems. Strict execution returns `inconclusive` at unknown kill selection; a separately named experimental pooled-I-kill policy enables an end-to-end MVP and always appears in assumptions. Domain rules remain independent of HTTP/UI, and unit data is versioned with provenance. This trades broad “winner” output for non-fabricated, calibratable behavior.
