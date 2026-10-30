"""Bounded user-entered focused candidate comparisons are not engine attestation."""
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT=Path(__file__).resolve().parents[2]


@pytest.mark.skipif(shutil.which("node") is None, reason="Node required")
def test_focused_candidate_model_guards_and_csv(tmp_path):
    js=tmp_path/"candidate.cjs"
    js.write_text(r"""
const assert=require('node:assert/strict'),M=require(process.argv[2]);
const fields=[{id:'land-max',lines:{
 first:{physical_order:[1,2,3]},flank:{physical_order:[2,1,3]}}}];
const c=M.create('Study','land-max');c.research=M.newResearch();
c.research.objective='Study flank damage';
c.research.observed_scope='Attacker flank only';
c.research.known_conditions='Front fully occupied; counts not given';
c.research.hypothetical_inputs='350 hoplites scenario is NOT original observation';
const r=c.rounds[0];r.number=80;r.phase='round_end';r.source='typed by researcher';
const a=M.newSlot('flank',1);a.unit='swordsman';a.wave='w1';
a.count=9;a.hp=83;a.deaths=2;
const b=M.newSlot('flank',2);b.unit='swordsman';b.wave='w1';
b.deaths=0; // Explicitly observed zero differs from missing
const x=M.newSlot('flank',3);x.unit='swordsman';x.wave='w1';
r.attacker.slots.push(a,b,x);
const snapshot=JSON.stringify(c),template=M.newFocusedCandidateTemplate(c,'attacker','flank',r.id,fields);
assert.equal(template.schema,'ikariam-focused-model-candidate-v1');
assert.equal(template.source_class,'USER_ENTERED_MODEL_CANDIDATE_NOT_ENGINE_ATTESTED');
assert.deepEqual(template.predictions.map(p=>p.count),[null,null,null]);
assert.deepEqual(template.predictions.map(p=>p.deaths),[null,null,null]);
assert.deepEqual(template.predictions.map(p=>p.pos),[1,2,3]);
assert.equal(JSON.stringify(c),snapshot);
const good={...template,candidate_label:'=UntrustedCandidate()',
 assumptions:'+External artificial prediction; the engine did not produce these'};
good.predictions[0]={...good.predictions[0],count:7,hp:80,deaths:0};
good.predictions[1]={...good.predictions[1],count:0,deaths:0};
good.predictions[2]={...good.predictions[2],count:10,deaths:8};
const result=M.compareFocusedCandidate(c,JSON.stringify(good),fields);
assert.equal(result.numericOverlap,4); // pos1 3 metrics, pos2 deaths 1
assert.equal(result.comparablePositions,2);
assert.equal(result.rows[0].difference.count,-2);
assert.equal(result.rows[0].difference.hp,-3);
assert.equal(result.rows[0].difference.deaths,-2);
assert.equal(result.rows[1].difference.count,null); // original count missing: not zero
assert.equal(result.rows[1].difference.deaths,0); // known zero vs zero
assert.equal(result.rows[2].difference.deaths,null); // candidate present, source missing
assert.equal(result.rows[2].code,'NO_SHARED_NUMERIC_FIELD');
assert.equal(result.attestedEngineExecution,false);
assert.equal(result.authenticatedGameSource,false);
assert.equal(result.globalCalibrationAllowed,false);
const csv=M.exportFocusedCandidateComparisonCsv(c,JSON.stringify(good),fields);
assert.match(csv,/NOT_ATTESTED/);
assert.match(csv,/NOT_AUTHENTICATED/);
assert.match(csv,/"'=UntrustedCandidate\(\)"/);
assert.match(csv,/"'\+External artificial/);
assert.match(csv,/,-2,/);
assert.equal(JSON.stringify(c),snapshot);
// Known label mismatches must suppress numeric differences, not show false fit.
const changed=JSON.parse(JSON.stringify(good));
changed.predictions[0].unit='hoplite';
const mismatch=M.compareFocusedCandidate(c,JSON.stringify(changed),fields);
assert.equal(mismatch.identityConflicts,1);
assert.equal(mismatch.rows[0].code,'KNOWN_LABEL_MISMATCH');
assert.equal(mismatch.rows[0].difference.deaths,null);
changed.predictions[0].unit='swordsman';changed.predictions[0].wave='unknown-wave';
assert.equal(M.compareFocusedCandidate(c,JSON.stringify(changed),fields).identityConflicts,1);
changed.predictions[0].wave='w1';
// All no overlap => export refuses, without manufacturing a score.
const blank={...template,candidate_label:'blank',assumptions:'No prediction provided yet'};
const noOverlap=M.compareFocusedCandidate(c,JSON.stringify(blank),fields);
assert.equal(noOverlap.status,'NO_COMPARABLE_FIELDS');
assert.throws(()=>M.exportFocusedCandidateComparisonCsv(c,JSON.stringify(blank),fields),/沒有任何可比較/);
function reject(obj,pattern){
 assert.throws(()=>M.compareFocusedCandidate(c,JSON.stringify(obj),fields),pattern);
}
reject({...good,source_class:'SIMULATOR_ATTESTED'},/來源類別/);
reject({...good,case_id:'different'},/識別/);
reject({...good,case_updated:'outdated'},/版本/);
reject({...good,battlefield:'naval-max'},/戰場不符/);
reject({...good,round_number:81},/回合編號/);
reject({...good,phase:'round_prefire'},/時點不符/);
reject({...good,round_id:'missing'},/不存在/);
reject({...good,predictions:good.predictions.slice(0,2)},/幾何不同/);
reject({...good,predictions:[good.predictions[0],good.predictions[0],good.predictions[2]]},/位置或數值無效/);
reject({...good,predictions:[{...good.predictions[0],deaths:1.5},...good.predictions.slice(1)]},/位置或數值無效/);
reject({...good,predictions:[{...good.predictions[0],hp:101},...good.predictions.slice(1)]},/位置或數值無效/);
reject({...good,assumptions:''},/模型假設/);
reject({...good,extra:1},/格式/);
assert.throws(()=>M.compareFocusedCandidate(c,'{bad JSON',fields),/無法解析/);
assert.throws(()=>M.compareFocusedCandidate(c,' '.repeat(128*1024+1),fields),/128 KiB/);
const before=JSON.stringify(c);
const olderRound=M.newRound(1);c.rounds.push(olderRound);
assert.throws(()=>M.newFocusedCandidateTemplate(c,'attacker','flank',olderRound.id,fields),/沒有數值觀測/);
assert.equal(JSON.stringify(c),JSON.stringify(c)); // sanity: pure comparisons only
c.research.kind='research_summary';
assert.throws(()=>M.newFocusedCandidateTemplate(c,'attacker','flank',r.id,fields),/不符合局部研究/);
c.research.kind='full_report';
assert.throws(()=>M.newFocusedCandidateTemplate(c,'attacker','flank',r.id,fields),/不符合局部研究/);
delete c.research;
assert.throws(()=>M.newFocusedCandidateTemplate(c,'attacker','flank',r.id,fields),/不符合局部研究/);
console.log('candidate source/geometry/identity/gap guards PASS');
""",encoding="utf-8")
    result=subprocess.run(
        ["node",str(js),str(ROOT/"battle-cases-model.js")],
        text=True,capture_output=True,check=False,
    )
    assert result.returncode==0,result.stdout+result.stderr


def test_candidate_static_browser_and_mirror_parity():
    main=(ROOT/"battle-cases.html").read_text(encoding="utf-8")
    assert main==(ROOT/"public/battle-cases.html").read_text(encoding="utf-8")
    assert (ROOT/"battle-cases-model.js").read_bytes()==(
        ROOT/"public/battle-cases-model.js").read_bytes()
    assert 'id="candidateJson"' in main
    assert 'id="candidateComparisonRows"' in main
    assert "M.newFocusedCandidateTemplate(c,focusedSide,focusedLine,r.id,fields)" in main
    assert "M.compareFocusedCandidate(c,$('candidateJson').value,fields)" in main
    assert "M.exportFocusedCandidateComparisonCsv(c,$('candidateJson').value,fields)" in main
