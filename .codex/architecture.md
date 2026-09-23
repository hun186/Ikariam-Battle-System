# Architecture

## Boundary and components
| Component | Responsibility | Location |
| --- | --- | --- |
| Domain model/service | Typed scenario, deterministic simulation, result | `ikariam_battle/models.py`, `engine.py` |
| Rules | formation/Am/damage/RR as independent pure logic | `ikariam_battle/battlefield.py`, `attacking_matrix.py`, `damage.py`, `redistribution.py` |
| Registry | Versioned provenance-bearing units | `ikariam_battle/units.py`, `data/units/` |
| Adapters | JSON HTTP/ASGI/Vercel and CLI | `web_simulator.py`, `asgi.py`, `api/`, `simulator.py` |
| UI | Builds typed scenarios and renders engine trace | `index.html` |

## Data flow
1. Adapter parses JSON through `Scenario.from_dict`.
2. Registry resolves supported unit records; formation deploys capacity/reserve by wave.
3. Strict policy stops at an unsupported mechanic; experimental phases run RR, refill, Am, damage/casualties.
4. Engine owns events and snapshots; UI only renders them.

## Boundaries and invariants
Domain never imports HTTP/browser code. Adapters never calculate combat rules. Unit count/damage are non-negative; deployed units respect capacity; reserve + deployed is the surviving wave; deterministic inputs reproduce; assumptions are machine-readable. Unknown kill selection, rounding, SR/IR triggers, retargeting, accuracy, and long-duration intervals cannot be silently fabricated.
