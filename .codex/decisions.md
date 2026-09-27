# Technical Decisions

- **ADR-0001 Accepted:** strict refuses result-affecting unknowns; experimental policies use stable response-visible IDs.
- **ADR-0002 Accepted:** empirical mechanics, current units, Workshop, Forge, support, and targeting are independent packaged profiles.
- **ADR-0003 Accepted:** Workshop ownership is per unit type; Forge ownership is per side. Conflicting same-unit levels are invalid.
- **ADR-0004 Accepted:** battlefield lines store slot space, units store size, and deployment derives capacity; unsupported geometry rejects.

- **ADR-0005 Accepted:** keep `simulate()` as the complete deterministic engine result, but bound HTTP transport with summary-first responses and stateless on-demand round pages (default 10, maximum 20); do not require server-side battle-session state.
