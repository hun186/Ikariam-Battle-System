from __future__ import annotations

from http.server import BaseHTTPRequestHandler
import json
from urllib.parse import urlparse

from simulator import BattleSimulator


API_SIMULATE_PATHS = {"/api/simulate", "/api/simulate.py"}


def run_battle(payload: dict) -> dict:
    attacker, defender, seed, max_rounds = load_battle_from_json_from_payload(payload)
    simulator = BattleSimulator(attacker, defender, seed=seed)
    winner, logs = simulator.run(max_rounds=max_rounds)
    return {
        "winner": winner,
        "seed": seed,
        "max_rounds": max_rounds,
        "attacker_units": attacker.total_units(),
        "defender_units": defender.total_units(),
        "logs": logs,
        "rounds": simulator.rounds,
    }


def load_battle_from_json_from_payload(payload: dict):
    # Reuse validation path through the existing scenario loader API shape.
    from simulator import army_from_dict

    attacker = army_from_dict("Attacker", payload["attacker"])
    defender = army_from_dict("Defender", payload["defender"])
    seed = int(payload.get("seed", 42))
    max_rounds = int(payload.get("max_rounds", 30))
    return attacker, defender, seed, max_rounds


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path.rstrip("/") or "/"
        if path in API_SIMULATE_PATHS:
            output = json.dumps(
                {
                    "message": "Use POST /api/simulate to run battle simulation.",
                    "docs": "Send JSON with attacker/defender, optional seed and max_rounds.",
                }
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(output)
            return

        self.send_response(404)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(b"Not found")

    def do_POST(self):
        path = urlparse(self.path).path.rstrip("/") or "/"
        if path not in API_SIMULATE_PATHS:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not found")
            return

        try:
            length = int(self.headers.get("content-length", "0"))
            body = self.rfile.read(length)
            payload = json.loads(body.decode("utf-8"))
            result = run_battle(payload)
            output = json.dumps(result).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(output)
        except Exception as exc:
            output = json.dumps({"error": str(exc)}).encode("utf-8")
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(output)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
