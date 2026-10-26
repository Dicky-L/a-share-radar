/* Unified history browser: one date index for verified market snapshots and actual report files.
   No market-only day is represented as a stock recommendation. */
(()=>{
"use strict";
const $=id=>document.getElementById(id);
const esc=v=>String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const fmt=(v,places=2)=>typeof v==="number"&&Number.isFinite(v)?v.toLocaleString("zh-CN",{maximumFractionDigits:places}):"待核";
let entries=[],selected=null,reportText="",rawPath="",archiveFilter="all",openSeq=0,loadWarnings=[];
const st=v=>v==="original"?"全文":v==="summary"?"摘要":"仅行情";
const labelFor=e=>e?.report_type==="historical_reconstruction"?"重建":st(e.status);
/* Always interpret 'today' in China Standard Time, not a visitor's device timezone. */
const beijingToday=()=>{
 const parts=new Intl.DateTimeFormat("en-US",{timeZone:"Asia/Shanghai",year:"numeric",month:"2-digit",day:"2-digit"}).formatToParts(new Date());
 const get=key=>parts.find(x=>x.type===key)?.value||"";
 return get("year")+"-"+get("month")+"-"+get("day");
};
function showTodayBanner(){
 const bar=$("today-bar"),title=$("today-title"),message=$("today-message"),open=$("today-open");
 if(!bar||!title||!message||!open)return;
 const today=beijingToday(),todayReport=entries.find(x=>x.date===today&&["original","summary"].includes(x.status));
 const latestReport=entries.find(x=>["original","summary"].includes(x.status));
 bar.classList.remove("state-ready","state-summary","state-missing");
 if(todayReport){
   const full=todayReport.status==="original";
   bar.classList.add(full?"state-ready":"state-summary");
   title.textContent=today+" · "+(full?"完整选股报告已发布":"选股报告摘要已发布");
   message.textContent=full?"今日全文已可阅读：A/B/C池、入选逻辑、买入验证、卖出计划、资金与历史复盘均以正文实际内容为准。":
      "今日仅有摘要，尚未同步完整推送原文；未归档的分析和数据不能视为已发布。";
   open.hidden=false;open.textContent="阅读今日"+(full?"完整报告":"已发布摘要");
   open.onclick=()=>openDate(today);
 }else{
   bar.classList.add("state-missing");
   title.textContent=today+" · 今天的选股报告尚未同步";
   message.textContent=latestReport?
      "网站最近一期选股报告为 "+latestReport.date+"（"+st(latestReport.status)+"）。可以先查阅旧报告，不能把它当作今天的推荐。":
      "仓库尚无可阅读的选股报告；行情快照不能代替今日完整研究和买卖计划。";
   open.hidden=!latestReport;
   if(latestReport){
     open.textContent="阅读最近一期 "+latestReport.date;
     open.onclick=()=>openDate(latestReport.date);
   }
 }
}
function clearPlugins(){
 const board=document.querySelector(".pickboard");if(board)board.hidden=true;
 const fold=document.querySelector(".market-fold");if(fold)fold.open=false;
 const digest=document.querySelector(".read-digest");if(digest)digest.hidden=true;
 const jumps=document.querySelector(".read-jump");if(jumps)jumps.hidden=true;
 const tooltip=document.querySelector(".term-panel");if(tooltip)tooltip.hidden=true;
}
function applyPlugins(item,md=""){
 window.RadarCurrentReport={date:item.date,status:item.status,markdown:md};
 if(item.status!=="market_only"){
   const board=document.querySelector(".pickboard");if(board)board.hidden=false;
   window.RadarPickBoard?.render?.(window.RadarCurrentReport);
 }
 window.RadarCharts?.render?.(window.RadarCurrentReport);
 if(item.status==="market_only"){
   const fold=document.querySelector(".market-fold");
   if(fold)fold.open=true;
 }
}
function activeList(){
 const q=$("search").value.trim().toLowerCase(),m=$("month").value;
 return entries.filter(e=>
   (!m||e.date.startsWith(m))&&
   (archiveFilter==="all"||(archiveFilter==="reports"&&e.status!=="market_only")||(archiveFilter==="market"&&e.market))&&
   (!q||[e.date,e.title,e.preview,e.search_text].join(" ").toLowerCase().includes(q))
 );
}
function list(){
 const filtered=activeList();
 const reportCount=entries.filter(e=>e.status!=="market_only").length;
 const marketCount=entries.filter(e=>e.market).length;
 $("count").textContent=filtered.length+"个日期 · "+reportCount+"篇报告 · "+marketCount+"个行情日";
 $("list").innerHTML=filtered.length?filtered.map(e=>
   "<button type='button' data-date='"+esc(e.date)+"' class='item "+(selected?.date===e.date?"current":"")+"' aria-current='"+(selected?.date===e.date?"true":"false")+
   "'><span class='date'>"+esc(e.date)+"</span><span class='tag "+(e.status==="original"?"full":e.status==="market_only"?"only-market":"")+"'>"+labelFor(e)+
   "</span><span class='desc'>"+esc(e.preview||"该日已有验证通过的行情快照")+"</span></button>").join(""):
   "<div class='placeholder'>没有符合筛选的日期。可清除筛选后查看全部历史行情与报告。</div>";
}
function actionState(report,ready=true){
 $("copy").disabled=!report||!ready;
 $("raw").disabled=!report||!ready;
 $("permalink").disabled=!ready;
 $("copy").textContent="复制正文";
 $("permalink").textContent="复制本篇链接";
}
function rememberDate(date){
 const url=new URL(location.href);url.searchParams.set("date",date);
 history.replaceState(null,"",url);
}
function marketCard(day,item){
 const panel=document.createElement("section");panel.className="market-day";
 panel.innerHTML=
   "<div class='eyebrow'>VERIFIED MARKET SNAPSHOT · 数据日期 "+esc(day)+"</div>"+
   "<h3>这一天的行情已经归档，选股日报原文尚未入库</h3>"+
   "<div class='warning'>注意：这里是当日行情数据，不是当日18:00选股推荐。没有报告文件不等于当时没有选股推送，不能事后补编当时的买点、止损位或卖出结论。</div>"+
   "<div class='numbers'><div class='metric'><small>已采集股票数量</small><strong id='arc-stock-total'>读取中…</strong></div>"+
   "<div class='metric'><small>有效股票成交额小计</small><strong id='arc-turnover'>读取中…</strong></div></div>"+
   "<p id='arc-quality' class='market-source'>读取数据来源与质量说明…</p>"+
   "<a class='go-market' href='./market.html?date="+encodeURIComponent(day)+"'>查询本交易日全部股票行情 →</a>"+
   "<h4>在本交易日搜索股票</h4><div class='search-row'><input id='arc-ticker-search' type='search' placeholder='输入股票代码 / 股票名称' aria-label='本日股票查询'></div>"+
   "<div id='arc-search-results' class='results'><p>请输入股票代码或名称，显示对应收盘价、涨跌幅和成交额。</p></div>";
 return panel;
}
async function openDate(day,options={}){
 const item=entries.find(e=>e.date===day);if(!item)return;
 const token=++openSeq;selected=item;list();
 $("title").textContent=item.title||("A股雷达 · "+day);
 $("meta").textContent=(item.status==="market_only"?"行情快照日期 ":"日报发布日期 ")+day+
   " · "+labelFor(item)+(item.market?" · 有当日行情快照":" · 无同日行情快照")+
   (item.source?" · "+item.source:"");
 $("content").innerHTML="<div class='placeholder'>正在读取归档…</div>";
 actionState(false,false);
 reportText="";rawPath="";
 clearPlugins();if(!options.keepUrl)rememberDate(day);
 if(item.status==="market_only"){
   $("title").textContent=day+" · 已归档市场行情（选股日报缺失）";
   $("content").replaceChildren(marketCard(day,item));
   actionState(false,true);
   try{
     const res=await fetch("./data/snapshots/"+encodeURIComponent(day)+".json?v="+Date.now(),{cache:"no-store"});
     if(!res.ok)throw Error("HTTP "+res.status);
     const d=await res.json();
     if(token!==openSeq)return;
     if(d.date!==day||!Array.isArray(d.stocks)||d.stocks.length<3000||!d.market||!(d.market.turnover_yi>0))throw Error("日期或快照质量校验失败");
     $("arc-stock-total").textContent=fmt(d.stocks.length,0)+" 只";
     $("arc-turnover").textContent=fmt(d.market.turnover_yi)+" 亿元";
     $("arc-quality").textContent=
        "口径："+(d.market.scope||"待核")+"；来源："+(d.data_sources||[]).map(s=>s.provider).join(" / ")+
        "；覆盖率："+(d.quality?.coverage_pct??"待核")+"%；"+(d.quality?.message||"");
     const input=$("arc-ticker-search"),out=$("arc-search-results");
     function search(){
       const q=input.value.trim().toLowerCase();
       if(!q){out.innerHTML="<p>输入股票代码或名称搜索本日历史行情。</p>";return}
       const arr=d.stocks.filter(s=>String(s.code||"").includes(q)||String(s.name||"").toLowerCase().includes(q)).slice(0,20);
       out.innerHTML=arr.length?
         "<table><thead><tr><th>代码</th><th>股票</th><th>收盘价(元)</th><th>涨跌幅</th><th>成交额(亿元)</th></tr></thead><tbody>"+
         arr.map(s=>"<tr><td>"+esc(s.code)+"</td><td>"+esc(s.name)+"</td><td>"+fmt(s.price)+"</td><td>"+
           (typeof s.change_pct==="number"?fmt(s.change_pct)+"%":"待核")+"</td><td>"+fmt(s.turnover_yi)+"</td></tr>").join("")+
         "</tbody></table>":"<p>本日有效行情样本中未找到该股票，可能当日无有效交易或不在回填名单。</p>";
     }
     input.addEventListener("input",search);
   }catch(e){
     if(token===openSeq)$("content").innerHTML="<div class='placeholder'>无法读取本日行情："+esc(e.message)+"。可访问原始交易日文件核对。</div>";
   }
   if(token===openSeq)applyPlugins(item,"");
   return;
 }
 rawPath=item.file;
 try{
   const res=await fetch(item.file+"?v="+Date.now(),{cache:"no-store"});
   if(!res.ok)throw Error("HTTP "+res.status);
   const text=await res.text();
   if(token!==openSeq)return;
   reportText=text;
   // renderMarkdown is provided by index.html's original source renderer.
   $("content").innerHTML=renderMarkdown(text);
   window.RadarReader?.refresh?.();
   applyPlugins(item,text);
   actionState(true,true);
 }catch(e){
   if(token!==openSeq)return;
   $("content").textContent="日报原文读取失败："+e.message;
   actionState(false,true);
 }
}
function initFilters(){
 const head=document.querySelector(".sidehead");
 if(!head)return;
 const nav=document.createElement("div");nav.className="arc-filter";nav.setAttribute("aria-label","历史记录类型筛选");
 for(const [type,title] of [["all","全部日期"],["reports","有选股报告"],["market","有行情数据"]]){
   const btn=document.createElement("button");
   btn.type="button";btn.textContent=title;btn.dataset.kind=type;
   btn.classList.toggle("active",type===archiveFilter);
   btn.onclick=()=>{
     archiveFilter=type;
     nav.querySelectorAll("button").forEach(x=>x.classList.toggle("active",x.dataset.kind===type));
     list();
   };
   nav.append(btn);
 }
 head.append(nav);
 const note=document.createElement("div");note.className="date-hint";
 note.textContent="报告原文与历史行情是两类数据；点击“仅行情”日期可直接查询当日股票。";
 head.append(note);
}
async function init(){
 initFilters();
 $("list").onclick=e=>{const node=e.target.closest("[data-date]");if(node)openDate(node.dataset.date)};
 $("today-open").hidden=true;
 $("today-refresh").onclick=()=>location.reload();
 $("search").oninput=list;$("month").onchange=list;
 $("reset").onclick=()=>{$("search").value="";$("month").value="";archiveFilter="all";
    document.querySelectorAll(".arc-filter button").forEach(x=>x.classList.toggle("active",x.dataset.kind==="all"));list()};
 $("copy").onclick=async()=>{
   if(!reportText)return;
   try{await navigator.clipboard.writeText(reportText);$("copy").textContent="已复制"}catch(e){$("copy").textContent="复制失败"}
 };
 $("permalink").onclick=async()=>{try{await navigator.clipboard.writeText(location.href);$("permalink").textContent="链接已复制"}catch(e){$("permalink").textContent="复制失败"}};
 $("raw").onclick=()=>{if(rawPath)window.open(rawPath,"_blank","noopener,noreferrer")};
 try{
   const data=await Promise.allSettled([
     fetch("./reports/index.json?v="+Date.now(),{cache:"no-store"}).then(r=>{if(!r.ok)throw Error("reports HTTP "+r.status);return r.json()}),
     fetch("./data/index.json?v="+Date.now(),{cache:"no-store"}).then(r=>{if(!r.ok)throw Error("market HTTP "+r.status);return r.json()})
   ]);
   const reports=data[0].status==="fulfilled"?data[0].value.items||[]:[];
   const marketDays=data[1].status==="fulfilled"?data[1].value.dates||[]:[];
   loadWarnings=data.filter(x=>x.status==="rejected").map(x=>String(x.reason));
   const marketSet=new Set(marketDays.filter(d=>/^\d{4}-\d{2}-\d{2}$/.test(d)));
   const map=new Map();
   for(const report of reports){
     if(!/^\d{4}-\d{2}-\d{2}$/.test(report.date)||!["original","summary"].includes(report.status))continue;
     map.set(report.date,{...report,market:marketSet.has(report.date)});
   }
   for(const day of marketSet){
     if(map.has(day))continue;
     map.set(day,{date:day,status:"market_only",title:"历史行情 · "+day,
       preview:"已归档本交易日价格、涨跌幅、成交额；选股日报原文未归档",
       market:true,source:"经校验的历史行情快照",search_text:"行情 收盘价 涨跌幅 成交额 股票 历史"});
   }
   entries=[...map.values()].sort((a,b)=>b.date.localeCompare(a.date));
   list();showTodayBanner();
   if(!entries.length)throw Error("没有可用的报告与行情日期索引；"+loadWarnings.join("; "));
   const requested=new URLSearchParams(location.search).get("date");
   // With a bare homepage URL, do not silently lock tomorrow's visit to an older date.
   // Prefer today's complete report; otherwise show newest real report, not a market-only snapshot.
   const latestReport=entries.find(x=>x.status==="original"||x.status==="summary");
   const preferred=entries.find(x=>x.date===beijingToday()&&x.status!=="market_only")||latestReport||entries[0];
   const chosen=entries.find(x=>x.date===requested)||preferred;
   await openDate(chosen.date,{keepUrl:!requested});
   if(loadWarnings.length){
     const info=document.createElement("p");info.className="date-hint";
     info.textContent="部分历史索引读取失败，当前仅显示成功加载的数据。";
     document.querySelector(".sidehead")?.append(info);
   }
 }catch(e){
   $("title").textContent="今日报告暂时不可用";
   $("content").textContent="报告或历史数据索引读取失败："+e.message;
   showTodayBanner();
 }
}
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",init,{once:true});
else init();
})();