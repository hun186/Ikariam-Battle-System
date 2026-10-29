/* User entered battle reports: local-only v1, never official Gameforge evidence. */
(function(root,fn){const x=fn();root.ReportCases=x;if(typeof module==='object'&&module.exports)module.exports=x;})(typeof globalThis!=='undefined'?globalThis:this,function(){
'use strict';
const SCHEMA='ikariam-report-cases-v1',STORAGE='ikariam-report-cases-v1',SIDES=['attacker','defender'];
// Single byte-based limit for both export and import. Browser localStorage normally
// caps saved cases well below this guard; avoid silent non-restorable JSON backups.
const MAX_JSON_BYTES=64*1024*1024;
const LINES=['first','second','third','flank','balloon','anti-balloon'];
const uid=()=>Date.now().toString(36)+Math.random().toString(36).slice(2,12);
const text=(v,max=120)=>typeof v==='string'&&v.length<=max;
const num=(v,hi)=>v===null||(Number.isInteger(v)&&v>=0&&v<=hi);
const err=(s)=>{throw Error(s)};
function newRound(n=1){return {id:uid(),number:n,phase:'round_end',source:'',baseline_confirmed:{attacker:false,defender:false},attacker:{slots:[],reserve:[]},defender:{slots:[],reserve:[]}};}
function validName(value){if(!text(value,120)||!value.trim())err('案例名稱不可空白或超過 120 字');return value.trim();}
function physicalPositions(damageOrder){return Array.isArray(damageOrder)?damageOrder.map((_,index)=>index+1):[];}
function invalidateReserveConfirmation(round,side){if(!SIDES.includes(side)||!round||!round.baseline_confirmed)err('Reserve 回合或陣營無效');round.baseline_confirmed[side]=false;}
function create(name='新案例',battlefield='naval-small'){const now=new Date().toISOString();return {schema:SCHEMA,id:uid(),name:validName(name),battlefield,notes:'',created:now,updated:now,rounds:[newRound()]};}
function newSlot(line,pos){return {line,pos,unit:'',wave:'',count:null,hp:null,deaths:null};}
function newReserve(){return {id:uid(),unit:'',wave:'',count:null,hp:100,source:'assumed_full',calculation:''};}
// Reuse labels only. A past screenshot is NEVER evidence for a later round's
// counts, HP, deaths, Reserve quantity/HP, confirmation, or source timestamp.
function reuseEarlierSlotLabels(c,targetId){
  if(!c||!Array.isArray(c.rounds))err('案例不正確');
  const target=c.rounds.find(r=>r.id===targetId);
  if(!target)err('指定的截錄回合不存在');
  const earlier=c.rounds.filter(r=>r.number<target.number).sort((a,b)=>b.number-a.number)[0];
  if(!earlier)err('沒有更早的截錄回合可供參考');
  if(SIDES.some(side=>!target[side]||!Array.isArray(target[side].slots)||target[side].slots.length))
    err('目前回合已有格位資料，不能覆蓋');
  const staged={};
  for(const side of SIDES){
    staged[side]=earlier[side].slots.filter(s=>s.unit||s.wave).map(s=>{
      const copy=newSlot(s.line,s.pos);
      copy.unit=s.unit;copy.wave=s.wave;
      return copy;
    });
  }
  const count=SIDES.reduce((total,side)=>total+staged[side].length,0);
  if(!count)err('最近較早回合沒有兵種或 Wave 標籤可沿用');
  // Complete validation before writing either side, so refusals are atomic.
  for(const side of SIDES)target[side].slots=staged[side];
  return {sourceRound:earlier.number,copiedSlots:count};
}
// Display-only progress of manually ENTERED visible fields; neither observation
// authenticity nor every physical battlefield position can be inferred here.
function roundEntrySummary(round){
  if(!round||SIDES.some(side=>!round[side]||!Array.isArray(round[side].slots)||!Array.isArray(round[side].reserve)))
    err('截錄回合資料不正確');
  const slots=SIDES.flatMap(side=>round[side].slots);
  const entries=slots.filter(s=>s.unit||s.wave||s.count!==null||s.hp!==null||s.deaths!==null);
  const enteredSlots=entries.filter(s=>s.unit&&s.count!==null&&s.hp!==null).length;
  const pendingSlots=entries.length-enteredSlots;
  const reserveRows=SIDES.reduce((n,side)=>n+round[side].reserve.length,0);
  const code=enteredSlots?(pendingSlots?'PARTIAL':'FIELDS_ENTERED'):
    (pendingSlots||reserveRows||(round.source||'').trim()?'DRAFT':'EMPTY');
  return {code,enteredSlots,pendingSlots,reserveRows};
}
// Read-only comparison of manually entered fields at the same physical address.
// Identical user-entered unit/Wave labels cannot authenticate a continuous wave.
// sourceId null/undefined means nearest earlier captured round (legacy default).
function compareCapturedRounds(c,targetId,sourceId=null){
  const problems=validateCase(c);
  if(problems.length)err('戰報案例格式無效：'+problems[0]);
  const target=c.rounds.find(r=>r.id===targetId);
  if(!target)err('指定的截錄回合不存在');
  let prior;
  if(sourceId===null){
    prior=c.rounds.filter(r=>r.number<target.number).sort((a,b)=>b.number-a.number)[0];
  }else{
    prior=c.rounds.find(r=>r.id===sourceId);
    if(!prior||prior.number>=target.number)err('比較來源必須是本案例較早的截錄回合');
  }
  if(!prior)return {sourceRound:null,targetRound:target.number,samePhase:false,rows:[]};
  const samePhase=prior.phase===target.phase,rows=[];
  const key=s=>s.line+':'+s.pos;
  const active=s=>s.unit||s.wave||s.count!==null||s.hp!==null||s.deaths!==null;
  for(const side of SIDES){
    const oldSlots=new Map(prior[side].slots.filter(active).map(s=>[key(s),s]));
    const newSlots=new Map(target[side].slots.filter(active).map(s=>[key(s),s]));
    const addresses=[...new Set([...oldSlots.keys(),...newSlots.keys()])];
    addresses.sort((a,b)=>{
      const [la,pa]=a.split(':'),[lb,pb]=b.split(':');
      return LINES.indexOf(la)-LINES.indexOf(lb)||Number(pa)-Number(pb);
    });
    for(const addr of addresses){
      const oldSlot=oldSlots.get(addr)||null,newSlot=newSlots.get(addr)||null;
      const snapshot=s=>s?{unit:s.unit,wave:s.wave,count:s.count,hp:s.hp}:null;
      let code='ONE_SIDED',countDelta=null,hpPointDelta=null;
      if(oldSlot&&newSlot){
        if(!samePhase)code='PHASE_MISMATCH';
        else if(!oldSlot.unit||!oldSlot.wave||!newSlot.unit||!newSlot.wave||
                oldSlot.count===null||oldSlot.hp===null||
                newSlot.count===null||newSlot.hp===null)code='INCOMPLETE';
        else if(oldSlot.unit!==newSlot.unit||oldSlot.wave!==newSlot.wave)code='LABEL_CHANGED';
        else{
          code='FIELDS_COMPARABLE';
          countDelta=newSlot.count-oldSlot.count;
          hpPointDelta=newSlot.hp-oldSlot.hp;
        }
      }
      const [line,pos]=addr.split(':');
      rows.push({side,line,pos:Number(pos),code,prior:snapshot(oldSlot),current:snapshot(newSlot),countDelta,hpPointDelta});
    }
  }
  return {sourceRound:prior.number,targetRound:target.number,samePhase,rows};
}
// Research export: derivative of typed *visible* field comparisons only.
// Never encode inferred kills, healing, Reserve HP, screenshots or official truth.
// Escape spreadsheet-formula entry points in ALL user-controlled CSV text.
function exportCapturedComparisonCsv(c,targetId,sourceId=null,fields=null){
  const issues=validateCase(c,fields);
  if(issues.length)err('無法匯出比較：'+issues[0]);
  const data=compareCapturedRounds(c,targetId,sourceId);
  if(data.sourceRound===null)err('沒有較早的截錄回合，無法匯出比較');
  if(!data.rows.length)err('兩個回合沒有已輸入的可見格位，無法匯出比較');
  const prior=c.rounds.find(r=>r.number===data.sourceRound);
  const target=c.rounds.find(r=>r.number===data.targetRound);
  const headers=[
    'evidence_class','case_id','case_name','battlefield',
    'earlier_round','target_round','round_number_gap',
    'earlier_phase','target_phase','side','line','physical_position',
    'comparison_status','earlier_unit','earlier_wave','earlier_count','earlier_hp_percent',
    'target_unit','target_wave','target_count','target_hp_percent',
    'typed_count_delta','typed_hp_percentage_point_delta','interpretation'
  ];
  const csvCell=v=>{
    if(v===null||v===undefined)return '';
    if(typeof v==='number')return String(v); // validated numeric fields (including negative deltas)
    let s=String(v).replace(/[\x00-\x1f\x7f]/g,' '); // no embedded CR/LF/TAB row injection
    if(/^\s*[=+\-@]/u.test(s))s="'"+s; // spreadsheet formula injection guard
    return '"'+s.replace(/"/g,'""')+'"';
  };
  const body=data.rows.map(row=>[
    'USER_TRANSCRIPTION_UNVERIFIED',c.id,c.name,c.battlefield,
    data.sourceRound,data.targetRound,data.targetRound-data.sourceRound,
    prior.phase,target.phase,row.side,row.line,row.pos,
    row.code,row.prior?.unit??'',row.prior?.wave??'',
    row.prior?.count??null,row.prior?.hp??null,
    row.current?.unit??'',row.current?.wave??'',
    row.current?.count??null,row.current?.hp??null,
    row.countDelta,row.hpPointDelta,'TYPED_FIELDS_ONLY_NOT_COMBAT_CAUSALITY'
  ]);
  const csv='\uFEFF'+[headers,...body].map(a=>a.map(csvCell).join(',')).join('\r\n')+'\r\n';
  if(new Blob([csv]).size>MAX_JSON_BYTES)err('比較 CSV 超過 64 MiB 上限');
  return csv;
}
function validateCase(c,fields=null){
const problems=[];
if(!c||typeof c!=='object'||Array.isArray(c))return ['案例不是物件'];
const exact=(o,keys)=>o&&typeof o==='object'&&!Array.isArray(o)&&Object.keys(o).sort().join('|')===keys.slice().sort().join('|');
if(!exact(c,['schema','id','name','battlefield','notes','created','updated','rounds'])||c.schema!==SCHEMA)problems.push('案例 schema 不符');
if(!text(c.id)||!c.id||!text(c.name)||!c.name.trim()||!text(c.battlefield)||!c.battlefield||!text(c.notes,4000)||!text(c.created,80)||!text(c.updated,80))problems.push('案例欄位無效');
const field=fields?.find(f=>f.id===c.battlefield);
if(fields&&!field)problems.push('戰場類型不存在');
if(!Array.isArray(c.rounds)||c.rounds.length<1||c.rounds.length>100)return [...problems,'截錄回合必須有 1–100 筆'];
let roundNums=new Set(),roundIds=new Set();
c.rounds.forEach((round,i)=>{
const tag='第 '+(i+1)+' 筆截錄';
if(!exact(round,['id','number','phase','source','baseline_confirmed','attacker','defender'])){problems.push(tag+' 格式無效');return;}
if(!text(round.id)||!round.id||roundIds.has(round.id))problems.push(tag+' ID 無效或重複');
roundIds.add(round.id);
if(!Number.isInteger(round.number)||round.number<1||round.number>1000||roundNums.has(round.number))problems.push(tag+' 回合編號重複或超界');
roundNums.add(round.number);
if(!['round_end','round_prefire'].includes(round.phase)||!text(round.source,2500))problems.push(tag+' 時點或來源無效');
if(!exact(round.baseline_confirmed,SIDES)||SIDES.some(s=>typeof round.baseline_confirmed?.[s]!=='boolean'))problems.push(tag+' 起始 Reserve 確認無效');
SIDES.forEach(side=>{
const group=round[side],prefix=tag+' '+side;
if(!exact(group,['slots','reserve'])||!Array.isArray(group.slots)||!Array.isArray(group.reserve)||group.slots.length>180||group.reserve.length>100){problems.push(prefix+' 格位或 Reserve 格式無效');return;}
const used=new Set(),reserveIds=new Set();
group.slots.forEach((slot,j)=>{
if(!exact(slot,['line','pos','unit','wave','count','hp','deaths'])){problems.push(prefix+' 格位結構無效');return;}
const key=slot.line+':'+slot.pos;
if(!LINES.includes(slot.line)||!Number.isInteger(slot.pos)||slot.pos<1||slot.pos>100||used.has(key)||field&&(!field.lines[slot.line]||slot.pos>field.lines[slot.line].physical_order.length))problems.push(prefix+' 格位位置無效／重複');
used.add(key);
if(!text(slot.unit)||!text(slot.wave)||!num(slot.count,1000000)||!num(slot.hp,100)||!num(slot.deaths,1000000))problems.push(prefix+' 格位數量／百分比無效');
});
group.reserve.forEach((v,j)=>{
if(!exact(v,['id','unit','wave','count','hp','source','calculation'])){problems.push(prefix+' Reserve 欄位錯誤');return;}
if(!text(v.id)||!v.id||reserveIds.has(v.id))problems.push(prefix+' Reserve ID 無效／重複');
reserveIds.add(v.id);
if(!text(v.unit)||!text(v.wave)||!num(v.count,1000000)||!Number.isInteger(v.hp)||v.hp<0||v.hp>100||!text(v.calculation,1500))problems.push(prefix+' Reserve 資料無效');
if(v.source==='assumed_full'&&(v.hp!==100||v.calculation!==''))
  problems.push(prefix+' 預設 Reserve 只能是 100% 假設');
else if(v.source==='calculated'&&v.calculation.trim().length<20)
  problems.push(prefix+' 精算 Reserve HP 必須寫至少 20 字計算依據');
else if(!['assumed_full','calculated'].includes(v.source))problems.push(prefix+' Reserve 來源類型錯誤');
});
});
});
return problems.slice(0,50);
}
function readiness(c){
const problems=validateCase(c);
if(problems.length)return {ready:false,code:'INVALID',issues:problems};
const first=[...c.rounds].sort((a,b)=>a.number-b.number)[0];
const firstHasVisibleSlot=SIDES.some(side=>first[side].slots.some(slot=>slot.unit&&slot.count!==null&&slot.hp!==null));
if(!firstHasVisibleSlot)problems.push('截錄起點 R'+first.number+' 尚無具兵種、數量及可見 HP 的格位，不能把後續回合當起始證據');
SIDES.forEach(side=>{
const reserve=first[side].reserve.filter(v=>v.count!==0);
if(reserve.some(v=>v.source==='assumed_full')&&!first.baseline_confirmed[side])
problems.push('截錄起點 R'+first.number+' '+side+' Reserve 預設 100% 尚未確認，不能當實測');
if(reserve.some(v=>v.source==='calculated'))problems.push('截錄起點 '+side+' 包含外部精算 Reserve HP，須獨立覆核');
if(reserve.some(v=>!v.unit||v.count===null))problems.push('截錄起點 '+side+' Reserve 數量或兵種未填');
});
return {ready:problems.length===0,code:problems.length?'REVIEW_REQUIRED':'BASELINE_USER_CONFIRMED_NOT_GAME_VERIFIED',issues:problems};
}
function byteSize(s){return new Blob([s],{type:'application/json;charset=utf-8'}).size;}
function checkJsonSize(s){
  if(typeof s!=='string'||s.length>MAX_JSON_BYTES||byteSize(s)>MAX_JSON_BYTES)
    err('JSON 超過單一案例備份上限 64 MiB；請分拆較小案例');
}
function exportCase(c,fields){
  const problems=validateCase(c,fields);
  if(problems.length)err('案例無法匯出：'+problems.slice(0,5).join('；'));
  // Compact JSON avoids making a readable, valid source exceed its own restore limit.
  const serialized=JSON.stringify(c)+'\n';
  checkJsonSize(serialized); // Refuse to generate a file that cannot be imported.
  return serialized;
}
function importCase(s,fields){
  checkJsonSize(s);
  const data=JSON.parse(s),problems=validateCase(data,fields);
  if(problems.length)err(problems.slice(0,5).join('；'));
  return data;
}
return {SCHEMA,STORAGE,MAX_JSON_BYTES,SIDES,LINES,create,newRound,newSlot,newReserve,validateCase,readiness,exportCase,importCase,uid,validName,physicalPositions,invalidateReserveConfirmation,reuseEarlierSlotLabels,roundEntrySummary,compareCapturedRounds,exportCapturedComparisonCsv};
});