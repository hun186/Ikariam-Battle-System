from pathlib import Path


INDEX = (Path(__file__).resolve().parents[2] / "index.html").read_text(encoding="utf-8")


def test_round_view_places_battle_board_directly_after_navigation_before_notices():
    start = INDEX.index('<section id="roundView"')
    end = INDEX.index('<section id="summaryView"', start)
    section = INDEX[start:end]
    assert section.index('id="roundPager"') < section.index('id="roundCaption"')
    assert section.index('id="roundCaption"') < section.index('id="battleBoard"')
    assert section.index('id="battleBoard"') < section.index('id="roundSafetyNotices"')
    assert section.index('id="roundSafetyNotices"') < section.index('id="researchData"')


def test_reserve_ui_explains_rr_snapshot_timing_and_wave_damage():
    assert "RR Reserve HP" in INDEX
    assert "Wave persistent damage total" in INDEX
    assert "本回合新傷仍在 deployed slots" in INDEX
    assert "Doctor full-clear 生效" in INDEX
