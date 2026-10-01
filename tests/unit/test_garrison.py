from ikariam_battle.garrison import (
 BARBARIAN_GARRISON_RULE_ID, counted_garrison_quantity,
 garrison_profile_metadata, player_garrison_limit, player_garrison_status,
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


def test_barbarian_formula_remains_non_executable_due_to_conflicting_evidence():
 army=Army.from_dict({'army_kind':'barbarian','units':[
  {'unit_id':'barbarian_clubman','quantity':100}
 ]})
 status=player_garrison_status(
  town_hall_level=None,wall_level=0,defender_army=army,
  base_battlefield_id='land-max')
 assert status['modeled'] is False
 assert status['status']=='barbarian_formula_unresolved'
 assert status['rule_id']==BARBARIAN_GARRISON_RULE_ID
 meta=garrison_profile_metadata()
 assert meta['barbarian_formula_status']=='CONFLICTING_COMMUNITY_EVIDENCE'
 assert len(meta['barbarian_candidates'])==2
