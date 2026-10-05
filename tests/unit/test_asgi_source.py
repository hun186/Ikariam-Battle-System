from pathlib import Path


ASGI = (Path(__file__).resolve().parents[2] / "asgi.py").read_text(encoding="utf-8")


def test_asgi_metadata_imports_barbarian_fleet_registry_before_use():
    assert "from ikariam_battle import BarbarianFleetRegistry, BarbarianRegistry, UnitRegistry" in ASGI
    assert "barbarian_fleet = BarbarianFleetRegistry.load()" in ASGI
