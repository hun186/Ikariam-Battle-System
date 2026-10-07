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


def test_reserve_ui_explains_rr_snapshot_timing_and_wave_damage_without_expanding_board():
    assert "RR Reserve HP" in INDEX
    assert "Wave persistent damage total" in INDEX
    assert "本回合新傷仍在 deployed slots" in INDEX
    assert "Doctor full-clear 生效" in INDEX
    assert 'class="reserve-info"' in INDEX
    assert 'class="reserve-heading"' in INDEX
    assert 'aria-label="Reserve HP 與 RR 說明"' in INDEX
    assert 'aria-describedby="floatingTooltip"' in INDEX
    assert 'id="floatingTooltip" class="floating-tooltip" role="tooltip"' in INDEX
    assert "const rrNote=reserve.length?" not in INDEX


def test_battlefield_air_units_match_game_left_right_layout():
    assert "const left=sideLine(state,'balloon',geometry,'left');" in INDEX
    assert "const right=sideLine(state,'anti-balloon',geometry,'right');" in INDEX
    assert "const left=sideLine(state,'anti-balloon',geometry,'left');" not in INDEX



def test_deployed_finite_ammo_slots_show_official_style_blue_munition_bar():
    assert 'function ammoBar(percent)' in INDEX
    assert 'class="ammo-rail"' in INDEX
    assert 'class="ammo-fill"' in INDEX
    assert "hpBar(hp,'HP')+ammoBar(ammo)" in INDEX
    assert "slot.munition_percent" in INDEX


def test_barbarian_fleet_stage_control_uses_linear_stage1_scaling():
    assert 'id="defenderBarbarianFleetStage"' in INDEX
    assert 'id="applyBarbarianFleetStage"' in INDEX
    assert 'function barbarianFleetCompositionForStage(stage)' in INDEX
    assert "growthBasisPoints" in INDEX
    assert "scaleBasisPoints=10000+growthBasisPoints*(n-1)" in INDEX
    assert "quantity:Math.floor((base*scaleBasisPoints+9999)/10000)" in INDEX
    assert "Math.ceil(Number(row.quantity)*(1+growth*(n-1)))" not in INDEX
