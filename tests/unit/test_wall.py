from ikariam_battle.battlefield import LAND_BATTLEFIELDS
from ikariam_battle.wall import MAX_TOWN_WALL_LEVEL, wall_profile_metadata, wall_stats, wall_status


def test_published_wall_stat_breakpoints_and_maximum():
 assert MAX_TOWN_WALL_LEVEL==46
 assert wall_stats(0)=={'level':0,'damage':0,'accuracy':0,'hit_points':0,'armor':0}
 assert wall_stats(1)=={'level':1,'damage':12,'accuracy':30,'hit_points':150,'armor':4}
 assert wall_stats(9)=={'level':9,'damage':28,'accuracy':30,'hit_points':550,'armor':36}
 assert wall_stats(10)=={'level':10,'damage':80,'accuracy':50,'hit_points':600,'armor':40}
 assert wall_stats(19)=={'level':19,'damage':125,'accuracy':50,'hit_points':1050,'armor':76}
 assert wall_stats(20)=={'level':20,'damage':250,'accuracy':80,'hit_points':1100,'armor':80}
 assert wall_stats(46)=={'level':46,'damage':510,'accuracy':80,'hit_points':2400,'armor':184}


def test_wall_sections_follow_selected_land_first_line_geometry():
 assert wall_status(1,LAND_BATTLEFIELDS['land-mini'])['segments']==3
 assert wall_status(1,LAND_BATTLEFIELDS['land-small'])['segments']==5
 assert wall_status(1,LAND_BATTLEFIELDS['land-medium'])['segments']==7
 assert wall_status(1,LAND_BATTLEFIELDS['land-large'])['segments']==7
 assert wall_status(1,LAND_BATTLEFIELDS['land-max'])['segments']==7


def test_wall_metadata_is_input_supported_but_combat_guarded():
 metadata=wall_profile_metadata()
 assert metadata['max_level']==46
 assert metadata['input_supported'] is True
 assert metadata['combat_model_status']=='INPUT_CAPTURED_COMBAT_UNSUPPORTED'
 assert metadata['rule_id']=='UNKNOWN-TOWN-WALL-COMBAT'
 assert metadata['source_type']=='GAMEFORGE_CURRENT_REFERENCE_PLUS_COMMUNITY_FORMULA'
 assert len(metadata['source_urls'])==2
