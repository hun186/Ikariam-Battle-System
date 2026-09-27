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

def post(value,report=None):
 body={**value}
 if report is not None: body['report']=report
 response=asyncio.run(request('POST','/api/simulate',json.dumps(body).encode())); return response[0]['status'],json.loads(response[1]['body'])

def post_page(value,start=0,limit=10):
 return post(value,{'mode':'round_page','round_start':start,'round_limit':limit})

def post_raw(value):
 response=asyncio.run(request('POST','/api/simulate',json.dumps(value).encode()))
 return response[0]['status'],json.loads(response[1]['body'])

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
 assert data['report_transport']=={'default_mode':'summary','default_round_page_size':10,'max_round_page_size':20}
 assert all(u['domain']=='barbarian' and not u['selectable_by_player'] and not u['simulation_ready'] for u in data['barbarian_units'])
 assert not ({u['id'] for u in data['barbarian_units']} & {u['id'] for u in data['units']})
 hoplite=next(u for u in data['units'] if u['id']=='hoplite')
 carabineer=next(u for u in data['units'] if u['id']=='sulphur_carabineer')
 assert (hoplite['size'],carabineer['size'])==(1,4)
 assert hoplite['unit_class']=='human' and carabineer['unit_class']=='human'
 machine_land={u['id'] for u in data['units'] if u['domain']=='land' and u['unit_class']=='machine'}
 assert machine_land=={'steam_giant','battering_ram','catapult','mortar','gyrocopter','bombardier'}
 assert data['combat_chronology']['firing_order']==['anti-balloon','balloon','third','flank','second','first']
 assert data['combat_chronology']['formation_fill_order']==['balloon','anti-balloon','third','second','first','flank']
 assert data['combat_chronology']['same_formation_simultaneous'] is True
 assert data['combat_chronology']['target_priorities']['third']==['first','flank']
 assert data['combat_chronology']['ir_trigger']=='UNKNOWN_DISABLED'
 assert data['combat_chronology']['sr_trigger']=='UNKNOWN_DISABLED'
 assert (hoplite['resource_cost_basis_total'],hoplite['general_score'])==(70,'1.4')
 assert (carabineer['resource_cost_basis_total'],carabineer['general_score'])==(200,'4')

def test_per_unit_workshop_forge_five_mini_api_smoke():
 status,data=post_page(payload()); assert status==200
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

def test_healing_status_and_null_healing_are_preserved_in_http_reports():
 value=payload('experimental'); value['attacker']['units'].append({'unit_id':'doctor','quantity':2})
 status,summary=post(value)
 assert status==200
 assert summary['healing_status']['derived_capacity_per_doctor']==4000
 assert summary['healing_status']['sides']['attacker']=={
  'doctor_count':2,'status':'ignored_by_named_assumption','effect_applied':False,'healing_amount':None
 }
 assert summary['combat_statistics']['attacker']['gross_healing'] is None
 status,page=post_page(value,0,10)
 assert status==200
 assert all(row['combat_statistics']['attacker']['healing'] is None for row in page['rounds'])
 assert all(row['combat_statistics']['attacker']['cumulative_healing'] is None for row in page['rounds'])


def test_doctor_and_cook_have_separate_boundaries():
 for unit,unknown,assumption in [('doctor','UNKNOWN-HEALING-ALLOCATION','EXP-HEAL-NONE-001'),('cook','UNKNOWN-MORALE-SUPPORT','EXP-MORALE-NONE-001')]:
  value=payload('strict'); value['attacker']['units'].append({'unit_id':unit,'quantity':1}); status,data=post(value)
  assert status==200 and unknown in {e['details'].get('rule_id') for e in data['events'] if e['type']=='unsupported_mechanic'}
  if unit=='cook':
   assert data['morale_status']['sides']['attacker']=={'cook_count':1,'status':'unsupported_boundary','effect_applied':False}
  value['policy']='experimental'; status,data=post(value); assert assumption in {a['id'] for a in data['assumptions']}
  if unit=='cook':
   assert data['morale_status']['modeled'] is False
   assert data['morale_status']['sides']['attacker']=={'cook_count':1,'status':'ignored_by_named_assumption','effect_applied':False}


 value={'policy':'experimental','battlefield':'land-mini','max_rounds':2,
   'attacker':{'units':[{'unit_id':'hoplite','quantity':30},{'unit_id':'steam_giant','quantity':10},{'unit_id':'cook','quantity':15}]},
   'defender':{'units':[{'unit_id':'hoplite','quantity':30}]}}
 status,data=post(value)
 assert status==200 and data['status']=='inconclusive'
 assert data['assumptions']==[]
 assert data['morale_status']['sides']['attacker']=={'cook_count':15,'status':'not_reached','effect_applied':False}

def test_static_ui_uses_game_like_setup_slot_steps_rounds_and_summary():
 response=asyncio.run(request('GET','/')); body=response[1]['body'].decode()
 assert response[0]['status']==200 and "fetch('/api/simulate')" in body and 'const units=[' not in body
 assert '兵力設定' in body and '逐回合戰報' in body and '總戰報' in body
 assert '戰鬥機制狀態 / Mechanics status' in body
 assert 'Air defence → Air → Artillery → Flanks → Long-range → Main battle line' in body
 assert 'P-kill' in body and 'IR / SR' in body and 'RR · Reserve Redistribution' in body
 assert 'Steam Giant、Ram、Catapult、Mortar、Gyrocopter、Bombardier' in body
 assert 'id="maxRounds" type="number" min="1" max="1000" value="100"' in body
 assert '預設 100 回合；1000 回合是可手動提高的安全上限' in body
 assert 'Cook 士氣目前尚未完整建模' in body
 assert '士氣支援（尚未建模）' in body and '治療支援（尚未建模）' in body
 assert 'Morale / 士氣尚未建模' in body and 'Cook / 士氣' in body
 assert 'Healing / 治療尚未建模' in body and 'Doctor / 治療' in body
 assert '攻擊方造成傷害' in body and '攻擊方承受傷害' in body and '攻擊方治療' in body
 assert 'Gross damage taken' in body and 'derived capacity reference' in body
 assert '尚未到達士氣處理' in body and "not_reached:'尚未到達'" in body
 assert "morale_status" in body
 assert "e.type==='safety_limit_reached'" in body
 assert 'Safety round cap reached / 已達安全回合上限' in body
 assert '長戰的逐回合資料會按需分頁載入' in body
 assert "report:{mode:'summary'}" in body
 assert "mode:'round_page'" in body
 assert 'roundPageCache' in body and 'pageStartForRound' in body
 assert 'page.events.filter(e=>e.round===round.round)' in body
 assert 'currentRoundIndex' not in body
 assert 'simulationGeneration=0' in body
 assert "cacheKey=generation+':'+start" in body
 assert 'if(generation!==simulationGeneration)return null' in body
 assert 'if(token!==roundRenderToken||generation!==simulationGeneration||!page)return' in body
 assert 'simulationRequestGeneration=0' in body
 assert 'let requestGeneration=null' in body
 assert 'requestGeneration=++simulationRequestGeneration' in body
 assert 'simulationGeneration=requestGeneration' in body
 assert 'requestGeneration===simulationRequestGeneration&&simulationGeneration===requestGeneration' in body
 assert 'scenarioByGeneration=new Map()' in body
 assert 'scenario=scenarioByGeneration.get(generation)' in body
 assert 'if(generation!==simulationGeneration||!scenario)return null' in body
 assert 'roundPageCache.clear();scenarioByGeneration.clear();scenarioByGeneration.set(simulationGeneration,scenario)' in body
 assert 'if(lastResult){' in body and 'await renderRound(currentRoundNumber)' in body
 assert 'Active report refresh failed' in body
 assert 'if(requestGeneration===simulationRequestGeneration)error.textContent=e.message' in body
 assert 'function disableReports(){setReportsEnabled(false)}' in body
 assert 'lastScenario' not in body
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
 assert '.battle-half{grid-template-columns:1fr}.battle-half.defender .reserve-box{order:2}.battle-board{overflow-x:auto}.formation{min-width:880px}' in body
 assert '.formation{min-width:790px}' not in body
 assert '.battle-half{grid-template-columns:1fr}.reserve-box{order:2}' not in body
 assert "reserveBox(state,name==='defender'?'Defender':'Attacker',geometry)+formation" in body
 assert '@media(max-width:900px){.setup-grid,.summary-grid,.mechanics-grid{grid-template-columns:1fr}' in body
 assert '}\n@media(max-width:900px)' in body
 assert '}\\n@media(max-width:900px)' not in body
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
 value={'policy':'experimental','battlefield':'land-mini','max_rounds':5,
   'attacker':{'units':[{'unit_id':'hoplite','quantity':90,'attack_upgrade':30}]},
   'defender':{'units':[{'unit_id':'hoplite','quantity':1},{'unit_id':'doctor','quantity':4}]}}
 status,data=post(value); assert status==200 and data['outcome']=='attacker' and data['rounds_completed']==1
 assert data['final_state']['defender']['remaining']['doctor']==4
 assert data['final_state']['defender']['main_line_holding_total']==0
 assert data['final_state']['defender']['continuation_state']=='not_sustaining'
 assert data['casualties']['defender'].get('doctor',0)==0
 ids=[a['id'] for a in data['assumptions']]; assert len(ids)==len(set(ids))

 value={'policy':'experimental','battlefield':'land-mini','max_rounds':5,
   'attacker':{'units':[{'unit_id':'hoplite','quantity':90,'attack_upgrade':30}]},
   'defender':{'units':[{'unit_id':'hoplite','quantity':1},{'unit_id':'catapult','quantity':6}]}}
 status,data=post(value); assert status==200 and data['outcome']=='attacker'
 assert data['final_state']['defender']['remaining'].get('catapult',0)==0
 assert data['casualties']['defender'].get('catapult')==6

def test_dynamic_front_collapse_api_retargets_main_into_long_range():
 value={'policy':'experimental','battlefield':'land-mini','max_rounds':5,
   'attacker':{'units':[{'unit_id':'hoplite','quantity':90,'attack_upgrade':30}]},
   'defender':{'units':[{'unit_id':'hoplite','quantity':1},{'unit_id':'sulphur_carabineer','quantity':7}]}}
 status,data=post_page(value); assert status==200
 assert data['status']=='completed' and data['rounds_completed']==1
 assert data['outcome']=='attacker'
 assert data['final_state']['defender']['continuation_state']=='not_sustaining'
 assert data['casualties']['defender'].get('sulphur_carabineer')==7
 assert any(e['type']=='damage' and e['side']=='defender'
            and e['details'].get('source_unit_id')=='sulphur_carabineer' for e in data['events'])
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


def test_http_summary_default_and_bounded_round_pages():
 value={'policy':'experimental','battlefield':'land-mini','max_rounds':5,
   'attacker':{'units':[{'unit_id':'hoplite','quantity':5000}]},
   'defender':{'units':[{'unit_id':'hoplite','quantity':5000}]}}
 status,summary=post(value)
 assert status==200 and summary['report']['mode']=='summary'
 assert summary['rounds']==[]
 assert summary['report']['rounds_returned']==0
 assert all(e['type'] in {'unsupported_mechanic','safety_limit_reached','battle_termination','assumption_applied'} for e in summary['events'])
 status,page=post_page(value,0,10)
 assert status==200 and page['report']['mode']=='round_page'
 assert 1 <= len(page['rounds']) <= 10
 assert page['report']['rounds_returned']==len(page['rounds'])
 assert all(0 <= row['round'] <= 9 for row in page['rounds'])
 assert all(0 <= event['round'] <= 9 for event in page['events'])
 assert all('combat_statistics' in row for row in page['rounds'])
 for row in page['rounds']:
  assert row['combat_statistics']['attacker']['damage_dealt']==row['combat_statistics']['defender']['damage_taken']
  assert row['combat_statistics']['defender']['damage_dealt']==row['combat_statistics']['attacker']['damage_taken']
 assert summary['combat_statistics']['attacker']['gross_damage_taken']==summary['combat_statistics']['defender']['gross_damage_dealt']
 assert summary['combat_statistics']['defender']['gross_damage_taken']==summary['combat_statistics']['attacker']['gross_damage_dealt']
 status,error=post(value,{'mode':'round_page','round_start':0,'round_limit':21})
 assert status==400 and 'report.round_limit must be 1..20' in error['error']


def test_http_round_page_rejects_start_past_completed_battle():
 value={'policy':'experimental','battlefield':'land-mini','max_rounds':5,
   'attacker':{'units':[{'unit_id':'hoplite','quantity':90,'attack_upgrade':30}]},
   'defender':{'units':[{'unit_id':'hoplite','quantity':1}]}}
 status,summary=post(value)
 assert status==200 and summary['rounds_completed']==1
 status,error=post(value,{'mode':'round_page','round_start':2,'round_limit':10})
 assert status==400 and 'report.round_start must be <= rounds_completed' in error['error']


def test_http_non_object_json_bodies_are_400_not_500():
 for value in ([],None,42,'scenario'):
  status,data=post_raw(value)
  assert status==400
  assert data=={'error':'request body must be an object'}
