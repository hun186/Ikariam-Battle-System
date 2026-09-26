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

def test_barbarian_metadata_contract_is_documented():
 contract=Path('.codex/contracts.md').read_text()
 assert 'barbarian_profile_metadata' in contract and 'barbarian_units' in contract
 assert 'selectable_by_player = false' in contract and 'simulation_ready = false' in contract
 assert 'never members of the player `units` collection' in contract
 assert 'do not make Barbarian units valid `POST /api/simulate` army `unit_id` values' in contract

def test_get_metadata_drives_complete_land_ui_and_profiles():
 response=asyncio.run(request('GET','/api/simulate')); data=json.loads(response[1]['body'])
 assert response[0]['status']==200 and data['profiles']['targeting']=='legacy-community-land-targeting'
 assert data['profiles']['battle_end']=='legacy-community-battle-end'
 assert data['profiles']['formation']=='formation-land'
 assert data['profiles']['economy']=='military-economy-current'
 assert set(data['profiles'])==set(Profiles().__dict__)
 assert data['profile_metadata']['verified_through_game_version']=='17.5.0'
 assert data['economy_metadata']['profile']=='military-economy-current'
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
 assert len(data['units'])==26
 assert len(data['barbarian_units'])==9
 assert data['barbarian_profile_metadata']['simulation_status']=='CATALOG_ONLY'
 assert all(u['domain']=='barbarian' and not u['selectable_by_player'] and not u['simulation_ready'] for u in data['barbarian_units'])
 assert not ({u['id'] for u in data['barbarian_units']} & {u['id'] for u in data['units']})
 hoplite=next(u for u in data['units'] if u['id']=='hoplite')
 carabineer=next(u for u in data['units'] if u['id']=='sulphur_carabineer')
 assert (hoplite['size'],carabineer['size'])==(1,4)
 assert (hoplite['resource_cost_basis_total'],hoplite['general_score'])==(70,'1.4')
 assert (carabineer['resource_cost_basis_total'],carabineer['general_score'])==(200,'4')

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
 assert "if(maxField)battlefield.value=maxField.id" in body
 assert "if(metadata.forge_levels['5'])select.value='5'" in body
 assert "line.physical_order.length*Math.floor(line.slot_space/unit.size)" in body
 assert 'formation-row front-row' in body and 'formation-row ranged-row' in body and 'formation-row rear-row' in body
 assert "sideLine(state,'flank',geometry,'left'" in body and "sideLine(state,'flank',geometry,'right'" in body
 assert "sideLine(state,'anti-balloon',geometry,'left')" in body and "sideLine(state,'balloon',geometry,'right')" in body
 assert "name==='attacker'?[rear,ranged,front]:[front,ranged,rear]" in body
 assert 'air-zone' not in body and 'flank-column' not in body and 'ground-zone' not in body
 assert '@media(max-width:1100px)' in body
 assert '.battle-half{grid-template-columns:1fr}.reserve-box{order:2}.battle-board{overflow-x:auto}.formation{min-width:790px}' in body
 assert '@media(max-width:900px){.setup-grid,.summary-grid{grid-template-columns:1fr}' in body
 assert '此戰場沒有 Flank slot；未能補入前線的側翼兵會留在 Reserve。' in body
 assert 'const formation=formationGrid(state,name,geometry)' in body
 assert "battleHalf(round.attacker,'attacker')" in body
 assert "battleHalf(round.defender,'defender')" in body
 assert "number===0?'部署':String(number)" in body
 assert "summarySide('attacker','攻擊方')" in body
 assert '軍分以未折扣的原始生產資源計分基礎 ÷ 50 計算' in body
 assert 'Workshop、熔爐神蹟與其他戰鬥 buff 不改變軍分' in body
 assert '新增進場批次' in body and 'addBatchRow' in body
 assert "row.dataset.batchIndex=String(batchIndex)" in body
 assert "同一兵種的不同進場批次必須使用相同的攻擊／防禦升級" in body
 assert 'roundSafetyNotices' in body and 'summarySafetyNotices' in body
 assert "data.events.filter(e=>e.type==='unsupported_mechanic')" in body
 assert 'Experimental assumptions actually used' in body and 'Evidence warnings' in body
 assert "不同的 Batch ID" in body and "batchIds.get(key).has(item.wave_id)" in body
 assert "Object.entries(state.deployed_support||{})" in body and 'No deployed support' in body
 assert '<summary>Continuation state</summary>' in body
 assert 'round.attacker.continuation_state' in body and 'round.defender.continuation_state' in body
 assert '軍分損失' in body and '造成軍分消減' in body and 'Gross HP damage' in body
 assert 'unit.general_score' in body and 'military.general_score_lost' in body


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


def test_general_score_loss_destroyed_and_gross_damage_are_reported():
 value={'policy':'experimental','battlefield':'land-mini','max_rounds':2,
   'attacker':{'units':[{'unit_id':'hoplite','quantity':90,'attack_upgrade':30}]},
   'defender':{'units':[{'unit_id':'hoplite','quantity':1}]}}
 status,data=post(value)
 assert status==200 and data['outcome']=='attacker'
 assert data['casualties']['defender']=={'hoplite':1}
 assert data['military_score']['defender']['resource_cost_basis_lost']==70
 assert data['military_score']['defender']['general_score_lost']==1.4
 assert data['military_score']['attacker']['general_score_destroyed']==1.4
 assert data['military_score']['attacker']['general_score_lost']==0
 assert data['combat_statistics']['attacker']['gross_damage_dealt']>0
 assert data['combat_statistics']['defender']['gross_damage_dealt']>0


def test_local_unit_icon_assets_and_shared_ui_mapping():
 body=Path('index.html').read_text()
 expected={
  'land':{
   'hoplite','spartan','steam_giant','spearman','swordsman','slinger','archer',
   'sulphur_carabineer','battering_ram','catapult','mortar','gyrocopter',
   'bombardier','doctor','cook'
  },
  'naval':{
   'steam_ram','fire_ship','ram_ship','ballista_ship','catapult_ship','mortar_ship',
   'diving_boat','rocket_ship','balloon_carrier','paddle_speedboat','tender'
  },
  'barbarian':{
   'barbarian_clubman','barbarian_axe_swinger','barbarian_knifeman','barbarian_axe_thrower',
   'barbarian_war_walker','barbarian_ram','barbarian_catapult','barbarian_dirigible','barbarian_fighter'
  },
 }
 assert "https://ika-sim.com/units/" not in body
 assert "function unitIconHtml(unit,cssClass='')" in body
 assert "unitIconHtml(unit)" in body
 assert 'onerror="this.hidden=true;this.nextElementSibling.hidden=false"' in body
 for domain,unit_ids in expected.items():
  for unit in unit_ids:
   ext='webp' if domain=='barbarian' else 'png'
   local=f'/assets/unit-icons/{domain}/{unit}.{ext}'
   assert local in body
   assert Path(local.lstrip('/')).is_file()
   assert Path('public'+local).is_file()
 assert '野蠻人兵種參考（9 種，catalog-only）' in body
 assert 'function renderBarbarianCatalog()' in body
 assert body==Path('public/index.html').read_text()
