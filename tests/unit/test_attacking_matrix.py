from ikariam_battle.attacking_matrix import distribute, from_slots


def test_row_to_target_modulo_distribution():
    # PDF pp. 4-6 (§2.1): row i targets i modulo q, with zero meaning q.
    trace = distribute([7] * 8, [6, 4, 2, 1, 3, 5, 7])
    assert trace.hits == {6: 14, 4: 7, 2: 7, 1: 7, 3: 7, 5: 7, 7: 7}


def test_pdf_steam_ram_and_catapult_vectors():
    # PDF p. 12 (§2.4). Physical slots are expressed in standard damage order.
    assert list(from_slots([5] * 7, [6, 4, 2, 1, 3, 5, 7]).hits.values()) == [7, 7, 7, 7, 7, 0, 0]
    assert list(from_slots([8] * 7, [6, 4, 2, 1, 3, 5, 7]).hits.values()) == [14, 7, 7, 7, 7, 7, 7]
