from pathlib import Path

from simulator import Army, BattleSimulator, Stack, UNIT_TYPES, load_battle_from_json


def test_battle_runs_and_has_result():
    a = Army("A", [Stack(UNIT_TYPES["swordsman"], 100), Stack(UNIT_TYPES["archer"], 20)])
    d = Army("D", [Stack(UNIT_TYPES["hoplite"], 90), Stack(UNIT_TYPES["slinger"], 30)])

    winner, log = BattleSimulator(a, d, seed=1).run(max_rounds=10)

    assert winner in {"A", "D", "draw"}
    assert any(line.startswith("RESULT") for line in log)


def test_no_negative_units_after_battle():
    a = Army("A", [Stack(UNIT_TYPES["swordsman"], 10)])
    d = Army("D", [Stack(UNIT_TYPES["hoplite"], 10)])

    BattleSimulator(a, d, seed=2).run(max_rounds=20)

    assert all(s.count >= 0 for s in a.stacks)
    assert all(s.count >= 0 for s in d.stacks)


def test_battle_records_round_snapshots_for_visualization():
    a = Army("A", [Stack(UNIT_TYPES["swordsman"], 25), Stack(UNIT_TYPES["archer"], 5)])
    d = Army("D", [Stack(UNIT_TYPES["hoplite"], 25), Stack(UNIT_TYPES["slinger"], 5)])
    simulator = BattleSimulator(a, d, seed=3)

    simulator.run(max_rounds=3)

    assert simulator.rounds[0]["label"] == "Initial deployment"
    assert simulator.rounds[0]["attacker"]["lines"] == {"front": 25, "back": 5, "air": 0}
    assert simulator.rounds[-1]["defender"]["morale"] <= 1.1
    assert all(
        "units" in side
        for round_state in simulator.rounds
        for side in (round_state["attacker"], round_state["defender"])
    )


def test_load_battle_from_json(tmp_path: Path):
    scenario = tmp_path / "scenario.json"
    scenario.write_text(
        '{"seed": 5, "max_rounds": 7, "attacker": {"swordsman": 10}, "defender": {"hoplite": 11}}',
        encoding="utf-8",
    )
    a, d, seed, max_rounds = load_battle_from_json(str(scenario))

    assert a.total_units() == 10
    assert d.total_units() == 11
    assert seed == 5
    assert max_rounds == 7


def test_vercel_rewrites_serve_root_index():
    import json

    config = json.loads(Path("vercel.json").read_text(encoding="utf-8"))

    index_html = Path("index.html").read_text(encoding="utf-8")

    assert Path("index.html").is_file()
    assert index_html == Path("public/index.html").read_text(encoding="utf-8")
    assert "fetch('/api/simulate'" in index_html
    assert config["rewrites"] == [
        {"source": "/api/simulate", "destination": "/api/simulate.py"},
        {"source": "/(.*)", "destination": "/index.html"},
    ]


def test_asgi_app_serves_index_and_api():
    import asyncio
    import json

    from asgi import application

    async def request(method, path, body=b""):
        events = [
            {
                "type": "http.request",
                "body": body,
                "more_body": False,
            }
        ]
        sent = []

        async def receive():
            return events.pop(0)

        async def send(message):
            sent.append(message)

        await application(
            {
                "type": "http",
                "method": method,
                "path": path,
            },
            receive,
            send,
        )
        return sent

    index_response = asyncio.run(request("GET", "/"))
    assert index_response[0]["status"] == 200
    assert b"Ikariam Battle Simulator" in index_response[1]["body"]

    payload = json.dumps(
        {
            "seed": 11,
            "max_rounds": 20,
            "attacker": {"swordsman": 100, "archer": 60, "gyrocopter": 10},
            "defender": {"hoplite": 110, "slinger": 55, "gyrocopter": 15},
        }
    ).encode("utf-8")
    api_response = asyncio.run(request("POST", "/api/simulate", payload))
    data = json.loads(api_response[1]["body"].decode("utf-8"))

    assert api_response[0]["status"] == 200
    assert data["winner"] == "Attacker"
    assert "logs" in data
    assert data["rounds"][0]["attacker"]["units"]["swordsman"] == 100
