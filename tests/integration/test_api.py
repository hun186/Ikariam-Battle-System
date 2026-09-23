import asyncio
import json
from pathlib import Path

from asgi import application


async def request(method, path, body=b""):
    events = [{"type": "http.request", "body": body, "more_body": False}]
    sent = []
    async def receive(): return events.pop(0)
    async def send(message): sent.append(message)
    await application({"type": "http", "method": method, "path": path}, receive, send)
    return sent


def test_api_calls_engine_with_typed_schema():
    payload = json.loads(Path("sample_scenario.json").read_text())
    response = asyncio.run(request("POST", "/api/simulate", json.dumps(payload).encode()))
    data = json.loads(response[1]["body"])
    assert response[0]["status"] == 200
    assert {"ruleset", "status", "outcome", "rounds", "events", "assumptions", "warnings"} <= data.keys()
    assert data["ruleset"] == "paper-2020"


def test_static_ui_is_operable_form_not_json_editor():
    response = asyncio.run(request("GET", "/"))
    body = response[1]["body"].decode()
    assert response[0]["status"] == 200
    assert "Attacker" in body and "Defender" in body and "Add unit" in body
    assert "fetch('/api/simulate'" in body


def test_invalid_legacy_payload_is_rejected():
    body = json.dumps({"attacker": {"swordsman": 10}, "defender": {"hoplite": 10}}).encode()
    response = asyncio.run(request("POST", "/api/simulate", body))
    assert response[0]["status"] == 400
