# Ikariam Battle Simulator (Prototype)

This repository contains:
- battle simulator core in `simulator.py`,
- PDF extraction helper in `pdf_extract.py`,
- tests in `test_simulator.py`,
- Vercel web UI in `public/index.html` + `api/simulate.py`.

## Local CLI usage

```bash
python simulator.py
python simulator.py --scenario sample_scenario.json
```

## Run tests

```bash
pytest -q
```

## Deploy to Vercel

1. Push this repository to GitHub.
2. Import project in Vercel.
3. Deploy (Python runtime will serve `api/simulate.py`, static UI from `public/`).

### UI features
- JSON scenario editor
- Form-based scenario editor (no need to hand-write JSON)
- One-click simulation
- Winner/remaining-unit summary
- Full battle log viewer
- Round-by-round playback
- Download battle report as JSON

## API

`POST /api/simulate`

Body example:

```json
{
  "seed": 11,
  "max_rounds": 20,
  "attacker": {"swordsman": 100, "archer": 60, "gyrocopter": 10},
  "defender": {"hoplite": 110, "slinger": 55, "gyrocopter": 15}
}
```
