from decimal import Decimal
from importlib.resources import files
import json

from ikariam_battle.economy import MilitaryEconomyProfile
from ikariam_battle.formation import FormationRules
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


def test_mechanics_profile_no_longer_marks_mixed_unit_rows_unknown():
 raw=json.loads(files('ikariam_battle.data.mechanics')
                .joinpath('battle-system-paper-2020.json').read_text(encoding='utf-8'))
 assert 'mixed_unit_rows' not in raw['unknown']


def test_workshop_forge_support_and_targeting_profiles():
 w=WorkshopProfile.load(); assert w.bonus('land',12)==60 and w.bonus('naval',12)==120
 f=ForgeProfile.load(); assert [(str(f.effect(i).damage_multiplier),f.effect(i).armor_bonus) for i in range(6)]==[('1',0),('1.075',0),('1.075',10),('1.1',10),('1.125',20),('1.15',20)]
 s=SupportProfile.load(); assert s.derived_capacity==4000 and s.raw['multiplier_provenance']['source_type']=='OFFICIAL_CHANGELOG'
 assert s.raw['eligibility']['land_doctor']=='human'
 assert s.raw['eligibility']['machine_excluded'] is True
 assert s.raw['timing_contract']['effect_frequency']=='per_round'
 assert s.raw['timing_contract']['visible_by']=='before_next_round_combat'
 assert s.raw['timing_contract']['exact_order_vs_rr']=='UNKNOWN'
 assert s.raw['executable_subset']['status']=='IMPLEMENTED_ORDER_INVARIANT_FULL_CLEAR'
 assert s.raw['executable_subset']['insufficient_capacity']=='EXP-HEAL-NONE-001'
 t=TargetingProfile.load(); assert t.priorities['flank'][0]=='flank'
 assert t.priorities['third']==('first','flank')
 assert t.firing_order==('anti-balloon','balloon','third','flank','second','first')
 assert t.formation_fill_order==('balloon','anti-balloon','third','second','first','flank')
 assert t.same_formation_simultaneous is True
 assert t.metadata['line_role_contract']['status']=='KNOWN'
 assert t.metadata['firing_order_contract']['status']=='KNOWN'
 assert t.metadata['target_eligibility_contract']['status']=='KNOWN_FOR_EFFECTIVE_ATK_VS_DEF'
 assert 'strictly greater' in t.metadata['target_eligibility_contract']['rule']
 assert t.metadata['wall_targeting_contract']['status']=='STRICT_GUARDED_EXPERIMENTAL_EXECUTABLE'
 assert t.metadata['weapon_selection']['status']=='UNKNOWN'
 b=BattleEndProfile.load()
 assert b.main_line_classes=={'first'} and b.fallback_candidate_classes=={'flank','second'}
 assert b.continuation_state(1,7) is ContinuationState.SUSTAINING
 assert b.continuation_state(0,7) is ContinuationState.FALLBACK_REQUIRED
 assert b.continuation_state(0,0) is ContinuationState.NOT_SUSTAINING
 assert {s['source_type'] for s in b.metadata['sources']}=={'COMMUNITY_REFERENCE','GAMEFORGE_FORUM_BATTLE_REPORT'}
 assert FormationRules.load().metadata['implementation_status']=='ALL_LAND_GEOMETRIES_PLANNER_IMPLEMENTED_COMBAT_GUARDED'


def test_land_military_economy_profile_derives_generals_from_resource_basis():
 e=MilitaryEconomyProfile.load()
 assert e.metadata['formula']['resources_per_general_point']==50
 assert e.metadata['formula']['population_included'] is False
 assert e.metadata['formula']['resource_reduction_buildings_affect_score'] is False
 expected={
  'spearman':('0.6',30),'swordsman':('1.2',60),'hoplite':('1.4',70),'spartan':('1.6',80),
  'steam_giant':('6.2',310),'slinger':('0.4',20),'archer':('1.1',55),'sulphur_carabineer':('4',200),
  'battering_ram':('4.4',220),'catapult':('11.2',560),'mortar':('31',1550),'gyrocopter':('2.5',125),
  'bombardier':('5.8',290),'doctor':('10',500),'cook':('4',200)}
 assert set(e.units)==set(LAND)
 for unit_id,(score,basis) in expected.items():
  assert e.score(unit_id)==Decimal(score)
  assert e.resource_cost_basis_total(unit_id)==basis
  assert e.score(unit_id)==Decimal(basis)/Decimal(50)


def test_military_score_loss_is_casualty_count_times_unmodified_score_basis():
 e=MilitaryEconomyProfile.load()
 casualties={'hoplite':3,'swordsman':2,'mortar':1}
 assert e.resource_cost_basis_loss(casualties)==1880
 assert e.score_loss(casualties)==Decimal('37.6')
