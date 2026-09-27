from __future__ import annotations

from http.server import BaseHTTPRequestHandler
import json
from urllib.parse import urlparse

from ikariam_battle import BarbarianRegistry, ScenarioError, UnitRegistry, simulate
from ikariam_battle.battlefield import battlefield_metadata
from ikariam_battle.economy import MilitaryEconomyProfile
from ikariam_battle.models import MAX_ROUNDS, Profiles
from ikariam_battle.profiles import ForgeProfile, SupportProfile, WorkshopProfile


API_SIMULATE_PATHS = {"/api/simulate", "/api/simulate.py"}
DEFAULT_ROUND_PAGE_SIZE = 10
MAX_ROUND_PAGE_SIZE = 20
SUMMARY_EVENT_TYPES = {
    "unsupported_mechanic",
    "safety_limit_reached",
    "battle_termination",
    "assumption_applied",
}


def _report_integer(value, name: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    if value < minimum or value > maximum:
        raise ValueError(f"{name} must be {minimum}..{maximum}")
    return value


def _report_spec(payload: dict) -> tuple[str, int, int]:
    report = payload.get("report")
    if report is None:
        return "summary", 0, DEFAULT_ROUND_PAGE_SIZE
    if not isinstance(report, dict):
        raise ValueError("report must be an object")
    mode = report.get("mode", "summary")
    if mode == "summary":
        return mode, 0, DEFAULT_ROUND_PAGE_SIZE
    if mode != "round_page":
        raise ValueError("report.mode must be summary or round_page")
    start = _report_integer(report.get("round_start", 0), "report.round_start", 0, MAX_ROUNDS)
    limit = _report_integer(
        report.get("round_limit", DEFAULT_ROUND_PAGE_SIZE),
        "report.round_limit",
        1,
        MAX_ROUND_PAGE_SIZE,
    )
    return mode, start, limit


def _summary_events(events: list[dict]) -> list[dict]:
    return [event for event in events if event.get("type") in SUMMARY_EVENT_TYPES]


def _transport_result(full: dict, mode: str, start: int, limit: int) -> dict:
    rounds = full.get("rounds", [])
    events = full.get("events", [])
    completed = int(full.get("rounds_completed", 0))
    if mode == "round_page" and start > completed:
        raise ValueError("report.round_start must be <= rounds_completed")

    result = {key: value for key, value in full.items() if key not in {"rounds", "events"}}
    if mode == "summary":
        returned_rounds: list[dict] = []
        returned_events = _summary_events(events)
        page_start = page_end = None
    else:
        page_end_value = min(completed, start + limit - 1)
        returned_rounds = [row for row in rounds if start <= int(row.get("round", -1)) <= page_end_value]
        returned_events = [event for event in events if start <= int(event.get("round", -1)) <= page_end_value]
        page_start = start
        page_end = page_end_value

    result["rounds"] = returned_rounds
    result["events"] = returned_events
    result["report"] = {
        "mode": mode,
        "default_page_size": DEFAULT_ROUND_PAGE_SIZE,
        "max_page_size": MAX_ROUND_PAGE_SIZE,
        "rounds_available": len(rounds),
        "events_available": len(events),
        "round_start": page_start,
        "round_end": page_end,
        "rounds_returned": len(returned_rounds),
        "events_returned": len(returned_events),
        "has_previous": bool(mode == "round_page" and start > 0),
        "has_next": bool(mode == "round_page" and page_end is not None and page_end < completed),
    }
    return result


def run_battle(payload: dict) -> dict:
    mode, start, limit = _report_spec(payload)
    return _transport_result(simulate(payload), mode, start, limit)


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
                "support_capacity": SupportProfile.load().derived_capacity,
                "report_transport":{"default_mode":"summary","default_round_page_size":DEFAULT_ROUND_PAGE_SIZE,
                                    "max_round_page_size":MAX_ROUND_PAGE_SIZE}})
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
