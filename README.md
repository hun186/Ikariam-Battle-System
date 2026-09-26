# Ikariam Battle Simulator — evidence-aware Phase A

A deterministic browser simulator combining current Infinite Horizons numerical profiles with empirically reconstructed battle mechanics. It is not official Gameforge source code; strict mode refuses unresolved mechanics and experimental mode exposes every named assumption.

## Current profiles

- Complete land and naval HP, damage, armor, accuracy, ammunition, size, and primary/secondary weapons from a reviewer-verified current community reference; naval values also carry Gameforge forum player-test corroboration.
- v14 Workshop: unit-type-specific upgrades, land +5 and naval +10 per level. Levels are non-negative integers and can differ between Hoplites, Swordsmen, and other unit types on the same side.
- v14 Forge: side-wide levels 0–5.
- v17 support: Doctor/Tender healing ×20; 4000 is derived from legacy 200. Cook morale and healing allocation remain unknown.
- Legacy empirical mechanics profile for formation labels, Am, and RR, with SR/IR/kill/chronology limitations retained.
- Legacy/community battle-end profile distinguishes actual main-line holders, unresolved light/long-range fallback candidates, and definitely non-sustaining artillery, air, and support.
- Current land military-economy profile derives General Score from the unmodified resource score basis at 1 point per 50 resources; Workshop, Forge, and combat buffs do not change score value.

Official changelog claims and exact community/PTS tables are not conflated. The reviewer verified sources through v17.5.0 with retrieval date 2026-09-24; this environment did not independently open those URLs. See [the evidence register](docs/mechanics-spec.md).

## Operational scope

All five land battlefield geometries are executable through explicit scenario IDs: `land-mini` (Town Hall 1–4), `land-small` (5–9), `land-medium` (10–16), `land-large` (17–24), and `land-max` (25+). The Town Hall ranges are descriptive metadata only; the simulator does not infer battlefield size from Town Hall level, garrison limit, walls, or mid-battle state. Capacity is `floor(slot_space / unit size)`, not a unit constant, and the browser renders line/slot counts from the selected battlefield geometry. Naval geometry remains reserved/unsupported. Initial land formation supports the evidence-backed Heavy-before-Light rules and homogeneous single-weapon Light Infantry fallback already modeled; unresolved multi-line wave execution, cross-wave rebuild, ranged fallback, and related transitions remain guarded rather than guessed.

Ammunition is pooled as shots across deployed and reserve units of a wave. Target priorities consider deployed slots only and use a versioned legacy/community experimental profile. Accuracy is per weapon but its algorithm is unresolved, so it is an explicit experimental assumption and a strict blocker. Doctor/Tender healing and Cook morale have separate boundaries and are represented as deployed support rather than ordinary reserve.

This remains a **unit-vs-unit Phase A** simulator. Town walls, wall targeting/damage, garrison-limit escalation of battlefield size, and complete city-battle behavior are not implemented.

Snapshots keep all survivors in `total` and expose `main_line_holding_total`, `fallback_candidate_total`, and `continuation_state`. If the front disappears while light or long-range units remain, both modes stop inconclusive at `fallback_required`; the engine does not fire another round from stale positions. Artillery, air, and support survivors withdraw/scatter without becoming casualties when the opponent retains a main line. A simultaneous both-no-main-line outcome remains unknown rather than being silently called a draw.

## Run and verify

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
pytest -q
uvicorn asgi:application --host 127.0.0.1 --port 8000
```

The browser obtains profiles, battlefield geometry, Forge effects, unit roles/lines, and unit size from `GET /api/simulate`. The setup screen presents all land units as dispatch-style rows with quantity, per-unit attack/armor Workshop levels, ±one-slot helpers derived from the selected battlefield, and advanced entry-batch controls; Forge/Hephaistos stays side-wide. Results are split into round replay and total summary views. The summary reports unit casualties, General Score lost/destroyed, and gross engine damage separately.

```bash
curl -X POST http://127.0.0.1:8000/api/simulate -H 'Content-Type: application/json' --data @sample_scenario.json
python simulator.py --scenario sample_scenario.json
```

Future Function B remains deferred. It must call `ikariam_battle.simulate()` and distinguish completed outcomes from inconclusive or assumption-bearing results.
