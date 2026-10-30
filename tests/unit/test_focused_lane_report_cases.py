"""Read-only focused line evidence projection: unknown is not zero."""
from pathlib import Path
import re
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.skipif(shutil.which("node") is None, reason="Node required")
def test_focused_lane_projection_and_csv_are_source_only(tmp_path):
    js = tmp_path / "focused.cjs"
    js.write_text(r"""
const assert=require('node:assert/strict');
const M=require(process.argv[2]);
const fields=[{id:'land-max',lines:{
 flank:{physical_order:[2,1,3]},
 first:{physical_order:[1,2,3]},
 second:{physical_order:[]}
}}];
const c=M.create('Flank =SUM(1+1)','land-max');
c.research=M.newResearch();
const r80=c.rounds[0];r80.number=80;r80.source='=CMD(1)';
r80.phase='round_end';
const s1=M.newSlot('flank',1);s1.unit='swordsman';s1.deaths=0;
const s3=M.newSlot('flank',3);s3.unit='swordsman';s3.deaths=2;s3.hp=94;
const draft=M.newSlot('flank',2);draft.unit='swordsman';
r80.attacker.slots.push(s1,s3,draft);
const r1=M.newRound(1);r1.phase='round_prefire';r1.source='raw first';
c.rounds.push(r1);
const original=JSON.stringify(c);
assert.equal(M.projectFocusedLane(c,'attacker','flank',fields).allowed,false);
c.research.objective='Compare flank kills';
assert.equal(M.projectFocusedLane(c,'attacker','flank',fields).allowed,false);
c.research.observed_scope='Only attacker flank';
c.research.known_conditions='front line full; exact unit counts unknown';
c.research.hypothetical_inputs='350 Hoplite scenario is NOT game observation';
const before=JSON.stringify(c);
const projection=M.projectFocusedLane(c,'attacker','flank',fields);
assert.equal(projection.allowed,true);
assert.equal(projection.positionCount,3);
assert.deepEqual(projection.rounds.map(x=>x.number),[1,80]);
assert.equal(projection.rounds[0].phase,'round_prefire');
assert.equal(projection.rounds[0].enteredDeaths,0);
assert.equal(projection.rounds[0].reportedDeathSum,0); // NOT an observed zero
assert.deepEqual(projection.rounds[0].cells.map(x=>x.deaths),[null,null,null]);
const rr=projection.rounds[1];
assert.equal(rr.reportedDeathSum,2);
assert.equal(rr.deathCoverage,'2/3');
assert.equal(rr.completeTypedDeathPositions,false);
assert.deepEqual(rr.cells.map(x=>x.deaths),[0,null,2]);
assert.deepEqual(rr.cells.map(x=>x.code),
 ['TYPED_NUMERIC_UNVERIFIED','LABEL_ONLY_UNVERIFIED','TYPED_NUMERIC_UNVERIFIED']);
const csv=M.exportFocusedLaneCsv(c,'attacker','flank',fields);
assert.match(csv,/UNKNOWN_NOT_ZERO/);
assert.match(csv,/NOT_AUTHENTICATED/);
assert.match(csv,/\xEF?CMD/); // Placeholder below updated by exact escape assertion
assert.match(csv,/"'=CMD\(1\)"/); // Source-note formula entry-point escaped
assert.match(csv,/"Flank =SUM\(1\+1\)"/);
assert.match(csv,/NOT game observation/);
assert.equal(JSON.stringify(c),before);
assert.equal(M.projectFocusedLane(c,'defender','flank',fields).code,'NO_FOCUSED_NUMERIC_EVIDENCE');
assert.equal(M.projectFocusedLane(c,'attacker','first',fields).allowed,false);
assert.equal(M.projectFocusedLane(c,'attacker','second',fields).code,'UNSUPPORTED_LINE_GEOMETRY');
assert.throws(()=>M.projectFocusedLane(c,'wrong','flank',fields),/無效/);
assert.throws(()=>M.exportFocusedLaneCsv(c,'defender','flank',fields),/無法匯出/);
const labelOnly=M.create('label only','land-max');labelOnly.research=M.newResearch();
labelOnly.research.objective='focus';labelOnly.research.observed_scope='flank';
labelOnly.rounds[0].attacker.slots.push({...M.newSlot('flank',1),unit:'swordsman'});
assert.equal(M.projectFocusedLane(labelOnly,'attacker','flank',fields).allowed,false);
for(const kind of ['research_summary','full_report']){
 c.research.kind=kind;
 assert.equal(M.projectFocusedLane(c,'attacker','flank',fields).allowed,false);
 assert.equal(M.researchEvidenceGate(c).globalCalibrationAllowed,false);
}
delete c.research;
assert.equal(M.projectFocusedLane(c,'attacker','flank',fields).allowed,false);
assert.equal(M.validateCase(c,fields).length,0);
console.log('Focused study source-only scope guards PASS');
""", encoding="utf-8")
    script = js.read_text(encoding="utf-8")
    script = script.replace("assert.match(csv,/\\xEF?CMD/); // Placeholder below updated by exact escape assertion\n", "")
    js.write_text(script, encoding="utf-8")
    result = subprocess.run(
        ["node", str(js), str(ROOT / "battle-cases-model.js")],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_focused_lane_static_asset_parity_and_browser_wiring():
    model = (ROOT / "battle-cases-model.js").read_bytes()
    page = (ROOT / "battle-cases.html").read_bytes()
    assert model == (ROOT / "public/battle-cases-model.js").read_bytes()
    assert page == (ROOT / "public/battle-cases.html").read_bytes()
    source = page.decode("utf-8")
    assert "id=\"focusedSide\"" in source
    assert "id=\"focusedLine\"" in source
    assert "M.projectFocusedLane(c,focusedSide,focusedLine,fields)" in source
    assert "M.exportFocusedLaneCsv(c,focusedSide,focusedLine,fields)" in source
    assert "未填格位" in source
    assert not re.search(r"POST\s+/api/simulate", source)
