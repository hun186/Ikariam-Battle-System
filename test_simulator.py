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
