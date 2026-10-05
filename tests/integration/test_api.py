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

def test_browser_wall_copy_matches_strict_experimental_policy_split():
 html=Path('public/index.html').read_text(encoding='utf-8')
 assert 'Strict 的 active-wall 戰鬥停在 UNKNOWN-TOWN-WALL-COMBAT' in html
 assert 'Experimental 可執行具名假設下的 Artillery 破牆' in html
 assert "wall.status==='unsupported_boundary'" in html
 assert "wall.status==='breached'" in html
 assert "wall.status==='not_reached'" in html
 assert 'Experimental wall runtime' in html
 assert 'Experimental wall capability 可執行，但本次戰鬥在進入牆戰前已結束' in html
 assert '城牆本身的破牆戰仍停在 UNKNOWN-TOWN-WALL-COMBAT' not in html
 assert 'HP 扣減／破洞、守軍補位與 Flank 鎖定仍停在 UNKNOWN-TOWN-WALL-COMBAT' not in html


def test_barbarian_metadata_contract_is_documented():
 contract=Path('.codex/contracts.md').read_text()
 assert 'barbarian_profile_metadata' in contract and 'barbarian_units' in contract
 assert 'selectable_by_player = false' in contract and 'simulation_ready = true' in contract
 assert 'remain outside the player `units` collection' in contract
 assert 'army_kind = player|barbarian' in contract
 assert 'no mixing with player unit IDs on the same side' in contract

def test_get_metadata_drives_complete_land_ui_and_profiles():
 response=asyncio.run(request('GET','/api/simulate')); data=json.loads(response[1]['body'])
 assert response[0]['status']==200 and data['profiles']['targeting']=='legacy-community-land-targeting'
 assert data['profiles']['battle_end']=='legacy-community-battle-end'
 assert data['profiles']['formation']=='formation-land'
 assert data['profiles']['economy']=='military-economy-current'
 assert set(data['profiles'])==set(Profiles().__dict__)
 assert data['profile_metadata']['verified_through_game_version']=='17.5.0'
 assert data['economy_metadata']['profile']=='military-economy-current'
 assert [(f['id'],f['domain'],f['display_name'],f['supported']) for f in data['battlefields']]==[
  ('land-mini','land','Land mini / Town Hall 1–4',True),
  ('land-small','land','Land small / Town Hall 5–9',True),
  ('land-medium','land','Land medium / Town Hall 10–16',True),
  ('land-large','land','Land large / Town Hall 17–24',True),
  ('land-max','land','Land max / Town Hall 25+',True),
  ('naval-max','naval','Naval max / current community geometry',True),
  ('naval-mini','naval','Naval battlefield / geometry pending',False),
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
 assert data['barbarian_profile_metadata']['simulation_status']=='LAND_COMBAT_READY'
 assert data['report_transport']=={'default_mode':'summary','default_round_page_size':10,'max_round_page_size':20}
 assert data['town_wall']['max_level']==48
 assert data['town_wall']['input_supported'] is True
 assert data['town_wall']['combat_model_status']=='STRICT_GUARDED_EXPERIMENTAL_EXECUTABLE_WITH_GUARDS'
 assert data['town_wall']['rule_id']=='UNKNOWN-TOWN-WALL-COMBAT'
 assert data['town_wall']['published_stat_fields']==['hit_points','armor','damage']
 assert data['town_wall']['unresolved_current_stat_fields']==['accuracy']
 assert data['town_wall']['hit_points_formula']=='1800 + 900 * level'
 assert data['town_wall']['armor_formula']=='72 * level'
 assert data['town_wall']['damage_observed_points']=={'1':216,'9':504,'18':2160,'26':5580}
 assert data['town_wall']['successful_breach_hits_formula']=='ceil((1800 + 900*level) / (attack_damage - 72*level))'
 assert data['town_wall']['targeting_contract']['artillery_priority']==['wall','first']
 assert data['town_wall']['targeting_contract']['penetration_rule']=='effective_attack > effective_defense'
 assert data['town_wall']['targeting_contract']['non_penetrating_target_consumes_ammunition'] is False
 assert data['garrison']['player_formula']=='250 + 50 * (town_hall_level + wall_level)'
 assert data['garrison']['max_town_hall_level']==66
 assert data['garrison']['open_field_battlefield']=='land-max'
 assert data['garrison']['excluded_land_units_since_17_4_0']==['cook','doctor']
 assert data['garrison']['barbarian_formula']=='(barbarian_village_level + wall_level + 5) * 50'
 assert data['garrison']['barbarian_formula_status']=='GAMEFORGE_FORUM_2024_COMMUNITY_REPORT'
 assert data['garrison']['max_barbarian_village_level']==50
 assert all(
  u['domain']=='land' and u['army_kind']=='barbarian'
  and not u['selectable_by_player'] and u['selectable_in_simulator'] and u['simulation_ready']
  and u['general_score']=='0'
  for u in data['barbarian_units'])
 assert not ({u['id'] for u in data['barbarian_units']} & {u['id'] for u in data['units']})
 clubman=next(u for u in data['barbarian_units'] if u['id']=='barbarian_clubman')
 assert (clubman['semantic_class'],clubman['native_line'])==('heavy_infantry','first')
 hoplite=next(u for u in data['units'] if u['id']=='hoplite')
 carabineer=next(u for u in data['units'] if u['id']=='sulphur_carabineer')
 assert (hoplite['size'],carabineer['size'])==(1,4)
 assert (hoplite['hit_points'],hoplite['base_armor'])==(1120,20)
 assert next(w for w in hoplite['weapons'] if w['trigger']=='primary')['damage']==360
 assert data['workshop_increments']=={'land':5,'naval':10}
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

def test_wall_level_api_validation_and_policy_split():
 value=payload()
 value['wall_level']=20
 status,data=post(value)
 assert status==200
 assert data['wall_status']['level']==20
 assert data['wall_status']['segments']==3
 assert data['wall_status']['hit_points']==19800
 assert data['wall_status']['armor']==1440
 assert data['wall_status']['damage']==4500
 assert data['wall_status']['accuracy'] is None
 assert data['wall_status']['combat_model_status']=='EXPERIMENTAL_EXECUTABLE_WITH_GUARDS'
 assert not any(
  event['type']=='unsupported_mechanic'
  and event['details'].get('rule_id')=='UNKNOWN-TOWN-WALL-COMBAT'
  for event in data['events']
 )

 strict=payload('strict'); strict['wall_level']=20
 strict_status,strict_data=post(strict)
 assert strict_status==200
 assert strict_data['status']=='inconclusive'
 assert strict_data['rounds_completed']==0
 assert any(
  event['type']=='unsupported_mechanic'
  and event['details'].get('rule_id')=='UNKNOWN-TOWN-WALL-COMBAT'
  for event in strict_data['events']
 )

 valid=payload(); valid['wall_level']=48
 valid_status,valid_data=post(valid)
 assert valid_status==200 and valid_data['wall_status']['level']==48
 invalid=payload(); invalid['wall_level']=49
 bad_status,bad=post(invalid)
 assert bad_status==400
 assert bad=={'error':'wall_level must be 0..48'}


def test_summary_reports_noop_garrison_crossing_even_when_event_is_filtered():
 value=payload()
 value['battlefield']='land-max'
 value['max_rounds']=1
 value['town_hall_level']=1
 value['wall_level']=0
 value['defender']['units']=[
  {'unit_id':'hoplite','quantity':100,'entry_batch_id':'g0','arrival_round':0},
  {'unit_id':'hoplite','quantity':201,'entry_batch_id':'g1','arrival_round':1},
 ]
 status,data=post(value)
 assert status==200
 assert data['garrison_status']['transition_reached'] is True
 assert data['garrison_status']['transition_blocked'] is False
 assert data['garrison_status']['transition']['direction']=='enter_open_field'
 assert data['garrison_status']['transition']['counted_defenders']==301
 assert not any(event['type']=='garrison_state_change' for event in data['events'])


def test_player_garrison_over_limit_uses_open_field_and_suppresses_wall():
 value=payload()
 value['town_hall_level']=1
 value['wall_level']=1
 value['defender']['units']=[{'unit_id':'hoplite','quantity':351}]
 status,data=post(value)
 assert status==200
 assert data['garrison_status']['garrison_limit']==350
 assert data['garrison_status']['open_field'] is True
 assert data['garrison_status']['effective_battlefield']=='land-max'
 assert data['wall_status']['status']=='suppressed'
 assert data['wall_status']['inactive_reason']=='open_field_garrison_limit'
 assert not any(
  event['type']=='unsupported_mechanic'
  and event['details'].get('rule_id')=='UNKNOWN-TOWN-WALL-COMBAT'
  for event in data['events']
 )


def test_barbarian_garrison_formula_is_executable_when_village_level_is_configured():
 value={'policy':'experimental','battlefield':'land-small','max_rounds':1,
   'barbarian_village_level':10,'wall_level':1,
   'attacker':{'army_kind':'player','units':[{'unit_id':'hoplite','quantity':150}]},
   'defender':{'army_kind':'barbarian','forge_level':0,'units':[
     {'unit_id':'barbarian_clubman','quantity':801}]}}
 status,data=post(value)
 assert status==200
 assert data['garrison_status']['settlement_kind']=='barbarian_village'
 assert data['garrison_status']['garrison_limit']==800
 assert data['garrison_status']['open_field'] is True
 assert data['garrison_status']['effective_battlefield']=='land-max'


def test_malformed_army_kind_values_return_json_400():
 for bad in ([],{},None,False):
  value=payload()
  value['attacker']['army_kind']=bad
  status,data=post_raw(value)
  assert status==400
  assert data=={'error':'army_kind must be player or barbarian'}


def test_barbarian_army_package_api_smoke():
 value={'policy':'experimental','battlefield':'land-mini','max_rounds':1,
   'attacker':{'army_kind':'player','units':[{'unit_id':'hoplite','quantity':90}]},
   'defender':{'army_kind':'barbarian','forge_level':0,'units':[
     {'unit_id':'barbarian_axe_swinger','quantity':90,'entry_batch_id':'barbarian-garrison'}]}}
 status,data=post(value)
 assert status==200
 assert data['initial_state']['defender']['remaining']['barbarian_axe_swinger']==90
 assert data['military_score']['defender']['general_score_lost']==0


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

def test_healing_status_and_exact_subset_are_preserved_in_http_reports():
 value=payload('experimental'); value['attacker']['units'].append({'unit_id':'doctor','quantity':100})
 status,summary=post(value)
 assert status==200
 healing=summary['healing_status']
 assert healing['derived_capacity_per_doctor']==4000
 assert healing['partial_model'] is True
 assert healing['model_status']=='EXACT_FULL_CLEAR_SUBSET_ONLY'
 assert healing['timing_contract']=='per_round_before_next_round_combat'
 side=healing['sides']['attacker']
 assert side['doctor_count']==100
 assert side['status']=='applied_exact_subset'
 assert side['effect_applied'] is True
 assert side['healing_amount']>0
 assert summary['combat_statistics']['attacker']['gross_healing']==side['healing_amount']
 status,page=post_page(value,0,10)
 assert status==200
 assert all(row['combat_statistics']['attacker']['healing'] is not None for row in page['rounds'])
 assert any(row['combat_statistics']['attacker']['healing']>0 for row in page['rounds'])
 assert page['rounds'][-1]['combat_statistics']['attacker']['cumulative_healing']==side['healing_amount']


def test_doctor_and_cook_have_separate_boundaries():
 for unit,unknown in [('doctor','UNKNOWN-HEALING-ALLOCATION'),('cook','UNKNOWN-MORALE-SUPPORT')]:
  value=payload('strict'); value['attacker']['units'].append({'unit_id':unit,'quantity':1}); status,data=post(value)
  assert status==200 and unknown in {e['details'].get('rule_id') for e in data['events'] if e['type']=='unsupported_mechanic'}
  if unit=='cook':
   assert data['morale_status']['sides']['attacker']=={'cook_count':1,'status':'unsupported_boundary','effect_applied':False}

 value=payload('experimental'); value['attacker']['units'].append({'unit_id':'doctor','quantity':100})
 status,data=post(value); assert status==200
 assert 'EXP-HEAL-NONE-001' not in {a['id'] for a in data['assumptions']}
 assert data['healing_status']['partial_model'] is True
 assert data['healing_status']['sides']['attacker']['status']=='applied_exact_subset'
 assert data['healing_status']['sides']['attacker']['effect_applied'] is True

 value=payload('experimental'); value['attacker']['units'].append({'unit_id':'cook','quantity':1})
 status,data=post(value); assert status==200
 assert 'EXP-MORALE-NONE-001' in {a['id'] for a in data['assumptions']}
 assert data['morale_status']['modeled'] is False
 assert data['morale_status']['sides']['attacker']=={
  'cook_count':1,'status':'ignored_by_named_assumption','effect_applied':False
 }


 value={'policy':'experimental','battlefield':'land-small','max_rounds':2,
   'attacker':{'units':[{'unit_id':'swordsman','quantity':180},{'unit_id':'cook','quantity':15}]},
   'defender':{'units':[{'unit_id':'hoplite','quantity':150}]}}
 status,data=post(value)
 assert status==200 and data['status']=='inconclusive'
 assert 'UNKNOWN-MULTILINE-WAVE-COMBAT-SEMANTICS' in {
  e['details'].get('rule_id') for e in data['events'] if e['type']=='unsupported_mechanic'}
 assert data['assumptions']==[]
 assert data['morale_status']['sides']['attacker']=={'cook_count':15,'status':'not_reached','effect_applied':False}

def test_static_ui_uses_game_like_setup_slot_steps_rounds_and_summary():
 response=asyncio.run(request('GET','/')); body=response[1]['body'].decode()
 assert response[0]['status']==200 and "fetch('/api/simulate')" in body and 'const units=[' not in body
 assert '兵力設定' in body and '逐回合戰報' in body and '總戰報' in body
 assert '戰鬥機制狀態 / Mechanics Status' in body
 assert 'Air defence → Air → Artillery → Flanks → Long-range → Main battle line' in body
 assert 'P-kill' in body and 'IR / SR' in body and 'RR · Reserve Redistribution' in body
 assert 'Steam Giant、Ram、Catapult、Mortar、Gyrocopter、Bombardier' in body
 assert 'id="maxRounds" type="number" min="1" max="1000" value="100"' in body
 assert '預設 100 回合；1000 回合是可手動提高的安全上限' in body
 assert 'Cook 士氣目前尚未完整建模' in body
 assert '士氣支援（尚未建模）' in body and '治療支援（部分建模）' in body
 assert 'Morale / 士氣尚未建模' in body and 'Cook / 士氣' in body
 assert 'Healing / 治療部分建模' in body and 'Doctor / 治療' in body
 assert '攻擊方造成傷害' in body and '攻擊方承受傷害' in body and '攻擊方治療' in body
 assert 'Gross damage taken' in body and 'derived capacity' in body
 assert '已知治療為每回合效果，並在下一回合戰鬥開始前反映。' in body
 assert 'full-clear 子集因結果為全部傷害歸零，不受先後順序影響。' in body
 assert "applied_exact_subset:'已套用可確定子集'" in body
 assert "partial_allocation_unresolved:'部分分配未知'" in body
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
 assert 'if(requestGeneration===simulationRequestGeneration)setSimulationError(e.message)' in body
 assert 'function disableReports(){setReportsEnabled(false)}' in body
 assert 'lastScenario' not in body
 assert '熔爐神蹟 / Forge' in body and '攻擊' in body and '防禦' in body
 assert 'id="battleDomain"' in body and 'id="aArmyKind"' in body and 'id="dArmyKind"' in body
 assert "army_kind:'barbarian'" in body and "army_kind:'player'" in body
 assert 'id="builtinPreset"' in body and 'id="applyBuiltinPreset"' in body and 'id="clearArmies"' in body
 assert '<details class="panel preset-panel" aria-label="快速設定與自訂套裝">' in body
 assert '<details class="panel preset-panel" aria-label="快速設定與自訂套裝" open>' not in body
 assert '需要時展開；預設收合。' in body
 assert '綜合陸戰（全戰線＋支援）' in body and '玩家 vs 野蠻人綜合' in body
 assert "USER_PRESET_STORAGE_KEY='ikariam-battle-user-presets-v1'" in body
 assert 'function setupConfigurationFromUi(){' in body and 'function applySetupConfiguration(config){' in body
 assert 'function saveCurrentPreset(){' in body and 'function loadSelectedPreset(){' in body and 'function deleteSelectedPreset(){' in body
 assert "localStorage.setItem(USER_PRESET_STORAGE_KEY,JSON.stringify(items))" in body
 assert "{unit_id:'hoplite',copies:2}" in body and "{unit_id:'mortar',copies:2}" in body and "{unit_id:'bombardier',copies:2}" in body
 assert "{unit_id:'steam_giant',copies:2},{unit_id:'swordsman',copies:2},{unit_id:'archer',copies:2}" in body
 assert "{unit_id:'barbarian_axe_swinger',copies:2}" in body and "{unit_id:'barbarian_dirigible',copies:2}" in body
 assert 'Barbarian 固定基礎數值 · 無 Workshop / Forge' in body
 assert '進階：進場批次' in body and 'Research mode' in body and 'floating-tooltip' in body
 assert 'id="showUnitStats" type="checkbox"' in body
 assert 'function effectiveSetupStats(row)' in body and 'workshop_increments' in body
 assert "含 Workshop + Forge Lv" in body
 assert 'function reserveGroups(state)' in body and 'reserve_hit_points_percent' in body
 assert 'batches.length>1' in body and 'batch-badge' in body
 assert "Persistent reserve damage" in body
 assert "Math.floor(field.lines[line].slot_space/unit.size)" in body
 assert "unit.semantic_class==='light_infantry'&&field.lines.first" in body
 assert "minus.textContent=step?'−'+step" in body and "plus.textContent=step?'＋'+step" in body
 assert "const submittedBattlefield=battlefield.value" in body
 assert "lastBattlefieldId=data.garrison_status?.effective_battlefield||submittedBattlefield" in body
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
 assert '@media(max-width:900px){.setup-grid,.summary-grid,.mechanics-grid,.source-grid{grid-template-columns:1fr}' in body
 assert '}\n@media(max-width:900px)' in body
 assert '}\\n@media(max-width:900px)' not in body
 assert '此戰場沒有 Flank slot；未能補入前線的側翼兵會留在 Reserve。' in body
 assert 'const formation=formationGrid(state,name,geometry)' in body
 assert "battleHalf(round.attacker,'attacker')" in body
 assert "battleHalf(round.defender,'defender')" in body
 assert "add('初始部署',0,false,'deployment-jump')" in body
 assert "add('«',1" in body and "add('»',maximum" in body
 assert "currentRoundNumber===0?1:Math.min(maximum,currentRoundNumber+1)" in body
 assert "input.step='1'" in body and "input.placeholder='回合'" in body
 assert "Math.trunc(raw)" in body and "Number.isFinite(raw)" in body
 assert "if(event.key==='Enter')jumpNow()" in body
 assert "number===0?'部署':String(number)" not in body
 assert "summarySide('attacker','攻擊方')" in body
 assert '軍分以未折扣的原始生產資源計分基礎 ÷ 50 計算' in body
 assert 'Workshop、熔爐神蹟與其他戰鬥 buff 不改變軍分' in body
 assert '新增進場批次' in body and 'addBatchRow' in body
 assert "row.dataset.batchIndex=String(batchIndex)" in body
 assert "同一兵種的不同進場批次必須使用相同的攻擊／防禦升級" in body
 assert 'roundSafetyNotices' in body and 'summarySafetyNotices' in body
 assert "data.events.filter(e=>e.type==='unsupported_mechanic')" in body
 assert 'Experimental assumptions actually used' in body and 'Evidence warnings' in body
 assert "不同的 Batch ID" in body and "batchIds.get(key).has(item.entry_batch_id)" in body
 assert "Object.entries(state.deployed_support||{})" in body and 'No deployed support' in body
 assert '<summary>Continuation state</summary>' in body
 assert 'round.attacker.continuation_state' in body and 'round.defender.continuation_state' in body
 assert '軍分損失' in body and '造成軍分消減' in body and 'Gross HP damage' in body
 assert 'unit.general_score' in body and 'military.general_score_lost' in body


def test_destroyed_snapshot_slots_keep_unit_identity_and_static_copies_match():
 response=asyncio.run(request('GET','/')); body=response[1]['body'].decode()
 assert 'state.slots.filter(s=>s.line===line)' in body
 assert 'state.slots.filter(s=>s.line===line&&s.units>0)' not in body
 assert "const dead=Number(slot.units||0)===0" in body
 assert "slot.dead .slot-glyph img" in body
 assert "(-'+loss+')" in body
 assert "hpBar(hp,'HP')" in body
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
 assert {'wave_id','entry_batch_id','ammo_capacity_shots','munition_percent','deployed_lines',
         'reserve_damage','reserve_hit_points_percent'} <= data['initial_state']['attacker']['waves'][0].keys()
 assert 'casualties' in slot


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
 assert '野蠻人兵種資料與出現等級（9 種）' in body
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


def test_zero_quantity_support_rows_are_absent_from_http_support_status():
 for support,status_key,count_key,assumption in (
  ('doctor','healing_status','doctor_count','EXP-HEAL-NONE-001'),
  ('cook','morale_status','cook_count','EXP-MORALE-NONE-001'),
 ):
  value={'policy':'experimental','battlefield':'land-mini','max_rounds':1,
    'attacker':{'units':[{'unit_id':'hoplite','quantity':30},{'unit_id':support,'quantity':0}]},
    'defender':{'units':[{'unit_id':'hoplite','quantity':30}]}}
  status,data=post(value)
  assert status==200
  side=data[status_key]['sides']['attacker']
  assert side[count_key]==0 and side['status']=='not_present'
  assert assumption not in {a['id'] for a in data['assumptions']}


def test_compact_setup_identity_stats_and_shared_floating_tooltip_contract():
 body=Path('index.html').read_text()
 # Experienced players can collapse repetitive unit names/basic metadata globally.
 assert 'id="showUnitIdentity" type="checkbox"' in body
 assert '顯示兵種名稱與基本資訊' in body
 assert '.show-unit-identity .unit-ident-copy' in body
 # Expanded HP/ATK/DEF must wrap instead of letting DEF overflow the setup card.
 assert '.unit-statbox{display:none' in body
 assert 'flex-wrap:wrap' in body
 # Round slots stay compact: icon + HP rail + alive/dead counts; name belongs in tooltip.
 assert "'<strong>'+esc(slot.display_name)+'</strong>" not in body
 # One body-level fixed tooltip is shared by battlefield slots and Reserve cards,
 # so board/reserve overflow cannot clip it at the viewport/container edge.
 assert 'id="floatingTooltip"' in body
 assert '.floating-tooltip{position:fixed' in body
 assert 'function showFloatingTooltip' in body
 assert 'function hideFloatingTooltip' in body
 assert 'getBoundingClientRect()' in body
 assert 'window.innerWidth' in body and 'window.innerHeight' in body
 # Hover and keyboard focus are independent: mouseleave must not hide a still-focused tooltip,
 # and blur must not hide while the pointer is still over the trigger.
 assert 'let hoveredTooltipTrigger=null,focusedTooltipTrigger=null' in body
 assert 'function refreshFloatingTooltip()' in body
 assert 'const trigger=hoveredTooltipTrigger||focusedTooltipTrigger' in body
 assert "trigger.addEventListener('mouseenter',()=>{hoveredTooltipTrigger=trigger;refreshFloatingTooltip()})" in body
 assert "trigger.addEventListener('mouseleave',()=>{if(hoveredTooltipTrigger===trigger)hoveredTooltipTrigger=null;refreshFloatingTooltip()})" in body
 assert "trigger.addEventListener('focus',()=>{focusedTooltipTrigger=trigger;refreshFloatingTooltip()})" in body
 assert "trigger.addEventListener('blur',()=>{if(focusedTooltipTrigger===trigger)focusedTooltipTrigger=null;refreshFloatingTooltip()})" in body
 assert 'function resetFloatingTooltipState()' in body
 assert 'resetFloatingTooltipState();' in body
 # Fixed tooltips must stay attached to focused/hovered triggers as any scroll
 # container moves or the viewport is resized. Capture=true covers battle-board scroll.
 assert 'function scheduleFloatingTooltipRefresh()' in body
 assert 'requestAnimationFrame(()=>{' in body
 assert "window.addEventListener('scroll',scheduleFloatingTooltipRefresh,true)" in body
 assert "window.addEventListener('resize',scheduleFloatingTooltipRefresh)" in body
 assert '.slot:hover .slot-tooltip' not in body
 assert '.reserve-card:hover .slot-tooltip' not in body
 assert body==Path('public/index.html').read_text()


def test_setup_exposes_top_and_bottom_simulate_buttons_with_one_handler():
 body=Path('index.html').read_text()
 assert 'id="simulateTop" class="primary" type="button">開始模擬</button>' in body
 assert 'id="simulate" class="primary" type="button">開始模擬</button>' in body
 assert body.count('>開始模擬</button>')==2
 assert 'async function runSimulation(){' in body
 assert "simulate.addEventListener('click',runSimulation)" in body
 assert "simulateTop.addEventListener('click',runSimulation)" in body
 assert body==Path('public/index.html').read_text()


def test_top_simulate_action_surfaces_shared_errors_without_duplicate_live_region():
 body=Path('index.html').read_text()
 assert 'id="errorTop" class="error" aria-hidden="true"' in body
 assert 'id="error" class="error" role="alert"' in body
 assert 'function setSimulationError(message)' in body
 assert 'errorTop.textContent=value;' in body
 assert 'error.textContent=value;' in body
 assert "async function runSimulation(){\n  setSimulationError('');" in body
 assert "setSimulationError(e.message);" in body
 assert "setSimulationError(e.message+' · Active report refresh failed: '+recoveryError.message);" in body
 assert "boot().catch(e=>setSimulationError(e.message));" in body
 assert body.count('role="alert"')==1
 assert body==Path('public/index.html').read_text()


def test_mechanics_and_pdf_resources_are_first_class_tabs():
 body=Path('index.html').read_text()
 assert 'data-view="mechanics">戰鬥機制</button>' in body
 assert 'data-view="source">Battle System PDF</button>' in body
 assert 'id="mechanicsView" class="hidden"' in body
 assert 'id="sourceView" class="hidden"' in body
 assert "mechanics:'mechanicsView'" in body and "source:'sourceView'" in body
 assert '戰鬥機制狀態 / Mechanics Status' in body
 assert '這一頁是模擬器正確度的核心依據' in body
 assert '已知 / 已實作' in body and '部分已知 / 仍需校準' in body and '未知 / 目前限制' in body
 assert 'Accuracy / Precision · Experimental concentration-v1' in body
 assert '能一擊殺死滿血目標的攻擊不製造 miss' in body
 assert 'ATK ≤ DEF 的候選直接跳過、不開火也不耗彈' in body
 assert '有 active Town Wall 時已知為 Wall 優先於普通 First' in body
 # Mechanics cards belong to the dedicated view, not the setup workbench.
 assert '<details class="mechanics-reference panel">' not in body
 setup=body.split('<section id="setupView">',1)[1].split('<section id="mechanicsView"',1)[0]
 assert 'Air defence → Air → Artillery → Flanks → Long-range → Main battle line' not in setup
 assert body==Path('public/index.html').read_text()


def test_pdf_source_tab_credits_authors_and_links_original_sources():
 body=Path('index.html').read_text()
 assert 'AT Barbarossa' in body and 'Xanto' in body
 assert 'PDF 署名：AT Barbarossa, Xanto · July 16, 2020' in body
 assert 'https://forum.ikariam.gameforge.com/forum/thread/43268-ikariam-battle-system/' in body
 assert 'href="/ikariam-battle-system.pdf"' in body
 assert 'scenarios/tests 早於遊戲 version 13' in body
 pdf=Path('ikariam-battle-system.pdf')
 assert pdf.is_file()
 with pdf.open('rb') as handle:
  assert handle.read(4)==b'%PDF'
 public_pdf=Path('public/ikariam-battle-system.pdf')
 assert public_pdf.is_file()
 with public_pdf.open('rb') as handle:
  assert handle.read(4)==b'%PDF'


def test_setup_presets_share_the_canonical_setup_serializer_and_public_entrypoint():
 body=Path('index.html').read_text()
 assert 'const config=setupConfigurationFromUi(),{setup_version,...scenario}=config;' in body
 assert "const config=setupConfigurationFromUi(),items=readUserPresets()" in body
 assert "applySetupConfiguration(builtinPresetConfiguration(builtinPreset.value))" in body
 assert "policy.addEventListener('change',updateWallControl)" in body
 assert "if(['experimental','strict'].includes(config.policy))policy.value=config.policy;\n  updateWallControl();" in body
 assert "clearSideRows('attacker');clearSideRows('defender')" in body
 assert "battleDomain.value=field.domain;refreshBattlefieldOptions(field.id)" in body
 assert "setup_version:1,policy:'experimental',battlefield:field.id,max_rounds:100" in body
 assert '自訂套裝只保存在此瀏覽器' in body
 assert "'UNKNOWN-FORMATION-FALLBACK':'主戰線需要 fallback。" in body
 assert '整個 Light Infantry wave 可完整轉入 First 的情況已支援' in body
 assert body==Path('public/index.html').read_text()


def test_land_setup_exposes_defender_wall_and_preserves_it_in_presets_and_scenario():
 body=Path('index.html').read_text()
 assert 'id="defenderTownHallLevel"' in body
 assert 'id="defenderBarbarianVillageLevel"' in body
 assert 'id="defenderWallLevel"' in body
 assert 'function populateTownHallLevel(){' in body
 assert 'function populateBarbarianVillageLevel(){' in body
 assert 'function populateWallLevels(){' in body
 assert "wall_level:Math.max(0,Math.trunc(+defenderWallLevel.value||0))" in body
 assert "town_hall_level:armyKind('defender')==='player'?" in body
 assert "barbarian_village_level:armyKind('defender')==='barbarian'?" in body
 assert "const wallLevel=Math.max(0,Math.min(wallMax,Math.trunc(Number(config.wall_level)||0)))" in body
 assert "defenderWallLevel.value=String(wallLevel)" in body
 assert "wall_level:0,town_hall_level:25,barbarian_village_level:null" in body
 assert "wall_level:0,town_hall_level:null,barbarian_village_level:50" in body
 assert "'UNKNOWN-GARRISON-BATTLEFIELD-TRANSITION':'防守方駐軍數跨過 garrison limit" in body
 assert "'UNKNOWN-TOWN-WALL-COMBAT':'Strict 模式遇到 active Town Wall 時停止於此 evidence boundary。" in body
 assert '城牆 Lv0–48' in body
 assert 'HP = 1800 + 900 × Lv、Armor = 72 × Lv' in body
 assert 'Lv1=216、Lv9=504、Lv18=2160、Lv26=5580' in body
 assert 'Accuracy：新版待校準' in body
 assert body==Path('public/index.html').read_text()


def test_setup_debug_json_download_uses_the_exact_simulation_scenario_builder():
 body=Path('index.html').read_text()
 assert 'id="downloadSetupTop" class="secondary" type="button">下載兵力設定 Debug JSON</button>' in body
 assert 'id="downloadSetup" class="secondary" type="button">下載兵力設定 Debug JSON</button>' in body
 assert 'function scenarioFromSetup(){' in body
 assert "const scenario=scenarioFromSetup(),submittedBattlefield=scenario.battlefield;" in body
 assert 'function setupDebugPayload(){' in body
 assert "debug_format:'ikariam-battle-simulator',debug_version:1,kind:'setup'" in body
 assert "scenario,context:{battlefield:currentField(),combat_chronology:metadata.combat_chronology}" in body
 assert "downloadJson('ikariam-setup-debug.json',setupDebugPayload())" in body
 assert "downloadSetup.addEventListener('click',downloadSetupDebug)" in body
 assert "downloadSetupTop.addEventListener('click',downloadSetupDebug)" in body
 assert 'Debug JSON 可直接貼回來協助重現問題；不包含 API key。' in body
 assert body==Path('public/index.html').read_text()


def test_round_debug_json_download_contains_reproducible_round_process_and_diagnostics():
 body=Path('index.html').read_text()
 assert 'id="downloadRoundDebug" class="secondary" type="button">下載本回合 Debug JSON</button>' in body
 assert 'function roundDebugPayload(){' in body
 assert 'simulation_summary:lastResult' in body
 assert 'current_round_number:round.round' in body
 assert 'current_round:round' in body
 assert 'current_round_events:currentRoundEvents' in body
 assert 'unsupported_mechanics:unsupportedMechanics' in body
 assert 'warnings:lastResult.warnings||[]' in body
 assert 'assumptions:lastResult.assumptions||[]' in body
 assert "page.report||null" in body
 assert "suffix=payload.current_round_number===0?'deployment':'round-'+payload.current_round_number" in body
 assert "downloadRoundDebug.addEventListener('click',downloadCurrentRoundDebug)" in body
 assert 'JSON.stringify(payload,null,2)' in body
 assert "type:'application/json;charset=utf-8'" in body
 assert body==Path('public/index.html').read_text()


def test_setup_layout_reclaims_hidden_identity_space_and_uses_compact_stat_strip():
 body=Path('index.html').read_text()
 assert '.unit-setup-row{display:grid;grid-template-columns:52px minmax(190px,1fr) 74px 74px' in body
 assert '.show-unit-identity .unit-setup-row{grid-template-columns:minmax(150px,.9fr)' in body
 assert '.unit-statbox{display:none;grid-column:2/-1' in body
 assert '.unit-statbox span:not(.stat-note)' in body
 assert '.advanced{grid-column:2/-1;margin:0}' in body
 assert '.unit-statbox{display:none;grid-column:3/5' not in body
 assert 'margin:0 0 4px 50px' not in body
 assert body==Path('public/index.html').read_text()


def test_setup_entry_batches_group_different_units_and_keep_unit_state_identity_separate():
 body=Path('index.html').read_text()
 assert "batchId=options.batchId||side+'-batch-'+batchIndex" in body
 assert 'class="entry-batch"' in body and 'class="arrival-round"' in body
 assert '同一時間抵達的不同兵種請使用相同 Batch ID 與進場回合' in body
 assert "entry_batch_id:entryBatchId,arrival_round:arrivalRound" in body
 assert "wave_id:entryBatchId+'::'+row.dataset.unitId" in body
 assert "batchRounds.get(item.entry_batch_id)!==item.arrival_round" in body
 assert body==Path('public/index.html').read_text()


def test_setup_compact_layout_keeps_advanced_batch_controls_full_width_on_mobile():
 body=Path('index.html').read_text()
 assert '@media(max-width:600px)' in body
 assert '.unit-ident,.qty-control,.unit-statbox,.advanced{grid-column:1/-1}' in body
 assert '.advanced{margin:0}' in body
 assert body==Path('public/index.html').read_text()


def test_http_rejects_explicit_invalid_batch_and_wave_ids_instead_of_defaulting():
 for field,bad in (
  ('entry_batch_id',''),('entry_batch_id',0),('entry_batch_id',False),('entry_batch_id',None),
  ('wave_id',''),('wave_id',0),('wave_id',False),('wave_id',None),
 ):
  value=payload('experimental')
  value['attacker']['units'][0][field]=bad
  status,data=post(value)
  assert status==400
  assert data['error']==f'{field} must be a non-empty string'


def test_round_page_exposes_arrival_boundary_round_and_events():
 value={'policy':'experimental','battlefield':'land-mini','max_rounds':3,
   'attacker':{'units':[
     {'unit_id':'hoplite','quantity':90,'entry_batch_id':'a3','arrival_round':3}]},
   'defender':{'units':[
     {'unit_id':'hoplite','quantity':90,'entry_batch_id':'d3','arrival_round':3}]}}
 status,data=post_page(value,start=3,limit=1)
 assert status==200
 assert data['status']=='inconclusive'
 assert data['rounds_completed']==3
 assert data['report']['round_start']==3
 assert data['report']['round_end']==3
 assert [row['round'] for row in data['rounds']]==[3]
 assert data['rounds'][0]['attacker']['reserve']['hoplite']==90
 assert data['rounds'][0]['defender']['reserve']['hoplite']==90
 assert any(e['type']=='entry_batch_arrived' and e['round']==3
            and e['side']=='attacker' for e in data['events'])
 assert any(e['type']=='entry_batch_arrived' and e['round']==3
            and e['side']=='defender' for e in data['events'])
 assert any(e['type']=='unsupported_mechanic' and e['round']==3
            and e['details'].get('rule_id')=='UNKNOWN-CROSS-WAVE-FORMATION-REBUILD'
            for e in data['events'])



def test_browser_uses_integer_barbarian_fleet_scaling_and_unavailable_score_label():
 body=Path('index.html').read_text()
 assert 'growthBasisPoints' in body
 assert 'quantity:Math.ceil(Number(row.quantity)*(1+growth*(n-1)))' not in body
 assert "military.general_score_lost==null?'不可用'" in body
 assert "military.general_score_destroyed==null?'不可用'" in body
