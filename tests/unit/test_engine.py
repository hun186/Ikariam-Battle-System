from copy import deepcopy
import pytest
from ikariam_battle import simulate
from ikariam_battle.battlefield import LAND_MINI, deploy
from ikariam_battle.engine import _plan_fire, _preflight, _prepare_round_start, _target
from ikariam_battle.formation import FormationRules
from ikariam_battle.models import Army, ArmyUnit, ScenarioError, Slot, Wave
from ikariam_battle.profiles import ForgeProfile, TargetingProfile, WorkshopProfile
from ikariam_battle.units import UnitRegistry


def scenario(policy='experimental',rounds=5):
 return {'policy':policy,'battlefield':'land-mini','max_rounds':rounds,
  'attacker':{'forge_level':5,'units':[{'unit_id':'hoplite','quantity':60,'attack_upgrade':12,'armor_upgrade':8}]},
  'defender':{'forge_level':0,'units':[{'unit_id':'hoplite','quantity':60,'attack_upgrade':4,'armor_upgrade':6}]}}


def test_strict_refuses_accuracy_targeting_and_other_unknowns():
 r=simulate(scenario('strict')); rules={e['details']['rule_id'] for e in r['events'] if e['type']=='unsupported_mechanic'}
 assert r['status']=='inconclusive' and r['rounds_completed']==0
 assert {'UNKNOWN-KILL-SELECTION','UNKNOWN-ACCURACY','UNKNOWN-TARGET-TRANSFER'} <= rules


def test_experimental_names_accuracy_targeting_and_is_reproducible():
 first=simulate(scenario()); assert first==simulate(scenario())
 ids={a['id'] for a in first['assumptions']}
 assert {'EXP-I-KILL-001','EXP-ACCURACY-IGNORED-001','EXP-TARGET-LEGACY-001'} <= ids
 assert 'EXP-AMMO-PARTIAL-ORDER-001' not in ids
 assert len(ids)==len(first['assumptions'])
 assert any(e['type']=='damage_calculation' and e['details']['workshop_attack_level']==12 for e in first['events'])


def test_symmetric_case_has_no_attacker_first_bias():
 s=scenario(); s['defender']=deepcopy(s['attacker']); r=simulate(s)
 assert r['casualties']['attacker']==r['casualties']['defender']


def test_carabineer_ammunition_is_pooled_shots_not_round_counter():
 registry=UnitRegistry.load(); attacker_army=Army.from_dict({'units':[{'unit_id':'sulphur_carabineer','quantity':42}]})
 defender_army=Army.from_dict({'units':[{'unit_id':'hoplite','quantity':90}]})
 attacker=deploy(attacker_army,registry,LAND_MINI); defender=deploy(defender_army,registry,LAND_MINI); events=[]
 assert attacker[0].ammo_pool_shots==126 and sum(s.units for s in attacker[0].slots)==21
 for round_no in range(1,5):
  plans=_plan_fire(attacker,deepcopy(defender),registry,WorkshopProfile.load(),ForgeProfile.load(),TargetingProfile.load(),events,round_no,'attacker',attacker_army,defender_army,{})
  assert plans
 assert attacker[0].ammo_pool_shots==42
 assert not any(e.type=='ammo_exhausted' for e in events)
 assert {e.details['weapon_id'] for e in events if e.type=='damage_calculation'}=={'primary'}


def test_partial_ammo_assumption_is_applied_only_when_partial_volley_occurs():
 registry=UnitRegistry.load(); attacker_army=Army.from_dict({'units':[{'unit_id':'sulphur_carabineer','quantity':42}]}); defender_army=Army.from_dict({'units':[{'unit_id':'hoplite','quantity':90}]})
 attacker=deploy(attacker_army,registry,LAND_MINI); defender=deploy(defender_army,registry,LAND_MINI)
 attacker[0].ammo_pool_shots=5; events=[]; applied={}
 _plan_fire(attacker,defender,registry,WorkshopProfile.load(),ForgeProfile.load(),TargetingProfile.load(),events,1,'attacker',attacker_army,defender_army,applied)
 assert list(applied).count('EXP-AMMO-PARTIAL-ORDER-001')==1


def target_wave(unit,line,units=10,reserve=0):
 slot=Slot(f'{line}-1',line,1,1,unit,'w',units,30)
 return Wave(ArmyUnit(unit,units+reserve,'w'),reserve,[slot])


def test_reserve_only_priority_class_is_skipped_for_deployed_target():
 registry=UnitRegistry.load(); targeting=TargetingProfile.load()
 source=Wave(ArmyUnit('sulphur_carabineer',7),7)
 reserve_flank=Wave(ArmyUnit('swordsman',10),10,[])
 ranged=target_wave('archer','second')
 target,target_class=_target(source,[reserve_flank,ranged],registry,targeting)
 assert target is ranged and target_class=='second'


def test_swordsman_targets_deployed_flank_before_front():
 registry=UnitRegistry.load(); targeting=TargetingProfile.load()
 source=Wave(ArmyUnit('swordsman',10),10)
 front=target_wave('hoplite','first'); flank=target_wave('swordsman','flank')
 targets=[front,flank]
 target,target_class=_target(source,targets,registry,targeting)
 assert target_class=='flank' and target is flank


def test_target_priority_uses_runtime_line_not_legacy_class():
 registry=UnitRegistry.load(); targeting=TargetingProfile.load()
 source=target_wave('swordsman','first')
 front=target_wave('hoplite','first'); flank=target_wave('swordsman','flank')
 target,target_class=_target(source,[front,flank],registry,targeting)
 assert target_class=='first' and target is front


def test_destroyed_deployed_wave_is_not_targetable():
 registry=UnitRegistry.load(); targeting=TargetingProfile.load(); source=Wave(ArmyUnit('swordsman',10),10)
 dead_flank=target_wave('swordsman','flank',0); front=target_wave('hoplite','first')
 target,target_class=_target(source,[dead_flank,front],registry,targeting)
 assert target is front and target_class=='first'


def test_support_unknowns_distinguish_healing_and_morale():
 registry=UnitRegistry.load()
 doctor=deploy(Army.from_dict({'units':[{'unit_id':'doctor','quantity':1}]}),registry,LAND_MINI)
 cook=deploy(Army.from_dict({'units':[{'unit_id':'cook','quantity':1}]}),registry,LAND_MINI)
 assert _preflight(doctor,registry,FormationRules.load(),LAND_MINI)==['UNKNOWN-HEALING-ALLOCATION']
 assert _preflight(cook,registry,FormationRules.load(),LAND_MINI)==['UNKNOWN-MORALE-SUPPORT']
 s=scenario(); s['attacker']['units'].append({'unit_id':'cook','quantity':15}); r=simulate(s)
 assert 'EXP-MORALE-NONE-001' in {a['id'] for a in r['assumptions']}
 assert 'EXP-HEAL-NONE-001' not in {a['id'] for a in r['assumptions']}
 morale=r['morale_status']
 assert morale['modeled'] is False
 assert morale['strict_rule_id']=='UNKNOWN-MORALE-SUPPORT'
 assert morale['experimental_assumption_id']=='EXP-MORALE-NONE-001'
 assert morale['sides']['attacker']=={'cook_count':15,'status':'ignored_by_named_assumption','effect_applied':False}
 assert morale['sides']['defender']=={'cook_count':0,'status':'not_present','effect_applied':False}

 strict=scenario('strict'); strict['attacker']['units'].append({'unit_id':'cook','quantity':15}); blocked=simulate(strict)
 assert blocked['status']=='inconclusive' and blocked['rounds_completed']==0
 assert blocked['morale_status']['sides']['attacker']['status']=='unsupported_boundary'
 assert blocked['morale_status']['sides']['attacker']['effect_applied'] is False


def test_support_is_deployed_separately_not_reported_as_reserve():
 s=scenario('strict'); s['attacker']['units'].append({'unit_id':'doctor','quantity':4})
 state=simulate(s)['initial_state']['attacker']
 assert state['deployed_support']=={'doctor':4}
 assert state['reserve'].get('doctor',0)==0


def test_single_weapon_light_fallback_has_no_specific_strict_blocker():
 s=scenario('strict'); s['attacker']['units']=[{'unit_id':'swordsman','quantity':30}]
 strict=simulate(s)
 rules={e['details']['rule_id'] for e in strict['events'] if e['type']=='unsupported_mechanic'}
 assert 'UNKNOWN-FALLBACK-LIGHT-INFANTRY-COMBAT' not in rules
 assert {'UNKNOWN-KILL-SELECTION','UNKNOWN-ACCURACY','UNKNOWN-TARGET-TRANSFER'} <= rules
 s['policy']='experimental'; experimental=simulate(s)
 assert any(e['type']=='attacking_matrix' for e in experimental['events'])


def test_homogeneous_swordsman_front_fires_primary_at_runtime_first_priority():
 s={'policy':'experimental','battlefield':'land-mini','max_rounds':1,
    'attacker':{'units':[{'unit_id':'swordsman','quantity':30}]},
    'defender':{'units':[{'unit_id':'hoplite','quantity':30}]}}
 result=simulate(s)
 rules={e['details']['rule_id'] for e in result['events'] if e['type']=='unsupported_mechanic'}
 assert 'UNKNOWN-FALLBACK-LIGHT-INFANTRY-COMBAT' not in rules
 deployment=next(e for e in result['events'] if e['type']=='deployment' and e['side']=='attacker')
 assert deployment['details']['line']=='first'
 matrix=next(e for e in result['events'] if e['type']=='attacking_matrix' and e['side']=='attacker')
 assert matrix['details']['target_class']=='first'
 assert matrix['details']['weapon_id']=='primary'
 damage=next(e for e in result['events'] if e['type']=='damage_calculation' and e['side']=='attacker')
 assert damage['details']['weapon_id']=='primary'


def test_round_start_refills_before_rr_uses_following_deployment():
 wave=Wave(ArmyUnit('hoplite',40,'w'),20,[Slot('first-1','first',2,1,'hoplite','w',20,30,20)],0,None)
 assert 'UNKNOWN-CROSS-WAVE-FORMATION-REBUILD' not in _preflight(
  [wave],UnitRegistry.load(),FormationRules.load(),LAND_MINI)
 events=[]; _prepare_round_start([wave],events,2,'attacker',{})
 assert (wave.slots[0].units,wave.slots[0].damage,wave.reserve,wave.reserve_damage)==(30,15,10,5)


def test_reserve_only_same_line_wave_stops_before_unsafe_cross_wave_rebuild():
 s={'policy':'experimental','battlefield':'land-mini','max_rounds':5,
    'attacker':{'units':[{'unit_id':'hoplite','quantity':90,'attack_upgrade':30}]},
    'defender':{'units':[{'unit_id':'hoplite','quantity':90,'wave_id':'wave-a'},
                         {'unit_id':'hoplite','quantity':90,'wave_id':'wave-b'}]}}
 result=simulate(s)
 assert result['status']=='inconclusive' and result['rounds_completed']==0
 assert result['initial_state']['defender']['reserve']['hoplite']==90
 assert result['initial_state']['defender']['remaining']['hoplite']==180
 rules={e['details']['rule_id'] for e in result['events'] if e['type']=='unsupported_mechanic'}
 assert 'UNKNOWN-CROSS-WAVE-FORMATION-REBUILD' in rules
 assert not any(e['type']=='attacking_matrix' for e in result['events'])


def test_reserve_light_fallback_candidate_stops_before_unsafe_cross_wave_rebuild():
 s={'policy':'experimental','battlefield':'land-mini','max_rounds':5,
    'attacker':{'units':[{'unit_id':'hoplite','quantity':90,'attack_upgrade':30}]},
    'defender':{'units':[{'unit_id':'hoplite','quantity':90},
                         {'unit_id':'swordsman','quantity':30}]}}
 result=simulate(s)
 assert result['status']=='inconclusive' and result['rounds_completed']==0
 assert result['initial_state']['defender']['reserve']['swordsman']==30
 rules={e['details']['rule_id'] for e in result['events'] if e['type']=='unsupported_mechanic'}
 assert 'UNKNOWN-CROSS-WAVE-FORMATION-REBUILD' in rules
 assert not any(e['type']=='attacking_matrix' for e in result['events'])


def test_unrelated_reserve_is_not_cross_wave_rebuild_candidate():
 registry=UnitRegistry.load(); rules=FormationRules.load()
 deployed=target_wave('hoplite','first',30)
 reserve=Wave(ArmyUnit('catapult',6,'reserve'),6)
 assert 'UNKNOWN-CROSS-WAVE-FORMATION-REBUILD' not in _preflight(
  [deployed,reserve],registry,rules,LAND_MINI)


def test_support_only_state_is_not_cross_wave_rebuild_candidate():
 registry=UnitRegistry.load()
 waves=deploy(Army.from_dict({'units':[{'unit_id':'doctor','quantity':4}]}),registry,LAND_MINI)
 assert 'UNKNOWN-CROSS-WAVE-FORMATION-REBUILD' not in _preflight(
  waves,registry,FormationRules.load(),LAND_MINI)


def test_domain_and_unsupported_geometry_rejections():
 s=scenario(); s['attacker']['units']=[{'unit_id':'rocket_ship','quantity':1}]
 with pytest.raises(ScenarioError): simulate(s)
 s=scenario(); s['battlefield']='naval-mini'
 with pytest.raises(ScenarioError,match='reserved'): simulate(s)


def test_land_medium_homogeneous_combat_uses_seven_front_slots_and_fires():
 s={'policy':'experimental','battlefield':'land-medium','max_rounds':1,
    'attacker':{'units':[{'unit_id':'hoplite','quantity':210}]},
    'defender':{'units':[{'unit_id':'hoplite','quantity':210}]}}
 result=simulate(s)
 assert result['rounds_completed']==1
 assert len([slot for slot in result['initial_state']['attacker']['slots'] if slot['line']=='first'])==7
 assert any(event['type']=='attacking_matrix' for event in result['events'])
 assert 'UNKNOWN-MULTILINE-WAVE-COMBAT-SEMANTICS' not in {
  event['details'].get('rule_id') for event in result['events']}


def test_larger_field_multiline_light_wave_remains_guarded():
 s={'policy':'experimental','battlefield':'land-small','max_rounds':1,
    'attacker':{'units':[{'unit_id':'swordsman','quantity':180}]},
    'defender':{'units':[{'unit_id':'hoplite','quantity':150}]}}
 result=simulate(s)
 assert {slot['line'] for slot in result['initial_state']['attacker']['slots']}=={'first','flank'}
 assert result['rounds_completed']==0
 assert 'UNKNOWN-MULTILINE-WAVE-COMBAT-SEMANTICS' in {
  event['details'].get('rule_id') for event in result['events']}


def test_larger_field_mixed_heavy_and_light_front_remains_guarded():
 s={'policy':'experimental','battlefield':'land-medium','max_rounds':1,
    'attacker':{'units':[{'unit_id':'hoplite','quantity':30},
                         {'unit_id':'swordsman','quantity':30}]},
    'defender':{'units':[{'unit_id':'hoplite','quantity':210}]}}
 result=simulate(s)
 assert result['rounds_completed']==0
 assert 'UNKNOWN-MIXED-UNIT-AM-ROWS' in {
  event['details'].get('rule_id') for event in result['events']}


def test_larger_field_cross_wave_reserve_candidate_remains_guarded():
 s={'policy':'experimental','battlefield':'land-small','max_rounds':1,
    'attacker':{'units':[{'unit_id':'hoplite','quantity':150,'wave_id':'a'},
                         {'unit_id':'hoplite','quantity':1,'wave_id':'b'}]},
    'defender':{'units':[{'unit_id':'hoplite','quantity':150}]}}
 result=simulate(s)
 assert result['rounds_completed']==0
 assert 'UNKNOWN-CROSS-WAVE-FORMATION-REBUILD' in {
  event['details'].get('rule_id') for event in result['events']}


def test_snapshots_preserve_line_positions_and_ammo_pool():
 r=simulate(scenario('strict')); slot=next(s for s in r['initial_state']['attacker']['slots'] if s['damage_position']==1)
 assert (slot['line'],slot['physical_position'])==('first',2)
 assert 'ammo_pool_shots' in slot


def test_tooltip_hp_is_derived_from_current_survivors_only():
 from ikariam_battle.engine import _snapshot
 from ikariam_battle.profiles import BattleEndProfile
 registry=UnitRegistry.load(); hp=registry.get('hoplite').hit_points
 wave=Wave(ArmyUnit('hoplite',12,'batch'),0,[Slot('first-1','first',2,1,'hoplite','batch',10,30,2*hp)],
           ammo_capacity_shots=None)
 slot=_snapshot([wave],registry,BattleEndProfile.load())['slots'][0]
 assert slot['hit_points_percent']==80


def test_tooltip_ammo_is_shared_wave_derived_state():
 from ikariam_battle.engine import _snapshot
 from ikariam_battle.profiles import BattleEndProfile
 registry=UnitRegistry.load()
 wave=Wave(ArmyUnit('sulphur_carabineer',14,'batch'),0,[
  Slot('second-1','second',2,1,'sulphur_carabineer','batch',7,7),
  Slot('second-2','second',1,2,'sulphur_carabineer','batch',7,7)],
  ammo_pool_shots=21,ammo_capacity_shots=42)
 state=_snapshot([wave],registry,BattleEndProfile.load())
 assert [slot['munition_percent'] for slot in state['slots']]==[50,50]
 assert state['waves'][0]['munition_percent']==50


def test_support_artillery_and_air_survive_but_do_not_sustain_battle():
 cases=[('doctor',4),('catapult',6),('gyrocopter',10)]
 for unit,quantity in cases:
  s={'policy':'experimental','battlefield':'land-mini','max_rounds':5,
     'attacker':{'units':[{'unit_id':'hoplite','quantity':90,'attack_upgrade':30}]},
     'defender':{'units':[{'unit_id':'hoplite','quantity':1},{'unit_id':unit,'quantity':quantity}]}}
  result=simulate(s); state=result['final_state']['defender']
  assert result['outcome']=='attacker' and result['rounds_completed']==1
  assert state['remaining'][unit]==quantity and state['main_line_holding_total']==0
  assert state['fallback_candidate_total']==0 and state['continuation_state']=='not_sustaining'
  assert result['casualties']['defender'].get(unit,0)==0
  event=next(e for e in result['events'] if e['type']=='battle_termination')
  assert event['details']['surviving_non_sustaining']['defender']=={unit:quantity}


def test_initial_long_range_requires_fallback_and_is_not_sustaining():
 s={'policy':'strict','battlefield':'land-mini','attacker':{'units':[{'unit_id':'hoplite','quantity':30}]},
    'defender':{'units':[{'unit_id':'sulphur_carabineer','quantity':7}]}}
 result=simulate(s)
 assert result['initial_state']['defender']['main_line_holding_total']==0
 assert result['initial_state']['defender']['fallback_candidate_total']==7
 assert result['initial_state']['defender']['continuation_state']=='fallback_required'
 assert 'UNKNOWN-FORMATION-FALLBACK' in {e['details']['rule_id'] for e in result['events'] if e['type']=='unsupported_mechanic'}


def test_final_sustaining_unit_dies_in_round_two_without_empty_round_three():
 s={'policy':'experimental','battlefield':'land-mini','max_rounds':5,
    'attacker':{'units':[{'unit_id':'hoplite','quantity':30}]},
    'defender':{'units':[{'unit_id':'hoplite','quantity':10}]}}
 result=simulate(s)
 assert result['outcome']=='attacker' and result['rounds_completed']==2
 assert max(round_state['round'] for round_state in result['rounds'])==2


def test_initial_non_sustaining_timing_is_strict_boundary_and_named_experimental_policy():
 s={'policy':'strict','battlefield':'land-mini','attacker':{'units':[{'unit_id':'hoplite','quantity':30}]},
    'defender':{'units':[{'unit_id':'doctor','quantity':4}]}}
 strict=simulate(s)
 assert 'UNKNOWN-INITIAL-BATTLE-END-TIMING' in {e['details']['rule_id'] for e in strict['events'] if e['type']=='unsupported_mechanic'}
 s['policy']='experimental'; experimental=simulate(s)
 assert experimental['outcome']=='attacker' and experimental['rounds_completed']==0
 assert [a['id'] for a in experimental['assumptions']].count('EXP-BATTLE-END-ROUND-BOUNDARY-001')==1


def test_front_alive_with_carabineer_is_sustaining():
 s={'policy':'experimental','battlefield':'land-mini','max_rounds':1,
    'attacker':{'units':[{'unit_id':'hoplite','quantity':1}]},
    'defender':{'units':[{'unit_id':'hoplite','quantity':90},{'unit_id':'sulphur_carabineer','quantity':7}]}}
 state=simulate(s)['rounds'][1]['defender']
 assert state['main_line_holding_total']>0 and state['fallback_candidate_total']==7
 assert state['continuation_state']=='sustaining'


@pytest.mark.parametrize('fallback_unit,quantity',[('sulphur_carabineer',7)])
def test_dynamic_front_collapse_stops_at_fallback_boundary(fallback_unit,quantity):
 s={'policy':'experimental','battlefield':'land-mini','max_rounds':5,
    'attacker':{'units':[{'unit_id':'hoplite','quantity':90,'attack_upgrade':30}]},
    'defender':{'units':[{'unit_id':'hoplite','quantity':1},{'unit_id':fallback_unit,'quantity':quantity}]}}
 result=simulate(s); state=result['final_state']['defender']
 assert result['status']=='inconclusive' and result['outcome']=='inconclusive'
 assert result['rounds_completed']==1 and state['continuation_state']=='fallback_required'
 assert state['fallback_candidate_total']==quantity
 boundary=next(e for e in result['events'] if e['type']=='unsupported_mechanic' and e['details']['rule_id']=='UNKNOWN-FORMATION-FALLBACK')
 assert boundary['round']==1
 assert not any(e['type']=='attacking_matrix' and e['side']=='defender' and e['round']>1 for e in result['events'])


def test_mixed_runtime_front_is_represented_but_never_fires():
 s={'policy':'experimental','battlefield':'land-mini','max_rounds':5,
    'attacker':{'units':[{'unit_id':'hoplite','quantity':90}]},
    'defender':{'units':[{'unit_id':'hoplite','quantity':8},{'unit_id':'swordsman','quantity':30}]}}
 result=simulate(s); front=result['initial_state']['defender']['slots']
 assert {(slot['unit_id'],slot['line']) for slot in front}=={('hoplite','first'),('swordsman','first')}
 rules={e['details']['rule_id'] for e in result['events'] if e['type']=='unsupported_mechanic'}
 assert 'UNKNOWN-MIXED-UNIT-AM-ROWS' in rules
 assert 'UNKNOWN-FALLBACK-LIGHT-INFANTRY-COMBAT' not in rules
 assert result['rounds_completed']==0
 assert not any(e['type']=='attacking_matrix' for e in result['events'])


def test_both_sides_without_main_line_is_not_an_unqualified_draw():
 s={'policy':'experimental','battlefield':'land-mini',
    'attacker':{'units':[{'unit_id':'doctor','quantity':1}]},
    'defender':{'units':[{'unit_id':'catapult','quantity':1}]}}
 result=simulate(s)
 assert result['status']=='inconclusive' and result['outcome']=='inconclusive'
 assert 'UNKNOWN-BOTH-SIDES-NO-MAIN-LINE-OUTCOME' in {e['details'].get('rule_id') for e in result['events']}


def test_round_cap_emits_explicit_safety_event():
 s=scenario(rounds=2)
 s['attacker']['units'][0]['quantity']=100000
 s['defender']['units'][0]['quantity']=100000
 result=simulate(s)
 cap=[e for e in result['events'] if e['type']=='safety_limit_reached']
 assert result['status']=='inconclusive' and result['outcome']=='inconclusive'
 assert result['rounds_completed']==2
 assert len(cap)==1 and cap[0]['round']==2
 assert cap[0]['details']=={'reason':'max_rounds_reached','limit':2}
