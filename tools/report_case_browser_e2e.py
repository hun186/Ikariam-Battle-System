#!/usr/bin/env python3
"""Real Chromium acceptance of browser battle-report cases using SYNTHETIC data only."""
from __future__ import annotations

import argparse
import csv
import io
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
        # This flow tests a fresh user-created case. Opt out of built-in seed
        # here; the catalog has a separate cold-start browser acceptance below.
        context.add_init_script("localStorage.setItem('ikariam-report-case-history-20261030-imported-v1', '1')")
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

            # The independent cold-start profile proves the catalog really
            # appears in an empty browser, not just via a button or mock UI.
            history_context = browser.new_context(locale="zh-TW")
            try:
                history_page = history_context.new_page()
                history_page.goto(base_url + "/battle-cases.html", wait_until="networkidle")
                expect(history_page.locator("#caseList option")).to_have_count(14)
                history_json = history_page.evaluate(
                    "() => JSON.parse(localStorage.getItem('ikariam-report-cases-v1'))"
                )
                assert len(history_json) == 14
                assert sum(x["research"]["kind"]=="partial_observation" for x in history_json) == 4
                assert sum(x["research"]["kind"]=="research_summary" for x in history_json) == 10
                expect(history_page.locator("#researchGate")).to_contain_text("全場自動模擬／校準：禁止")
                expect(history_page.locator("#researchKind")).to_have_value("partial_observation")
                assert history_page.locator("#researchUnknownFields").input_value()
                assert all(not c["research"]["confirmed_absences"] for c in history_json
                           if c["id"]!="research-land-slinger-400-r76-r80")
                assert history_json[0]["rounds"][0]["number"] == 1
                assert len(history_json[0]["rounds"]) == 11
                assert history_json[0]["rounds"][1]["number"] == 80
                assert "not" not in history_json[0]["notes"].lower() or "非" in history_json[0]["notes"]
                history_page.reload(wait_until="networkidle")
                expect(history_page.locator("#caseList option")).to_have_count(14)
                print("PASS: 14 actual source-annotated historical cases auto-seeded once")
            finally:
                history_context.close()


            # Codex P2 #4421688617: rejected historical raw storage must
            # survive automatic and explicit catalog import byte-for-byte.
            corrupted = json.loads(json.dumps(history_json[0]))
            corrupted["rounds"][0]["attacker"]["slots"][0]["hp"] = 101
            for payload, visible in (([corrupted], 0), ([history_json[1], corrupted], 1)):
                raw_cases = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
                invalid_context = browser.new_context(locale="zh-TW")
                try:
                    invalid_context.add_init_script(
                        "localStorage.setItem('ikariam-report-cases-v1', "
                        + json.dumps(raw_cases, ensure_ascii=False) + ");"
                    )
                    invalid_page = invalid_context.new_page()
                    invalid_page.goto(base_url + "/battle-cases.html", wait_until="networkidle")
                    expect(invalid_page.locator("#caseList option")).to_have_count(visible)
                    expect(invalid_page.locator("#storageStatus")).to_contain_text("鎖定寫入")
                    assert invalid_page.evaluate(
                        "() => localStorage.getItem('ikariam-report-cases-v1')"
                    ) == raw_cases
                    invalid_page.locator("#loadHistoricalCases").click()
                    expect(invalid_page.locator("#storageStatus")).to_contain_text("鎖定寫入")
                    assert invalid_page.evaluate(
                        "() => localStorage.getItem('ikariam-report-cases-v1')"
                    ) == raw_cases
                    invalid_page.reload(wait_until="networkidle")
                    assert invalid_page.evaluate(
                        "() => localStorage.getItem('ikariam-report-cases-v1')"
                    ) == raw_cases
                    expect(invalid_page.locator("#caseList option")).to_have_count(visible)
                finally:
                    invalid_context.close()
            print("PASS: rejected localStorage protected against auto/manual seed")
            # Old v1 JSON remains untouched until an explicit owner edit; the
            # old browser record is not automatically declared a full report.
            legacy = json.loads(json.dumps(history_json[0]))
            del legacy["research"]
            legacy_raw = json.dumps([legacy], ensure_ascii=False)
            legacy_context = browser.new_context(locale="zh-TW")
            try:
                legacy_context.add_init_script(
                    "localStorage.setItem('ikariam-report-cases-v1',"
                    + json.dumps(legacy_raw, ensure_ascii=False) + ");"
                )
                legacy_page = legacy_context.new_page()
                legacy_page.goto(base_url + "/battle-cases.html", wait_until="networkidle")
                expect(legacy_page.locator("#researchKind")).to_have_value("unclassified")
                expect(legacy_page.locator("#researchGate")).to_contain_text("未分類")
                assert legacy_page.evaluate(
                    "() => localStorage.getItem('ikariam-report-cases-v1')"
                ) == legacy_raw
                legacy_page.locator("#researchKind").select_option("partial_observation")
                classified = legacy_page.evaluate(
                    "() => JSON.parse(localStorage.getItem('ikariam-report-cases-v1'))[0]"
                )
                assert classified["research"]["kind"] == "partial_observation"
                assert classified["rounds"] == legacy["rounds"]
            finally:
                legacy_context.close()
            print("PASS: legacy cases remain unclassified until user edit")

            prompted_click(page, "#addCase", "瀏覽器驗收 R80 海戰（合成資料）")
            expect(page.locator("#caseHeading")).to_contain_text("瀏覽器驗收 R80")
            expect(page.locator("#researchKind")).to_have_value("partial_observation")
            expect(page.locator("#researchGate")).to_contain_text("全場自動模擬／校準：禁止")
            page.locator("#researchObjective").fill("只研究側翼劍士互砍（合成測試）")
            page.locator("#researchObjective").blur()
            page.locator("#researchObservedScope").fill("只觀測第一線第 1 格，其他格位均未提供")
            page.locator("#researchObservedScope").blur()
            page.locator("#researchKnownConditions").fill("前線填滿；精確兵量未提供")
            page.locator("#researchKnownConditions").blur()
            page.locator("#researchHypotheticalInputs").fill("模擬假設前排 350 重裝步兵，非實戰觀測")
            page.locator("#researchHypotheticalInputs").blur()
            page.locator("#researchUnknownFields").fill("前排精確兵量、Reserve 與其他戰線均未知")
            page.locator("#researchUnknownFields").blur()
            assert "全場自動模擬／校準：禁止" in page.locator("#researchGate").inner_text()
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
            expect(page.locator("#roundEntryStatus")).to_contain_text("可見欄位已填 1 格")
            page.locator("#focusedStudy summary").click()
            page.locator("#focusedLine").select_option("first")
            expect(page.locator("#focusedLaneStatus")).to_contain_text("條件式局部對照")
            expect(page.locator("#focusedLaneContent")).to_contain_text("未知≠0")
            expect(page.locator("#focusedLaneContent")).to_contain_text("已填 1/")
            focused_raw_before = page.evaluate(
                "() => localStorage.getItem('ikariam-report-cases-v1')"
            )
            with page.expect_download() as focused_download:
                page.locator("#exportFocusedLane").click()
            focused_csv = Path(focused_download.value.path()).read_text(encoding="utf-8-sig")
            focused_rows = list(csv.DictReader(io.StringIO(focused_csv)))
            assert len(focused_rows) == count
            assert focused_rows[0]["typed_count"] == "9"
            assert focused_rows[0]["typed_hp_percent"] == "83"
            assert focused_rows[0]["typed_deaths"] == "2"
            assert focused_rows[1]["typed_deaths"] == ""
            assert focused_rows[1]["slot_data_status"] == "UNKNOWN_NOT_ZERO"
            assert all(row["original_source_authenticated"]=="NOT_AUTHENTICATED" for row in focused_rows)
            # Candidate comparison uses user-entered proposals and must not
            # claim to run the actual engine or alter source-localStorage.
            page.locator("#candidateStudy summary").click()
            page.locator("#newCandidateTemplate").click()
            template = json.loads(page.locator("#candidateJson").input_value())
            assert template["source_class"] == "USER_ENTERED_MODEL_CANDIDATE_NOT_ENGINE_ATTESTED"
            assert template["round_number"] == 80
            assert template["side"] == "attacker" and template["line"] == "first"
            assert all(p["count"] is None and p["hp"] is None and p["deaths"] is None
                       for p in template["predictions"])
            template["candidate_label"] = "SYNTHETIC candidate"
            template["assumptions"] = "User-entered artificial candidate for browser E2E only"
            template["predictions"][0]["count"] = 7
            template["predictions"][0]["hp"] = 80
            template["predictions"][0]["deaths"] = 0
            page.locator("#candidateJson").fill(json.dumps(template, ensure_ascii=False))
            page.locator("#compareCandidate").click()
            expect(page.locator("#candidateComparisonStatus")).to_contain_text(
                "可比較數值欄位 3"
            )
            row = page.locator("#candidateComparisonRows tbody tr").first
            expect(row).to_contain_text("9 / 7 / -2")
            expect(row).to_contain_text("83 / 80 / -3")
            expect(row).to_contain_text("2 / 0 / -2")
            with page.expect_download() as candidate_download:
                page.locator("#exportCandidateCsv").click()
            candidate_csv = Path(candidate_download.value.path()).read_text(
                encoding="utf-8-sig"
            )
            candidate_rows = list(csv.DictReader(io.StringIO(candidate_csv)))
            assert len(candidate_rows) == count
            assert candidate_rows[0]["candidate_minus_typed_count"] == "-2"
            assert candidate_rows[0]["candidate_minus_typed_deaths"] == "-2"
            assert candidate_rows[1]["candidate_minus_typed_count"] == ""
            assert candidate_rows[1]["typed_deaths"] == ""
            assert all(
                r["engine_execution_attested"] == "NOT_ATTESTED"
                for r in candidate_rows
            )
            assert page.evaluate(
                "() => localStorage.getItem('ikariam-report-cases-v1')"
            ) == focused_raw_before, "candidate comparison modified the original case"
            # A prospective prediction is not a source fact. Switching lane
            # must clear this editable worksheet and disable old CSV export.
            page.locator("#focusedSide").select_option("defender")
            expect(page.locator("#candidateJson")).to_be_empty()
            expect(page.locator("#exportCandidateCsv")).to_be_disabled()
            expect(page.locator("#focusedLaneStatus")).to_contain_text("不可做局部數值對照")
            expect(page.locator("#exportFocusedLane")).to_be_disabled()
            assert page.evaluate(
                "() => localStorage.getItem('ikariam-report-cases-v1')"
            ) == focused_raw_before, "focused-lane exploration mutated stored cases"
            page.locator("#focusedSide").select_option("attacker")
            assert page.locator('#roundTabs [aria-label="R80"]').get_attribute("data-entry-status") == "FIELDS_ENTERED"
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
            page.locator("#roundComparison summary").click()
            expect(page.locator("#roundComparisonContent")).to_contain_text("R80 → R81")
            expect(page.locator("#roundComparisonContent")).to_contain_text("兵數差≠死亡數")
            expect(page.locator("#roundComparisonContent")).to_contain_text("Reserve HP 不可從戰報觀測")
            rows = page.locator("#roundComparisonContent tbody tr")
            expect(rows).to_have_count(1)
            cells = rows.first.locator("td")
            assert cells.nth(2).inner_text() == "-1"
            assert cells.nth(3).inner_text() == "-7"

            # Reuse R81's labels for a later R82 DRAFT, never its observations.
            prompted_click(page, "#addRound", "82")
            expect(page.locator("#roundHeading")).to_contain_text("R82")
            page.once("dialog", lambda dialog: dialog.accept())
            page.locator("#reuseEarlierLabels").click()
            expect(page.locator("#storageStatus")).to_contain_text("R81")
            expect(first_tile).to_contain_text("HP 未填")
            assert page.locator('#roundTabs [aria-label="R82"]').get_attribute("data-entry-status") == "DRAFT"
            expect(page.locator("#roundEntryStatus")).to_contain_text("可見欄位已填 0 格、待補 1 格")
            expect(page.locator("#roundComparisonContent")).to_contain_text("R81 → R82")
            expect(page.locator("#roundComparisonContent")).to_contain_text("兵種／Wave／數量／HP 未填齊")
            assert page.locator("#roundComparisonContent tbody tr").first.locator("td").nth(2).inner_text() == "—"
            first_tile.click()
            assert page.locator("#editUnit").input_value() == unit
            assert page.locator("#editWave").input_value() == "browser-e2e"
            for key in ("#editCount", "#editHp", "#editDeaths"):
                assert page.locator(key).input_value() == "", key
            page.locator("#closeDrawer").click()
            # Refuse to overwrite even a label-only draft on a repeat click.
            page.once("dialog", lambda dialog: dialog.accept())
            page.locator("#reuseEarlierLabels").click()
            expect(page.locator("#storageStatus")).to_contain_text("已有格位資料")

            # Adding an earlier R50 re-evaluates baseline readiness.
            prompted_click(page, "#addRound", "50")
            expect(page.locator("#roundHeading")).to_contain_text("R50")
            expect(page.locator("#readiness")).to_contain_text("R50")
            expect(page.locator("#roundComparisonContent")).to_contain_text("目前沒有更早的截錄回合")
            expect(page.locator("#readiness")).to_contain_text("資料待覆核")
            fill_visible_slot(page, unit, count=7, hp=94)
            assert page.locator('#roundTabs [aria-label="R50"]').get_attribute("data-entry-status") == "FIELDS_ENTERED"
            add_reserve(page, unit, count=4)
            page.locator('#battleBoard input[data-confirm-side="attacker"]').check()
            expect(page.locator("#readiness")).to_contain_text("已記錄可見格位")

            # Select a NON-nearest source R50 when comparing R81; no case mutation.
            r50_id = page.locator('#roundTabs [aria-label="R50"]').get_attribute("data-round-id")
            r80_id = page.locator('#roundTabs [aria-label="R80"]').get_attribute("data-round-id")
            r81_id = page.locator('#roundTabs [aria-label="R81"]').get_attribute("data-round-id")
            assert r50_id and r80_id and r81_id
            page.get_by_role("button", name="R81", exact=True).click()
            expect(page.locator("#comparisonSource")).to_have_value(r80_id)
            page.locator("#comparisonSource").select_option(r50_id)
            expect(page.locator("#roundComparisonContent")).to_contain_text("R50 → R81")
            expect(page.locator("#roundComparisonContent")).to_contain_text("回合編號相隔 31")
            compared_cells = page.locator("#roundComparisonContent tbody tr").first.locator("td")
            assert compared_cells.nth(2).inner_text() == "+1"
            assert compared_cells.nth(3).inner_text() == "-18"

            # Current source is R50, not the nearest R80; download exactly that pair.
            before_csv = page.evaluate(
                "() => localStorage.getItem('ikariam-report-cases-v1')"
            )
            with page.expect_download() as comparison_event:
                page.locator("#exportComparisonCsv").click()
            comparison_download = comparison_event.value
            assert comparison_download.suggested_filename.endswith("-R50-R81.csv")
            comparison_bytes = Path(comparison_download.path()).read_bytes()
            assert comparison_bytes.startswith(b"\xef\xbb\xbf")
            comparison_rows = list(csv.DictReader(io.StringIO(
                comparison_bytes.decode("utf-8-sig"), newline=""
            )))
            assert len(comparison_rows) == 1
            first_comparison = comparison_rows[0]
            assert first_comparison["evidence_class"] == "USER_TRANSCRIPTION_UNVERIFIED"
            assert first_comparison["earlier_round"] == "50"
            assert first_comparison["target_round"] == "81"
            assert first_comparison["round_number_gap"] == "31"
            assert first_comparison["comparison_status"] == "FIELDS_COMPARABLE"
            assert first_comparison["earlier_count"] == "7"
            assert first_comparison["target_count"] == "8"
            assert first_comparison["typed_count_delta"] == "1"
            assert first_comparison["typed_hp_percentage_point_delta"] == "-18"
            assert not any("reserve" in name.lower() for name in first_comparison)
            assert page.evaluate(
                "() => localStorage.getItem('ikariam-report-cases-v1')"
            ) == before_csv, "read-only CSV export modified case storage"
            page.locator("#readMode").click()
            expect(page.locator("#comparisonSource")).to_have_value(r50_id)
            page.locator("#editMode").click()
            expect(page.locator("#comparisonSource")).to_have_value(r50_id)
            page.get_by_role("button", name="R82", exact=True).click()
            expect(page.locator("#comparisonSource")).to_have_value(r81_id)
            page.locator("#comparisonSource").select_option(r50_id)
            expect(page.locator("#roundComparisonContent")).to_contain_text("R50 → R82")
            expect(page.locator("#roundComparisonContent")).to_contain_text("兵種／Wave／數量／HP 未填齊")
            with page.expect_download() as draft_csv_event:
                page.locator("#exportComparisonCsv").click()
            draft_csv = list(csv.DictReader(io.StringIO(
                Path(draft_csv_event.value.path()).read_bytes().decode("utf-8-sig"),
                newline=""
            )))
            assert len(draft_csv) == 1
            assert draft_csv[0]["comparison_status"] == "INCOMPLETE"
            assert draft_csv[0]["typed_count_delta"] == ""
            assert draft_csv[0]["typed_hp_percentage_point_delta"] == ""
            page.get_by_role("button", name="R81", exact=True).click()
            page.get_by_role("button", name="R82", exact=True).click()
            expect(page.locator("#comparisonSource")).to_have_value(r81_id)
            page.get_by_role("button", name="R50", exact=True).click()
            expect(page.locator("#comparisonSource")).to_be_disabled()
            expect(page.locator("#exportComparisonCsv")).to_be_disabled()
            expect(page.locator("#exportTimelineCsv")).to_be_enabled()
            before_timeline = page.evaluate(
                "() => localStorage.getItem('ikariam-report-cases-v1')"
            )
            with page.expect_download() as timeline_event:
                page.locator("#exportTimelineCsv").click()
            timeline_file = timeline_event.value
            assert timeline_file.suggested_filename.startswith("ikariam-typed-timeline-")
            assert timeline_file.suggested_filename.endswith(".csv")
            timeline_bytes = Path(timeline_file.path()).read_bytes()
            assert timeline_bytes.startswith(b"\xef\xbb\xbf")
            timeline_rows = list(csv.DictReader(io.StringIO(
                timeline_bytes.decode("utf-8-sig"), newline=""
            )))
            assert [(row["earlier_round"], row["target_round"]) for row in timeline_rows] == [
                ("50", "80"), ("80", "81"), ("81", "82")
            ]
            assert [row["comparison_status"] for row in timeline_rows] == [
                "FIELDS_COMPARABLE", "FIELDS_COMPARABLE", "INCOMPLETE"
            ]
            assert [row["typed_count_delta"] for row in timeline_rows] == ["2", "-1", ""]
            assert [row["typed_hp_percentage_point_delta"] for row in timeline_rows] == [
                "-11", "-7", ""
            ]
            assert all(row["evidence_class"] == "USER_TRANSCRIPTION_UNVERIFIED"
                       for row in timeline_rows)
            assert all(row["interpretation"] == "TYPED_FIELDS_ONLY_NOT_COMBAT_CAUSALITY"
                       for row in timeline_rows)
            assert page.evaluate(
                "() => localStorage.getItem('ikariam-report-cases-v1')"
            ) == before_timeline, "timeline CSV export changed case storage"

            # Coverage ledger lists typed input status, not verified battlefield losses.
            page.locator("#captureCoverage summary").click()
            coverage_rows = page.locator("#captureCoverageContent tbody tr")
            expect(coverage_rows).to_have_count(3)
            expect(coverage_rows.nth(0)).to_contain_text("R50 → R80")
            expect(coverage_rows.nth(1)).to_contain_text("R80 → R81")
            expect(coverage_rows.nth(2)).to_contain_text("R81 → R82")
            assert coverage_rows.nth(0).locator("td").nth(0).inner_text() == "30"
            assert coverage_rows.nth(0).locator("td").nth(1).inner_text() == "1"
            assert coverage_rows.nth(1).locator("td").nth(1).inner_text() == "1"
            assert coverage_rows.nth(2).locator("td").nth(3).inner_text() == "1"
            assert coverage_rows.nth(2).locator("td").nth(1).inner_text() == "0"
            original_coverage_storage = page.evaluate(
                "() => localStorage.getItem('ikariam-report-cases-v1')"
            )
            # Original screenshots are NOT attached. Export existing note text
            # for every captured round, including blanks, without verification.
            expect(page.locator("#exportSourceManifestCsv")).to_be_enabled()
            with page.expect_download() as source_notes_event:
                page.locator("#exportSourceManifestCsv").click()
            manifest_file = source_notes_event.value
            assert manifest_file.suggested_filename.startswith(
                "ikariam-source-notes-manifest-"
            )
            assert manifest_file.suggested_filename.endswith(".csv")
            manifest_bytes = Path(manifest_file.path()).read_bytes()
            assert manifest_bytes.startswith(b"\xef\xbb\xbf")
            manifest_rows = list(csv.DictReader(io.StringIO(
                manifest_bytes.decode("utf-8-sig"), newline=""
            )))
            assert [row["capture_round"] for row in manifest_rows] == [
                "50", "80", "81", "82"
            ]
            manifest_by_round = {row["capture_round"]: row for row in manifest_rows}
            assert manifest_by_round["80"]["source_note_status"] == (
                "SOURCE_NOTE_TYPED_UNVERIFIED"
            )
            assert "所有圖片均為合成測試" in manifest_by_round["80"]["source_note_text"]
            assert manifest_by_round["82"]["source_note_status"] == "SOURCE_NOTE_MISSING"
            assert manifest_by_round["82"]["source_note_text"] == ""
            assert all(row["original_image_in_export"] == "ORIGINAL_IMAGE_NOT_INCLUDED"
                       for row in manifest_rows)
            assert all(row["source_authentication"] == "NOT_AUTHENTICATED"
                       for row in manifest_rows)
            assert page.evaluate(
                "() => localStorage.getItem('ikariam-report-cases-v1')"
            ) == original_coverage_storage, "source-note manifest wrote to case storage"
            expect(page.locator("#exportCoverageReviewCsv")).to_be_enabled()
            expect(page.locator("#exportJoinedReviewCsv")).to_be_enabled()
            # Join both captured-round source notes for the ONE pending pair.
            with page.expect_download() as joined_review_event:
                page.locator("#exportJoinedReviewCsv").click()
            joined_download = joined_review_event.value
            assert joined_download.suggested_filename.startswith(
                "ikariam-pending-review-with-notes-"
            )
            joined_bytes = Path(joined_download.path()).read_bytes()
            assert joined_bytes.startswith(b"\xef\xbb\xbf")
            joined_rows = list(csv.DictReader(io.StringIO(
                joined_bytes.decode("utf-8-sig"), newline=""
            )))
            assert len(joined_rows) == 1, joined_rows
            joined_row = joined_rows[0]
            assert (joined_row["earlier_round"], joined_row["target_round"]) == (
                "81", "82"
            )
            assert joined_row["review_reason"] == "INCOMPLETE"
            assert joined_row["earlier_source_note_status"] == "SOURCE_NOTE_MISSING"
            assert joined_row["target_source_note_status"] == "SOURCE_NOTE_MISSING"
            assert joined_row["earlier_source_note_text"] == ""
            assert joined_row["target_source_note_text"] == ""
            assert joined_row["original_image_in_export"] == "ORIGINAL_IMAGE_NOT_INCLUDED"
            assert joined_row["source_authentication"] == "NOT_AUTHENTICATED"
            assert joined_row["interpretation"] == (
                "NOTE_TEXT_ONLY_NOT_PROOF_OF_SOURCE_OR_COMBAT_CAUSALITY"
            )
            assert page.evaluate(
                "() => localStorage.getItem('ikariam-report-cases-v1')"
            ) == original_coverage_storage, "joined CSV download persisted case data"
            # Export only the unresolved R81→R82 draft, not comparable R50/R80/R81.
            with page.expect_download() as review_queue_download:
                page.locator("#exportCoverageReviewCsv").click()
            review_download = review_queue_download.value
            assert review_download.suggested_filename.startswith(
                "ikariam-typed-review-queue-"
            )
            assert review_download.suggested_filename.endswith(".csv")
            review_bytes = Path(review_download.path()).read_bytes()
            assert review_bytes.startswith(b"\xef\xbb\xbf")
            review_rows = list(csv.DictReader(io.StringIO(
                review_bytes.decode("utf-8-sig"), newline=""
            )))
            assert len(review_rows) == 1, review_rows
            row = review_rows[0]
            assert (row["earlier_round"], row["target_round"]) == ("81", "82")
            assert row["review_reason"] == "INCOMPLETE"
            assert (row["side"], row["line"], row["physical_position"]) == (
                "attacker", "first", "1"
            )
            assert row["earlier_count"] == "8"
            assert row["earlier_hp_percent"] == "76"
            assert row["target_count"] == "" and row["target_hp_percent"] == ""
            assert row["interpretation"] == (
                "SOURCE_IMAGE_NOT_VERIFIED_NO_COMBAT_CAUSALITY"
            )
            assert "不可推算補值" in row["source_check_instruction"]
            assert page.evaluate(
                "() => localStorage.getItem('ikariam-report-cases-v1')"
            ) == original_coverage_storage, "review-queue download persisted case data"
            # Inspect the exact physical slot in the draft R81→R82 pair.
            coverage_rows.nth(2).locator('button[data-coverage-review]').click()
            detail = page.locator("#coverageReviewDetail")
            expect(detail).to_contain_text("R81 → R82 待查欄位（1 筆）")
            expect(detail).to_contain_text("攻 前排 格位 1")
            expect(detail).to_contain_text("兵種／Wave／數量／HP 未填齊")
            expect(detail).to_contain_text("不可推算補值")
            expect(detail).to_contain_text("HP 未填")
            assert page.evaluate(
                "() => localStorage.getItem('ikariam-report-cases-v1')"
            ) == original_coverage_storage, "reviewing a gap persisted case data"
            # The R50→R80 pair is comparable, but never 'authenticated'.
            coverage_rows.nth(0).locator('button[data-coverage-review]').click()
            expect(detail).to_contain_text("沒有這組截錄的欄位限制項目")
            expect(detail).to_contain_text("不代表截圖來源已經核實")
            page.locator(
                f'#captureCoverageContent button[data-coverage-target="{r81_id}"]'
            ).click()
            expect(page.locator("#coverageReviewDetail")).to_be_empty()
            expect(page.locator("#roundHeading")).to_contain_text("R81")
            assert page.evaluate(
                "() => localStorage.getItem('ikariam-report-cases-v1')"
            ) == original_coverage_storage, "coverage navigation persisted source data"
            page.get_by_role("button", name="R50", exact=True).click()
            page.screenshot(path=str(evidence_dir / "battle-report-desktop-synthetic.png"), full_page=True)

            with page.expect_download() as d:
                page.locator("#exportCase").click()
            download = d.value
            payload = Path(download.path()).read_bytes()
            saved = json.loads(payload.decode("utf-8"))
            assert saved["id"] == original_id
            assert saved["research"]["kind"] == "partial_observation"
            assert "側翼劍士互砍" in saved["research"]["objective"]
            assert "前線填滿" in saved["research"]["known_conditions"]
            assert "非實戰觀測" in saved["research"]["hypothetical_inputs"]
            assert saved["research"]["confirmed_absences"] == ""
            assert sorted(r["number"] for r in saved["rounds"]) == [50, 80, 81, 82]
            rounds = {r["number"]: r for r in saved["rounds"]}
            assert rounds[80]["attacker"]["slots"][0]["pos"] == 1
            assert rounds[80]["attacker"]["slots"][0]["hp"] == 83
            assert rounds[80]["attacker"]["reserve"][0]["source"] == "assumed_full"
            assert rounds[80]["attacker"]["reserve"][0]["hp"] == 100
            assert rounds[50]["baseline_confirmed"]["attacker"] is True
            r82 = rounds[82]
            assert r82["source"] == ""
            assert r82["phase"] == "round_end"
            assert r82["baseline_confirmed"] == {"attacker": False, "defender": False}
            assert not r82["attacker"]["reserve"] and not r82["defender"]["reserve"]
            assert r82["attacker"]["slots"][0] == {
                "line": "first", "pos": 1, "unit": unit, "wave": "browser-e2e",
                "count": None, "hp": None, "deaths": None,
            }
            assert 100 < len(payload) <= 64 * 1024 * 1024
            print("PASS: real browser R50/R80/R81/R82, label-only drafts, Reserve, JSON download")

            page.locator("#importCase").set_input_files({
                "name": download.suggested_filename,
                "mimeType": "application/json",
                "buffer": payload,
            })
            expect(page.locator("#caseList option")).to_have_count(2)
            expect(page.locator("#caseHeading")).to_contain_text("匯入")
            imported_id = page.locator("#caseList").input_value()
            assert imported_id and imported_id != original_id
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
            assert page.locator("#caseList").input_value() == imported_id
            page.get_by_role("button", name="R80", exact=True).click()
            expect(first_tile).to_contain_text("HP 83%")

            # Do not mistake a successful file-picker interaction for lossless restore.
            # Re-export the IMPORTED case after localStorage reload, and compare all
            # nested rounds (R50/R80/R81/R82), slots, Reserve, counts, deaths, notes,
            # chronology, confirmation flags and source provenance as parsed JSON.
            with page.expect_download() as restored_download_event:
                page.locator("#exportCase").click()
            restored_payload = Path(restored_download_event.value.path()).read_bytes()
            restored = json.loads(restored_payload.decode("utf-8"))
            assert restored["id"] == imported_id
            assert restored["name"] == saved["name"][:114] + "（匯入）"
            assert restored["created"] == restored["updated"]
            expected_payload = dict(saved)
            # Import intentionally assigns new identity, name and timestamps only.
            for key in ("id", "name", "created", "updated"):
                expected_payload[key] = restored[key]
            assert restored == expected_payload, (
                "Imported case lost/changed data across upload, delete, reload and "
                "download: full nested case JSON differs from the original backup"
            )
            print("PASS: complete 4-round JSON backup round-trip after localStorage reload")

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
