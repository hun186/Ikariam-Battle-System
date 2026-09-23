# Ikariam Battle Simulator — Phase A

This browser-operated simulation workbench researches Ikariam battle mechanics. It replaces the former random toy with an evidence-aware domain engine. The bundled `paper-2020` ruleset comes from the repository’s empirical PDF and **is not current official Gameforge data**.

## What works

- Side-by-side armies with quantity and attack/armor upgrades.
- Strict mode returns `inconclusive` rather than inventing unknown mechanics.
- Experimental mode discloses its pooled I-kill/floor-rounding assumption.
- Formation slots, capacity, reserves/waves, persistent damage, attacking-matrix traces, RR, casualties, and round events.
- Typed `POST /api/simulate` and pure Python `ikariam_battle.simulate()`.

See [the mechanics evidence register](docs/mechanics-spec.md) for documented, empirical, hypothetical, and unknown rules. Force Solver / Minimum Winning Army is deferred.

## Install and verify

Python 3.11+ is declared in `pyproject.toml`.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
pytest -q
```

## Browser and API

```bash
uvicorn asgi:application --host 127.0.0.1 --port 8000
```

Open <http://127.0.0.1:8000>, configure both sides, select strict or experimental, and simulate. The result shows status/outcome, uncertainty, slots, damage, casualties, and expandable events.

```bash
curl -X POST http://127.0.0.1:8000/api/simulate \
  -H 'Content-Type: application/json' --data @sample_scenario.json
python simulator.py --scenario sample_scenario.json
```

## Layout

- `ikariam_battle/` — framework-independent engine/public API.
- `data/units/paper-2020.json` — versioned, provenance-bearing supported subset.
- `tests/` — PDF regressions, invariants, API, and UI smoke tests.
- `index.html`, `asgi.py`, `web_simulator.py`, `api/` — browser/deployment adapters.
- `ikariam battle system.pdf`, `docs/mechanics-spec.md` — empirical reference/evidence register.

The Vercel `/api/simulate` path remains available; `public/index.html` mirrors the root UI.
