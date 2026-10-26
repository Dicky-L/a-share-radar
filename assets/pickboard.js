/* Stock picks are the first-class product. Only records explicitly extracted from reports.
   No synthetic buy signals, stop prices, holdings, or backfilled returns. */
(()=>{
"use strict";
const FILE="./reports/candidates.json";
const make=(tag,cls,text)=>{
 const node=document.createElement(tag);
 if(cls)node.className=cls;
 if(text!=null)node.textContent=String(text);
 return node;
};
const validDate=x=>/^\d{4}-\d{2}-\d{2}$/.test(x||"");
const rank=p=>({A:0,B:1,C:2})[p]??3;
let host,body,selection=null,data=null,loading=null,renderToken=0;
const reportLink=d=>"?date="+encodeURIComponent(d);
function button(text,click){
 const b=make("button","",text);
 b.type="button";b.addEventListener("click",click);return b;
}
function notice(text){
 return make("div","pick-empty",text);
}
function field(label,text,mark){
 const box=make("div","pick-field"+(text?"":" missing")+(mark?" pick-entry-check":""));
 box.append(make("label","",label),make("p","",text||"原报告未单独记录；不能据此确定买卖条件"));
 return box;
}
function stockTimeline(card,code){
 const history=(data?.stocks||[]).find(x=>x.code===code);
 if(!history?.observations?.length)return;
 const el=make("div","pick-timeline");el.hidden=true;
 el.append(make("strong","","本股在已归档表格中的历次记录（不是实盘交易流水）"));
 for(const item of history.observations.slice().sort((a,b)=>a.date.localeCompare(b.date))){
   const row=make("div","pick-historyline");
   const link=make("a","",item.date);link.href=reportLink(item.date);
   const status=item.role==="historical_review"?"复盘记录":(item.pool?item.pool+"池":"观察");
   const tail=item.report_status==="summary"?"历史摘要":"原文档案";
   row.append(link,make("span","",status),make("span","",tail));
   el.append(row);
 }
 card.append(el);
 const toggle=button("历次观察记录",()=>{
   el.hidden=!el.hidden;toggle.textContent=el.hidden?"历次观察记录":"收起历次记录";
 });
 return toggle;
}
function stockCard(rec){
 const card=make("article","pick-card");
 const head=make("div","pick-card-head");
 const title=make("div");
 title.append(make("div","pick-name",rec.name),make("span","pick-code",rec.code));
 head.append(title,make("span","pick-pool pool-"+(rec.pool||"U"),rec.pool?rec.pool+" 池":"未注明池别"));
 card.append(head);
 card.append(field("① 入选逻辑 / 观察依据",rec.reason,true));
 card.append(field("② 下一交易日买入验证",rec.entry_trigger));
 card.append(field("③ 失效与止损条件",rec.invalidation));
 card.append(field("④ 卖出与利润保护",rec.exit_plan));
 if(rec.supplement_source){
   card.append(make("p","pick-provenance","以上补充条件源自先前推送记录的可检索摘要，不是已保存的逐字完整原报告；请按当期日期理解，非当前买卖建议。"));
 }
 if(rec.no_chase)card.append(field("追高约束",rec.no_chase));
 if(rec.risk)card.append(field("风险与拥挤度",rec.risk));
 const links=make("div","pick-links");
 const original=make("a","","阅读对应日报原文");
 original.href=reportLink(rec.date);
 links.append(original);
 const score=make("a","","追踪推荐后的真实走势 ↗");
 score.href="./performance.html?code="+encodeURIComponent(rec.code)+"&date="+encodeURIComponent(rec.date);
 links.append(score);
 const timeline=stockTimeline(card,rec.code);
 if(timeline)links.append(timeline);
 card.insertBefore(links,card.lastElementChild?.classList.contains("pick-timeline")?card.lastElementChild:null);
 return card;
}
function group(rows,title,subtitle){
 if(!rows.length)return null;
 const wrapper=make("section","pickgroup");
 const h=make("h4","",title);
 h.append(make("span","pickgroup-sub",subtitle));
 wrapper.append(h);
 const grid=make("div","pickcards");
 for(const r of rows)grid.append(stockCard(r));
 wrapper.append(grid);
 return wrapper;
}
function showCurrent(){
 if(!selection || !body)return;
 const rows=(data?.records||[]).filter(r=>r.date===selection.date);
 body.replaceChildren();
 const watched=rows.filter(r=>r.role==="watchlist").sort((a,b)=>rank(a.pool)-rank(b.pool));
 const review=rows.filter(r=>r.role==="historical_review");
 const head=make("div","pick-header");
 const intro=make("div");
 intro.append(make("div","pick-eyebrow","STOCK PICKING FIRST · 选股主线"));
 intro.append(make("h3","","本期选股观察与卖出计划"));
 intro.append(make("p","pick-lead","优先回答：选哪些股票、为何入选、什么条件才能买、何时应当退出。市场资金图用于核验，不替代交易计划。"));
 const count=make("div","pick-count");
 count.append(make("strong","",watched.length),make("small","","只明确入选观察表的股票"));
 head.append(intro,count);body.append(head);
 if(rows.some(r=>r.report_type==="historical_reconstruction")){
   body.append(make("div","pick-notice",
     "来源校验：这是后来按历史截面补写的研究方案，并不是该日期18:00真正推送的股票名单。可用于研究和后续观察，但不可计入当日原始推荐胜率。"));
 }
 const performance=make("div","pick-links");
 const monthly=make("a","","按月份查看全部候选与卖出计划 →");
 monthly.href="./monthly.html";
 performance.append(monthly);
 const perf=make("a","","查看全部股票的推荐兑现与走势总览 →");
 perf.href="./performance.html";
 performance.append(perf);body.append(performance);
 body.append(make("div","pick-meta","归档发布日期："+selection.date+"　·　"+(rows.some(r=>r.report_type==="historical_reconstruction")?"来源：事后历史截面重建（非当天实际推送）":selection.status==="summary"?"来源：历史摘要（不是原始完整推送）":"来源：当期已归档原文")));
 body.append(make("div","pick-notice",
   "阅读提示：所有股票均为当期观察记录，非本人真实持仓，也不表示现在仍可买入。条件缺失就展示缺失，不补编买点、止损或盈利回测。"));
 if(watched.length){
   const buckets=[
     [watched.filter(x=>x.pool==="A"),"A池 · 条件相对充分","仍需按当期价格与市场环境重新核验"],
     [watched.filter(x=>x.pool==="B"),"B池 · 等待确认","未触发条件前不视作已买入"],
     [watched.filter(x=>x.pool==="C"),"C池 · 失效/拥挤","保留风险及淘汰记录"],
     [watched.filter(x=>!x.pool),"未标明池别","以原文为准，不强制归类"],
   ];
   const bars=make("div","pick-split");
   for(const p of ["A","B","C"]){
     const chip=make("div","pick-chip");chip.append(make("strong","",watched.filter(x=>x.pool===p).length),make("span","",p+"池 · 已识别记录"));bars.append(chip);
   }
   body.append(bars);
   for(const [groupRows,title,description] of buckets){const el=group(groupRows,title,description);if(el)body.append(el)}
 }else body.append(notice("本篇归档尚无可直接解析的当期观察候选表。可能是报告使用段落、当前存档只是摘要，或当期没有新候选。请以本篇原始文字为准，不能把“未解析到”理解成“当日没有推荐”。"));
 if(review.length){
   const g=group(review,"历史验证与复盘记录","不是新一轮买入推荐");
   if(g)body.append(g);
 }
 const divider=make("div","pick-search");
 const input=make("input");input.placeholder="查股票名称或代码，查看跨日报记录";
 input.type="search";input.setAttribute("aria-label","跨日报检索股票");
 const clear=button("清除",()=>{input.value="";runSearch()});
 divider.append(input,clear);body.append(divider);
 const matches=make("div","pick-search-result","输入股票名称或6位代码，查看历史归档中是否出现过。");
 const results=make("div","pick-history-results");body.append(matches,results);
 const runSearch=()=>{
   const q=input.value.trim().toLowerCase();
   results.replaceChildren();
   if(!q){matches.textContent="搜索只查询已归档股票记录，不进行实时选股。";return}
   const matched=(data?.stocks||[]).filter(x=>(x.name+x.code).toLowerCase().includes(q)).slice(0,20);
   matches.textContent=matched.length?"查询到 "+matched.length+" 只已归档股票（最多展示20只）":"已归档表格中没有匹配记录，不代表股票不存在。";
   for(const stock of matched){
     const line=make("div");
     line.append(make("strong","",stock.name+" ("+stock.code+")："));
     for(const obs of stock.observations){
       const a=make("a","",obs.date+" "+(obs.role==="historical_review"?"复盘":(obs.pool||"观察")));
       a.href=reportLink(obs.date);line.append(a,document.createTextNode("  "));
     }
     results.append(line);
   }
 };
 input.oninput=runSearch;
 body.append(make("p","pick-foot","归档数据只代表报告当时写过什么；没有真实成交记录、后续交易日价量及执行信息时，不能把候选股出现次数当成策略胜率。完整的次日买入触发、无效位和卖出条件应从未来正式日报中保留并结构化。"));
}
async function load(){
 if(data)return data;
 if(loading)return loading;
 loading=(async()=>{
   const response=await fetch(FILE+"?v="+Date.now(),{cache:"no-store"});
   if(!response.ok)throw Error("候选索引 HTTP "+response.status);
   const object=await response.json();
   if(object.schema_version!==1||!Array.isArray(object.records)||!Array.isArray(object.stocks))throw Error("候选索引结构有误");
   for(const rec of object.records){
     if(!validDate(rec.date)||!/(?:60|00|30)\d{4}/.test(rec.code||"")||!rec.name||
       !["watchlist","historical_review"].includes(rec.role))throw Error("候选索引含不合规记录");
   }
   data=object;return data;
 })();
 try{return await loading}finally{loading=null}
}
async function render(report){
 if(!host||!report)return;
 const token=++renderToken;
 selection={date:report.date,status:report.status};
 body.replaceChildren(notice("读取当期股票观察和历史复盘记录…"));
 try{await load();if(token!==renderToken)return;showCurrent()}
 catch(e){if(token!==renderToken)return;body.replaceChildren(notice("选股档案暂时无法加载："+e.message+"。请继续阅读下方报告原文。"))}
}
function setup(){
 const reader=document.querySelector(".reader"),content=document.getElementById("content");
 if(!reader||!content)return;
 host=make("section","pickboard");host.setAttribute("aria-label","本期选股观察记录");
 const explainer=make("div");explainer.dataset.poolGuide="";host.append(explainer);
 body=make("div","pickbody");host.append(body);
 window.RadarPoolGuide?.mount?.(explainer);
 const market=reader.querySelector(".market-fold");
 if(market)reader.insertBefore(host,market);else reader.insertBefore(host,reader.querySelector(".radar-viz")||content);
 if(window.RadarCurrentReport)render(window.RadarCurrentReport);
}
window.RadarPickBoard={render};
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",setup,{once:true});else setup();
})();