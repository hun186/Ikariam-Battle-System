# Project Profile

## Metadata
- 初始化狀態：`INITIALIZED`
- 最後查證日期：`2026-09-23`
- 查證基準：`codex/rewrite-battle-engine-phase-a` from local/declared baseline `b1e3ec9a65447584e842772ca98226a990e14f7a`

## 一句話目的
以 browser 操作可解釋、可重現且誠實揭露未知規則的 Ikariam Phase A 戰鬥模擬器。

## 使用者、輸入與輸出
- 使用者設定雙方 unit rows、數量、攻防升級、ruleset、policy、Hephaistos 與 rounds。
- 輸出 status/outcome、formation/reserve/damage、casualties、逐 round state、events、assumptions/warnings。
- `paper-2020` 是 empirical PDF ruleset，不代表目前官方遊戲資料。

## 目標與非目標
- 目標：domain engine 與 Web 分離；documented mechanics 有回歸測試；未知規則可回報 inconclusive。
- 非目標：本階段不做 Force Solver；不宣稱完整/current Ikariam correctness。

## 技術與入口
| 面向 | 狀態／證據 |
| --- | --- |
| Runtime | Python >=3.11，`pyproject.toml` |
| Domain | `ikariam_battle/`; public `simulate()` |
| Web | vanilla UI `index.html`; ASGI `asgi:application`; Vercel handler `api/simulate.py` |
| Data | `data/units/paper-2020.json` |
| Tests | `pytest -q`, `tests/` |

## 事實來源與邊界
1. Executable code/tests and typed scenario parser.
2. `docs/mechanics-spec.md` confidence/evidence register.
3. Repository PDF as empirical source, never an official complete specification.

Commit source/data/docs; ignore caches, virtual environments, extracted PDF files, screenshots, and secrets. Unit counts/damage cannot be negative; capacities hold; deterministic inputs reproduce; unsupported rules never silently become exact victories.
