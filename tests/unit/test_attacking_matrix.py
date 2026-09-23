from ikariam_battle.attacking_matrix import distribute, from_slot_counts

PHYSICAL = (6,4,2,1,3,5,7)


def test_rows_target_damage_positions_not_physical_indexes():
    trace = distribute([7] * 8, list(PHYSICAL))
    assert trace.target_damage_positions == (1,2,3,4,5,6,7)
    assert trace.hits_by_damage_position[1] == 14
    assert trace.hits_by_damage_position[2] == 7


def test_pdf_steam_ram_vector_in_physical_layout():
    trace = from_slot_counts([5] * 7, list(PHYSICAL))
    assert trace.physical_vector(PHYSICAL) == [0,7,7,7,7,7,0]


def test_pdf_catapult_vector_in_physical_layout():
    trace = from_slot_counts([8] * 7, list(PHYSICAL))
    assert trace.physical_vector(PHYSICAL) == [7,7,7,14,7,7,7]
