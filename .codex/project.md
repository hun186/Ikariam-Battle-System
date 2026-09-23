# Project Profile

- Status: `INITIALIZED`; verified locally 2026-09-23 against PR-correction workspace.
- Purpose: browser-operated, deterministic, evidence-aware Ikariam Phase A simulator using current numeric profiles with empirically reconstructed mechanics.
- Inputs: profile bundle, land battlefield, strict/experimental policy, side-level Workshop/Forge, units/waves.
- Outputs: completed/inconclusive outcome, formation/reserve/ammo/damage, casualties, events, assumptions/warnings.
- Non-goal: Function B solver and claims of official/current mechanics completeness.

## Technology and map

Python 3.11+; pure `ikariam_battle.simulate()` domain package; no-framework ASGI/Vercel adapter; vanilla HTML/CSS/JS. Packaged JSON resources live under `ikariam_battle/data/{mechanics,units,rules}`. Tests are under `tests/`; evidence details are in `docs/mechanics-spec.md`.

## Truth and invariants

Executable code/tests and per-field profile provenance outrank prose. The PDF is empirical mechanics evidence. Current numeric targets are review-supplied/network-unverified. Domain does not import Web code; land/naval cannot mix; duplicate same-unit/wave rows normalize; input order is not a combat rule; damage is conserved; finite ammo cannot fire primary forever; unknown result-affecting behavior is explicit/inconclusive or named experimental policy.
