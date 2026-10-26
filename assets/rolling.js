/* Every archived stock recommendation remains in the ongoing watchboard.
   A candidate is NOT a position, an executable trade, or a live buy recommendation. */
(()=>{
"use strict";
const $=id=>document.getElementById(id);
const txt=(tag,cls,str)=>{const e=document.createElement(tag);if(cls)e.className=cls;if(str!==undefined)e.textContent=str==null?"":String(str);return e};
const price=n=>typeof n==="number"&&Number.isFinite(n)?n.toFixed(2):"待核";
const pct=n=>typeof n==="number"&&Number.isFinite(n)?(n>0?"+":"")+n.toFixed(2)+"%":"待观察";
const poolRank={A:0,B:1,C:2};
let items=[],showAll=false,keyword="";
const reportUrl=d=>"?date="+encodeURIComponent(d);
function addField(root,label,value){
 const dt=txt("dt","",label),dd=txt("dd",value?"":"rolling-missing",value||"原报告未记录，尚不可执行");
 root.append(dt,dd);
}
function getOutcome(item,byKey){
 const rec=byKey.get(item.date+"|"+item.code);
 if(!rec)return null;
 const last=(rec.observations||[]).filter(x=>typeof x.close==="number"&&x.close>0&&typeof x.return_pct==="number").at(-1);
 if(last)return {asof:last.date,close:last.close,change:last.return_pct,reference:rec.reference_close,reference_date:rec.reference_date,source:"后续交易日收盘观察"};
 if(typeof rec.reference_close==="number")return {asof:rec.reference_date,close:rec.reference_close,change:0,reference:rec.reference_close,reference_date:rec.reference_date,source:"当期基准收盘（尚无后续验证）"};
 return null;
}
function groupByStock(records){
 const by=new Map();
 for(const rec of records){
   if(!rec||!/^(?:60|00|30)\d{4}$/.test(rec.code||"")||!/^\d{4}-\d{2}-\d{2}$/.test(rec.date||""))continue;
   const old=by.get(rec.code)||{code:rec.code,observations:[],picks:[]};
   old.observations.push(rec);
   if(rec.role==="watchlist")old.picks.push(rec);
   by.set(rec.code,old);
 }
 return [...by.values()].filter(r=>r.picks.length).map(group=>{
   group.picks.sort((a,b)=>a.date.localeCompare(b.date));
   group.observations.sort((a,b)=>a.date.localeCompare(b.date));
   group.latest=group.picks.at(-1);
   group.lastMention=group.observations.at(-1);
   return group;
 }).sort((a,b)=>b.latest.date.localeCompare(a.latest.date)||
   (poolRank[a.latest.pool]??3)-(poolRank[b.latest.pool]??3)||a.code.localeCompare(b.code));
}
function card(group,outcomes,latestMarket){
 const rec=group.latest,observed=getOutcome(rec,outcomes);
 const elem=txt("article","rolling-card");
 const head=txt("div","rolling-card-title");
 const name=txt("div");name.append(txt("strong","",rec.name),txt("small","",rec.code+" · 最近一次当期观察 "+rec.date));
 const p=rec.pool||"U";
 const chip=txt("span","rolling-level pool-"+p,p==="U"?"池别未核":p+"池 · 历史记录");
 head.append(name,chip);elem.append(head);
 const movement=txt("div","rolling-price");
 const pbox=txt("div");
 pbox.append(txt("b","",observed?price(observed.close)+"元":"暂无可核收盘价"));
 pbox.append(txt("small","",observed?"行情截至 "+observed.asof+" · "+observed.source:"没有可核验的价格记录"));
 const growth=txt("div");
 growth.append(txt("em",observed?(observed.change>=0?"positive":"negative"):"",observed?pct(observed.change):"待观察"));
 growth.append(txt("small","","较该次观察的收盘基准，非实盘盈利"));
 movement.append(pbox,growth);elem.append(movement);
 const fields=txt("div","rolling-fields");const dl=txt("dl");
 addField(dl,"原始入选理由",rec.reason);
 addField(dl,"买入验证条件",rec.entry_trigger);
 addField(dl,"结构失效/卖出计划",[rec.invalidation,rec.exit_plan].filter(Boolean).join("；"));
 fields.append(dl);elem.append(fields);
 const status=txt("p","rolling-foot");
 status.textContent="档案共 "+group.picks.length+" 次当期观察"+
   (group.lastMention.role==="historical_review"?"；后续有复盘记录":"")+
   (rec.report_status==="summary"?"；来源为历史摘要":"；来源为归档原文")+
   (latestMarket&&observed&&observed.asof!==latestMarket?"；并非最新交易日行情":"")+
   "。未重新验证，不代表今天仍符合入场条件。";
 elem.append(status);
 const links=txt("div","rolling-links");
 const a=txt("a","","打开当期原报告");a.href=reportUrl(rec.date);
 const b=txt("a","","查看历次表现");b.href="./performance.html?code="+encodeURIComponent(rec.code);
 const c=txt("a","","本月计划");c.href="./monthly.html?month="+encodeURIComponent(rec.date.slice(0,7));
 links.append(a,b,c);elem.append(links);
 return elem;
}
function render(outcomes,marketDay){
 const grid=$("rolling-grid"),count=$("rolling-count"),toggle=$("rolling-toggle");
 if(!grid)return;
 const matches=items.filter(x=>(x.latest.name+" "+x.code).toLowerCase().includes(keyword));
 const show=showAll||keyword?matches:matches.slice(0,6);
 grid.replaceChildren(...show.map(g=>card(g,outcomes,marketDay)));
 count.textContent=items.length+"只曾入选 · "+items.reduce((n,r)=>n+r.picks.length,0)+"次当期观察";
 toggle.hidden=matches.length<=6;
 if(toggle.hidden)toggle.textContent="";
 else toggle.textContent=showAll||keyword?"收起为最近6只":"显示全部 "+matches.length+" 只";
 if(!matches.length)grid.replaceChildren(txt("div","rolling-alert","没有找到相应股票；仅索引已经归档的历史推荐。"));
}
async function init(){
 const grid=$("rolling-grid"),search=$("rolling-search"),toggle=$("rolling-toggle");
 if(!grid)return;
 toggle.onclick=()=>{showAll=!showAll;render(window.__rollingOutcomes||new Map(),window.__rollingMarketDay)};
 search.oninput=()=>{keyword=search.value.trim().toLowerCase();render(window.__rollingOutcomes||new Map(),window.__rollingMarketDay)};
 try{
   const [candidates,performance]=await Promise.all([
     fetch("./reports/candidates.json?ts="+Date.now(),{cache:"no-store"}).then(r=>{if(!r.ok)throw Error("候选报告索引HTTP "+r.status);return r.json()}),
     fetch("./reports/performance.json?ts="+Date.now(),{cache:"no-store"}).then(r=>r.ok?r.json():null).catch(()=>null)
   ]);
   if(candidates.schema_version!==1||!Array.isArray(candidates.records))throw Error("候选数据不符合已发布格式");
   items=groupByStock(candidates.records);
   const outcomes=new Map();
   if(performance?.schema_version===1&&Array.isArray(performance.records)){
     for(const r of performance.records){if(r.date&&r.code)outcomes.set(r.date+"|"+r.code,r)}
   }
   window.__rollingOutcomes=outcomes;
   window.__rollingMarketDay=performance?.market_dates?.at(-1)||null;
   if(!items.length){grid.replaceChildren(txt("div","rolling-alert","暂无可确认的历史当期候选。请以已发布日报原文为准。"));count.textContent="0只";return}
   render(outcomes,window.__rollingMarketDay);
   $("rolling-note").textContent=outcomes.size?
      "历史名单均保留；收盘变化只核验选股方向，不代表可成交收益。最新已核验行情："+(window.__rollingMarketDay||"待核")+"；每只股票必须重新检查当日触发、风险与失效。":
      "历史名单可查，但后续行情绩效索引暂不可用：不显示估算收益。每只股票的观察条件均以原始日期为准。";
 }catch(e){
   count.textContent="数据尚未就绪";
   grid.replaceChildren(txt("div","rolling-alert","无法核对历史推荐："+e.message+"。可点击“本月选股计划”查看已发布日报。"));
 }
}
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",init,{once:true});else init();
})();