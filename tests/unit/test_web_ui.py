from pathlib import Path


INDEX = (Path(__file__).resolve().parents[2] / "index.html").read_text(encoding="utf-8")
PUBLIC_INDEX = (Path(__file__).resolve().parents[2] / "public" / "index.html").read_text(encoding="utf-8")


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
    assert "attackerReserveRrDescription" in INDEX
    assert "defenderReserveRrDescription" in INDEX
    assert "aria-describedby=\"'+rrDescriptionId+'\"" in INDEX
    assert 'aria-describedby="floatingTooltip"' not in INDEX
    assert 'class="sr-only"' in INDEX
    assert ".sr-only{position:absolute!important" in INDEX
    assert 'id="floatingTooltip" class="floating-tooltip" role="tooltip"' in INDEX
    assert "const rrNote=reserve.length?" not in INDEX


def test_round_reserve_uses_content_aware_columns_and_mobile_scrolling():
    # Both entry points must render the same UI.
    assert INDEX == PUBLIC_INDEX
    assert "Math.max(2,Math.min(4,reserve.length))" in INDEX
    assert "const reserveWidth=reserveColumns*68+12" in INDEX
    assert "grid-template-columns:var(--reserve-width,284px) minmax(0,1fr)" in INDEX
    assert ".reserve-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(62px,1fr))" in INDEX
    assert '.reserve-card{position:relative;min-width:0;' in INDEX
    assert '@media(max-width:1190px){.battle-half{grid-template-columns:minmax(0,1fr)}' in INDEX
    assert '.battle-half.defender .reserve-box{order:2}' in INDEX
    assert '.formation{max-width:100%;overflow-x:auto;overscroll-behavior-x:contain}' in INDEX
    assert '.formation-row{min-width:880px}' in INDEX
    assert '.battle-board{overflow-x:auto}' not in INDEX


def test_round_formation_hides_visual_line_headings_and_preserves_slot_geometry():
    # Remove the round's decorative headings only; setup reference labels stay.
    assert INDEX == PUBLIC_INDEX
    assert "battle-line-name" not in INDEX
    assert "function lineLabel(line)" in INDEX
    assert 'function lineRow(state,line,geometry){' in INDEX
    assert '''return '<div class="battle-line">'+lineSlots(state,line,geometry)+'</div>';''' in INDEX
    assert '''return '<div class="formation-side '+side+'">'+lineSlots(state,line,geometry,chosen,true)+'</div>';''' in INDEX
    assert ".battle-line{display:grid;grid-template-columns:minmax(0,1fr);align-items:center}" in INDEX
    assert "const front=frontRow(state,geometry,wall),ranged=rangedRow(state,geometry),rear=rearRow(state,geometry);" in INDEX
    assert "const rows=name==='attacker'?[rear,ranged,front]:[front,ranged,rear];" in INDEX
    assert "slotTooltipHtml(slot)" in INDEX
    assert "lineSlots(state,line,geometry" in INDEX


def test_round_wall_view_shows_actual_round_segments_with_experimental_warning():
    assert INDEX == PUBLIC_INDEX
    assert 'function wallLineRow(wall,state)' in INDEX
    assert "wallLineRow(wall,state)+'</div>'" in INDEX
    assert "state.slots.find(s=>s.line==='first'" in INDEX
    assert "Number(s.physical_position)===Number(section.physical_position)" in INDEX
    assert "Number(s.physical_position)===Number(section.physical_position)&&Number(s.units||0)>0" not in INDEX
    assert "dead=Number(slot.units||0)===0,hp=dead?0:Number(slot.hit_points_percent??0)" in INDEX
    assert "return '<div class=\"slot'+(dead?' dead':'')+'\" tabindex=\"0\"'" in INDEX
    assert 'tooltipAttribute(slotTooltipHtml(slot))' in INDEX
    assert 'const showWall=wall?.active&&(wall.sections||[]).some(section=>!section.destroyed)' in INDEX
    assert "battleHalf(round.defender,'defender',round.wall)" in INDEX
    assert '城牆反擊尚未建模' in INDEX
    assert 'section.remaining_hit_points' in INDEX
    assert 'physical_position' in INDEX
    assert 'tooltipAttribute(details)' in INDEX


def test_battlefield_air_units_match_game_left_right_layout():
    assert "const left=sideLine(state,'balloon',geometry,'left');" in INDEX
    assert "const right=sideLine(state,'anti-balloon',geometry,'right');" in INDEX
    assert "const left=sideLine(state,'anti-balloon',geometry,'left');" not in INDEX



def test_setup_unit_icon_keeps_fixed_size_when_identity_details_are_shown():
    assert ".unit-icon{width:46px;height:46px;min-width:46px;flex:0 0 46px" in INDEX
    assert ".show-unit-identity .unit-ident-copy{display:block}" in INDEX


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
