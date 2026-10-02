from ikariam_battle.battlefield import LAND_BATTLEFIELDS
from ikariam_battle.wall import (
 MAX_TOWN_WALL_LEVEL, successful_hits_to_breach_wall_section,
 wall_profile_metadata, wall_stats, wall_status,
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
