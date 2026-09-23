# Architecture

| Component | Responsibility | Location |
| --- | --- | --- |
| Scenario/state | typed profile bundle, side-level Workshop/Forge, normalized waves, positioned slots | `models.py` |
| Evidence profiles | packaged mechanics/current units/v14/v17 rules with metadata | `ikariam_battle/data/`, `profiles.py`, `units.py` |
| Pure rules | physical/damage geometry, Am, traceable damage, per-wave RR | `battlefield.py`, `attacking_matrix.py`, `damage.py`, `redistribution.py` |
| Engine | preflight boundaries, simultaneous experimental planning, ammo, events/results | `engine.py` |
| Calibration | versioned observed battle-report fixture and percentage intervals | `calibration.py` |
| Adapters/UI | JSON HTTP/CLI and metadata-rendered browser | `web_simulator.py`, `asgi.py`, `simulator.py`, `index.html` |

Flow: parse/normalize → load packaged profiles → validate domain/numbers/geometry → deploy by damage priority → strict preflight or named experimental phases → snapshots/events/result. Both sides plan from phase-start state before mutations. Support does not enter Am. Unknown mixed rows, healing, rounding, kill selection, chronology and transfers are never selected by list order.
