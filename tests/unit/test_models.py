import pytest
from ikariam_battle.models import Army, Scenario, ScenarioError

BASE={'policy':'strict','battlefield':'small-land','attacker':{'units':[{'unit_id':'hoplite','quantity':1}]},'defender':{'units':[{'unit_id':'hoplite','quantity':1}]}}


def test_workshop_above_three_accepted_and_negative_rejected():
    value={**BASE,'attacker':{'units':[{'unit_id':'hoplite','quantity':1}],'workshop':{'attack_level':30,'armor_level':12}}}
    assert Scenario.from_dict(value).attacker.workshop.attack_level==30
    value['attacker']['workshop']['attack_level']=-1
    with pytest.raises(ScenarioError): Scenario.from_dict(value)


def test_typed_ints_do_not_accept_bool_or_string():
    for bad in (True,'12'):
        value={**BASE,'max_rounds':bad}
        with pytest.raises(ScenarioError): Scenario.from_dict(value)
