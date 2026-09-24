from ikariam_battle.calibration import BattleReportFixture, damage_interval_from_report, ranged_formation_observations


def test_damage_percentage_round_up_maps_to_interval(): assert damage_interval_from_report(1,1120)==(1,11)

def test_fixture_reserves_current_report_fields():
 fixture=BattleReportFixture.from_dict({'game_version':'17.5.0','round_number':1,'scenario':{'policy':'strict','battlefield':'land-mini','attacker':{'forge_level':5,'units':[{'unit_id':'hoplite','quantity':30,'attack_upgrade':12,'armor_upgrade':8}]},'defender':{'forge_level':0,'units':[{'unit_id':'hoplite','quantity':30}]}},'observations':[{'side':'defender','line':'first','damage_position':1,'casualties':2,'damage_percent':1,'life_percent':99}]})
 assert fixture.game_version=='17.5.0' and fixture.observations[0].damage_percent==1


def test_user_observed_ranged_calibration_case_a_is_not_a_production_rule():
 data=ranged_formation_observations(); case=data['cases'][0]
 assert data['evidence_class']=='USER_PROVIDED_BATTLE_OBSERVATION'
 assert data['implementation_status']=='CALIBRATION_ONLY_UNSUPPORTED_IN_PRODUCTION'
 assert (case['alive'],case['ammo_pool_shots'],case['observed_second_line_deployed'])==(42,2,2)
 assert 'front_weapon' in case['unknowns']


def test_user_observed_ranged_calibration_case_b_keeps_remainder_off_field():
 case=ranged_formation_observations()['cases'][1]
 assert (case['alive'],case['ammo_pool_shots'],case['observed_second_line_slots_full'])==(838,282,7)
 assert case['observed_ammo_less_remainder_location']=='reserve_or_off_field'
 assert case['observed_automatic_front_fallback'] is False
