from ikariam_battle.calibration import BattleReportFixture, damage_interval_from_report


def test_damage_percentage_round_up_maps_to_interval():
    assert damage_interval_from_report(1,1120)==(1,11)


def test_fixture_reserves_current_report_fields():
    fixture=BattleReportFixture.from_dict({'game_version':'17.5.0','round_number':1,
      'scenario':{'policy':'strict','battlefield':'small-land','attacker':{'workshop':{'attack_level':12,'armor_level':12},'forge_level':5,'units':[{'unit_id':'hoplite','quantity':30}]},'defender':{'workshop':{'attack_level':12,'armor_level':12},'forge_level':0,'units':[{'unit_id':'hoplite','quantity':30}]}},
      'observations':[{'side':'defender','line':'first','damage_position':1,'casualties':2,'damage_percent':1,'life_percent':99}]})
    assert fixture.game_version=='17.5.0' and fixture.observations[0].damage_percent==1
