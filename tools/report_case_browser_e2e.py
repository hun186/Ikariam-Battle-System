#!/usr/bin/env python3
"""Real Chromium acceptance of browser battle-report cases using SYNTHETIC data only."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright, expect


def prompted_click(page, selector: str, value: str) -> None:
    page.once("dialog", lambda dialog: dialog.accept(value))
    page.locator(selector).click()


def fill_visible_slot(page, unit: str, count: int, hp: int, deaths: int = 0) -> None:
    tile = page.locator(
        '#battleBoard button.slot[data-side="attacker"][data-line="first"][data-pos="1"]'
    )
    expect(tile).to_be_visible()
    tile.click()
    expect(page.locator("#slotEditor")).to_be_visible()
    page.locator("#editUnit").select_option(unit)
    page.locator("#editWave").fill("browser-e2e")
    page.locator("#editCount").fill(str(count))
    page.locator("#editHp").fill(str(hp))
    page.locator("#editDeaths").fill(str(deaths))
    page.locator("#saveDrawer").click()
    expect(tile).to_contain_text(f"HP {hp}%")


def add_reserve(page, unit: str, count: int) -> None:
    page.locator('#battleBoard button[data-add-reserve="attacker"]').click()
    expect(page.locator("#slotEditor")).to_contain_text("Reserve 編輯")
    page.locator("#editUnit").select_option(unit)
    page.locator("#editCount").fill(str(count))
    assert page.locator("#editOrigin").input_value() == "assumed_full"
    assert page.locator("#editHp").input_value() == "100"
    assert page.locator("#editHp").get_attribute("readonly") is not None
    page.locator("#saveDrawer").click()
    expect(page.locator("#readiness")).to_contain_text("100%")


def run(base_url: str, evidence_dir: Path) -> None:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as api:
        browser = api.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 960},
            device_scale_factor=1,
            accept_downloads=True,
            locale="zh-TW",
        )
        page = context.new_page()
        errors: list[str] = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        try:
            response = context.request.get(base_url + "/api/simulate")
            assert response.ok, f"GET metadata: HTTP {response.status}"
            metadata = response.json()
            fields = {f["id"]: f for f in metadata["battlefields"]}
            assert "naval-small" in fields

            response = page.goto(base_url + "/battle-cases.html", wait_until="networkidle")
            assert response is not None and response.ok
            prompted_click(page, "#addCase", "瀏覽器驗收 R80 海戰（合成資料）")
            expect(page.locator("#caseHeading")).to_contain_text("瀏覽器驗收 R80")
            original_id = page.locator("#caseList").input_value()
            page.locator("#caseField").select_option("naval-small")

            # First captured snapshot need not equal the real battle's round one.
            prompted_click(page, "#addRound", "80")
            page.get_by_role("button", name="R1", exact=True).click()
            page.once("dialog", lambda dialog: dialog.accept())
            page.locator("#removeRound").click()
            expect(page.locator("#roundHeading")).to_contain_text("R80")
            expect(page.locator("#roundTabs button")).to_have_count(1)
            page.locator("#roundSource").fill("人工轉錄：R80 回合結束；所有圖片均為合成測試")
            page.locator("#roundSource").blur()

            count = len(fields["naval-small"]["lines"]["first"]["physical_order"])
            positions = page.locator(
                '#battleBoard button.slot[data-side="attacker"][data-line="first"]'
            ).evaluate_all("(nodes) => nodes.map(n => Number(n.dataset.pos))")
            assert positions == list(range(1, count + 1)), positions

            first_tile = page.locator(
                '#battleBoard button.slot[data-side="attacker"][data-line="first"][data-pos="1"]'
            )
            first_tile.click()
            options = page.locator('#editUnit option:not([value=""])')
            assert options.count() > 0, "Naval unit options missing"
            unit = options.first.get_attribute("value")
            assert unit, "Unit selection is empty"
            page.locator("#closeDrawer").click()
            fill_visible_slot(page, unit, count=9, hp=83, deaths=2)
            add_reserve(page, unit, count=6)
            expect(page.locator("#readiness")).to_contain_text("資料待覆核")
            page.locator('#battleBoard input[data-confirm-side="attacker"]').check()
            expect(page.locator("#readiness")).to_contain_text("已記錄可見格位")

            page.locator("#readMode").click()
            expect(first_tile).to_be_disabled()
            expect(first_tile).to_contain_text("HP 83%")
            page.locator("#editMode").click()
            expect(first_tile).to_be_enabled()

            prompted_click(page, "#addRound", "81")
            expect(page.locator("#roundHeading")).to_contain_text("R81")
            fill_visible_slot(page, unit, count=8, hp=76)
            page.get_by_role("button", name="R80", exact=True).click()
            expect(first_tile).to_contain_text("HP 83%")
            page.get_by_role("button", name="R81", exact=True).click()
            expect(first_tile).to_contain_text("HP 76%")

            # Adding an earlier R50 re-evaluates baseline readiness.
            prompted_click(page, "#addRound", "50")
            expect(page.locator("#roundHeading")).to_contain_text("R50")
            expect(page.locator("#readiness")).to_contain_text("R50")
            expect(page.locator("#readiness")).to_contain_text("資料待覆核")
            fill_visible_slot(page, unit, count=7, hp=94)
            add_reserve(page, unit, count=4)
            page.locator('#battleBoard input[data-confirm-side="attacker"]').check()
            expect(page.locator("#readiness")).to_contain_text("已記錄可見格位")
            page.screenshot(path=str(evidence_dir / "battle-report-desktop-synthetic.png"), full_page=True)

            with page.expect_download() as d:
                page.locator("#exportCase").click()
            download = d.value
            payload = Path(download.path()).read_bytes()
            saved = json.loads(payload.decode("utf-8"))
            assert saved["id"] == original_id
            assert sorted(r["number"] for r in saved["rounds"]) == [50, 80, 81]
            rounds = {r["number"]: r for r in saved["rounds"]}
            assert rounds[80]["attacker"]["slots"][0]["pos"] == 1
            assert rounds[80]["attacker"]["slots"][0]["hp"] == 83
            assert rounds[80]["attacker"]["reserve"][0]["source"] == "assumed_full"
            assert rounds[80]["attacker"]["reserve"][0]["hp"] == 100
            assert rounds[50]["baseline_confirmed"]["attacker"] is True
            assert 100 < len(payload) <= 64 * 1024 * 1024
            print("PASS: real browser R80/R81/R50, physical slots, Reserve, JSON download")

            page.locator("#importCase").set_input_files({
                "name": download.suggested_filename,
                "mimeType": "application/json",
                "buffer": payload,
            })
            expect(page.locator("#caseList option")).to_have_count(2)
            expect(page.locator("#caseHeading")).to_contain_text("匯入")
            page.get_by_role("button", name="R80", exact=True).click()
            expect(first_tile).to_contain_text("HP 83%")
            expect(page.locator('#battleBoard .reserve-tag')).to_contain_text(
                ["預設 100%（未觀測）"]
            )

            page.locator("#caseList").select_option(original_id)
            page.once("dialog", lambda dialog: dialog.accept())
            page.locator("#removeCase").click()
            expect(page.locator("#caseList option")).to_have_count(1)
            page.reload(wait_until="networkidle")
            expect(page.locator("#caseList option")).to_have_count(1)
            expect(page.locator("#caseHeading")).to_contain_text("匯入")
            page.get_by_role("button", name="R80", exact=True).click()
            expect(first_tile).to_contain_text("HP 83%")
            print("PASS: JSON upload, case deletion, browser localStorage reload")

            page.set_viewport_size({"width": 390, "height": 844})
            expect(page.locator("#caseList")).to_be_visible()
            expect(page.locator("#battleBoard")).to_be_visible()
            page.screenshot(path=str(evidence_dir / "battle-report-mobile-synthetic.png"), full_page=True)
            assert not errors, "Uncaught browser JS errors: " + " | ".join(errors)
            print("PASS: Chromium mobile-sized UI, zero browser JS errors")
        except Exception:
            page.screenshot(path=str(evidence_dir / "battle-report-FAILURE-synthetic.png"), full_page=True)
            raise
        finally:
            context.close()
            browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8871")
    parser.add_argument("--evidence-dir", type=Path, default=Path("artifacts/browser-report-acceptance"))
    args = parser.parse_args()
    run(args.base_url.rstrip("/"), args.evidence_dir)
