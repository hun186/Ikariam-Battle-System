from copy import deepcopy
from dataclasses import replace
import pytest
from ikariam_battle import simulate
from ikariam_battle.engine import _preflight
from ikariam_battle.battlefield import SMALL_LAND, deploy
from ikariam_battle.models import Army, ScenarioError
from ikariam_battle.units import UnitRegistry


def scenario(policy='experimental'):
 return {'policy':policy,'battlefield':'small-land','max_rounds':5,
  'attacker':{'workshop':{'attack_level':12,'armor_level':12},'forge_level':5,'units':[{'unit_id':'hoplite','quantity':60}]},
  'defender':{'workshop':{'attack_level':12,'armor_level':12},'forge_level':0,'units':[{'unit_id':'hoplite','quantity':60}]}}


def test_strict_refuses_unknown_mechanics_without_casualties():
 r=simulate(scenario('strict'))
 assert r['status']=='inconclusive' and r['rounds_completed']==0 and not r['casualties']['attacker']
 assert {'UNKNOWN-KILL-SELECTION','UNKNOWN-COMPLETE-CHRONOLOGY'} <= {e['details']['rule_id'] for e in r['events'] if e['type']=='unsupported_mechanic'}


def test_experimental_names_every_policy_and_is_reproducible():
 first=simulate(scenario()); second=simulate(scenario())
 assert first==second
 ids={a['id'] for a in first['assumptions']}
 assert {'EXP-I-KILL-001','EXP-ROUND-FLOOR-001','EXP-CHRONOLOGY-001','EXP-AMMO-STOP-001'} <= ids
 assert any(e['type']=='damage_calculation' and e['details']['workshop_attack_level']==12 for e in first['events'])


def test_symmetric_case_has_no_attacker_first_bias():
 s=scenario(); s['defender']['forge_level']=5
 r=simulate(s)
 assert r['casualties']['attacker']==r['casualties']['defender']


def test_ammo_is_consumed_and_primary_does_not_fire_forever():
 s=scenario(); s['attacker']['units']=[{'unit_id':'sulphur_carabineer','quantity':14}]
 s['defender']['units']=[{'unit_id':'hoplite','quantity':90}]
 r=simulate(s)
 assert any(e['type']=='ammo_exhausted' for e in r['events'])
 assert not any(e['type']=='attacking_matrix' and e['side']=='attacker' and e['round']>3 for e in r['events'])


def test_row_order_is_invariant_after_normalization():
 one=scenario(); one['attacker']['units']=[{'unit_id':'hoplite','quantity':60,'wave_id':'w'}]
 split=deepcopy(one); split['attacker']['units']=[{'unit_id':'hoplite','quantity':30,'wave_id':'w'},{'unit_id':'hoplite','quantity':30,'wave_id':'w'}]
 assert simulate(one)==simulate(split)


def test_mixed_unit_line_is_inconclusive_not_row_order_rule():
 registry=UnitRegistry.load()
 registry._definitions['swordsman']=replace(registry.get('swordsman'),battlefield_class='first')
 army=Army.from_dict({'units':[{'unit_id':'hoplite','quantity':30},{'unit_id':'swordsman','quantity':30}]})
 assert 'UNKNOWN-MIXED-UNIT-AM-ROWS' in _preflight(deploy(army,registry,SMALL_LAND),registry)


def test_domain_and_unsupported_naval_geometry_rejections():
 s=scenario(); s['attacker']['units']=[{'unit_id':'rocket_ship','quantity':1}]
 with pytest.raises(ScenarioError): simulate(s)
 s=scenario(); s['battlefield']='small-naval'; s['attacker']['units']=[{'unit_id':'hoplite','quantity':1}]
 with pytest.raises(ScenarioError): simulate(s)


def test_support_strict_boundary_and_wrong_domain():
 s=scenario('strict'); s['attacker']['units'].append({'unit_id':'doctor','quantity':1})
 r=simulate(s)
 assert 'UNKNOWN-HEALING-ALLOCATION' in {e['details']['rule_id'] for e in r['events'] if e['type']=='unsupported_mechanic'}
 s=scenario(); s['attacker']['units']=[{'unit_id':'tender','quantity':1}]
 with pytest.raises(ScenarioError): simulate(s)


def test_snapshots_preserve_line_and_both_positions():
 slot=next(s for s in simulate(scenario('strict'))['initial_state']['attacker']['slots'] if s['damage_position']==1)
 assert slot['line']=='first' and slot['damage_position']==1 and slot['physical_position']==2
