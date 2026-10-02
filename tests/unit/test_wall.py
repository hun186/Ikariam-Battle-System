from ikariam_battle.battlefield import LAND_BATTLEFIELDS
from ikariam_battle.wall import (
 MAX_TOWN_WALL_LEVEL, apply_exact_wall_redistribution,
 apply_wall_successful_hit, initial_wall_sections,
 successful_hits_to_breach_wall_section, wall_breached_positions,
 wall_flanks_locked, wall_profile_metadata, wall_redistribution_plan,
 wall_section_snapshot, wall_stats, wall_status,
)


def test_infinite_horizons_wall_hp_armour_and_maximum():
 assert MAX_TOWN_WALL_LEVEL==48
 assert wall_stats(0)=={'level':0,'damage':0,'accuracy':0,'hit_points':0,'armor':0}
 assert wall_stats(1)=={'level':1,'damage':216,'accuracy':None,'hit_points':2700,'armor':72}
 assert wall_stats(9)=={'level':9,'damage':504,'accuracy':None,'hit_points':9900,'armor':648}
 assert wall_stats(10)=={'level':10,'damage':1440,'accuracy':None,'hit_points':10800,'armor':720}
 assert wall_stats(18)=={'level':18,'damage':2160,'accuracy':None,'hit_points':18000,'armor':1296}
 assert wall_stats(19)=={'level':19,'damage':2250,'accuracy':None,'hit_points':18900,'armor':1368}
 assert wall_stats(20)=={'level':20,'damage':4500,'accuracy':None,'hit_points':19800,'armor':1440}
 assert wall_stats(26)=={'level':26,'damage':5580,'accuracy':None,'hit_points':25200,'armor':1872}
 assert wall_stats(34)=={'level':34,'damage':7020,'accuracy':None,'hit_points':32400,'armor':2448}
 assert wall_stats(48)=={'level':48,'damage':9540,'accuracy':None,'hit_points':45000,'armor':3456}


def test_successful_hits_to_breach_wall_section_matches_spreadsheet_core():
 # Base Infinite Horizons Mortar primary damage = 5400.
 assert successful_hits_to_breach_wall_section(10,5400)==3
 assert successful_hits_to_breach_wall_section(48,5400)==24
 assert successful_hits_to_breach_wall_section(48,3456) is None
 assert successful_hits_to_breach_wall_section(0,5400)==0

def test_wall_sections_follow_selected_land_first_line_geometry():
 assert wall_status(1,LAND_BATTLEFIELDS['land-mini'])['segments']==3
 assert wall_status(1,LAND_BATTLEFIELDS['land-small'])['segments']==5
 assert wall_status(1,LAND_BATTLEFIELDS['land-medium'])['segments']==7
 assert wall_status(1,LAND_BATTLEFIELDS['land-large'])['segments']==7
 assert wall_status(1,LAND_BATTLEFIELDS['land-max'])['segments']==7


def test_wall_section_state_uses_first_line_physical_and_damage_positions():
 sections=initial_wall_sections(10,LAND_BATTLEFIELDS['land-mini'])
 assert [
  (section.physical_position,section.damage_position)
  for section in sections
 ]==[(1,2),(2,1),(3,3)]
 assert wall_breached_positions(sections)==()
 assert wall_flanks_locked(sections) is True
 assert wall_section_snapshot(sections,10)==[
  {'damage_position':2,'physical_position':1,'damage':0,
   'remaining_hit_points':10800,'destroyed':False},
  {'damage_position':1,'physical_position':2,'damage':0,
   'remaining_hit_points':10800,'destroyed':False},
  {'damage_position':3,'physical_position':3,'damage':0,
   'remaining_hit_points':10800,'destroyed':False},
 ]


def test_wall_successful_hit_applies_post_armor_damage_and_breaches_one_section():
 sections=initial_wall_sections(10,LAND_BATTLEFIELDS['land-mini'])
 # Lv10 HP=10800, Armor=720. A 5400 Mortar hit applies 4680 damage.
 first=apply_wall_successful_hit(sections,10,1,5400)
 second=apply_wall_successful_hit(sections,10,1,5400)
 third=apply_wall_successful_hit(sections,10,1,5400)
 assert first['damage_applied']==4680 and first['destroyed'] is False
 assert second['persistent_damage']==9360 and second['destroyed'] is False
 assert third['damage_applied']==1440 and third['destroyed'] is True
 assert wall_breached_positions(sections)==(1,)
 assert wall_flanks_locked(sections) is True
 assert next(s for s in sections if s.damage_position==1).damage==10800


def test_wall_nonpenetrating_or_already_breached_hit_does_not_mutate_section():
 sections=initial_wall_sections(48,LAND_BATTLEFIELDS['land-mini'])
 before=wall_section_snapshot(sections,48)
 blocked=apply_wall_successful_hit(sections,48,1,3456)
 assert blocked=={
  'applied':False,'reason':'effective_attack_not_above_defense',
  'damage_position':1,'net_damage':0,'damage_applied':0,'destroyed':False,
 }
 assert wall_section_snapshot(sections,48)==before

 section=next(s for s in sections if s.damage_position==1)
 section.damage=45000
 section.destroyed=True
 repeated=apply_wall_successful_hit(sections,48,1,5400)
 assert repeated['applied'] is False
 assert repeated['reason']=='section_already_breached'
 assert section.damage==45000


def test_wall_flanks_unlock_only_after_every_section_is_breached():
 sections=initial_wall_sections(1,LAND_BATTLEFIELDS['land-mini'])
 for position in (1,2):
  section=next(s for s in sections if s.damage_position==position)
  section.damage=2700
  section.destroyed=True
 assert wall_flanks_locked(sections) is True
 final=next(s for s in sections if s.damage_position==3)
 final.damage=2700
 final.destroyed=True
 assert wall_breached_positions(sections)==(1,2,3)
 assert wall_flanks_locked(sections) is False


def test_wall_round_start_redistribution_is_exact_only_without_rounding_choice():
 sections=initial_wall_sections(1,LAND_BATTLEFIELDS['land-mini'])
 by_position={section.damage_position:section for section in sections}
 by_position[1].damage=900
 by_position[2].damage=600
 by_position[3].damage=0
 plan=wall_redistribution_plan(sections,1)
 assert plan=={
  'status':'exact','surviving_positions':[1,2,3],
  'total_damage':1500,'per_section_damage':500,'remainder':0,
 }
 assert apply_exact_wall_redistribution(sections,1)==plan
 assert {section.damage_position:section.damage for section in sections}=={
  1:500,2:500,3:500,
 }

 by_position[1].damage=501
 unresolved=wall_redistribution_plan(sections,1)
 assert unresolved['status']=='rounding_unresolved'
 assert unresolved['total_damage']==1501
 assert unresolved['per_section_damage'] is None
 assert unresolved['remainder']==1
 with pytest.raises(ValueError,match='rounding is unresolved'):
  apply_exact_wall_redistribution(sections,1)


def test_wall_redistribution_excludes_destroyed_sections_and_preserves_breach():
 sections=initial_wall_sections(1,LAND_BATTLEFIELDS['land-mini'])
 by_position={section.damage_position:section for section in sections}
 by_position[1].damage=2700
 by_position[1].destroyed=True
 by_position[2].damage=800
 by_position[3].damage=400
 plan=apply_exact_wall_redistribution(sections,1)
 assert plan['surviving_positions']==[2,3]
 assert plan['total_damage']==1200
 assert plan['per_section_damage']==600
 assert by_position[1].damage==2700 and by_position[1].destroyed is True
 assert by_position[2].damage==600 and by_position[3].damage==600


def test_wall_metadata_is_input_supported_but_combat_guarded():
 metadata=wall_profile_metadata()
 assert metadata['max_level']==48
 assert metadata['input_supported'] is True
 assert metadata['combat_model_status']=='INPUT_CAPTURED_COMBAT_UNSUPPORTED'
 assert metadata['rule_id']=='UNKNOWN-TOWN-WALL-COMBAT'
 assert metadata['source_type']=='MIXED_CURRENT_REFERENCE'
 assert metadata['gameforge_reference_max_level']==46
 assert metadata['current_game_max_level_evidence']=='GAMEFORGE_FORUM_PLUS_COMMUNITY_TABLE'
 assert metadata['published_stat_fields']==['hit_points','armor','damage']
 assert metadata['unresolved_current_stat_fields']==['accuracy']
 assert metadata['hit_points_formula']=='1800 + 900 * level'
 assert metadata['armor_formula']=='72 * level'
 assert metadata['damage_formula']=={
  '1-9':'(10 + 2*level) * 18',
  '10-19':'(30 + 5*level) * 18',
  '20+':'(50 + 10*level) * 18',
 }
 assert metadata['damage_observed_points']=={'1':216,'9':504,'18':2160,'26':5580}
 assert metadata['successful_breach_hits_formula']=='ceil((1800 + 900*level) / (attack_damage - 72*level))'
 assert metadata['section_state_contract']['status']=='EXECUTABLE_CORE_ENGINE_GUARDED'
 assert metadata['section_state_contract']['identity']=='selected battlefield First-line damage_position'
 assert metadata['section_state_contract']['flank_lock']=='locked while any wall section survives'
 assert metadata['section_state_contract']['redistribution_rounding']=='unresolved when total damage is not evenly divisible'
 assert metadata['targeting_contract']['artillery_priority']==['wall','first']
 assert metadata['targeting_contract']['penetration_rule']=='effective_attack > effective_defense'
 assert metadata['targeting_contract']['non_penetrating_target_consumes_ammunition'] is False
 assert len(metadata['source_urls'])==8


def test_wall_can_be_suppressed_by_open_field_state():
 status=wall_status(20,LAND_BATTLEFIELDS['land-mini'],active=False,inactive_reason='open_field_garrison_limit')
 assert status['status']=='suppressed'
 assert status['active'] is False
 assert status['inactive_reason']=='open_field_garrison_limit'
 assert status['segments']==3
