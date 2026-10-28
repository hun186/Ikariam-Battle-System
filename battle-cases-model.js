/* User entered battle reports: local-only v1, never official Gameforge evidence. */
(function(root,fn){const x=fn();root.ReportCases=x;if(typeof module==='object'&&module.exports)module.exports=x;})(typeof globalThis!=='undefined'?globalThis:this,function(){
'use strict';
const SCHEMA='ikariam-report-cases-v1',STORAGE='ikariam-report-cases-v1',SIDES=['attacker','defender'];
const LINES=['first','second','third','flank','balloon','anti-balloon'];
const uid=()=>Date.now().toString(36)+Math.random().toString(36).slice(2,12);
const text=(v,max=120)=>typeof v==='string'&&v.length<=max;
const num=(v,hi)=>v===null||(Number.isInteger(v)&&v>=0&&v<=hi);
const err=(s)=>{throw Error(s)};
function newRound(n=1){return {id:uid(),number:n,phase:'round_end',source:'',baseline_confirmed:{attacker:false,defender:false},attacker:{slots:[],reserve:[]},defender:{slots:[],reserve:[]}};}
function create(name='新案例',battlefield='naval-small'){const now=new Date().toISOString();return {schema:SCHEMA,id:uid(),name,battlefield,notes:'',created:now,updated:now,rounds:[newRound()]};}
function newSlot(line,pos){return {line,pos,unit:'',wave:'',count:null,hp:null,deaths:null};}
function newReserve(){return {id:uid(),unit:'',wave:'',count:null,hp:100,source:'assumed_full',calculation:''};}
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
if(!LINES.includes(slot.line)||!Number.isInteger(slot.pos)||slot.pos<1||slot.pos>100||used.has(key)||field&&(!field.lines[slot.line]||!field.lines[slot.line].physical_order.includes(slot.pos)))problems.push(prefix+' 格位位置無效／重複');
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
SIDES.forEach(side=>{
const reserve=first[side].reserve.filter(v=>v.count!==0);
if(reserve.some(v=>v.source==='assumed_full')&&!first.baseline_confirmed[side])
problems.push('截錄起點 R'+first.number+' '+side+' Reserve 預設 100% 尚未確認，不能當實測');
if(reserve.some(v=>v.source==='calculated'))problems.push('截錄起點 '+side+' 包含外部精算 Reserve HP，須獨立覆核');
if(reserve.some(v=>!v.unit||v.count===null))problems.push('截錄起點 '+side+' Reserve 數量或兵種未填');
});
return {ready:problems.length===0,code:problems.length?'REVIEW_REQUIRED':'BASELINE_USER_CONFIRMED_NOT_GAME_VERIFIED',issues:problems};
}
function importCase(s,fields){
if(typeof s!=='string'||s.length>1500000)err('匯入檔太大（上限 1.5MB）');
const data=JSON.parse(s),problems=validateCase(data,fields);
if(problems.length)err(problems.slice(0,5).join('；'));
return data;
}
return {SCHEMA,STORAGE,SIDES,LINES,create,newRound,newSlot,newReserve,validateCase,readiness,importCase,uid};
});