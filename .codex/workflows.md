# Development Workflows

Python 3.11+; no environment variables or services required.

| Purpose | Command |
| --- | --- |
| Focused | `pytest -q tests/unit` |
| Full | `pytest -q` |
| Compile | `python -m compileall -q ikariam_battle asgi.py web_simulator.py simulator.py` |
| Build | `python -m build` |
| Server | `uvicorn asgi:application --host 127.0.0.1 --port 8000` |
| Browser report case E2E | `uvicorn asgi:application --host 127.0.0.1 --port 8871` (terminal 1) and `python tools/report_case_browser_e2e.py` (terminal 2; requires Playwright Python + Chromium) |
| CLI | `python simulator.py --scenario sample_scenario.json` |

Package verification must install the wheel into a temporary venv, change outside the checkout, load all profiles, and run a minimal simulation. API work requires GET/POST/invalid-domain smoke. UI work requires real browser interaction/screenshot when a runtime is available; HTML assertions are static smoke only.
