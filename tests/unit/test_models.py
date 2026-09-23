import pytest
from ikariam_battle.models import Army, Scenario, ScenarioError

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
