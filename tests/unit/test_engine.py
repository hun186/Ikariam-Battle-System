from copy import deepcopy
import pytest
from ikariam_battle import simulate
from ikariam_battle.battlefield import LAND_MINI, deploy
from ikariam_battle.engine import (
 _apply_sequential_hit, _ir_trigger, _plan_fire, _preflight, _prepare_round_start,
 _redistribute, _sr_trigger, _target,
)
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
 assert {'UNKNOWN-KILL-SELECTION','UNKNOWN-ACCURACY','UNKNOWN-IR-TRIGGER','UNKNOWN-SR-TRIGGER'} <= rules


def test_experimental_names_accuracy_targeting_and_is_reproducible():
 first=simulate(scenario()); assert first==simulate(scenario())
 ids={a['id'] for a in first['assumptions']}
 assert {'EXP-D-KILL-SEQUENTIAL-001','EXP-ACCURACY-IGNORED-001',
         'EXP-IR-DISABLED-001','EXP-SR-DISABLED-001'} <= ids
 assert 'EXP-TARGET-LEGACY-001' not in ids
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
  assert plans and {plan['weapon_id'] for plan in plans}=={'primary'}
 assert attacker[0].ammo_pool_shots==42
 assert not any(e.type=='ammo_exhausted' for e in events)


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


 hard_blocked={
  'policy':'experimental','battlefield':'land-mini','max_rounds':2,
  'attacker':{'units':[
   {'unit_id':'hoplite','quantity':30},
   {'unit_id':'steam_giant','quantity':10},
   {'unit_id':'cook','quantity':15},
  ]},
  'defender':{'units':[{'unit_id':'hoplite','quantity':30}]},
 }
 stopped=simulate(hard_blocked)
 hard_rules={e['details'].get('rule_id') for e in stopped['events'] if e['type']=='unsupported_mechanic'}
 assert {'UNKNOWN-MIXED-UNIT-AM-ROWS','UNKNOWN-MORALE-SUPPORT'} <= hard_rules
 assert stopped['assumptions']==[]
 assert stopped['morale_status']['sides']['attacker']=={
  'cook_count':15,'status':'not_reached','effect_applied':False
 }


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
 assert {'UNKNOWN-KILL-SELECTION','UNKNOWN-ACCURACY','UNKNOWN-IR-TRIGGER','UNKNOWN-SR-TRIGGER'} <= rules
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


def test_support_and_air_survive_but_main_can_retarget_artillery_after_front_dies():
 for unit,quantity in [('doctor',4),('gyrocopter',10)]:
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

 s={'policy':'experimental','battlefield':'land-mini','max_rounds':5,
    'attacker':{'units':[{'unit_id':'hoplite','quantity':90,'attack_upgrade':30}]},
    'defender':{'units':[{'unit_id':'hoplite','quantity':1},{'unit_id':'catapult','quantity':6}]}}
 result=simulate(s)
 assert result['outcome']=='attacker' and result['rounds_completed']==1
 assert result['final_state']['defender']['remaining'].get('catapult',0)==0
 assert result['casualties']['defender'].get('catapult')==6
 catapult_hits=[e for e in result['events'] if e['type']=='damage'
                and e['side']=='attacker' and e['details'].get('target_unit_id')=='catapult']
 assert catapult_hits and {e['details']['firing_phase'] for e in catapult_hits}=={'first'}


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


def test_dynamic_front_collapse_retargets_later_main_shots_into_long_range():
 quantity=7
 s={'policy':'experimental','battlefield':'land-mini','max_rounds':5,
    'attacker':{'units':[{'unit_id':'hoplite','quantity':90,'attack_upgrade':30}]},
    'defender':{'units':[{'unit_id':'hoplite','quantity':1},
                         {'unit_id':'sulphur_carabineer','quantity':quantity}]}}
 result=simulate(s); state=result['final_state']['defender']
 assert result['status']=='completed' and result['outcome']=='attacker'
 assert result['rounds_completed']==1 and state['continuation_state']=='not_sustaining'
 assert state['fallback_candidate_total']==0
 assert result['casualties']['defender'].get('sulphur_carabineer')==quantity
 assert any(e['type']=='damage' and e['side']=='defender'
            and e['details'].get('source_unit_id')=='sulphur_carabineer'
            and e['details'].get('firing_phase')=='second' for e in result['events'])
 assert any(e['type']=='damage' and e['side']=='attacker'
            and e['details'].get('target_unit_id')=='sulphur_carabineer'
            and e['details'].get('firing_phase')=='first' for e in result['events'])


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


def test_round_combat_statistics_track_dealt_taken_and_cumulative_damage():
 result=simulate(scenario())
 assert result['rounds'][0]['combat_statistics']['attacker']=={
  'damage_dealt':0,'damage_taken':0,'cumulative_damage_dealt':0,'cumulative_damage_taken':0,
  'healing':0,'cumulative_healing':0,
 }
 assert result['rounds'][0]['combat_statistics']['defender']=={
  'damage_dealt':0,'damage_taken':0,'cumulative_damage_dealt':0,'cumulative_damage_taken':0,
  'healing':0,'cumulative_healing':0,
 }
 prev={'attacker':(0,0),'defender':(0,0)}
 for row in result['rounds']:
  stats=row['combat_statistics']
  assert stats['attacker']['damage_dealt']==stats['defender']['damage_taken']
  assert stats['defender']['damage_dealt']==stats['attacker']['damage_taken']
  for side in ('attacker','defender'):
   assert stats[side]['cumulative_damage_dealt']>=prev[side][0]
   assert stats[side]['cumulative_damage_taken']>=prev[side][1]
   prev[side]=(stats[side]['cumulative_damage_dealt'],stats[side]['cumulative_damage_taken'])
 final=result['rounds'][-1]['combat_statistics']
 for side in ('attacker','defender'):
  assert final[side]['cumulative_damage_dealt']==result['combat_statistics'][side]['gross_damage_dealt']
  assert final[side]['cumulative_damage_taken']==result['combat_statistics'][side]['gross_damage_taken']
  assert result['combat_statistics'][side]['gross_healing']==0


def test_doctor_healing_is_explicitly_unknown_not_zero():
 s=scenario(); s['attacker']['units'].append({'unit_id':'doctor','quantity':2}); result=simulate(s)
 healing=result['healing_status']
 assert healing['modeled'] is False
 assert healing['derived_capacity_per_doctor']==4000
 assert healing['capacity_is_allocation_formula'] is False
 assert healing['sides']['attacker']=={
  'doctor_count':2,'status':'ignored_by_named_assumption','effect_applied':False,'healing_amount':None
 }
 assert result['combat_statistics']['attacker']['gross_healing'] is None
 assert all(row['combat_statistics']['attacker']['healing'] is None for row in result['rounds'])
 assert all(row['combat_statistics']['attacker']['cumulative_healing'] is None for row in result['rounds'])

 strict=scenario('strict'); strict['attacker']['units'].append({'unit_id':'doctor','quantity':2}); blocked=simulate(strict)
 assert blocked['healing_status']['sides']['attacker']['status']=='unsupported_boundary'
 assert blocked['healing_status']['sides']['attacker']['healing_amount'] is None


def test_art_of_warfare_firing_order_profile_and_artillery_targets_are_exact():
 t=TargetingProfile.load()
 assert t.firing_order==('anti-balloon','balloon','third','flank','second','first')
 assert t.priorities['third']==('first','flank')
 assert 'second' not in t.priorities['third'] and 'third' not in t.priorities['third']


def test_flank_phase_can_kill_long_range_before_long_range_fires():
 s={'policy':'experimental','battlefield':'land-max','max_rounds':1,
    'attacker':{'units':[{'unit_id':'hoplite','quantity':350},
                         {'unit_id':'swordsman','quantity':240,'attack_upgrade':30}]},
    'defender':{'units':[{'unit_id':'hoplite','quantity':350},
                         {'unit_id':'sulphur_carabineer','quantity':84}]}}
 result=simulate(s)
 assert result['casualties']['defender'].get('sulphur_carabineer')==84
 assert not any(e['type']=='damage' and e['side']=='defender'
                and e['details'].get('source_unit_id')=='sulphur_carabineer'
                for e in result['events'])


def test_artillery_fires_before_flank_and_hits_front_only_while_front_exists():
 s={'policy':'experimental','battlefield':'land-max','max_rounds':1,
    'attacker':{'units':[{'unit_id':'hoplite','quantity':350},
                         {'unit_id':'swordsman','quantity':240,'attack_upgrade':30}]},
    'defender':{'units':[{'unit_id':'hoplite','quantity':350},
                         {'unit_id':'sulphur_carabineer','quantity':84},
                         {'unit_id':'mortar','quantity':30}]}}
 result=simulate(s)
 mortar_events=[e for e in result['events'] if e['type']=='damage'
                and e['side']=='defender' and e['details'].get('source_unit_id')=='mortar']
 assert mortar_events
 assert {e['details']['target_line'] for e in mortar_events}=={'first'}
 assert sum(e['details']['casualties'] for e in mortar_events)==30
 assert not any(e['type']=='damage' and e['side']=='defender'
                and e['details'].get('source_unit_id')=='sulphur_carabineer'
                for e in result['events'])
 phases=[e['details']['firing_phase'] for e in result['events']
         if e['type']=='formation_fire_phase']
 assert phases.index('third') < phases.index('flank')


def test_same_formation_both_sides_keep_phase_start_firing_eligibility():
 s={'policy':'experimental','battlefield':'land-max','max_rounds':1,
    'attacker':{'forge_level':5,'units':[{'unit_id':'hoplite','quantity':350},
                         {'unit_id':'swordsman','quantity':240,'attack_upgrade':30}]},
    'defender':{'forge_level':5,'units':[{'unit_id':'hoplite','quantity':350},
                         {'unit_id':'swordsman','quantity':240,'attack_upgrade':30}]}}
 result=simulate(s)
 sword_damage=[e for e in result['events'] if e['type']=='damage'
               and e['details'].get('source_unit_id')=='swordsman']
 assert {e['side'] for e in sword_damage}=={'attacker','defender'}
 attacker_losses=result['casualties']['attacker'].get('swordsman',0)
 defender_losses=result['casualties']['defender'].get('swordsman',0)
 assert attacker_losses>0
 assert attacker_losses==defender_losses


def test_zero_quantity_support_rows_do_not_create_blockers_or_assumptions():
 for support,blocker,assumption,status_key,count_key in (
  ('doctor','UNKNOWN-HEALING-ALLOCATION','EXP-HEAL-NONE-001','healing_status','doctor_count'),
  ('cook','UNKNOWN-MORALE-SUPPORT','EXP-MORALE-NONE-001','morale_status','cook_count'),
 ):
  s={'policy':'experimental','battlefield':'land-mini','max_rounds':1,
     'attacker':{'units':[{'unit_id':'hoplite','quantity':30},
                          {'unit_id':support,'quantity':0}]},
     'defender':{'units':[{'unit_id':'hoplite','quantity':30}]}}
  result=simulate(s)
  rules={e['details'].get('rule_id') for e in result['events']
         if e['type']=='unsupported_mechanic'}
  ids={a['id'] for a in result['assumptions']}
  assert blocker not in rules
  assert assumption not in ids
  side=result[status_key]['sides']['attacker']
  assert side[count_key]==0 and side['status']=='not_present'


def test_am_slot_addresses_stay_fixed_when_target_slot_empties_mid_volley():
 s={'policy':'experimental','battlefield':'land-mini','max_rounds':1,
    'attacker':{'units':[{'unit_id':'hoplite','quantity':4}]},
    'defender':{'units':[{'unit_id':'spearman','quantity':31}]}}
 result=simulate(s)

 # land-mini deploys 31 Spearmen as damage-position 1:30 and 2:1.
 # Four Hoplite rows address 1,2,1,2. Once position 2 empties, row 4
 # remains addressed to position 2 instead of being redirected to position 1.
 assert result['casualties']['defender'].get('spearman')==3
 wasted=[e for e in result['events']
         if e['type']=='shot_addressed_empty_slot' and e['side']=='attacker']
 assert len(wasted)==1
 assert wasted[0]['details']['target_damage_position']==2
 assert wasted[0]['details']['action']=='address_preserved_no_retarget'

 matrix=next(e for e in result['events']
             if e['type']=='attacking_matrix'
             and e['side']=='attacker'
             and e['details'].get('source_unit_id','hoplite')=='hoplite')
 trace=matrix['details']['trace']
 assert trace['target_damage_positions']==[1,2]
 assert trace['hits_by_damage_position']=={1:2,2:2}
 assert trace['empty_addressed_shots_by_damage_position']=={2:1}


def test_round_snapshot_keeps_destroyed_slot_identity_and_round_casualties():
 s={'policy':'experimental','battlefield':'land-mini','max_rounds':1,
    'attacker':{'units':[{'unit_id':'hoplite','quantity':90,'attack_upgrade':30}]},
    'defender':{'units':[{'unit_id':'hoplite','quantity':1}]}}
 result=simulate(s)
 slot=next(row for row in result['rounds'][1]['defender']['slots']
           if row['unit_id']=='hoplite' and row['line']=='first')
 assert slot['units']==0
 assert slot['hit_points_percent']==0
 assert slot['casualties']==1


def test_snapshot_exposes_batch_reserve_damage_and_hp_percent():
 from ikariam_battle.engine import _snapshot
 from ikariam_battle.profiles import BattleEndProfile
 registry=UnitRegistry.load()
 hp=registry.get('hoplite').hit_points
 wave=Wave(ArmyUnit('hoplite',40,'reserve-batch'),10,
           [Slot('first-1','first',2,1,'hoplite','reserve-batch',30,30)],
           reserve_damage=2*hp)
 state=_snapshot([wave],registry,BattleEndProfile.load())
 batch=state['waves'][0]
 assert batch['reserve']==10
 assert batch['reserve_damage']==2*hp
 assert batch['reserve_hit_points_percent']==80


def test_partial_flank_casualties_reduce_later_long_range_shots():
 s={'policy':'experimental','battlefield':'land-max','max_rounds':1,
    'attacker':{'units':[{'unit_id':'hoplite','quantity':350},
                         {'unit_id':'swordsman','quantity':60,'attack_upgrade':30}]},
    'defender':{'units':[{'unit_id':'hoplite','quantity':350},
                         {'unit_id':'sulphur_carabineer','quantity':84}]}}
 result=simulate(s)
 killed=result['casualties']['defender'].get('sulphur_carabineer',0)
 assert 0 < killed < 84
 second_phase=next(e for e in result['events']
                   if e['type']=='formation_fire_phase'
                   and e['details']['firing_phase']=='second')
 assert second_phase['details']['defender_shots']==84-killed


def test_sequential_hits_can_differ_from_legacy_pooled_casualty_math():
 slot=Slot('first-1','first',1,1,'spearman','wave-1',2,2,90)
 queue=[90,0]
 hp=100
 hit=90
 killed=0
 for _ in range(2):
  _, casualty, _ = _apply_sequential_hit(slot,queue,hp,hit)
  killed += casualty

 pooled_casualties=(90 + 2*hit)//hp
 assert pooled_casualties==2
 assert killed==1
 assert slot.units==1 and slot.damage==90 and queue==[90]


def test_ir_and_sr_hooks_are_explicitly_disabled_at_baseline():
 assert _ir_trigger(object()) is False
 assert _sr_trigger('flank',[],[]) is False


def test_round_redistribution_keeps_entry_waves_isolated():
 wave_a=Wave(
  ArmyUnit('hoplite',40,'wave-a'),10,
  [Slot('first-a','first',1,1,'hoplite','wave-a',30,30,90)],
  reserve_damage=10,
 )
 wave_b=Wave(
  ArmyUnit('hoplite',40,'wave-b'),10,
  [Slot('first-b','first',1,1,'hoplite','wave-b',30,30,5)],
  reserve_damage=2,
 )
 events=[]
 _redistribute([wave_a,wave_b],events,2,'attacker',{})

 assert wave_a.reserve_damage + sum(slot.damage for slot in wave_a.slots)==100
 assert wave_b.reserve_damage + sum(slot.damage for slot in wave_b.slots)==7
 rr=[e for e in events if e.type=='redistribution']
 assert {(e.details['wave_id'],e.details['total_wave_damage']) for e in rr}=={
  ('wave-a',100),('wave-b',7),
 }
