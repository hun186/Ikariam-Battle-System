# Ikariam Battle Simulator (Prototype)

This repository contains:
- battle simulator core in `simulator.py`,
- PDF extraction helper in `pdf_extract.py`,
- tests in `test_simulator.py`,
- Vercel web UI in root `index.html` (mirrored at `public/index.html`) + `api/simulate.py`.

## Local CLI usage

```bash
python simulator.py
python simulator.py --scenario sample_scenario.json
```

## Run tests

```bash
pytest -q
```


## Local web deployment with Uvicorn

Run the same static UI and simulation API locally with Uvicorn:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
uvicorn asgi:application --host 127.0.0.1 --port 8000
```

Then open <http://127.0.0.1:8000>. The ASGI app serves `index.html` and handles `POST /api/simulate`.

Quick API smoke test:

```bash
curl -X POST http://127.0.0.1:8000/api/simulate \
  -H 'Content-Type: application/json' \
  --data @sample_scenario.json
```

## Deploy to Vercel

1. Push this repository to GitHub.
2. Import project in Vercel.
3. Deploy (Python runtime will serve `api/simulate.py`, static UI from root `index.html`).

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
