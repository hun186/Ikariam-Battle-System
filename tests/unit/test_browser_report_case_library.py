"""Browser report-case regression: local-only schema, reserve provenance and HTML parity."""
import asyncio
import json
from pathlib import Path
import re
import shutil
import subprocess

import pytest
from asgi import application

ROOT = Path(__file__).resolve().parents[2]


def test_same_report_case_ui_works_in_asgi_and_vercel_public():
    assert (ROOT / "battle-cases.html").read_bytes() == (ROOT / "public/battle-cases.html").read_bytes()
    assert (ROOT / "battle-cases-model.js").read_bytes() == (ROOT / "public/battle-cases-model.js").read_bytes()
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    assert index == (ROOT / "public/index.html").read_text(encoding="utf-8")
    assert 'href="/battle-cases.html"' in index
    page = (ROOT / "battle-cases.html").read_text(encoding="utf-8")
    assert '<script src="/battle-cases-model.js"></script>' in page
    assert 'id="battleBoard"' in page and 'id="slotEditor"' in page
    assert 'data-confirm-side' in page and 'data-edit-reserve' in page
    assert 'JSON 備份' in page and '不會顯示 Reserve' in page


def test_vercel_routes_case_page_and_model_before_spa_fallback():
    data = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))
    rules = data["rewrites"]
    assert {"source": "/battle-cases.html", "destination": "/battle-cases.html"} in rules[:-1]
    assert {"source": "/battle-cases-model.js", "destination": "/battle-cases-model.js"} in rules[:-1]
    assert rules[-1] == {"source": "/(.*)", "destination": "/index.html"}


async def _request(path):
    events = [{"type": "http.request", "body": b"", "more_body": False}]
    response = []
    async def receive():
        return events.pop(0)
    async def send(msg):
        response.append(msg)
    await application({"type": "http", "method": "GET", "path": path},
                      receive, send)
    return response


@pytest.mark.parametrize("path,needle", [
    ("/battle-cases.html", b"battleBoard"),
    ("/battle-cases-model.js", b"assumed_full"),
])
def test_asgi_serves_new_battle_case_static_assets(path, needle):
    response = asyncio.run(_request(path))
    assert response[0]["status"] == 200
    assert needle in response[1]["body"]


@pytest.mark.skipif(shutil.which("node") is None, reason="node needed for JS model and syntax regression")
def test_battle_case_scripts_parse_as_javascript(tmp_path):
    html = (ROOT / "battle-cases.html").read_text(encoding="utf-8")
    blocks = [part for part in re.findall(r"<script(?:\s[^>]*)?>([\s\S]*?)</script>", html) if part.strip()]
    assert len(blocks) == 1  # external src script intentionally has no inline body
    inline = tmp_path / "case-frontend.js"
    inline.write_text(blocks[0], encoding="utf-8")
    for file in [inline, ROOT / "battle-cases-model.js"]:
        proc = subprocess.run(["node", "--check", str(file)],
                              capture_output=True, text=True, check=False)
        assert proc.returncode == 0, proc.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="node needed for JS contract tests")
def test_provenance_contract_and_case_crud_model(tmp_path):
    script = r"""
const assert=require('node:assert/strict');
const M=require(process.argv[2]);
let c=M.create('sample','naval-small');
assert.equal(M.validateCase(c).length,0);
assert.equal(c.rounds.length,1);
assert.equal(M.readiness(c).ready,false); // empty draft is not evidence
let a=c.rounds[0].attacker;
const observed=M.newSlot('first',1);
observed.unit='ram_ship';observed.count=4;observed.hp=80;
a.slots.push(observed);
let reserve=M.newReserve();
reserve.unit='balloon_carrier';
reserve.count=3;
a.reserve.push(reserve);
assert.equal(reserve.hp,100);
assert.equal(reserve.source,'assumed_full');
let status=M.readiness(c);
assert.equal(status.ready,false);
assert(status.issues.some(s=>s.includes('100%')));
c.rounds[0].baseline_confirmed.attacker=true;
assert.equal(M.readiness(c).ready,true);
reserve.hp=75;
assert(M.validateCase(c).some(s=>s.includes('預設 Reserve')));
reserve.source='calculated';
reserve.calculation='很短';
assert(M.validateCase(c).some(s=>s.includes('至少 20 字')));
reserve.calculation='逐回合統計已知傷害和補血並核對實際出場數量，非直接取自戰報。';
assert.equal(M.validateCase(c).length,0);
assert.equal(M.readiness(c).ready,false);
assert(M.readiness(c).issues.some(s=>s.includes('外部精算')));
const original=JSON.stringify(c);
const imported=M.importCase(original);
assert.deepEqual(imported,c);
assert.equal(M.validateCase({...c,schema:'forged_official_gameforge'}).length>0,true);
assert.throws(()=>M.importCase(JSON.stringify({...c,schema:'forged_official_gameforge'})));
// Earliest CAPTURE round may be R50, not real battle's round 1.
const later=M.newRound(80);
let first=c.rounds[0];
first.number=90;
c.rounds.push(later);
const earlier=M.newRound(50);
earlier.attacker.reserve.push(M.newReserve());
earlier.attacker.reserve[0].unit='balloon_carrier';
earlier.attacker.reserve[0].count=2;
c.rounds.push(earlier);
assert.equal(M.readiness(c).ready,false);
assert(M.readiness(c).issues.some(s=>s.includes('R50')));
earlier.baseline_confirmed.attacker=true;
assert.equal(M.readiness(c).ready,false); // R50 lacks visible formation slot
const r50Observed=M.newSlot('first',1);
r50Observed.unit='ram_ship';r50Observed.count=3;r50Observed.hp=75;
earlier.attacker.slots.push(r50Observed);
assert.equal(M.readiness(c).ready,true); // earliest baseline R50 has visible slot and confirmed Reserve
// Real validation forbids duplicate round numbers and slot identity collisions.
later.number=50;
assert(M.validateCase(c).some(s=>s.includes('重複')));
later.number=80;
const slot=M.newSlot('first',1);
slot.unit='ram_ship';slot.count=4;slot.hp=50;
earlier.defender.slots.push(slot);
earlier.defender.slots.push({...slot});
assert(M.validateCase(c).some(s=>s.includes('格位位置')));
// No official-game observation metadata is minted by this model.
assert.equal(Object.hasOwn(c,'verified_gameforge'),false);
"""
    js = tmp_path / "verify.cjs"
    js.write_text(script, encoding="utf-8")
    result = subprocess.run(["node", str(js), str(ROOT / "battle-cases-model.js")],
                            capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr

def test_editing_first_captured_reserve_invalidates_prior_full_hp_confirmation():
    html = (ROOT / "battle-cases.html").read_text(encoding="utf-8")
    assert html.count("M.invalidateReserveConfirmation(round,side);") == 3
    assert "source:origin,calculation:cal" in html
    assert "if(!cal)$('editHp').value='100'" in html


@pytest.mark.skipif(shutil.which("node") is None, reason="Node required for report-case model regression")
def test_codex_p2_physical_indices_and_baseline_staleness_and_case_rename(tmp_path):
    """Reproduces all four P2 findings with observed data and untrusted input."""
    script = r"""
const assert=require('node:assert/strict');
const M=require(process.argv[2]);
const physicalOrder=[4,2,1,3,5]; // Naval Small: damage positions, left to right.
assert.deepEqual(M.physicalPositions(physicalOrder),[1,2,3,4,5]);
const fields=[{id:'naval-small',lines:{first:{physical_order:physicalOrder},
  flank:{physical_order:[2,1]}}}];
let c=M.create('round-80 sample','naval-small');
let r80=c.rounds[0];r80.number=80;
const visible=M.newSlot('first',1);
visible.unit='balloon_carrier';visible.count=3;visible.hp=99;
r80.attacker.slots.push(visible);
const reserve=M.newReserve();
reserve.unit='balloon_carrier';reserve.count=8;
r80.attacker.reserve.push(reserve);
r80.baseline_confirmed.attacker=true;
assert.equal(M.validateCase(c,fields).length,0);
assert.equal(M.readiness(c).ready,true);
// Physical slot 1 is valid even though the first damage label is 4.
const stored=M.importCase(JSON.stringify(c),fields);
assert.equal(stored.rounds[0].attacker.slots[0].pos,1);
const bad=M.newSlot('first',6);
c.rounds[0].defender.slots.push(bad);
assert(M.validateCase(c,fields).some(x=>x.includes('格位位置')));
c.rounds[0].defender.slots.pop();
// A former earliest round can become earliest again after an earlier snapshot is removed.
const earlier=M.newRound(50);c.rounds.push(earlier);
assert.equal(M.readiness(c).ready,false); // Empty R50 is NOT a valid baseline.
r80.attacker.reserve[0].count=9;
M.invalidateReserveConfirmation(r80,'attacker');
assert.equal(r80.baseline_confirmed.attacker,false);
c.rounds=c.rounds.filter(x=>x.id!==earlier.id);
assert.equal(M.readiness(c).ready,false);
assert(M.readiness(c).issues.some(x=>x.includes('100%')));
// A later observed slot cannot make an EMPTY earlier snapshot research ready.
let r50=M.newRound(50);c.rounds.push(r50);
assert.equal(M.readiness(c).ready,false);
assert(M.readiness(c).issues.some(x=>x.includes('R50')));
c.rounds=c.rounds.filter(x=>x.id!==r50.id);
// Guard in normal name editing path: reject blank values before ANY persisted mutation.
const before=JSON.stringify(c);
assert.throws(()=>M.validName('    '),/案例名稱/);
assert.throws(()=>M.validName('x'.repeat(121)),/案例名稱/);
assert.equal(JSON.stringify(c),before);
assert.equal(M.validName('  記錄  '),'記錄');
assert.equal(M.create('  案例  ').name,'案例');
"""
    js = tmp_path / "p2_cases.cjs"
    js.write_text(script, encoding="utf-8")
    cmd = subprocess.run(["node", str(js), str(ROOT / "battle-cases-model.js")],
                         capture_output=True, text=True, check=False)
    assert cmd.returncode == 0, cmd.stderr


def test_codex_p2_ui_bindings_keep_model_guards_active():
    html = (ROOT / "battle-cases.html").read_text(encoding="utf-8")
    assert "const pos=M.physicalPositions(geometry?.[line]?.physical_order);" in html
    assert "const accepted=M.validName(e.value);" in html
    assert "e.value=previous;notify('未儲存案例名稱：" in html
    assert "saveCaseName();saveInput('caseNotes','notes');" in html
    assert html.count("M.invalidateReserveConfirmation(round,side);") == 3
    assert 'if(round.id===firstRoundId())round.baseline_confirmed[side]=false' not in html


def test_codex_p2_reserve_add_refresh_and_limit_bindings():
    html = (ROOT / "battle-cases.html").read_text(encoding="utf-8")
    assert "if(round[side].reserve.length>=100)" in html
    assert "selected={side,reserveId:item.id};render();" in html
    assert "$('closeDrawer').onclick=()=>{selected=null;render();};" in html
    assert html.index("if(round[side].reserve.length>=100)") < html.index(
        "round[side].reserve.push(item);")
    assert (ROOT / "public/battle-cases.html").read_text(encoding="utf-8") == html


@pytest.mark.skipif(shutil.which("node") is None, reason="Node required for real UI event-handler regression")
def test_codex_p2_reserve_add_live_event_and_full_limit_guard(tmp_path):
    """Run the shipped inline UI in a lightweight browser DOM harness, then click Add/Cancel."""
    script = r"""
const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
const M=require(process.argv[2]);
const html=fs.readFileSync(process.argv[3],'utf8');
const inline=html.match(/<script>\s*([\s\S]*?)<\/script>/)[1];
const metadata={battlefields:[{id:'naval-small',domain:'naval',display_name:'Naval Small',
  lines:{first:{physical_order:[4,2,1,3,5]}}}],units:[{id:'ram_ship',domain:'naval',display_name:'Ram Ship'}]};
function sample(reserveCount){
  const c=M.create('Test captured round','naval-small');
  const visible=M.newSlot('first',1);
  Object.assign(visible,{unit:'ram_ship',count:4,hp:80});
  c.rounds[0].attacker.slots.push(visible);
  for(let i=0;i<reserveCount;i++){
    const item=M.newReserve();item.unit='ram_ship';item.count=1;
    c.rounds[0].attacker.reserve.push(item);
  }
  c.rounds[0].baseline_confirmed.attacker=true;
  assert.equal(M.readiness(c).ready,true);
  return c;
}
async function harness(caseValue){
  let stored=JSON.stringify([caseValue]), writes=0;
  const elements=new Map();
  function el(id){
    if(!elements.has(id))elements.set(id,{id,innerHTML:'',value:'',textContent:'',
      style:{},classList:{toggle(){},add(){},remove(){}},disabled:false,
      addEventListener(){},scrollIntoView(){}});
    return elements.get(id);
  }
  const document={getElementById:el};
  const localStorage={getItem:key=>key===M.STORAGE?stored:null,
    setItem:(key,value)=>{assert.equal(key,M.STORAGE);writes++;stored=value;}};
  vm.runInNewContext(inline,{window:{ReportCases:M},document,localStorage,
    fetch:async()=>({ok:true,json:async()=>metadata}),console,
    setTimeout,Date,Math,Number,String,Error,JSON,process});
  for(let i=0;i<8;i++)await new Promise(resolve=>setImmediate(resolve));
  return {el,read:()=>JSON.parse(stored)[0],writes:()=>writes,stored:()=>stored};
}
function clickAdd(h){
  h.el('battleBoard').onclick({target:{closest:(selector)=>
    selector==='[data-add-reserve]'?{dataset:{addReserve:'attacker'}}:null}});
}
(async()=>{
  // Adding Reserve immediately invalidates the former confirmed baseline,
  // and the on-screen readiness status reflects it before editing or cancel.
  const h=await harness(sample(1));
  assert.match(h.el('readiness').textContent,/已記錄可見格位/);
  clickAdd(h);
  assert.equal(h.read().rounds[0].attacker.reserve.length,2);
  assert.equal(h.read().rounds[0].baseline_confirmed.attacker,false);
  assert.match(h.el('readiness').textContent,/資料待覆核/);
  assert.match(h.el('readiness').textContent,/100%/);
  assert.match(h.el('slotEditor').innerHTML,/Reserve 編輯/);
  h.el('closeDrawer').onclick();
  assert.match(h.el('readiness').textContent,/資料待覆核/);
  // At exactly the accepted schema maximum, click must not mutate,
  // invalidate the confirmed baseline, or write an invalid JSON document.
  const full=await harness(sample(100));
  assert.match(full.el('readiness').textContent,/已記錄可見格位/);
  const before=full.stored(),writes=full.writes();
  clickAdd(full);
  assert.equal(full.stored(),before);
  assert.equal(full.writes(),writes);
  assert.equal(full.read().rounds[0].attacker.reserve.length,100);
  assert.equal(full.read().rounds[0].baseline_confirmed.attacker,true);
  assert.equal(M.validateCase(full.read(),metadata.battlefields).length,0);
  assert.match(full.el('storageStatus').textContent,/100 筆上限/);
})().catch(e=>{console.error(e);process.exitCode=1;});
"""
    js = tmp_path / "reserve_click.cjs"
    js.write_text(script, encoding="utf-8")
    result = subprocess.run(["node", str(js), str(ROOT / "battle-cases-model.js"),
                             str(ROOT / "battle-cases.html")],
                            capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="Node required for round-label draft contract")
def test_reuse_earlier_slot_labels_never_duplicates_observed_data(tmp_path):
    """Nearest chronological source only; no copied HP, deaths, counts or Reserve."""
    script = r"""
const assert=require('node:assert/strict');
const M=require(process.argv[2]);
const c=M.create('source snapshots','naval-small');
const r80=c.rounds[0];r80.number=80;
const early=M.newSlot('first',1);
Object.assign(early,{unit:'ram_ship',wave:'R80',count:11,hp:91,deaths:2});
r80.attacker.slots.push(early);
const reserve=M.newReserve();
Object.assign(reserve,{unit:'ram_ship',wave:'R80',count:9});
r80.attacker.reserve.push(reserve);r80.baseline_confirmed.attacker=true;
const noEarlier=JSON.stringify(c);
assert.throws(()=>M.reuseEarlierSlotLabels(c,r80.id),/沒有更早/);
assert.equal(JSON.stringify(c),noEarlier);

const r82=M.newRound(82);r82.source='不同於 R81 的合成截圖來源';
c.rounds.push(r82);
const r81=M.newRound(81);
const candidate=M.newSlot('first',3);
Object.assign(candidate,{unit:'balloon_carrier',wave:'R81',count:7,hp:83,deaths:5});
r81.defender.slots.push(candidate);
c.rounds.push(r81); // chronology is by round number, not array order
const result=M.reuseEarlierSlotLabels(c,r82.id);
assert.deepEqual(result,{sourceRound:81,copiedSlots:1});
assert.deepEqual(r82.attacker,{slots:[],reserve:[]});
assert.deepEqual(r82.defender.slots,[{
  line:'first',pos:3,unit:'balloon_carrier',wave:'R81',
  count:null,hp:null,deaths:null,
}]);
assert.equal(r82.defender.reserve.length,0);
assert.equal(r82.source,'不同於 R81 的合成截圖來源');
assert.deepEqual(r82.baseline_confirmed,{attacker:false,defender:false});
assert.equal(r82.phase,'round_end');
assert.equal(M.validateCase(c).length,0);
assert.equal(r81.defender.slots[0].hp,83);
r82.defender.slots[0].wave='edited';
assert.equal(r81.defender.slots[0].wave,'R81'); // not shared objects
const beforeRepeat=JSON.stringify(c);
assert.throws(()=>M.reuseEarlierSlotLabels(c,r82.id),/已有格位/);
assert.equal(JSON.stringify(c),beforeRepeat);

// Do not silently skip the nearest earlier EMPTY snapshot to copy stale labels.
const r84=M.newRound(84);
r84.attacker.slots.push(M.newSlot('first',1)); // no unit or wave
const r85=M.newRound(85);c.rounds.push(r84,r85);
const beforeEmpty=JSON.stringify(c);
assert.throws(()=>M.reuseEarlierSlotLabels(c,r85.id),/沒有兵種或 Wave/);
assert.equal(JSON.stringify(c),beforeEmpty);
assert.equal(M.validateCase(c).length,0);
"""
    js = tmp_path / "draft_labels.cjs"
    js.write_text(script, encoding="utf-8")
    result = subprocess.run(["node", str(js), str(ROOT / "battle-cases-model.js")],
                            capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="Node required for captured-round progress contract")
def test_round_entry_progress_never_conflates_draft_with_observation(tmp_path):
    """Visible fields entered != verified screenshot, complete capture or Reserve HP."""
    script = r"""
const assert=require('node:assert/strict');
const M=require(process.argv[2]);
const c=M.create('synthetic','naval-small'),r80=c.rounds[0];
r80.number=80;
assert.deepEqual(M.roundEntrySummary(r80),{code:'EMPTY',enteredSlots:0,pendingSlots:0,reserveRows:0});
r80.source='有備註不代表有觀測值';
assert.equal(M.roundEntrySummary(r80).code,'DRAFT');
const reserve=M.newReserve();reserve.unit='ram_ship';reserve.count=12;
r80.attacker.reserve.push(reserve);
assert.deepEqual(M.roundEntrySummary(r80),{code:'DRAFT',enteredSlots:0,pendingSlots:0,reserveRows:1});
const visible=M.newSlot('first',1);visible.unit='ram_ship';visible.wave='a';
r80.attacker.slots.push(visible);
assert.deepEqual(M.roundEntrySummary(r80),{code:'DRAFT',enteredSlots:0,pendingSlots:1,reserveRows:1});
visible.count=0; // Zero is entered, not missing; HP is still missing.
assert.equal(M.roundEntrySummary(r80).code,'DRAFT');
visible.hp=0;
assert.deepEqual(M.roundEntrySummary(r80),{code:'FIELDS_ENTERED',enteredSlots:1,pendingSlots:0,reserveRows:1});
const broken=M.newSlot('flank',2);broken.hp=77; // No unit label: never count as a visible entry.
r80.defender.slots.push(broken);
assert.deepEqual(M.roundEntrySummary(r80),{code:'PARTIAL',enteredSlots:1,pendingSlots:1,reserveRows:1});
broken.unit='steam_ram';broken.count=4;
assert.equal(M.roundEntrySummary(r80).code,'FIELDS_ENTERED');
const r81=M.newRound(81);c.rounds.push(r81);
M.reuseEarlierSlotLabels(c,r81.id);
assert.deepEqual(M.roundEntrySummary(r81),{code:'DRAFT',enteredSlots:0,pendingSlots:2,reserveRows:0});
assert.equal(M.roundEntrySummary(r80).enteredSlots,2);
const before=JSON.stringify(c);
assert.deepEqual(M.validateCase(c),[]);
assert.equal(M.importCase(M.exportCase(c)).rounds.length,2);
assert.equal(JSON.stringify(c),before,'progress must not persist or mutate case data');
assert.throws(()=>M.roundEntrySummary({}),/截錄回合資料/);
"""
    js=tmp_path / "round_progress.cjs"
    js.write_text(script,encoding="utf-8")
    result=subprocess.run(["node",str(js),str(ROOT / "battle-cases-model.js")],
                          capture_output=True,text=True,check=False)
    assert result.returncode==0,result.stderr


def test_round_entry_progress_ui_has_clear_non_verified_labels_and_parity():
    html=(ROOT / "battle-cases.html").read_text(encoding="utf-8")
    assert 'id="roundEntryStatus"' in html
    assert 'data-entry-status="'+ "'" in html
    assert 'aria-label="R' in html
    assert "M.roundEntrySummary(x)" in html and "M.roundEntrySummary(r)" in html
    assert "此進度僅代表手動輸入" in html
    assert html == (ROOT / "public/battle-cases.html").read_text(encoding="utf-8")


@pytest.mark.skipif(shutil.which("node") is None, reason="Node required for conservative round comparison contract")
def test_round_compare_nearest_captured_physical_slots_and_provenance(tmp_path):
    """Only typed visible fields; no casualty, healing, Reserve or source authenticity inference."""
    script=r"""
const assert=require('node:assert/strict');
const M=require(process.argv[2]);
const c=M.create('synthetic','naval-small');
const r80=c.rounds[0];r80.number=80;
const s=M.newSlot('first',1);Object.assign(s,{unit:'ram_ship',wave:'a',count:12,hp:83,deaths:4});
r80.attacker.slots.push(s);
const reserve=M.newReserve();reserve.unit='ram_ship';reserve.count=7;r80.attacker.reserve.push(reserve);
const r82=M.newRound(82),r81=M.newRound(81);
c.rounds.push(r82,r81); // out-of-order JSON array
const t=M.newSlot('first',1);Object.assign(t,{unit:'ram_ship',wave:'a',count:10,hp:72,deaths:0});
r81.attacker.slots.push(t);
const extra=M.newSlot('second',2);Object.assign(extra,{unit:'balloon_carrier',wave:'x',count:2,hp:100});
r81.defender.slots.push(extra);
assert.equal(M.compareCapturedRounds(c,r80.id).sourceRound,null);
let d=M.compareCapturedRounds(c,r81.id);
assert.equal(d.sourceRound,80);
assert.equal(d.targetRound,81);
assert.equal(d.rows.length,2);
assert.deepEqual(d.rows[0],{
 side:'attacker',line:'first',pos:1,code:'FIELDS_COMPARABLE',
 prior:{unit:'ram_ship',wave:'a',count:12,hp:83},
 current:{unit:'ram_ship',wave:'a',count:10,hp:72},countDelta:-2,hpPointDelta:-11
});
assert.equal(d.rows[1].code,'ONE_SIDED');
assert.equal(d.rows[1].countDelta,null);
assert.equal(d.rows.some(x=>x.prior?.hp===100),false,'Reserve never used');
M.reuseEarlierSlotLabels(c,r82.id); // label-only from R81
d=M.compareCapturedRounds(c,r82.id);
assert.equal(d.sourceRound,81);
assert.equal(d.rows.every(x=>x.code==='INCOMPLETE'),true);
assert.equal(d.rows.every(x=>x.countDelta===null&&x.hpPointDelta===null),true);
r82.attacker.slots[0].count=0;r82.attacker.slots[0].hp=0;
d=M.compareCapturedRounds(c,r82.id);
assert.equal(d.rows.find(x=>x.side==='attacker').code,'FIELDS_COMPARABLE');
assert.equal(d.rows.find(x=>x.side==='attacker').countDelta,-10);
assert.equal(d.rows.find(x=>x.side==='attacker').hpPointDelta,-72);
r82.phase='round_prefire';
assert.equal(M.compareCapturedRounds(c,r82.id).rows[0].code,'PHASE_MISMATCH');
r82.phase='round_end';
r82.attacker.slots[0].wave='changed';
assert.equal(M.compareCapturedRounds(c,r82.id).rows[0].code,'LABEL_CHANGED');
r82.attacker.slots[0].wave='a';r82.attacker.slots[0].hp=null;
assert.equal(M.compareCapturedRounds(c,r82.id).rows[0].code,'INCOMPLETE');
const r50=M.newRound(50);c.rounds.push(r50);
assert.equal(M.compareCapturedRounds(c,r80.id).sourceRound,50);
const backup=M.exportCase(c);
assert.equal(M.importCase(backup).rounds.length,4);
assert.deepEqual(M.validateCase(c),[]);
const prior=JSON.stringify(c);
M.compareCapturedRounds(c,r82.id);
assert.equal(JSON.stringify(c),prior,'read-only comparison may not mutate case');
assert.throws(()=>M.compareCapturedRounds(c,'missing'),/不存在/);
"""
    js=tmp_path/"compare_rounds.cjs"
    js.write_text(script,encoding="utf-8")
    result=subprocess.run(["node",str(js),str(ROOT/"battle-cases-model.js")],
                          capture_output=True,text=True,check=False)
    assert result.returncode==0,result.stderr


def test_round_comparison_panel_is_read_only_escaped_and_static_parity():
    html=(ROOT/"battle-cases.html").read_text(encoding="utf-8")
    assert 'id="roundComparison"' in html
    assert 'id="roundComparisonContent"' in html
    assert 'M.compareCapturedRounds(c,r.id)' in html
    assert '兵數差≠死亡數' in html and 'Reserve HP 不可從戰報觀測' in html
    assert 'esc((s.unit||' in html and 'esc(compareReason[x.code])' in html
    assert html == (ROOT/"public/battle-cases.html").read_text(encoding="utf-8")
    assert (ROOT/"battle-cases-model.js").read_bytes() == (ROOT/"public/battle-cases-model.js").read_bytes()



@pytest.mark.skipif(shutil.which("node") is None, reason="Node needed for selectable round comparison")
def test_explicit_earlier_comparison_source_rejects_stale_future_and_cross_case_ids(tmp_path):
    script=r"""
const assert=require('node:assert/strict');
const M=require(process.argv[2]);
const c=M.create('user transcription','naval-small');
const r50=c.rounds[0];r50.number=50;
const r80=M.newRound(80),r81=M.newRound(81),r82=M.newRound(82);
c.rounds.push(r82,r80,r81); // intentionally unsorted
const a=M.newSlot('first',1);
Object.assign(a,{unit:'ram_ship',wave:'user-label',count:7,hp:94});
r50.attacker.slots.push(a);
const b=M.newSlot('first',1);
Object.assign(b,{unit:'ram_ship',wave:'user-label',count:9,hp:83});
r80.attacker.slots.push(b);
const d=M.newSlot('first',1);
Object.assign(d,{unit:'ram_ship',wave:'user-label',count:8,hp:76});
r81.attacker.slots.push(d);
assert.equal(M.compareCapturedRounds(c,r81.id).sourceRound,80,'legacy nearest earlier');
assert.equal(M.compareCapturedRounds(c,r81.id,null).sourceRound,80);
const selected=M.compareCapturedRounds(c,r81.id,r50.id);
assert.equal(selected.sourceRound,50);
assert.equal(selected.rows.length,1);
assert.equal(selected.rows[0].countDelta,1);
assert.equal(selected.rows[0].hpPointDelta,-18);
assert.equal(M.compareCapturedRounds(c,r82.id,r50.id).sourceRound,50);
assert.equal(M.compareCapturedRounds(c,r50.id).sourceRound,null);
assert.throws(()=>M.compareCapturedRounds(c,r50.id,r80.id),/較早/);
assert.throws(()=>M.compareCapturedRounds(c,r81.id,r81.id),/較早/);
assert.throws(()=>M.compareCapturedRounds(c,r81.id,r82.id),/較早/);
assert.throws(()=>M.compareCapturedRounds(c,r81.id,'missing'),/較早/);
const other=M.create('another case','naval-small');
assert.throws(()=>M.compareCapturedRounds(c,r81.id,other.rounds[0].id),/較早/);
const before=JSON.stringify(c);
M.compareCapturedRounds(c,r81.id,r50.id);
assert.equal(JSON.stringify(c),before,'comparison must not mutate case or add metadata');
assert.deepEqual(M.validateCase(c),[]);
assert.deepEqual(M.importCase(M.exportCase(c)),c);
r50.phase='round_prefire'; // no arithmetic across unlike phases
assert.equal(M.compareCapturedRounds(c,r81.id,r50.id).rows[0].code,'PHASE_MISMATCH');
"""
    js=tmp_path/"selectable_round_source.cjs"
    js.write_text(script,encoding="utf-8")
    result=subprocess.run(["node",str(js),str(ROOT/"battle-cases-model.js")],
                          capture_output=True,text=True,check=False)
    assert result.returncode==0,result.stderr


def test_compare_source_ui_is_an_ephemeral_safe_selector():
    html=(ROOT/"battle-cases.html").read_text(encoding="utf-8")
    assert 'id="comparisonSource"' in html
    assert "comparisonCaseId!==c.id||comparisonTargetId!==r.id" in html
    assert "comparisonSourceId=earlier[0]?.id||null" in html
    assert "M.compareCapturedRounds(c,r.id,comparisonSourceId)" in html
    assert "select.disabled=!earlier.length" in html
    assert "renderRoundComparison(c,r); // Strictly read-only; no mutate/persist." in html
    assert "回合編號相隔 " in html
    assert html == (ROOT/"public/battle-cases.html").read_text(encoding="utf-8")
    assert (ROOT/"battle-cases-model.js").read_bytes() == (ROOT/"public/battle-cases-model.js").read_bytes()


def test_draft_label_ui_is_visible_and_public_page_stays_identical():
    html = (ROOT / "battle-cases.html").read_text(encoding="utf-8")
    assert 'id="reuseEarlierLabels"' in html
    assert "M.reuseEarlierSlotLabels(c,r.id)" in html
    assert "reuseEarlierLabels','removeRound" in html
    assert "HP 未填（非觀測草稿）" in html
    assert "不複製兵量、HP、死亡" in html
    assert html == (ROOT / "public/battle-cases.html").read_text(encoding="utf-8")


@pytest.mark.skipif(shutil.which("node") is None, reason="Node required for JSON backup round-trip")
def test_large_case_compact_export_utf8_backup_round_trip(tmp_path):
    """Codex P2: an exported valid 1.5 MB+ case must restore on a second machine."""
    js = tmp_path / "large_backup.cjs"
    js.write_text(r"""
const assert=require('node:assert/strict');
const M=require(process.argv[2]);
const {Blob}=require('node:buffer');
let c=M.create('大型案例（原始戰報）','naval-small');
const evidence='多回合獨立精算依據及資料來源：'+
  '本資料為外部計算，並非遊戲戰報直接顯示後備血量。'.repeat(60);
const calculation=evidence.slice(0,1300);
assert.equal(calculation.length,1300);
for(let i=0;i<5;i++){
  const round=i?M.newRound(80+i):c.rounds[0];
  round.number=80+i;
  if(i)c.rounds.push(round);
  const slot=M.newSlot('first',1);
  Object.assign(slot,{unit:'ram_ship',count:40,hp:95});
  round.attacker.slots.push(slot);
  for(const side of M.SIDES){
    for(let j=0;j<100;j++){
      const rv=M.newReserve();
      Object.assign(rv,{unit:'balloon_carrier',count:j+1,source:'calculated',
                        hp:73,calculation});
      round[side].reserve.push(rv);
    }
  }
}
assert.deepEqual(M.validateCase(c),[]);
const compact=JSON.stringify(c);
const pretty=JSON.stringify(c,null,2)+'\n';
assert(new Blob([pretty]).size>1_500_000,'fixture must reproduce old failure');
assert(new Blob([compact]).size>1_500_000,
  'include a legitimate large file, not only pretty-print growth');
const exported=M.exportCase(c);
assert.equal(exported,JSON.stringify(c)+'\n');
assert(new Blob([exported]).size<=M.MAX_JSON_BYTES);
const restored=M.importCase(exported);
assert.deepEqual(restored,c);
assert.deepEqual(M.importCase(pretty),c);
assert(M.importCase(exported).rounds[0].attacker.reserve[0].source==='calculated');
assert(M.importCase(exported).rounds[0].attacker.reserve[0].hp===73);
// Byte (not UTF-16 code-unit) limit: raw input over guard rejects even if parsable.
const over=M.MAX_JSON_BYTES+1;
const oversized='中'.repeat(Math.ceil(over/3));
assert(oversized.length<M.MAX_JSON_BYTES);
assert.throws(()=>M.importCase(oversized),/64 MiB/);
// A valid but absurdly large export must fail explicitly rather than yield an
// advertised backup that the import path will later reject.
assert.equal(M.MAX_JSON_BYTES,64*1024*1024);
""", encoding="utf-8")
    result = subprocess.run(["node", str(js), str(ROOT / "battle-cases-model.js")],
                            capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr


def test_export_and_import_share_one_json_byte_limit_and_ui_route():
    html = (ROOT / "battle-cases.html").read_text(encoding="utf-8")
    model = (ROOT / "battle-cases-model.js").read_text(encoding="utf-8")
    assert "const blob=new Blob([M.exportCase(c,fields)]" in html
    assert "if(f.size>M.MAX_JSON_BYTES)" in html
    assert "function checkJsonSize(s)" in model
    assert "checkJsonSize(serialized)" in model
    assert "checkJsonSize(s)" in model
    assert 'JSON.stringify(c,null,2)' not in html
    assert "1500000" not in html and "1500000" not in model
    assert html == (ROOT / "public/battle-cases.html").read_text(encoding="utf-8")
    assert model == (ROOT / "public/battle-cases-model.js").read_text(encoding="utf-8")
