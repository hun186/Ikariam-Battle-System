"""Source-grounded, non-destructive historical research battle-case catalog."""
import json
from pathlib import Path
import re
import shutil
import subprocess

import pytest

ROOT=Path(__file__).resolve().parents[2]
HISTORY=ROOT/"battle-cases-history.json"
MODEL=ROOT/"battle-cases-model.js"

def test_bundled_historical_catalog_has_provenance_and_round_gap():
    bundle=json.loads(HISTORY.read_text(encoding="utf-8"))
    assert bundle["schema"]=="ikariam-research-battle-history-v1"
    cases=bundle["cases"]
    assert len(cases)==14
    assert (ROOT/"public/battle-cases-history.json").read_bytes()==HISTORY.read_bytes()
    assert len({c["id"] for c in cases})==14
    assert all(c["id"].startswith("research-") and "非 Gameforge" in c["notes"] for c in cases)
    for c in cases:
        assert c["schema"]=="ikariam-report-cases-v1"
        assert "tests/fixtures/reverse_engineering/" in c["notes"]
        assert len(c["rounds"])>=1
        for r in c["rounds"]:
            assert "未獨立驗證" in r["source"]
            assert r["baseline_confirmed"]=={"attacker":False,"defender":False}
            assert r["attacker"]["reserve"]==r["defender"]["reserve"]==[]
            assert all(s["wave"]=="" for side in ("attacker","defender") for s in r[side]["slots"])
    main=next(c for c in cases if c["id"]=="research-land-forge5-r1-r80-r89")
    assert [r["number"] for r in main["rounds"]]==[1,*range(80,90)]
    assert sum(x["deaths"] for x in main["rounds"][0]["attacker"]["slots"])==80
    fixture=json.loads((ROOT/"tests/fixtures/reverse_engineering/land_barbarian_rounds80_89_20261014.json").read_text(encoding="utf-8"))
    for row,round_ in zip(fixture["observations"],main["rounds"][1:]):
        assert row["round"]==round_["number"]
        for s in round_["attacker"]["slots"]:
            assert s["deaths"]==row["attacker_barbarian_main_line_deaths_left_to_right"][s["pos"]-1]
    slinger=next(c for c in cases if c["id"]=="research-land-slinger-400-r76-r80")
    assert [r["number"] for r in slinger["rounds"]]==[76,77,78,79,80]
    assert slinger["rounds"][0]["defender"]["slots"]==[]
    ram=[c for c in cases if c["id"].startswith("research-naval-ram-")]
    assert len(ram)==3
    assert all(not c["rounds"][0]["defender"]["slots"] for c in ram)
    assert all("索引占位" in c["notes"] for c in ram)
    naval=[c for c in cases if c["id"].startswith("research-naval-pvp-")]
    assert len(naval)==3 and all(c["rounds"][0]["defender"]["slots"]==[] for c in naval)

@pytest.mark.skipif(shutil.which("node") is None,reason="Node required")
def test_history_catalog_validates_and_merges_without_overwriting_user_cases(tmp_path):
    js=tmp_path/"history.cjs"
    js.write_text(r'''
const fs=require('node:fs'), assert=require('node:assert/strict');
const M=require(process.argv[2]);
const bundle=JSON.parse(fs.readFileSync(process.argv[3],"utf8"));
const fields=[
 {id:"land-max",lines:Object.fromEntries(["first","second","third","flank","balloon","anti-balloon"].map(n=>[n,{physical_order:Array.from({length:7},(_,i)=>i+1)}]))},
 {id:"naval-max",lines:Object.fromEntries(["first","second","third","flank","balloon","anti-balloon"].map(n=>[n,{physical_order:Array.from({length:7},(_,i)=>i+1)}]))}
];
for(const c of bundle.cases) assert.deepEqual(M.validateCase(c,fields),[],c.id);
let merged=M.mergeHistoricalCases([],bundle,fields);
assert.equal(merged.added,14);
assert.equal(merged.total,14);
assert.equal(merged.cases.length,14);
merged.cases[0].notes+='(researcher local edit)';
const first=merged.cases[0];
const repeated=M.mergeHistoricalCases(merged.cases,bundle,fields);
assert.equal(repeated.added,0);
assert.equal(repeated.cases[0],first);
assert.match(repeated.cases[0].notes,/researcher local edit/);
const restored=M.mergeHistoricalCases([first],bundle,fields);
assert.equal(restored.added,13);
assert.equal(restored.cases[0],first);
const own=M.create('My own case','land-max');
const withOwn=M.mergeHistoricalCases([own],bundle,fields);
assert.equal(withOwn.cases[0],own);
assert.equal(withOwn.cases.length,15);
assert.throws(()=>M.mergeHistoricalCases([], {...bundle,schema:'official'},fields),/格式無效/);
assert.throws(()=>M.mergeHistoricalCases([], {...bundle,cases:[bundle.cases[0],bundle.cases[0]]},fields),/ID 無效或重複/);
const corrupted=JSON.parse(JSON.stringify(bundle));
corrupted.cases[1].rounds[0].attacker.slots[0].hp=101;
assert.throws(()=>M.mergeHistoricalCases([],corrupted,fields),/案例無效/);
assert.throws(()=>M.mergeHistoricalCases(Array.from({length:37},(_,i)=>({...M.create('own'+i,'land-max'),id:'own'+i})),bundle,fields),/超過 50/);
console.log('history catalog provenance, validation and idempotence PASS');
''',encoding="utf-8")
    x=subprocess.run(["node",str(js),str(MODEL),str(HISTORY)],capture_output=True,text=True)
    assert x.returncode==0,x.stdout+x.stderr

def test_historical_asset_routes_and_browser_import_are_real():
    page=(ROOT/"battle-cases.html").read_text(encoding="utf-8")
    assert page==(ROOT/"public/battle-cases.html").read_text(encoding="utf-8")
    assert "id=\"loadHistoricalCases\"" in page
    assert "await loadHistoricalCases(true)" in page
    assert "localStorage.getItem(HISTORY_MARKER)" in page
    assert "M.mergeHistoricalCases(cases,JSON.parse(source),fields)" in page
    assert "localStorage.setItem(M.STORAGE,JSON.stringify(merged.cases))" in page
    vercel=json.loads((ROOT/"vercel.json").read_text(encoding="utf-8"))
    assert {"source":"/battle-cases-history.json","destination":"/battle-cases-history.json"} in vercel["rewrites"][:-1]
    assert (ROOT/"battle-cases-model.js").read_bytes()==(ROOT/"public/battle-cases-model.js").read_bytes()
    assert len(re.findall(r'<script>',page))==1
