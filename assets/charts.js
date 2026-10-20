/* Evidence-first charts. The Markdown report is NEVER edited or replaced.
   All numerical market figures come from scripts/build_chart_data.py output.
   Users can view later market snapshots only after explicitly selecting "latest". */
(()=>{
"use strict";
const file="./data/market-history.json";
const mk=(tag,className,text)=>{
 const x=document.createElement(tag);
 if(className)x.className=className;
 if(text!==undefined)x.textContent=String(text);
 return x;
};
const valid=x=>typeof x==="number"&&Number.isFinite(x);
const fmt=(n,d=2)=>valid(n)?n.toLocaleString("zh-CN",{maximumFractionDigits:d}):"待核";
const pct=(num,den)=>valid(num)&&valid(den)&&den>0?num/den*100:0;
const selection={report:null,tab:"report",history:null,load:null,version:0};
let root,body,buttons;
function btn(label,handler,active){
 const n=mk("button",active?"active":"",label);n.type="button";n.onclick=handler;return n;
}
function notice(text,warning=false){
 const p=mk("div",warning?"viz-alert":"viz-empty",text);return p;
}
function card(title){
 const box=mk("div","viz-card");
 box.append(mk("h4","",title));
 return box;
}
function explain(box,text,css="viz-note"){
 box.append(mk("p",css,text));
}
function barRow(label,value,max,color="focus",unit="",detail=""){
 const line=mk("div","viz-barline");
 const l=mk("span","viz-barlabel",label);
 const track=mk("div","viz-track");track.setAttribute("role","img");
 const portion=mk("div","viz-fill "+color);
 portion.style.width=(max>0?Math.max(0,Math.min(100,value/max*100)):0)+"%";
 track.title=label+": "+fmt(value)+" "+unit+(detail?"，"+detail:"");
 track.setAttribute("aria-label",track.title);
 track.append(portion);
 const number=mk("span","viz-barnum",fmt(value)+(unit||""));
 line.append(l,track,number);
 return line;
}
function poolRows(markdown){
 let heading="",rows=[],seen=new Set();
 const lines=markdown.replace(/\r/g,"").split("\n");
 for(let i=0;i<lines.length;i++){
   const line=lines[i].trim();
   if(line.startsWith("## ")){heading=line.replace(/^##\s+/,"");continue}
   if(!/观察|候选|推荐|计划|池/.test(heading))continue;
   if(!line.startsWith("|")||!line.includes("股票")||!line.includes("代码"))continue;
   if(i+1>=lines.length||!(/^\|[\s:|-]+\|$/.test(lines[i+1].trim())))continue;
   const cells=t=>t.replace(/^\||\|$/g,"").split("|").map(v=>v.trim());
   const head=cells(line);
   const nameIndex=head.findIndex(x=>/股票|名称|标的/.test(x));
   const codeIndex=head.findIndex(x=>/代码/.test(x));
   const poolIndex=head.findIndex(x=>/池别|类别|池/.test(x));
   if(nameIndex<0||codeIndex<0)continue;
   i+=2;
   for(;i<lines.length&&lines[i].trim().startsWith("|");i++){
     const col=cells(lines[i]),match=(col[codeIndex]||"").match(/(?:00|30|60)\d{4}/);
     if(!match)continue;
     const name=(col[nameIndex]||"").replace(/[*\[\]]/g,"").trim();
     if(!name||seen.has(match[0]))continue;
     seen.add(match[0]);
     const pool=(col[poolIndex]||"").match(/(?:^|[^A-Za-z])([ABC])(?:池|[^A-Za-z]|$)/i)?.[1]?.toUpperCase()||null;
     rows.push({name,code:match[0],pool});
   }
   i--;
 }
 return rows;
}
function reportPanel(){
 body.replaceChildren();
 const current=selection.report;
 if(!current)return;
 const stocks=poolRows(current.markdown||"");
 if(!stocks.length){
   body.append(notice("这篇归档没有可可靠解析的「股票名称 + 股票代码」表格，因此不生成股票数量图。正文及文字分析仍可完整阅读。"));
   return;
 }
 const box=card("本期归档中的股票观察记录");
 const c=mk("p","viz-sub",current.status==="summary"?"数据来自历史摘要中的股票表，不等于当时完整推荐名单。":"从当期归档报告的股票表格提取，不代表实际买入或已经获利。");
 box.append(c);
 const cnt={A:0,B:0,C:0,unknown:0};
 for(const row of stocks)cnt[row.pool||"unknown"]++;
 const amount=stocks.length;
 const stat=mk("div","viz-stat");stat.append(mk("strong","",amount),mk("small","","只股票出现在可识别的原文表格中"));
 box.append(stat);
 const groups=[["A","A池","rise"],["B","B池","focus"],["C","C池","fall"],["unknown","未注明池别","flat"]];
 for(const [key,label,color] of groups)if(cnt[key])box.append(barRow(label,cnt[key],amount,color," 只"));
 const pills=mk("div","viz-tags");
 for(const r of stocks){
   const p=mk("span","viz-tag",(r.pool?r.pool+"池 · ":"未标池别 · ")+r.name+" ("+r.code+")");pills.append(p);
 }
 box.append(pills);
 explain(box,"统计范围仅为本篇已归档股票表格；未出现的A/B/C分类不作“零只”结论。点击上方「复制正文」可核对全文。");
 body.append(box);
}
async function loadHistory(){
 if(selection.history)return selection.history;
 if(selection.load)return selection.load;
 selection.load=(async()=>{
  const r=await fetch(file+"?v="+Date.now(),{cache:"no-store"});
  if(!r.ok)throw Error("行情归档目录 HTTP "+r.status);
  const d=await r.json();
  if(d.schema_version!==1||!Array.isArray(d.days))throw Error("图表数据格式不匹配");
  for(const row of d.days){
    if(!/^\d{4}-\d{2}-\d{2}$/.test(row.date)||!valid(row.market_turnover_yi)||row.market_turnover_yi<=0){
      throw Error("行情归档内含异常日期或成交数据");
    }
  }
  selection.history=d.days.slice().sort((a,b)=>a.date.localeCompare(b.date));
  return selection.history;
 })();
 try{return await selection.load}finally{selection.load=null}
}
function available(history){
 const reportDate=selection.report?.date||"";
 const upto=history.filter(d=>d.date<=reportDate);
 const scope=selection.tab==="latest"?history:upto;
 return {days:scope,selected:scope[scope.length-1]||null,isLater:selection.tab==="latest"&&(history.at(-1)?.date>reportDate)};
}
function quoteDetails(box,current){
 const p=mk("p","viz-note",
 "来源："+current.source+"；日期："+current.date+"；行情覆盖股票："+fmt(current.stock_count,0)+"只（有效涨跌幅："+fmt(current.valid_change_count,0)+"只）。");
 box.append(p);
 const source=current.data_sources||[];
 if(source.length)box.append(mk("p","viz-note","采集来源："+source.map(x=>x.provider+" / "+x.api).join("；")));
}
function turnoverTrend(days){
 const box=card("沪深A股成交额：逐日对比（亿元）");
 const selected=days[days.length-1];
 if(!selected){box.append(notice("没有合格的日期数据。"));return box}
 const comparable=days.filter(x=>x.scope===selected.scope).slice(-6);
 if(comparable.length!==days.slice(-6).length)explain(box,"数据口径不一致的历史快照已排除，不进行跨范围比较。");
 const max=Math.max(...comparable.map(x=>x.market_turnover_yi),1);
 const s=mk("div","viz-stat");
 s.append(mk("strong","",fmt(selected.market_turnover_yi)+" 亿元"),mk("small","","股票有效成交额小计 · "+selected.date));
 box.append(s);
 for(const d of comparable)box.append(barRow(d.date.slice(5),d.market_turnover_yi,max,"focus"," 亿"));
 if(comparable.length===1)explain(box,"当前仅有一个可比日期，展示单日数据，不绘制虚假的涨跌趋势。");
 else {
   const a=comparable[comparable.length-2],b=comparable[comparable.length-1];
   const d=(b.market_turnover_yi-a.market_turnover_yi)/a.market_turnover_yi*100;
   explain(box,"最近两份同口径快照变动："+(d>0?"+":"")+fmt(d)+"%；这是已采集股票成交额的变化，并非交易所全市场公布值。");
 }
 explain(box,"统计口径："+selected.scope+"。不同日期采集覆盖率可能不同；仅用于辅助理解，不直接当作主力净流入。");
 return box;
}
function breadthChart(current){
 const box=card("股票涨跌家数分布");
 const b=current.breadth;
 if(!b||!["up","down","flat","missing"].every(k=>Number.isSafeInteger(b[k])&&b[k]>=0)||
   b.up+b.down+b.flat+b.missing!==current.stock_count){
   box.append(notice("归档涨跌家数校验未通过，不显示图表。"));return box;
 }
 const total=current.stock_count;
 const line=mk("div","viz-stacked");
 for(const [key,label] of [["up","上涨"],["down","下跌"],["flat","平盘"],["missing","无有效涨跌幅"]]){
   if(b[key]===0)continue;
   const s=mk("div","viz-piece "+key);
   s.style.width=pct(b[key],total)+"%";
   s.title=label+"："+b[key]+"只，占"+fmt(pct(b[key],total))+"%";
   line.append(s);
 }
 line.setAttribute("role","img");
 line.setAttribute("aria-label","上涨"+b.up+"只，下跌"+b.down+"只，平盘"+b.flat+"只，未取到涨跌幅"+b.missing+"只。");
 box.append(line);
 const legend=mk("div","viz-legend");
 for(const [key,label] of [["up","上涨"],["down","下跌"],["flat","平盘"],["missing","缺失"]]){
   const item=mk("span","");item.append(mk("i","viz-swatch "+key),document.createTextNode(label+" "+b[key]+"只（"+fmt(pct(b[key],total))+"%）"));legend.append(item);
 }
 box.append(legend);
 explain(box,"红色代表上涨、绿色代表下跌；家数比例的分母是该日成功采集的股票数，不代表账户获利概率。");
 return box;
}
function topTurnover(current){
 const box=card("个股成交额排名 Top 10（亿元）");
 const rows=current.top_turnover;
 if(!Array.isArray(rows)||!rows.length){box.append(notice("该日没有验证通过的股票成交额排名。"));return box}
 const vetted=rows.filter(x=>valid(x.turnover_yi)&&x.turnover_yi>=0&&/^\d{6}$/.test(x.code)).slice(0,10);
 if(!vetted.length){box.append(notice("该日个股成交额数值不可用。"));return box}
 const max=Math.max(...vetted.map(x=>x.turnover_yi),1);
 for(const x of vetted)box.append(barRow(x.name+" "+x.code,x.turnover_yi,max,"flat"," 亿",
  valid(x.change_pct)?"当日涨跌幅"+fmt(x.change_pct)+"%":"涨跌幅待核"));
 explain(box,"成交额大表示交易活跃，不代表买入信号。样本含快照范围内的科创板等股票；投资候选筛选池规则与此图不同。");
 return box;
}
function diverge(box,value,max){
 const track=mk("div","viz-diverge");
 if(!valid(value)||!max)return track;
 const fill=mk("div","viz-piece "+(value>=0?"rise":"fall"));
 const width=Math.min(50,Math.abs(value)/max*50);
 fill.style.position="absolute";fill.style.width=width+"%";fill.style.left=(value>=0?50:50-width)+"%";
 track.append(fill);return track;
}
function sectorsPanel(days){
 const box=card("双日行业：成交额与估算主力净流向");
 if(days.length<2){box.append(notice("目前只有一日（或更少）行情快照，不能制作双日行业对比。"));return box}
 const a=days[days.length-2],b=days[days.length-1];
 if(a.scope!==b.scope){box.append(notice("两日股票市场统计范围不一致，暂不比较行业数据。"));return box}
 const older=new Map((a.sectors||[]).filter(x=>x.classification).map(x=>[x.name,x]));
 const matched=(b.sectors||[]).filter(x=>{
   const p=older.get(x.name);
   return p&&p.classification===x.classification&&valid(p.turnover_yi)&&valid(x.turnover_yi)&&valid(p.net_yi)&&valid(x.net_yi);
 }).slice(0,10).map(x=>({newer:x,older:older.get(x.name)}));
 if(!matched.length){
   box.append(notice("行业主力资金缺少同源、同一级行业分类的连续两日数据。此图暂不生成，以免把成交额、板块涨幅或未核实资金净额混为一谈。"));
   return box;
 }
 const maxNet=Math.max(...matched.flatMap(x=>[Math.abs(x.newer.net_yi),Math.abs(x.older.net_yi)]),1);
 for(const row of matched){
   const name=row.newer.name,section=mk("div","viz-funds-row");
   section.append(mk("strong","",name));
   const sides=mk("div","viz-funds-columns");
   for(const [d,s] of [[a,row.older],[b,row.newer]]){
     const panel=mk("div","viz-funds-side");
     panel.append(mk("span","",d.date+" · 成交额"+fmt(s.turnover_yi)+"亿元"));
     panel.append(diverge(panel,s.net_yi,maxNet));
     const sign=s.net_yi>0?"+":"";
     panel.append(mk("strong","", "主力净额 "+sign+fmt(s.net_yi)+"亿元"));
     panel.append(mk("p","", "净流强度 "+(s.net_yi>0?"+":"")+fmt(s.net_strength_pct)+"%"));
     sides.append(panel);
   }
   section.append(sides);box.append(section);
 }
 explain(box,"资金图只有在两天行业分类一致、成交额与净额都已核实的情况下显示。红=估算净流入，绿=估算净流出；每条图以零为中线，不表示行业之间存在实际资金转账。");
 return box;
}
async function marketPanel(){
 const v=selection.version;
 body.replaceChildren(notice("读取真实归档行情并核对数据口径…"));
 try{
   const hist=await loadHistory();
   if(v!==selection.version||selection.tab==="report")return;
   const info=available(hist);
   body.replaceChildren();
   if(!info.selected){
     body.append(notice("没有截止本篇日报发布日（"+selection.report.date+"）的已核实行情快照。要查看更新日期的市场数据，请切换到「最新行情（独立查看）」。"));
     return;
   }
   if(info.isLater){
     body.append(notice("注意：本图为 "+info.selected.date+" 收盘行情，晚于当前所选 "+selection.report.date+" 的日报。只能用于查看后续市场数据，不得作为当期报告的原始依据。",true));
   }
   const scope=mk("p","viz-sub","行情日期："+info.selected.date+"　·　数据质量："+info.selected.quality_status+"　·　已归档数据，仅盘后更新");
   body.append(scope);
   body.append(turnoverTrend(info.days),breadthChart(info.selected),topTurnover(info.selected),sectorsPanel(info.days));
   const source=card("数据来源与口径");
   quoteDetails(source,info.selected);
   explain(source,"行情衍生图表与日报文字相互独立。报告原文不会因为之后的股价变动被改写；主力资金不足时仍标记缺失。");
   body.append(source);
 }catch(e){
   if(v!==selection.version)return;
   body.replaceChildren(notice("无法读取或校验行情图表数据："+e.message+"。原文仍可正常阅读。"));
 }
}
function show(tab){
 if(!selection.report)return;
 selection.tab=tab;selection.version++;
 for(const [key,n] of Object.entries(buttons)){
   n.classList.toggle("active",key===tab);n.setAttribute("aria-pressed",String(key===tab));
 }
 if(tab==="report")reportPanel();else marketPanel();
}
function render(obj){
 if(!root||!obj)return;
 selection.report={date:String(obj.date||""),status:obj.status,markdown:String(obj.markdown||"")};
 show("report");
}
function setup(){
 const reader=document.querySelector(".reader"),content=document.getElementById("content");
 if(!reader||!content)return;
 root=mk("section","radar-viz");
 const head=mk("div","viz-head");
 const group=mk("div");group.append(mk("div","viz-eyebrow","VISUAL EVIDENCE · 图表辅助"),mk("h3","","市场环境与资金数据 · 辅助验证"),
  mk("p","viz-sub","选股观察和买卖条件在上方优先展示；此处只用于核对市场数据，不更改原报告。"));
 head.append(group);
 const nav=mk("div","viz-segment");buttons={};
 for(const [key,label] of [["report","本期报告"],["date","对应日期行情"],["latest","最新行情（独立查看）"]]){
   buttons[key]=btn(label,()=>show(key),key==="report");buttons[key].setAttribute("aria-pressed",String(key==="report"));nav.append(buttons[key]);
 }
 head.append(nav);root.append(head);
 body=mk("div","viz-body");root.append(body);
 const fold=mk("details","market-fold");
 const summary=mk("summary","","市场与资金图表 · 辅助验证（点击展开）");
 fold.append(summary,root);
 reader.insertBefore(fold,content);
 if(window.RadarCurrentReport)render(window.RadarCurrentReport);
}
window.RadarCharts={render};
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",setup,{once:true});else setup();
})();