from ikariam_battle.profiles import BattleEndProfile, ContinuationState, ForgeProfile, SupportProfile, TargetingProfile, WorkshopProfile
from ikariam_battle.units import UnitRegistry

LAND={'spearman','swordsman','hoplite','spartan','steam_giant','slinger','archer','sulphur_carabineer','battering_ram','catapult','mortar','gyrocopter','bombardier','doctor','cook'}
NAVAL={'steam_ram','fire_ship','ram_ship','ballista_ship','catapult_ship','mortar_ship','diving_boat','rocket_ship','balloon_carrier','paddle_speedboat','tender'}


def test_complete_land_and_naval_numeric_data():
 r=UnitRegistry.load(); ids={u.id for u in r.all()}
 assert ids==LAND|NAVAL
 for unit in r.all():
  assert unit.hit_points is not None and unit.base_armor is not None and unit.size is not None
  assert unit.primary_weapon.damage is not None and unit.primary_weapon.accuracy is not None
  assert unit.numerically_supported


def test_complete_current_raw_table_values_are_locked():
 r=UnitRegistry.load()
 expected={
 'spearman':(260,80,0,70,None,1),'swordsman':(360,200,0,90,None,1),'hoplite':(1120,360,20,90,None,1),
 'spartan':(1200,560,120,100,None,1),'steam_giant':(3680,840,60,80,None,3),'slinger':(160,60,0,20,5,1),
 'archer':(320,100,0,40,3,1),'sulphur_carabineer':(240,580,0,70,3,4),'battering_ram':(1760,1600,20,10,None,5),
 'catapult':(1080,2660,0,10,5,5),'mortar':(640,5400,0,10,3,5),'gyrocopter':(580,340,0,80,4,1),
 'bombardier':(800,960,0,20,2,2),'doctor':(240,160,0,30,None,1),'cook':(440,400,0,50,None,2),
 'steam_ram':(11520,3320,320,90,None,5),'fire_ship':(4380,1640,160,50,None,2),'ram_ship':(3080,1500,180,80,None,3),
 'ballista_ship':(3080,560,280,50,7,2),'catapult_ship':(2960,900,200,30,6,3),'mortar_ship':(3080,1380,120,10,5,4),
 'diving_boat':(2200,2460,120,80,4,3),'rocket_ship':(1300,7600,120,20,2,4),'balloon_carrier':(2800,2000,0,50,5,5),
 'paddle_speedboat':(400,240,0,90,5,1),'tender':(2800,300,0,50,None,6)}
 assert {u.id:(u.hit_points,u.primary_weapon.damage,u.base_armor,u.primary_weapon.accuracy,u.primary_weapon.ammunition,u.size) for u in r.all()}==expected


def test_key_values_and_weapon_accuracy():
 r=UnitRegistry.load()
 assert (r.get('hoplite').hit_points,r.get('hoplite').primary_weapon.damage,r.get('hoplite').size)==(1120,360,1)
 car=r.get('sulphur_carabineer'); assert (car.hit_points,car.primary_weapon.damage,car.primary_weapon.accuracy,car.primary_weapon.ammunition,car.size)==(240,580,70,3,4)
 rocket=r.get('rocket_ship'); assert (rocket.hit_points,rocket.primary_weapon.damage,rocket.primary_weapon.accuracy,rocket.size)==(1300,7600,20,4)
 assert (rocket.weapons[1].damage,rocket.weapons[1].accuracy)==(400,80)


def test_current_provenance_and_v175_status():
 r=UnitRegistry.load()
 assert r.metadata['verification_status']=='REVIEWER_WEB_VERIFIED'
 assert r.metadata['verified_through_game_version']=='17.5.0'
 assert r.get('hoplite').provenance['hp']['confidence']=='COMMUNITY_REFERENCE_CURRENT'
 assert any(s['source_type']=='GAMEFORGE_FORUM_PLAYER_TEST' for s in r.get('steam_ram').provenance['hp']['sources'])
 assert r.get('doctor').provenance['garrison_limit']['confidence']=='OFFICIAL_CHANGELOG'
 assert r.get('hoplite').provenance['garrison_limit']['confidence']=='LEGACY_DEFAULT'


def test_rocket_forum_provenance_excludes_accuracy_and_unlimited_inference():
 r=UnitRegistry.load(); rocket=r.get('rocket_ship'); forum='GAMEFORGE_FORUM_PLAYER_TEST'
 assert forum in {s['source_type'] for s in rocket.provenance['hp']['sources']}
 assert forum in {s['source_type'] for s in rocket.primary_weapon.provenance['damage']['sources']}
 assert forum in {s['source_type'] for s in rocket.primary_weapon.provenance['ammunition']['sources']}
 assert forum not in {s['source_type'] for s in rocket.primary_weapon.provenance['accuracy']['sources']}
 assert forum not in {s['source_type'] for s in rocket.weapons[1].provenance['accuracy']['sources']}
 steam=r.get('steam_ram')
 assert forum not in {s['source_type'] for s in steam.primary_weapon.provenance['ammunition']['sources']}


def test_workshop_forge_support_and_targeting_profiles():
 w=WorkshopProfile.load(); assert w.bonus('land',12)==60 and w.bonus('naval',12)==120
 f=ForgeProfile.load(); assert [(str(f.effect(i).damage_multiplier),f.effect(i).armor_bonus) for i in range(6)]==[('1',0),('1.075',0),('1.075',10),('1.1',10),('1.125',20),('1.15',20)]
 s=SupportProfile.load(); assert s.derived_capacity==4000 and s.raw['multiplier_provenance']['source_type']=='OFFICIAL_CHANGELOG'
 t=TargetingProfile.load(); assert t.priorities['flank'][0]=='flank'
 b=BattleEndProfile.load()
 assert b.main_line_classes=={'first'} and b.fallback_candidate_classes=={'flank','second'}
 assert b.continuation_state(1,7) is ContinuationState.SUSTAINING
 assert b.continuation_state(0,7) is ContinuationState.FALLBACK_REQUIRED
 assert b.continuation_state(0,0) is ContinuationState.NOT_SUSTAINING
 assert {s['source_type'] for s in b.metadata['sources']}=={'COMMUNITY_REFERENCE','GAMEFORGE_FORUM_BATTLE_REPORT'}
