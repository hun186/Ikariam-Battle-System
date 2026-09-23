# Ikariam Battle Simulator — evidence-aware Phase A

A browser-operated deterministic simulator using **current numerical data profiles with empirically reconstructed battle mechanics**. It is not official Gameforge source code, and unresolved mechanics are never silently promoted to facts.

## Versioned evidence layers

- Infinite Horizons candidate unit stats (`infinite-horizons-current`).
- v14 Workshop increments (`v14-workshop`): land +5 and naval +10 per level.
- v14 Hephaistos Forge table (`v14-hephaistos`), levels 0–5.
- v17 Doctor/Tender healing scaling (`v17-support-healing`): review-supplied changelog multiplier ×20; 4000 is explicitly derived from legacy 200.
- Legacy mechanics (`battle-system-paper-2020`): formation labels, Am and RR plus observational/open SR, IR, kill, chronology and retargeting research.

Network verification was unavailable during this correction, so current numeric/changelog claims remain review-supplied and marked for community/official cross-check in field-level provenance. See [the complete evidence register](docs/mechanics-spec.md).

## Safety modes

- **Strict** refuses casualty simulation when kill selection, rounding, chronology, healing, mixed-unit rows, retargeting, or another result-affecting rule is unsupported. It returns `inconclusive` plus machine-readable events.
- **Experimental** exists for calibration and end-to-end research. Every invented policy has an `EXP-*` identifier in response assumptions and event traces.

The UI currently enables supported **land** numeric records only. Naval records exist in the registry, but naval battlefield geometry is rejected until it can be calibrated. Land/naval mixing is invalid. Support units never fire through Am; healing capacity is shown while allocation remains unresolved.

## Run

Python 3.11+:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
pytest -q
uvicorn asgi:application --host 127.0.0.1 --port 8000
```

Open <http://127.0.0.1:8000>. Unit options/profile metadata come from `GET /api/simulate`, not a second JavaScript registry. Workshop is player-side and accepts any non-negative integer; Forge is 0–5.

```bash
curl -X POST http://127.0.0.1:8000/api/simulate -H 'Content-Type: application/json' --data @sample_scenario.json
python simulator.py --scenario sample_scenario.json
```

## Architecture

- `ikariam_battle/`: pure callable domain engine, profiles, rules, and calibration schema.
- `ikariam_battle/data/`: packaged mechanics/unit/workshop/forge/support resources.
- `tests/`: semantic PDF regressions, current-profile/provenance boundaries, API and packaging checks.
- `index.html`, `asgi.py`, `web_simulator.py`: metadata-driven browser/API adapters.

Future Function B (minimum winning army) is deferred until Phase A is sufficiently calibrated. It must repeatedly call `ikariam_battle.simulate()`, never duplicate rules, and distinguish completed outcomes from inconclusive/assumption-bearing results.
