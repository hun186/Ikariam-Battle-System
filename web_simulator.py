from __future__ import annotations

from http.server import BaseHTTPRequestHandler
import json
from urllib.parse import urlparse

from ikariam_battle import ScenarioError, UnitRegistry, simulate
from ikariam_battle.models import Profiles
from ikariam_battle.profiles import ForgeProfile, SupportProfile, WorkshopProfile


API_SIMULATE_PATHS = {"/api/simulate", "/api/simulate.py"}


def run_battle(payload: dict) -> dict:
    return simulate(payload)


class handler(BaseHTTPRequestHandler):
    def _json(self, status: int, value: dict) -> None:
        output = json.dumps(value).encode()
        self.send_response(status); self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*"); self.end_headers(); self.wfile.write(output)

    def do_GET(self):
        if urlparse(self.path).path.rstrip("/") in API_SIMULATE_PATHS:
            registry = UnitRegistry.load()
            self._json(200, {"message": "POST a typed scenario to /api/simulate",
                "profiles": Profiles().__dict__,
                "battlefields": [{"id":"land-mini","display_name":"Land mini / Town Hall 1–4","supported":True},
                                 {"id":"land-small","display_name":"Land small","supported":False},
                                 {"id":"land-medium","display_name":"Land medium","supported":False},
                                 {"id":"land-large","display_name":"Land large","supported":False},
                                 {"id":"land-max","display_name":"Land max","supported":False}],
                "profile_metadata": registry.metadata, "units": registry.public(),
                "forge_levels": {str(k): {"damage_multiplier":str(v.damage_multiplier),"armor_bonus":v.armor_bonus}
                                 for k,v in ForgeProfile.load().levels.items()},
                "support_capacity": SupportProfile.load().derived_capacity})
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self):
        if urlparse(self.path).path.rstrip("/") not in API_SIMULATE_PATHS:
            self._json(404, {"error": "not found"}); return
        try:
            payload = json.loads(self.rfile.read(int(self.headers.get("content-length", "0"))))
            self._json(200, run_battle(payload))
        except (ScenarioError, ValueError, json.JSONDecodeError) as exc:
            self._json(400, {"error": str(exc)})

    def do_OPTIONS(self):
        self.send_response(204); self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type"); self.end_headers()
