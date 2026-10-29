/* Daily report template v1.
   Renders fixed sections from already-published Markdown WITHOUT replacing
   original evidence. Missing sections display explicit placeholders.
   Extend LAYOUT below to evolve the template; never fabricate old content. */
(()=>{
"use strict";
const VERSION="2026.10-v1.3";
const LAYOUT=[
 {key:"selection",label:"本期选股结论",hint:"A/B/C池、方向、是否允许等待买入",rules:["选股结论","今日结论","本期结论","总体结论"]},
 {key:"market",label:"全市场资金总览",hint:"指数、两日成交额、涨跌家数与市场广度",rules:["全市场数据","市场资金总览","市场环境与风险","市场环境","市场概况","市场资金","市场总览"]},
 {key:"industry",label:"10个申万一级行业双日对照",hint:"同口径前日/当日主力净额、净额变化与方向",rules:["10个申万一级行业双日对照","申万一级行业主力净流向","申万一级行业","行业资金双日"]},
 {key:"funds",label:"资金关注度与产业解读",hint:"净额改善/转弱、板块主线、拥挤与催化",rules:["资金关注度与产业解读","资金关注度变化","资金关注度","资金流向解读","资金与板块变化","产业线索","行业资金"]},
 {key:"plan",label:"本期选股观察与卖出计划",hint:"逐股入选依据、确认价、失效位、分批退出",rules:["本期选股观察与卖出计划","本期选股","选股观察与卖出","观察与卖出管理","观察候选","候选池","本期B池"]},
 {key:"review",label:"前期推荐与失败复盘",hint:"历史冻结样本、条件是否触发、D+1/D+3与失败记录",rules:["日前推荐股票复盘","日前推荐","前期推荐","历史冻结批次","历史样本复盘","历史复盘","候选跟踪","回测复盘","历史观察"]},
 {key:"risk",label:"仓位与卖出风险管理",hint:"未买入/实际持仓区别、T+1、跳空、费用及失效",rules:["卖出与风险管理","风险和退出","风险管理","风控与仓位","交易风险"]},
 {key:"next",label:"下一交易日验证清单",hint:"需再次核验的触发条件、资金方向与退出事件",rules:["下一个交易日","下一交易日","下日验证","明日观察","明日计划","后续验证"]},
 {key:"sources",label:"数据口径、来源与局限",hint:"真实数据口径、原始链接、缺项与报告版本",rules:["来源与归档完整性","数据来源与口径","数据口径","来源与引用","来源及归档","数据来源"]}
];
const $=id=>document.getElementById(id);
const el=(tag,cls,value)=>{let x=document.createElement(tag);if(cls)x.className=cls;if(value!==undefined)x.textContent=value;return x};
const norm=s=>String(s||"").replace(/^[一二三四五六七八九十0-9]+\s*[、.．·-]\s*/,"").replace(/[：:|｜\s（）()·【】]+/g,"").toLowerCase();
function match(name){
 const clean=norm(name);
 for(const group of LAYOUT){if(group.rules.some(rule=>clean.includes(norm(rule))))return group.key}
 return null;
}
function takeSegments(content){
 const headings=[...content.children].filter(x=>x.tagName==="H2");
 if(!headings.length)return {lead:[...content.children],segments:[]};
 const lead=[],segments=[];let active=null;
 for(const node of [...content.children]){
   if(node.tagName==="H2"){active={heading:node,title:node.textContent.trim(),nodes:[]};segments.push(active)}
   else if(active)active.nodes.push(node);
   else lead.push(node);
 }
 return {lead,segments};
}
/* Accept either "10月27日主力净额" or "27日净额".
   Other columns such as 净额变化 / 净流强度 never count as a dated money value. */
function datedNetColumns(table){
 const heads=[...table.querySelectorAll("thead th")].map(n=>n.textContent.trim());
 const indices=heads.map((name,i)=>(
   i>0 && /净额/.test(name) && !/(变化|差额|强度|占比|环比|买入|卖出)/.test(name) &&
   (/(\d{1,2}月)?\d{1,2}日/.test(name)||/前日|当日|上日|昨日|今日/.test(name))?i:-1
 )).filter(x=>x>=0);
 return {heads,indices:indices.slice(0,2)};
}
function sectorTable(slot){
 return [...slot.querySelectorAll("table")].find(table=>{
   const {heads,indices}=datedNetColumns(table);
   return heads.length>=3 && /行业/.test(heads[0]) && indices.length===2;
 });
}
function numeric(str){
 const clean=String(str||"").replace(/[,\s*]/g,"").replace(/亿元|亿|元/g,"").trim();
 return /^[+\-−]?\d+(?:\.\d+)?$/.test(clean)?Number(clean.replace("−","-")):null;
}
function formatFundDate(header,reportDate){
 const m=header.match(/(?:(\d{1,2})月)?(\d{1,2})日/);
 if(!m)return header;
 let month=m[1]?Number(m[1]):Number((reportDate||"").slice(5,7));
 const day=Number(m[2]),reportDay=Number((reportDate||"").slice(8,10));
 // Explicit report timestamps make prev-month boundaries unambiguous.
 if(!m[1] && Number.isFinite(reportDay) && day>reportDay)month=month===1?12:month-1;
 const label=month?month+"月"+day+"日":day+"日";
 return label+"主力净额";
}
function collapseLegacyEmojiChart(boxed){
 // Keep the source's original emoji illustration accessible, but do not
 // display two competing graphs. Move nodes rather than delete original text.
 const desc=boxed.nextElementSibling;
 const list=desc?.nextElementSibling;
 if(!desc||desc.tagName!=="P"||!/^红绿同刻度方向图/.test(desc.textContent.trim()))return;
 if(!list||list.tagName!=="UL"||!/[🟥🟩]/u.test(list.textContent))return;
 const details=el("details","frame-legacy-emoji");
 const summary=el("summary","","查看原报告字符图（已由精确刻度图替代）");
 desc.before(details);details.append(summary,desc,list);
}
/* Both daily source files must cover the same ENTIRE trading session.
   Differences in posting time are disclosed, never silently normalized.
   The report table is CI-verified against these canonical daily files. */
function checkFundsWindow(doc,day){
 if(doc.date!==day||doc.source_id!=="stcn_databao_sw1_mainflow"||
    doc.industry_classification!=="申万一级"||doc.unit!=="亿元"||
    !Array.isArray(doc.industries)||!doc.published_at||!doc.source_url)
   throw new Error("数据源、申万分类或单位不一致");
 const stamp=new Date(doc.published_at).getTime();
 const afterClose=new Date(day+"T15:00:00+08:00").getTime();
 const cutoff=new Date(day+"T18:00:00+08:00").getTime();
 if(!Number.isFinite(stamp)||stamp<afterClose||stamp>cutoff)
   throw new Error(day+" 资金发布日期不在15:00至18:00收盘资料窗口");
 return stamp;
}
async function verifyFundsChart(chart,reportDate,heads,indices,rows,evidence){
 if(typeof fetch!=="function"||reportDate!=="2026-10-28")return;
 const days=indices.map(i=>{
   const m=heads[i].match(/(?:(\d{1,2})月)(\d{1,2})日/);
   if(!m)throw new Error("日期表头不能核实");
   return reportDate.slice(0,4)+"-"+m[1].padStart(2,"0")+"-"+m[2].padStart(2,"0");
 });
 try{
   if(days[1]!==reportDate||days[0]>=days[1])throw new Error("前日/当日日期不一致");
   const docs=await Promise.all(days.map(async day=>{
     const res=await fetch("./data/industry-flows/"+day+".json",{cache:"no-store"});
     if(!res.ok)throw new Error(day+" 同源日级台账尚未可用");
     return res.json();
   }));
   const times=docs.map((doc,i)=>checkFundsWindow(doc,days[i]));
   if(docs[0].source_id!==docs[1].source_id||docs[0].metric!==docs[1].metric)
     throw new Error("数据商或主力资金定义不一致");
   const by=docs.map(doc=>new Map(doc.industries.map(r=>[r.name,r.net_yi])));
   for(const row of rows){
     if(by.some((m,i)=>typeof m.get(row.name)!=="number"||Math.abs(m.get(row.name)-(i?row.right:row.left))>0.005))
       throw new Error(row.name+" 主图金额与日级数据源不一致");
   }
   if(!chart.isConnected)return;
   const label=d=>Number(d.slice(5,7))+"月"+Number(d.slice(8,10))+"日";
   const hm=stamp=>new Date(stamp).toLocaleTimeString("zh-CN",{timeZone:"Asia/Shanghai",hour12:false,hour:"2-digit",minute:"2-digit"});
   evidence.textContent="";
   evidence.append(el("strong","","已核验：相同统计窗口（全天交易至15:00收盘），同一数据商与申万一级行业"));
   const info=el("span","","发布时点："+label(days[0])+" "+hm(times[0])+" / "+label(days[1])+" "+hm(times[1])+"；发布时间不同，但均为盘后全日汇总。");
   evidence.append(info);
   docs.forEach((doc,i)=>{
     const a=el("a","",label(days[i])+"原始资金日报");
     a.href=doc.source_url;a.target="_blank";a.rel="noopener noreferrer";
     evidence.append(a);
   });
   evidence.className="frame-funds-evidence verified";
   chart.dataset.sourceValidated="true";
 }catch(e){
   if(!chart.isConnected)return;
   evidence.textContent="数据口径异常："+e.message+"。暂停展示主图，避免不同供应商、统计窗口或金额混在一起；请核对原报告表格。";
   evidence.className="frame-funds-evidence alert";
   chart.dataset.sourceValidated="false";
   chart.querySelectorAll(".frame-funds-row").forEach(row=>row.remove());
 }
}

function industryGraphic(slot,reportDate){
 const table=sectorTable(slot);
 if(!table)return;
 const {heads,indices}=datedNetColumns(table);
 const trs=[...table.querySelectorAll("tbody tr")],valid=[];
 for(const tr of trs){
   const cells=[...tr.children];
   if(cells.length<=indices[1])continue;
   const left=numeric(cells[indices[0]].textContent),right=numeric(cells[indices[1]].textContent);
   if(Number.isFinite(left)&&Number.isFinite(right)){
     valid.push({name:cells[0].textContent.trim(),left,right});
   }
 }
 if(valid.length<2)return;
 if(valid.length!==10 && reportDate==="2026-10-28")return;
 const max=Math.max(1,...valid.flatMap(x=>[Math.abs(x.left),Math.abs(x.right)]));
 const graph=el("section","frame-funds");
 graph.dataset.source="dated-net-table";
 graph.dataset.scaleMaximum=max.toFixed(2);
 graph.dataset.rowCount=String(valid.length);
 graph.setAttribute("aria-label","申万一级行业双日主力资金净额对照图");
 const head=el("div","frame-funds-heading");
 head.append(el("strong","","行业资金双日方向 · 同金额刻度"),
   el("small","","单位：亿元 · 红=估算净流入 / 绿=估算净流出"));
 graph.append(head);
 const labels=indices.map(i=>formatFundDate(heads[i],reportDate));
 for(const row of valid.slice(0,10)){
   const group=el("div","frame-funds-row");
   group.append(el("strong","frame-funds-name",row.name));
   const pairs=el("div","frame-funds-pairs");
   for(const [label,value] of [[labels[0],row.left],[labels[1],row.right]]){
     const line=el("div","frame-funds-pair");
     line.append(el("span","frame-funds-day",label));
     const track=el("div","frame-funds-track");
     track.setAttribute("role","img");
     track.setAttribute("aria-label",row.name+" "+label+" "+(value>0?"+":"")+value.toFixed(2)+"亿元");
     const bar=el("span","frame-funds-bar "+(value>=0?"positive":"negative"));
     bar.style.width=(Math.abs(value)/max*50).toFixed(3)+"%";
     bar.dataset.amount=String(value);
     track.append(bar);
     line.append(track,el("span","frame-funds-amount "+(value>=0?"up":"down"),(value>0?"+":"")+value.toFixed(2)));
     pairs.append(line);
   }
   group.append(pairs);graph.append(group);
 }
 graph.append(el("p","frame-funds-note","同图统一绝对金额刻度，零线位于中央；仅比较主力净额方向，不表示成交总额或行业之间的资金转移。精确值与数据来源以原报告表格为准。"));
 const evidence=el("div","frame-funds-evidence",reportDate==="2026-10-28"?"正在交叉核对27/28日收盘资金台账…":"主力净额取自当期报告表格；数据商及发布时间请查看报告来源。");
 graph.append(evidence);
 verifyFundsChart(graph,reportDate,heads,indices,valid,evidence).catch(err=>{
   evidence.className="frame-funds-evidence alert";
   evidence.textContent="来源核对失败："+err.message;
 });
 const boxed=table.closest(".tablebox")||table;
 boxed.before(graph);
 collapseLegacyEmojiChart(boxed);
}
function render(data){
 const content=$("content"),host=$("template-overview");
 if(!content||!host)return;
 host.replaceChildren();
 if(!data||data.status==="market_only"){host.hidden=true;return}
 host.hidden=false;
 const {lead,segments}=takeSegments(content);
 if(!segments.length){host.hidden=true;return}
 const bucket=new Map(LAYOUT.map(x=>[x.key,[]])),extra=[];
 for(const section of segments){
   const key=match(section.title);
   if(key)bucket.get(key).push(section);else extra.push(section);
 }
 // The 23rd's capital-flow interpretation lives inside the industry section.
 // Label it as integrated rather than inventing a separate funding article.
 const mergedFunds=!bucket.get("funds").length && bucket.get("industry").some(section=>section.nodes.some(x=>
   x.tagName==="H3"&&/资金关注度|资金关注|资金含义|价格、成交规模和资金含义/.test(x.textContent)
 ));
 const heading=el("div","frame-overview-head");
 heading.append(el("div","frame-kicker","STANDARD DAILY REPORT · "+VERSION),
  el("h3","","每日统一报告框架"),
  el("p","","以10月23日的研究顺序为基准，保留原报告所有文字和表格。未覆盖项目只标缺口，不补造数字。"));
 host.append(heading);
 const nav=el("nav","frame-overview-grid");
 nav.setAttribute("aria-label","统一报告章节导航");
 for(let i=0;i<LAYOUT.length;i++){
   const item=LAYOUT[i],count=bucket.get(item.key).length;
   const merged=item.key==="funds"&&mergedFunds;
   const a=el("a","frame-overview-link "+(count||merged?"filled":"missing"));
   a.href="#frame-"+item.key;
   a.append(el("span","frame-overview-number",String(i+1).padStart(2,"0")),
      el("span","frame-overview-label",item.label),
      el("span","frame-overview-state",count?"已覆盖":merged?"并入行业解读":"待补"));
   nav.append(a);
 }
 host.append(nav);
 const info=el("p","frame-overview-help","栏目按统一位置呈现；每个章节仍可展开收起。历史重建与摘要不会被伪装成当期完整原文。");
 host.append(info);
 const fragment=document.createDocumentFragment();
 for(const node of lead)fragment.append(node);
 LAYOUT.forEach((item,i)=>{
   const heading=el("h2","frame-slot-heading",String(i+1).padStart(2,"0")+" · "+item.label);
   heading.id="frame-"+item.key;
   fragment.append(heading);
   const chosen=bucket.get(item.key);
   if(chosen.length){
     for(const section of chosen){
       const orig=section.heading;
       const oldTitle=section.title;
       const h3=el("h3","frame-original-title",oldTitle);
       fragment.append(h3);
       for(const node of section.nodes)fragment.append(node);
     }
   }else if(item.key==="funds"&&mergedFunds){
     fragment.append(el("p","frame-integrated","资金关注度分析已包含在上一板块的行业对照与资金含义中；原文没有重复展开。"));
   }else{
     fragment.append(el("p","frame-empty","本期原报告未单独覆盖「"+item.label+"」。"+item.hint+"——数据待核或暂无可靠原始记录，不生成推断性数字。"));
   }
 });
 if(extra.length){
   fragment.append(el("h2","frame-slot-heading","附录 · 原报告其他信息"));
   for(const section of extra){
     fragment.append(el("h3","frame-original-title",section.title));
     for(const node of section.nodes)fragment.append(node);
   }
 }
 content.replaceChildren(fragment);
 const industry=$("frame-industry");
 if(industry){
   const following=[];
   let next=industry.nextSibling;
   while(next&&next.tagName!=="H2"){following.push(next);next=next.nextSibling}
   const temp=el("div");
   for(const node of following)temp.append(node);
   // Render graphic at the top of industry section, keep original comparison table intact.
   industryGraphic(temp,data.date);
   industry.after(...[...temp.children]);
 }
}
window.RadarReportTemplate={version:VERSION,layout:LAYOUT,render,sectorColumns:datedNetColumns,industryGraphic,formatFundDate,checkFundsWindow};
})();