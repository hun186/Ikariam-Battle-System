from __future__ import annotations

from http.server import BaseHTTPRequestHandler
import json
from urllib.parse import urlparse

from ikariam_battle import BarbarianRegistry, ScenarioError, UnitRegistry, simulate
from ikariam_battle.battlefield import battlefield_metadata
from ikariam_battle.economy import MilitaryEconomyProfile
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
            barbarians = BarbarianRegistry.load()
            economy = MilitaryEconomyProfile.load()
            economy_units = economy.public()
            units = registry.public()
            for row in units:
                if row["id"] in economy_units:
                    row.update(economy_units[row["id"]])
            self._json(200, {"message": "POST a typed scenario to /api/simulate",
                "profiles": Profiles().__dict__,
                "battlefields": battlefield_metadata(),
                "profile_metadata": registry.metadata, "economy_metadata": economy.metadata, "units": units,
                "barbarian_profile_metadata": barbarians.metadata, "barbarian_units": barbarians.public(),
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
