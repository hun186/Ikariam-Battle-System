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
