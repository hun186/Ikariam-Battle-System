import asyncio,json
from pathlib import Path
from asgi import application
from ikariam_battle.models import Profiles

async def request(method,path,body=b''):
 events=[{'type':'http.request','body':body,'more_body':False}]; sent=[]
 async def receive(): return events.pop(0)
 async def send(message): sent.append(message)
 await application({'type':'http','method':method,'path':path},receive,send); return sent

def payload(policy='experimental'):
 value=json.loads(Path('sample_scenario.json').read_text()); value['policy']=policy; return value

def post(value):
 response=asyncio.run(request('POST','/api/simulate',json.dumps(value).encode())); return response[0]['status'],json.loads(response[1]['body'])

def test_get_metadata_drives_complete_land_ui_and_profiles():
 response=asyncio.run(request('GET','/api/simulate')); data=json.loads(response[1]['body'])
 assert response[0]['status']==200 and data['profiles']['targeting']=='legacy-community-land-targeting'
 assert data['profiles']['battle_end']=='legacy-community-battle-end'
 assert data['profiles']['formation']=='formation-land'
 assert set(data['profiles'])==set(Profiles().__dict__)
 assert data['profile_metadata']['verified_through_game_version']=='17.5.0'
 assert [(f['id'],f['display_name'],f['supported']) for f in data['battlefields']]==[
  ('land-mini','Land mini / Town Hall 1–4',True),
  ('land-small','Land small / Town Hall 5–9',True),
  ('land-medium','Land medium / Town Hall 10–16',True),
  ('land-large','Land large / Town Hall 17–24',True),
  ('land-max','Land max / Town Hall 25+',True),
 ]
 medium=next(f for f in data['battlefields'] if f['id']=='land-medium')
 assert {line:len(spec['physical_order']) for line,spec in medium['lines'].items()}=={
  'first':7,'second':7,'flank':4,'third':3,'anti-balloon':1,'balloon':1}
 maximum=next(f for f in data['battlefields'] if f['id']=='land-max')
 assert {line:len(spec['physical_order']) for line,spec in maximum['lines'].items()}=={
  'first':7,'second':7,'flank':6,'third':5,'anti-balloon':2,'balloon':2}
 assert medium['lines']['flank']['slot_space']==30
 assert maximum['lines']['first']['slot_space']==50
 assert len([u for u in data['units'] if u['domain']=='land' and u['numerically_supported']])==15
 hoplite=next(u for u in data['units'] if u['id']=='hoplite')
 carabineer=next(u for u in data['units'] if u['id']=='sulphur_carabineer')
 assert (hoplite['size'],carabineer['size'])==(1,4)

def test_per_unit_workshop_forge_five_mini_api_smoke():
 status,data=post(payload()); assert status==200
 calculations=[e['details'] for e in data['events'] if e['type']=='damage_calculation' and e['side']=='attacker']
 assert any(c['workshop_attack_level']==12 for c in calculations)
 assert any(c['workshop_attack_level']==3 for c in calculations)
 assert all(c['forge_level']==5 for c in calculations)

def test_land_mini_air_caps_through_api():
 value=payload('strict')
 value['attacker']['units']=[{'unit_id':'gyrocopter','quantity':25},{'unit_id':'bombardier','quantity':12}]
 status,data=post(value); assert status==200
 slots={s['unit_id']:s for s in data['initial_state']['attacker']['slots']}
 assert slots['gyrocopter']['units']==10 and slots['bombardier']['units']==5

def test_conflicting_same_unit_upgrades_and_invalid_domain_rejected():
 value=payload(); value['attacker']['units'].append({'unit_id':'hoplite','quantity':1,'wave_id':'w2','attack_upgrade':3})
 assert post(value)[0]==400
 value=payload(); value['attacker']['units']=[{'unit_id':'rocket_ship','quantity':1}]
 assert post(value)[0]==400

def test_doctor_and_cook_have_separate_boundaries():
 for unit,unknown,assumption in [('doctor','UNKNOWN-HEALING-ALLOCATION','EXP-HEAL-NONE-001'),('cook','UNKNOWN-MORALE-SUPPORT','EXP-MORALE-NONE-001')]:
  value=payload('strict'); value['attacker']['units'].append({'unit_id':unit,'quantity':1}); status,data=post(value)
  assert status==200 and unknown in {e['details'].get('rule_id') for e in data['events'] if e['type']=='unsupported_mechanic'}
  value['policy']='experimental'; status,data=post(value); assert assumption in {a['id'] for a in data['assumptions']}

def test_static_ui_uses_game_like_setup_slot_steps_rounds_and_summary():
 response=asyncio.run(request('GET','/')); body=response[1]['body'].decode()
 assert response[0]['status']==200 and "fetch('/api/simulate')" in body and 'const units=[' not in body
 assert '兵力設定' in body and '逐回合戰報' in body and '總戰報' in body
 assert '熔爐神蹟 / Forge' in body and '攻擊' in body and '防禦' in body
 assert '進階：進場批次' in body and 'Research mode' in body and 'slot-tooltip' in body
 assert "Math.floor(field.lines[line].slot_space/unit.size)" in body
 assert "unit.semantic_class==='light_infantry'&&field.lines.first" in body
 assert "minus.textContent=step?'−'+step" in body and "plus.textContent=step?'＋'+step" in body
 assert "const submittedBattlefield=battlefield.value" in body
 assert "lastBattlefieldId=submittedBattlefield" in body
 assert "lineOrderDefender=['balloon','anti-balloon','third','second','flank','first']" in body
 assert "lineOrderAttacker=['first','flank','second','third','anti-balloon','balloon']" in body
 assert "summarySide('attacker','攻擊方')" in body
 assert '原始生產資源成本 ÷ 50' in body


def test_zero_unit_snapshot_slots_render_as_empty_and_static_copies_match():
 response=asyncio.run(request('GET','/')); body=response[1]['body'].decode()
 assert 'state.slots.filter(s=>s.line===line&&s.units>0)' in body
 assert body==Path('public/index.html').read_text()

def test_battle_end_survivors_round_boundary_and_unique_assumptions_api():
 for survivor,quantity in [('doctor',4),('catapult',6)]:
  value={'policy':'experimental','battlefield':'land-mini','max_rounds':5,
    'attacker':{'units':[{'unit_id':'hoplite','quantity':90,'attack_upgrade':30}]},
    'defender':{'units':[{'unit_id':'hoplite','quantity':1},{'unit_id':survivor,'quantity':quantity}]}}
  status,data=post(value); assert status==200 and data['outcome']=='attacker' and data['rounds_completed']==1
  assert data['final_state']['defender']['remaining'][survivor]==quantity
  assert data['final_state']['defender']['main_line_holding_total']==0
  assert data['final_state']['defender']['continuation_state']=='not_sustaining'
  assert data['casualties']['defender'].get(survivor,0)==0
  ids=[a['id'] for a in data['assumptions']]; assert len(ids)==len(set(ids))

def test_dynamic_fallback_boundary_api_stops_without_stale_round():
 value={'policy':'experimental','battlefield':'land-mini','max_rounds':5,
   'attacker':{'units':[{'unit_id':'hoplite','quantity':90,'attack_upgrade':30}]},
   'defender':{'units':[{'unit_id':'hoplite','quantity':1},{'unit_id':'sulphur_carabineer','quantity':7}]}}
 status,data=post(value); assert status==200
 assert data['status']=='inconclusive' and data['rounds_completed']==1
 assert data['final_state']['defender']['continuation_state']=='fallback_required'
 assert not any(e['type']=='attacking_matrix' and e['side']=='defender' and e['round']>1 for e in data['events'])
 ids=[a['id'] for a in data['assumptions']]; assert len(ids)==len(set(ids))

def test_front_alive_continuation_state_api():
 value={'policy':'experimental','battlefield':'land-mini','max_rounds':1,
   'attacker':{'units':[{'unit_id':'hoplite','quantity':1}]},
   'defender':{'units':[{'unit_id':'hoplite','quantity':90},{'unit_id':'sulphur_carabineer','quantity':7}]}}
 status,data=post(value); assert status==200
 state=data['final_state']['defender']
 assert state['continuation_state']=='sustaining'
 assert state['main_line_holding_total']>0 and state['fallback_candidate_total']==7


def test_additive_ui_state_fields_keep_existing_api_contract():
 value=payload('strict'); status,data=post(value)
 assert status==200 and {'remaining','reserve','slots','total'} <= data['initial_state']['attacker'].keys()
 slot=data['initial_state']['attacker']['slots'][0]
 assert {'entry_batch_id','display_name','hit_points_percent','munition_percent','native_line','semantic_class'} <= slot.keys()
 assert {'wave_id','entry_batch_id','ammo_capacity_shots','munition_percent','deployed_lines'} <= data['initial_state']['attacker']['waves'][0].keys()
