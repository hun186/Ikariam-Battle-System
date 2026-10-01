from ikariam_battle.battlefield import LAND_BATTLEFIELDS
from ikariam_battle.wall import (
 MAX_TOWN_WALL_LEVEL, successful_hits_to_breach_wall_section,
 wall_profile_metadata, wall_stats, wall_status,
)


def test_infinite_horizons_wall_hp_armour_and_maximum():
 assert MAX_TOWN_WALL_LEVEL==48
 assert wall_stats(0)=={'level':0,'damage':0,'accuracy':0,'hit_points':0,'armor':0}
 assert wall_stats(1)=={'level':1,'damage':None,'accuracy':None,'hit_points':2700,'armor':72}
 assert wall_stats(10)=={'level':10,'damage':None,'accuracy':None,'hit_points':10800,'armor':720}
 assert wall_stats(20)=={'level':20,'damage':None,'accuracy':None,'hit_points':19800,'armor':1440}
 assert wall_stats(34)=={'level':34,'damage':None,'accuracy':None,'hit_points':32400,'armor':2448}
 assert wall_stats(48)=={'level':48,'damage':None,'accuracy':None,'hit_points':45000,'armor':3456}


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
 assert metadata['published_stat_fields']==['hit_points','armor']
 assert metadata['unresolved_current_stat_fields']==['damage','accuracy']
 assert metadata['hit_points_formula']=='1800 + 900 * level'
 assert metadata['armor_formula']=='72 * level'
 assert metadata['successful_breach_hits_formula']=='ceil((1800 + 900*level) / (attack_damage - 72*level))'
 assert len(metadata['source_urls'])==6


def test_wall_can_be_suppressed_by_open_field_state():
 status=wall_status(20,LAND_BATTLEFIELDS['land-mini'],active=False,inactive_reason='open_field_garrison_limit')
 assert status['status']=='suppressed'
 assert status['active'] is False
 assert status['inactive_reason']=='open_field_garrison_limit'
 assert status['segments']==3
