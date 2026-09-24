import argparse
import json

from .engine import simulate


def main() -> None:
    parser = argparse.ArgumentParser(description="Evidence-aware Ikariam Phase A simulator")
    parser.add_argument("--scenario", required=True)
    args = parser.parse_args()
    with open(args.scenario, encoding="utf-8") as stream:
        print(json.dumps(simulate(json.load(stream)), indent=2))
