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


def test_wall_level_defaults_to_zero_and_accepts_current_maximum():
 assert Scenario.from_dict(BASE).wall_level==0
 assert Scenario.from_dict({**BASE,'wall_level':48}).wall_level==48
 for bad in (-1,49,True,'20'):
  with pytest.raises(ScenarioError):
   Scenario.from_dict({**BASE,'wall_level':bad})


def test_town_hall_level_is_optional_and_validates_current_range():
 assert Scenario.from_dict(BASE).town_hall_level is None
 assert Scenario.from_dict({**BASE,'town_hall_level':1}).town_hall_level==1
 assert Scenario.from_dict({**BASE,'town_hall_level':66}).town_hall_level==66
 for bad in (0,67,True,'25'):
  with pytest.raises(ScenarioError):
   Scenario.from_dict({**BASE,'town_hall_level':bad})


def test_barbarian_village_level_is_optional_and_validates_range():
 assert Scenario.from_dict(BASE).barbarian_village_level is None
 assert Scenario.from_dict({**BASE,'barbarian_village_level':1}).barbarian_village_level==1
 assert Scenario.from_dict({**BASE,'barbarian_village_level':50}).barbarian_village_level==50
 for bad in (0,51,True,'20'):
  with pytest.raises(ScenarioError):
   Scenario.from_dict({**BASE,'barbarian_village_level':bad})


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


def test_same_unit_wave_id_cannot_be_reused_across_entry_batches():
 with pytest.raises(ScenarioError,match='cannot be reused across entry batches'):
  Army.from_dict({'units':[
   {'unit_id':'hoplite','quantity':10,'entry_batch_id':'batch-a','wave_id':'same'},
   {'unit_id':'hoplite','quantity':20,'entry_batch_id':'batch-b','wave_id':'same'},
  ]})


def test_same_unit_wave_id_may_repeat_inside_one_entry_batch_and_aggregates():
 army=Army.from_dict({'units':[
  {'unit_id':'hoplite','quantity':10,'entry_batch_id':'batch-a','wave_id':'same'},
  {'unit_id':'hoplite','quantity':20,'entry_batch_id':'batch-a','wave_id':'same'},
 ]})
 assert len(army.units)==1
 assert army.units[0].quantity==30
 assert army.units[0].batch_id=='batch-a'


@pytest.mark.parametrize('field,bad',[
 ('entry_batch_id',''),('entry_batch_id',0),('entry_batch_id',False),('entry_batch_id',None),
 ('wave_id',''),('wave_id',0),('wave_id',False),('wave_id',None),
])
def test_explicit_invalid_batch_or_wave_identity_is_rejected(field,bad):
 row={'unit_id':'hoplite','quantity':10,field:bad}
 with pytest.raises(ScenarioError,match=f'{field} must be a non-empty string'):
  Army.from_dict({'units':[row]})


def test_barbarian_army_package_rejects_player_only_controls():
 army=Army.from_dict({'army_kind':'barbarian','forge_level':0,'units':[
  {'unit_id':'barbarian_clubman','quantity':30,'entry_batch_id':'barbarian'}]})
 assert army.army_kind=='barbarian'
 assert army.forge_level==0
 with pytest.raises(ScenarioError,match='do not use Forge'):
  Army.from_dict({'army_kind':'barbarian','forge_level':1,'units':[
   {'unit_id':'barbarian_clubman','quantity':30,'entry_batch_id':'barbarian'}]})
 with pytest.raises(ScenarioError,match='do not use Workshop'):
  Army.from_dict({'army_kind':'barbarian','units':[
   {'unit_id':'barbarian_clubman','quantity':30,'entry_batch_id':'barbarian','attack_upgrade':1}]})
 with pytest.raises(ScenarioError,match='delayed entry'):
  Army.from_dict({'army_kind':'barbarian','units':[
   {'unit_id':'barbarian_clubman','quantity':30,'entry_batch_id':'barbarian','arrival_round':1}]})


def test_barbarian_army_uses_one_batch_and_one_wave_per_unit_type():
 with pytest.raises(ScenarioError,match='one fixed entry batch'):
  Army.from_dict({'army_kind':'barbarian','units':[
   {'unit_id':'barbarian_clubman','quantity':10,'entry_batch_id':'a'},
   {'unit_id':'barbarian_ram','quantity':1,'entry_batch_id':'b'}]})
 with pytest.raises(ScenarioError,match='cannot be split across waves'):
  Army.from_dict({'army_kind':'barbarian','units':[
   {'unit_id':'barbarian_clubman','quantity':10,'entry_batch_id':'barbarian','wave_id':'w1'},
   {'unit_id':'barbarian_clubman','quantity':10,'entry_batch_id':'barbarian','wave_id':'w2'}]})


@pytest.mark.parametrize('bad',['pirate',[],{},None,False])
def test_invalid_army_kind_is_rejected(bad):
 with pytest.raises(ScenarioError,match='army_kind must be player or barbarian'):
  Army.from_dict({'army_kind':bad,'units':[{'unit_id':'hoplite','quantity':1}]})
