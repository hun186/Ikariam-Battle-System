from ikariam_battle.garrison import (
 barbarian_garrison_limit, counted_garrison_quantity,
 garrison_profile_metadata, land_garrison_status,
 player_garrison_limit, player_garrison_status,
)
from ikariam_battle.models import Army


def test_player_garrison_formula_and_strict_open_field_threshold():
 assert player_garrison_limit(1,0)==300
 assert player_garrison_limit(25,20)==2500
 army=Army.from_dict({'units':[{'unit_id':'hoplite','quantity':300}]})
 at_limit=player_garrison_status(
  town_hall_level=1,wall_level=0,defender_army=army,
  base_battlefield_id='land-mini')
 assert at_limit['open_field'] is False
 over=Army.from_dict({'units':[{'unit_id':'hoplite','quantity':301}]})
 above=player_garrison_status(
  town_hall_level=1,wall_level=0,defender_army=over,
  base_battlefield_id='land-mini')
 assert above['open_field'] is True
 assert above['effective_battlefield']=='land-max'


def test_v17_4_support_units_do_not_count_toward_land_garrison_limit():
 army=Army.from_dict({'units':[
  {'unit_id':'hoplite','quantity':250},
  {'unit_id':'doctor','quantity':100},
  {'unit_id':'cook','quantity':100},
 ]})
 assert counted_garrison_quantity(army)==250
 status=player_garrison_status(
  town_hall_level=1,wall_level=0,defender_army=army,
  base_battlefield_id='land-mini')
 assert status['garrison_limit']==300
 assert status['counted_defenders']==250
 assert status['open_field'] is False


def test_barbarian_formula_matches_2024_forum_rule_and_strict_threshold():
 assert barbarian_garrison_limit(10,1)==800
 army=Army.from_dict({'army_kind':'barbarian','units':[
  {'unit_id':'barbarian_clubman','quantity':800}
 ]})
 at_limit=land_garrison_status(
  town_hall_level=None,barbarian_village_level=10,wall_level=1,
  defender_army=army,base_battlefield_id='land-small')
 assert at_limit['open_field'] is False
 over=Army.from_dict({'army_kind':'barbarian','units':[
  {'unit_id':'barbarian_clubman','quantity':801}
 ]})
 above=land_garrison_status(
  town_hall_level=None,barbarian_village_level=10,wall_level=1,
  defender_army=over,base_battlefield_id='land-small')
 assert above['open_field'] is True
 assert above['effective_battlefield']=='land-max'
 meta=garrison_profile_metadata()
 assert meta['barbarian_formula']=='(barbarian_village_level + wall_level + 5) * 50'
 assert meta['barbarian_formula_status']=='GAMEFORGE_FORUM_2024_COMMUNITY_REPORT'
 assert meta['barbarian_historical_approximation']=='approximately 250 + 75 * wall_level'
