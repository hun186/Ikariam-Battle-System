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
    blocks = re.findall(r"<script(?:\s[^>]*)?>([\s\S]*?)</script>", html)
    assert len(blocks) == 1
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
let a=c.rounds[0].attacker;
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
assert.equal(M.readiness(c).ready,false); // calculated R90 no longer first; R50 confirmed
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
