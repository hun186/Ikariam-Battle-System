# Development Workflows

## Environment
Python 3.11+; runtime server dependency is in `requirements.txt`; no required environment variables or external service.

## Canonical commands
| Purpose | Command | Status (2026-09-23) |
| --- | --- | --- |
| Install | `python -m pip install -r requirements.txt && python -m pip install -e .` | Manifest-backed |
| Focused tests | `pytest -q tests/unit` | Verified |
| Full suite | `pytest -q` | Verified |
| Local Web/API | `uvicorn asgi:application --host 127.0.0.1 --port 8000` | Verified |
| CLI | `python simulator.py --scenario sample_scenario.json` | Verified |
| API smoke | `curl -sS -X POST http://127.0.0.1:8000/api/simulate -H 'Content-Type: application/json' --data @sample_scenario.json` | Verified |

UI changes require static form assertions plus a browser screenshot/interaction. API changes require integration tests; mechanics changes require PDF-focused unit tests and full suite. No JS build exists.
