/* Presentation-only reader; source reports are never modified. */
(()=>{
"use strict";
const $=s=>document.querySelector(s);
const make=(tag,className,text)=>{
 const node=document.createElement(tag);
 if(className)node.className=className;
 if(text!==undefined)node.textContent=text;
 return node;
};
const glossary={
 "主力净流入":"行情服务商按大额交易、主动买卖等规则估算的净买入差额，不是精确追踪到某一批资金的真实跨板块转账。",
 "主力净流出":"按数据商规则估算的卖出压力大于买入压力。每笔成交都有买方和卖方，不能据此认定资金去了哪里。",
 "主力净流强度":"通常为同口径估算主力净额除以板块成交额，再乘100%。并不是全体成交资金的实际流入比例。",
 "主力净流额":"行情数据服务商估算的大单买卖差额；不同来源算法可能不同，比较时必须统一口径。",
 "主力资金":"分析软件按成交额或主动买卖等规则估计的一类大额交易，并不代表可准确识别真实资金持有人。",
 "成交额":"一段时间内股票买卖发生的总金额。反映交易活跃程度，不等于净流入。",
 "成交量":"一段时间内成交的股票数量，需与历史水平和价格同时比较。",
 "换手率":"成交股数相对流通股数的比例。通常用于观察交易是否活跃。",
 "放量承接":"成交增加，但价格仍获得较强支撑的市场表现；并不意味着未来一定上涨。",
 "放量":"比之前成交更多。可能是更多人买，也可能是抛压变大，不能单独判断。",
 "缩量":"比之前成交更少，可能表示观望；本身不等于看涨。",
 "净流强度":"资金净额相对成交额的比例指标，不能当成真实资金转账方向。",
 "冲高回落":"盘中曾上涨，但到收盘涨幅减少或转跌。可能意味着高位卖压增加。",
 "浮盈亏":"未卖出时的账面盈利或亏损，不是最终实际收益，还需考虑费用等。",
 "结构失效":"原来支持交易判断的价格、成交量等条件不再成立，需要重新评估。",
 "最大不利波动":"从指定基准到观察期间不利价格位置的最大波动幅度，衡量潜在下行风险。",
 "相对指数收益":"股票收益与同期基准指数收益之差。跑赢指数也可能仍在亏损。",
 "回撤":"价格或资产从高点向下回落的幅度，和相对买入价的亏损不同。",
 "止盈":"价格达到预定盈利条件时，考虑分批卖出，保护已有收益。",
 "止损":"触及事先设定的风险条件时考虑退出；跳空和跌停可能使计划价格无法成交。",
 "T+1":"普通A股通常当天买入不能当天卖出，最快下一个交易日卖出，需承担隔夜风险。",
 "D+1":"报告冻结候选后的第一个交易日，用来做事后验证，不代表真实成交收益。",
 "D+3":"报告冻结候选后的第三个交易日，必须按事先规则统计，不能事后挑选有利价格。",
 "A池":"证据相对充分的观察股票池，不意味着保证上涨或应当立即买入。",
 "B池":"条件尚待验证的候选股票池。",
 "C池":"过热、淘汰或结构失效的观察池，也必须保留失败记录。",
 "催化":"财报、政策、订单等可能影响市场预期的事件，不保证股价上涨。",
 "环比":"跟上一期比较。例如今日成交额与上一交易日成交额比较。"
};
const keys=Object.keys(glossary).sort((a,b)=>b.length-a.length);
const pattern=new RegExp(keys.map(k=>k.replace(/\+/g,"\\+")).join("|"),"g");
let reader,content,tip,summary,jump,progress;
let theme=localStorage.getItem("radar-read-theme")||"light";
let font=Number(localStorage.getItem("radar-read-font")||17);
if(!["light","dark"].includes(theme))theme="light";
if(!Number.isFinite(font)||font<14||font>22)font=17;
document.documentElement.dataset.readerTheme=theme;
document.documentElement.style.setProperty("--read-font",font+"px");
function button(label,onClick){
 let b=make("button","",label);b.type="button";b.onclick=onClick;return b;
}
function progressBar(){
 if(!content||!progress)return;
 const rect=content.getBoundingClientRect();
 const total=Math.max(1,content.offsetHeight-window.innerHeight+140);
 progress.style.width=(Math.min(100,Math.max(0,-rect.top/total*100))).toFixed(1)+"%";
}
function expandAll(expand){
 content.querySelectorAll(".read-section-body").forEach(n=>n.hidden=!expand);
 content.querySelectorAll(".section-toggle").forEach(n=>n.textContent=expand?"收起":"展开");
 progressBar();
}
function showDefinition(key,origin){
 tip.replaceChildren();
 let close=button("关闭",()=>{tip.hidden=true;origin.focus()});
 close.className="term-close";
 tip.append(make("strong","",key),make("p","",glossary[key]),make("small","tip","术语说明仅帮助阅读，不替代原始数据和风险核实。"),close);
 tip.hidden=false;close.focus();
}
function definitions(){
 const nodes=[];
 const walker=document.createTreeWalker(content,NodeFilter.SHOW_TEXT,{
  acceptNode(n){
   const p=n.parentElement;
   if(!p||!p.closest("p,li,td,blockquote")||p.closest("a,button,code,pre,.term-help"))return NodeFilter.FILTER_REJECT;
   pattern.lastIndex=0;
   return pattern.test(n.nodeValue)?NodeFilter.FILTER_ACCEPT:NodeFilter.FILTER_REJECT;
  }
 });
 while(walker.nextNode())nodes.push(walker.currentNode);
 for(const n of nodes){
  const txt=n.nodeValue,frag=document.createDocumentFragment();
  pattern.lastIndex=0;let last=0,m;
  while((m=pattern.exec(txt))){
   if(m.index>last)frag.append(document.createTextNode(txt.slice(last,m.index)));
   const b=button(m[0],()=>showDefinition(m[0],b));
   b.className="term-help";b.title="点击了解："+m[0];
   b.setAttribute("aria-label",m[0]+"，查看通俗解释");
   frag.append(b);last=m.index+m[0].length;
  }
  if(last<txt.length)frag.append(document.createTextNode(txt.slice(last)));
  n.replaceWith(frag);
 }
}
function sectionNavigation(){
 const headings=[...content.children].filter(n=>n.tagName==="H2");
 const sections=[];
 headings.forEach((heading,i)=>{
   let name=heading.textContent.trim(),nextHeading=headings[i+1];
   heading.id="reader-section-"+i;heading.classList.add("section-header");
   let section=make("div","read-section-body");
   heading.after(section);
   let node=section.nextSibling;
   while(node && node!==nextHeading){
     let after=node.nextSibling;section.append(node);node=after;
   }
   let fold=button("收起",()=>{section.hidden=!section.hidden;fold.textContent=section.hidden?"展开":"收起";progressBar()});
   fold.className="section-toggle";
   fold.setAttribute("aria-label",name+" 展开或收起");
   heading.append(fold);
   sections.push({id:heading.id,name,section,fold});
 });
 jump.replaceChildren();
 jump.hidden=!sections.length;
 if(sections.length)jump.append(make("strong","","快速跳到"));
 for(const s of sections){
   jump.append(button(s.name,()=>{
     if(s.section.hidden){s.section.hidden=false;s.fold.textContent="收起"}
     document.getElementById(s.id).scrollIntoView({behavior:"smooth",block:"start"});
   }));
 }
}
function refresh(){
 if(!content||content.querySelector(".section-toggle"))return;
 tip.hidden=true;
 const preview=$(".item.current .desc")?.textContent?.trim();
 summary.replaceChildren();
 if(preview){
   summary.append(make("div","read-digest-head","先看这期重点 · 来自原报告的归档导语"),make("p","",preview),make("small","","以下是归档正文，未改变当时的观点和数据；历史摘要不等于原始全文。"));
   summary.hidden=false;
 }else summary.hidden=true;
 sectionNavigation();
 definitions();
 progressBar();
}
function setup(){
 reader=$(".reader");content=$("#content");const head=$(".readerhead");
 if(!reader||!content||!head)return;
 const bar=make("div","reader-tools");
 bar.append(
   button("A−",()=>{font=Math.max(14,font-1);document.documentElement.style.setProperty("--read-font",font+"px");localStorage.setItem("radar-read-font",font);progressBar()}),
   button("A+",()=>{font=Math.min(22,font+1);document.documentElement.style.setProperty("--read-font",font+"px");localStorage.setItem("radar-read-font",font);progressBar()}),
   button("亮色 / 深色",()=>{theme=theme==="light"?"dark":"light";document.documentElement.dataset.readerTheme=theme;localStorage.setItem("radar-read-theme",theme)}),
   button("展开全部",()=>expandAll(true)),
   button("折叠章节",()=>expandAll(false)),
   button("打印 / 保存PDF",()=>window.print()),
   make("small","","阅读增强只改变展示，不更改日报原文")
 );
 head.append(bar);
 summary=make("div","read-digest");summary.hidden=true;
 jump=make("nav","read-jump");jump.hidden=true;jump.setAttribute("aria-label","报告章节目录");
 reader.insertBefore(summary,content);
 reader.insertBefore(jump,content);
 tip=make("aside","term-panel");tip.hidden=true;tip.setAttribute("role","dialog");tip.setAttribute("aria-label","金融术语解释");document.body.append(tip);
 progress=make("div","read-progress");document.body.append(progress);
 document.addEventListener("keydown",e=>{if(e.key==="Escape")tip.hidden=true});
 document.addEventListener("click",e=>{if(!tip.hidden&&!e.target.closest(".term-panel,.term-help"))tip.hidden=true});
 window.addEventListener("scroll",progressBar,{passive:true});
 window.addEventListener("resize",progressBar,{passive:true});
 refresh();
}
window.RadarReader={refresh};
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",setup,{once:true});
else setup();
})();