# Project Profile

Initialized evidence-aware Phase A Ikariam browser simulator. Python 3.11+, pure `ikariam_battle.simulate()`, no-framework ASGI/Vercel, vanilla UI, packaged profiles under `ikariam_battle/data/`.

Inputs are profile bundle, explicit battlefield ID, strict/experimental policy, side-wide Forge, unit-specific Workshop levels, units/waves. Outputs include positioned slots, reserve, ammo-pool shots, damage/casualties, all-survivor totals, main-line/fallback continuation state, termination events, and assumptions actually applied. Function B is excluded.

Facts: reviewer-web-verified current data through 17.5.0 is distinct from empirical PDF mechanics. All five land geometries are operational through explicit manual IDs; naval geometry and automatic Town Hall/garrison/wall selection or transitions remain unsupported. Duplicate same unit/wave/upgrades normalize; contradictory same-unit upgrades reject; input ordering is not a rule; ammo is pooled shots; support healing and morale are distinct; unknowns never silently produce exact strict outcomes.
