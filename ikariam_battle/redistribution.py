from __future__ import annotations


def reserve_redistribution(total_damage: int, alive_wave_units: int, deployed: list[tuple[int, int]]) -> dict[int, int]:
    """PDF §4.3.1 RR, with integer remainders in standard deployment order."""
    if total_damage < 0 or alive_wave_units <= 0:
        raise ValueError("damage must be non-negative and alive units positive")
    exact = [(number, total_damage * count / alive_wave_units) for number, count in deployed]
    result = {number: int(value) for number, value in exact}
    wanted = min(total_damage, round(sum(value for _, value in exact)))
    for number, _ in exact:
        if sum(result.values()) >= wanted:
            break
        result[number] += 1
    return result
