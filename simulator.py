"""Compatibility CLI for the rules-based engine.

The old stochastic prototype was intentionally removed.  Domain consumers should
import :func:`ikariam_battle.simulate` directly.
"""
from ikariam_battle.cli import main

if __name__ == "__main__":
    main()
