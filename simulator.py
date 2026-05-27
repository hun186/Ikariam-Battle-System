from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple
import argparse
import json
import random


@dataclass(frozen=True)
class UnitType:
    name: str
    attack: int
    defense: int
    health: int
    line: str = "front"  # front, back, air
    ranged: bool = False


UNIT_TYPES: Dict[str, UnitType] = {
    "swordsman": UnitType("swordsman", attack=48, defense=14, health=120, line="front"),
    "hoplite": UnitType("hoplite", attack=36, defense=22, health=130, line="front"),
    "archer": UnitType("archer", attack=34, defense=8, health=70, line="back", ranged=True),
    "slinger": UnitType("slinger", attack=26, defense=6, health=60, line="back", ranged=True),
    "gyrocopter": UnitType("gyrocopter", attack=52, defense=18, health=90, line="air", ranged=False),
}


@dataclass
class Stack:
    unit: UnitType
    count: int

    def is_alive(self) -> bool:
        return self.count > 0


@dataclass
class Army:
    name: str
    stacks: List[Stack] = field(default_factory=list)
    morale: float = 1.0

    def total_units(self) -> int:
        return sum(s.count for s in self.stacks if s.count > 0)

    def alive_stacks(self) -> List[Stack]:
        return [s for s in self.stacks if s.is_alive()]

    def alive_by_line(self, line: str) -> List[Stack]:
        return [s for s in self.alive_stacks() if s.unit.line == line]


class BattleSimulator:
    def __init__(self, attacker: Army, defender: Army, seed: int = 42):
        self.a = attacker
        self.d = defender
        self.rng = random.Random(seed)
        self.log: List[str] = []

    def _target(self, enemy: Army, attacker_stack: Stack) -> Stack | None:
        alive = enemy.alive_stacks()
        if not alive:
            return None

        if attacker_stack.unit.line == "air":
            for line in ("air", "back", "front"):
                options = enemy.alive_by_line(line)
                if options:
                    return self.rng.choice(options)
            return self.rng.choice(alive)

        if attacker_stack.unit.ranged:
            for line in ("front", "back", "air"):
                options = enemy.alive_by_line(line)
                if options:
                    return self.rng.choice(options)
            return self.rng.choice(alive)

        for line in ("front", "back", "air"):
            options = enemy.alive_by_line(line)
            if options:
                return self.rng.choice(options)
        return self.rng.choice(alive)

    def _apply_damage(self, atk: Stack, tgt: Stack, morale: float) -> int:
        variance = self.rng.uniform(0.9, 1.1)
        attack_power = atk.unit.attack * atk.count * morale * variance
        defense_factor = max(1.0, tgt.unit.defense)
        kills = int(attack_power / (tgt.unit.health + defense_factor))
        kills = max(0, min(kills, tgt.count))
        tgt.count -= kills
        return kills

    def _step(self, source: Army, target: Army, round_no: int) -> None:
        for stack in source.alive_stacks():
            tgt = self._target(target, stack)
            if not tgt:
                return
            before = stack.count
            kills = self._apply_damage(stack, tgt, source.morale)
            self.log.append(
                f"R{round_no} {source.name} {stack.unit.name} x{before} -> "
                f"{target.name} {tgt.unit.name}: -{kills}"
            )

    def _update_morale(self, army: Army, initial: int) -> None:
        ratio = army.total_units() / max(1, initial)
        army.morale = max(0.50, min(1.10, 0.50 + ratio * 0.60))

    def run(self, max_rounds: int = 30) -> Tuple[str, List[str]]:
        init_a, init_d = self.a.total_units(), self.d.total_units()
        for r in range(1, max_rounds + 1):
            if self.a.total_units() == 0 or self.d.total_units() == 0:
                break

            self._step(self.a, self.d, r)
            self._step(self.d, self.a, r)
            self._update_morale(self.a, init_a)
            self._update_morale(self.d, init_d)

            self.log.append(f"R{r} morale {self.a.name}={self.a.morale:.2f}, {self.d.name}={self.d.morale:.2f}")
            if self.a.morale <= 0.55 or self.d.morale <= 0.55:
                self.log.append(f"R{r} retreat trigger by morale")
                break

        if self.a.total_units() > self.d.total_units():
            winner = self.a.name
        elif self.d.total_units() > self.a.total_units():
            winner = self.d.name
        else:
            winner = "draw"
        self.log.append(f"RESULT winner={winner} units {self.a.name}={self.a.total_units()} {self.d.name}={self.d.total_units()}")
        return winner, self.log


def army_from_dict(name: str, data: Dict[str, int]) -> Army:
    stacks: List[Stack] = []
    for unit_name, count in data.items():
        if unit_name not in UNIT_TYPES:
            raise ValueError(f"Unknown unit type: {unit_name}")
        if count < 0:
            raise ValueError(f"Unit count must be non-negative: {unit_name}={count}")
        stacks.append(Stack(UNIT_TYPES[unit_name], count))
    return Army(name=name, stacks=stacks)


def load_battle_from_json(path: str) -> tuple[Army, Army, int, int]:
    payload = json.loads(open(path, "r", encoding="utf-8").read())
    attacker = army_from_dict("Attacker", payload["attacker"])
    defender = army_from_dict("Defender", payload["defender"])
    seed = int(payload.get("seed", 42))
    max_rounds = int(payload.get("max_rounds", 30))
    return attacker, defender, seed, max_rounds


def demo_battle() -> None:
    attacker = Army("Attacker", [
        Stack(UNIT_TYPES["swordsman"], 120),
        Stack(UNIT_TYPES["archer"], 40),
        Stack(UNIT_TYPES["gyrocopter"], 20),
    ])
    defender = Army("Defender", [
        Stack(UNIT_TYPES["hoplite"], 110),
        Stack(UNIT_TYPES["slinger"], 50),
        Stack(UNIT_TYPES["gyrocopter"], 15),
    ])

    winner, logs = BattleSimulator(attacker, defender, seed=7).run()
    print(f"winner: {winner}")
    print("\n".join(logs[:25]))
    if len(logs) > 25:
        print(f"... ({len(logs)-25} more lines)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ikariam battle simulator prototype")
    parser.add_argument("--scenario", help="Path to scenario JSON file")
    args = parser.parse_args()

    if not args.scenario:
        demo_battle()
        return

    attacker, defender, seed, max_rounds = load_battle_from_json(args.scenario)
    winner, logs = BattleSimulator(attacker, defender, seed=seed).run(max_rounds=max_rounds)
    print(f"winner: {winner}")
    print("\n".join(logs))


if __name__ == "__main__":
    main()
