import pytest
from ikariam_battle.models import Army, Profiles, Scenario, ScenarioError

BASE={'policy':'strict','battlefield':'land-mini','attacker':{'units':[{'unit_id':'hoplite','quantity':1}]},'defender':{'units':[{'unit_id':'hoplite','quantity':1}]}}


def test_unit_specific_workshop_levels_above_three():
 army=Army.from_dict({'forge_level':5,'units':[{'unit_id':'hoplite','quantity':30,'attack_upgrade':12,'armor_upgrade':8},{'unit_id':'swordsman','quantity':20,'attack_upgrade':3,'armor_upgrade':2}]})
 levels={u.unit_id:(u.attack_upgrade,u.armor_upgrade) for u in army.units}
 assert levels=={'hoplite':(12,8),'swordsman':(3,2)}


def test_same_unit_conflicting_workshop_levels_rejected_across_waves():
 with pytest.raises(ScenarioError,match='conflicting Workshop'):
  Army.from_dict({'units':[{'unit_id':'hoplite','quantity':30,'attack_upgrade':12},{'unit_id':'hoplite','quantity':30,'wave_id':'w2','attack_upgrade':3}]})


def test_negative_upgrade_and_non_integer_rejected():
 for bad in (-1,True,'12'):
  value={**BASE,'attacker':{'units':[{'unit_id':'hoplite','quantity':1,'attack_upgrade':bad}]}}
  with pytest.raises(ScenarioError): Scenario.from_dict(value)


def test_profiles_preserve_original_eight_positional_arguments():
 legacy=Profiles(
  'battle-system-paper-2020',
  'infinite-horizons-current',
  'v14-workshop',
  'v14-hephaistos',
  'v17-support-healing',
  'legacy-community-land-targeting',
  'legacy-community-battle-end',
  'formation-land',
 )
 assert legacy==Profiles()
 assert legacy.economy=='military-economy-current'


def test_profiles_from_dict_uses_named_mapping_with_economy_extension():
 value=Profiles.from_dict({'economy':'military-economy-current'})
 assert value==Profiles()
 assert value.workshop=='v14-workshop' and value.economy=='military-economy-current'


def test_max_rounds_defaults_to_100_and_allows_1000_safety_cap():
 assert Scenario.from_dict(BASE).max_rounds==100
 assert Scenario.from_dict({**BASE,'max_rounds':1000}).max_rounds==1000
 with pytest.raises(ScenarioError,match='max_rounds must be 1..1000'):
  Scenario.from_dict({**BASE,'max_rounds':1001})


def test_entry_batch_can_group_multiple_unit_types_without_merging_unit_state():
 army=Army.from_dict({'units':[
  {'unit_id':'hoplite','quantity':30,'entry_batch_id':'batch-a','arrival_round':0},
  {'unit_id':'swordsman','quantity':20,'entry_batch_id':'batch-a','arrival_round':0},
 ]})
 assert {u.batch_id for u in army.units}=={'batch-a'}
 assert {u.wave_id for u in army.units}=={'batch-a::hoplite','batch-a::swordsman'}


def test_entry_batch_requires_one_shared_arrival_round():
 with pytest.raises(ScenarioError,match='conflicting arrival_round'):
  Army.from_dict({'units':[
   {'unit_id':'hoplite','quantity':30,'entry_batch_id':'batch-a','arrival_round':0},
   {'unit_id':'swordsman','quantity':20,'entry_batch_id':'batch-a','arrival_round':2},
  ]})


def test_legacy_wave_id_remains_backward_compatible_as_batch_identity():
 army=Army.from_dict({'units':[{'unit_id':'hoplite','quantity':30,'wave_id':'legacy-w1'}]})
 unit=army.units[0]
 assert unit.wave_id=='legacy-w1' and unit.batch_id=='legacy-w1' and unit.arrival_round==0
