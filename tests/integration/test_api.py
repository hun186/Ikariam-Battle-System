import asyncio
import json
from pathlib import Path

from asgi import application


async def request(method,path,body=b''):
 events=[{'type':'http.request','body':body,'more_body':False}]; sent=[]
 async def receive(): return events.pop(0)
 async def send(message): sent.append(message)
 await application({'type':'http','method':method,'path':path},receive,send)
 return sent


def payload(policy='experimental'):
 value=json.loads(Path('sample_scenario.json').read_text())
 value['policy']=policy
 return value


def post(value):
 response=asyncio.run(request('POST','/api/simulate',json.dumps(value).encode()))
 return response[0]['status'],json.loads(response[1]['body'])


def test_get_metadata_drives_current_ui_registry_and_profiles():
 response=asyncio.run(request('GET','/api/simulate'))
 data=json.loads(response[1]['body'])
 assert response[0]['status']==200
 assert data['profiles']['unit_stats']=='infinite-horizons-current'
 assert {u['domain'] for u in data['units']}=={'land','naval'}
 assert data['forge_levels']['5']=={'damage_multiplier':'1.15','armor_bonus':20}
 assert data['support_capacity']==4000


def test_workshop_twelve_forge_zero_and_five_land_scenario():
 status,data=post(payload())
 assert status==200 and data['profiles']['workshop']=='v14-workshop'
 calculations=[e['details'] for e in data['events'] if e['type']=='damage_calculation']
 assert {c['forge_level'] for c in calculations}=={0,5}
 assert all(c['workshop_attack_level']==12 for c in calculations)
 assert all(c['target_workshop_armor_level']==12 for c in calculations)


def test_invalid_land_naval_mix_and_tender_wrong_domain():
 for unit in ('rocket_ship','tender'):
  value=payload(); value['attacker']['units']=[{'unit_id':unit,'quantity':1}]
  status,data=post(value)
  assert status==400 and 'cannot enter small-land' in data['error']


def test_doctor_strict_is_inconclusive_and_experimental_discloses_healing_none():
 value=payload('strict'); value['attacker']['units'].append({'unit_id':'doctor','quantity':1})
 status,data=post(value)
 assert status==200 and data['status']=='inconclusive'
 assert any(e['details'].get('rule_id')=='UNKNOWN-HEALING-ALLOCATION' for e in data['events'])
 value['policy']='experimental'; status,data=post(value)
 assert status==200 and 'EXP-HEAL-NONE-001' in {a['id'] for a in data['assumptions']}


def test_level_above_three_api_and_negative_rejection():
 value=payload(); value['attacker']['workshop']['attack_level']=30
 assert post(value)[0]==200
 value['attacker']['workshop']['attack_level']=-1
 assert post(value)[0]==400


def test_static_ui_uses_metadata_not_hardcoded_units():
 response=asyncio.run(request('GET','/')); body=response[1]['body'].decode()
 assert response[0]['status']==200
 assert "fetch('/api/simulate')" in body and "const units=[" not in body
 assert 'Workshop attack' in body and 'Support (allocation unresolved)' in body
