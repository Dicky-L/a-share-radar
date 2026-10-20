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
 "主力净流入":{definition:"行情服务商依据大单金额、主动买卖方向等规则计算的估算主力净买入差额为正。",formula:"净流额 = 估算主力买入额 − 估算主力卖出额。",interpretation:"只能反映特定模型下的交易方向；不是交易所公布的真实跨板块资金转账。"},
 "主力净流出":{definition:"同一估算口径下，主力净买卖额为负，说明被归类为主力的卖出额大于买入额。",formula:"净流额 = 估算主力买入额 − 估算主力卖出额，结果小于0。",interpretation:"净流出不代表真实资金流往某个具体板块，分析时还要比较成交规模和价格表现。"},
 "主力净流强度":{definition:"将某一行业或证券的估算主力净流额标准化为同范围成交额的百分比，便于比较资金方向的相对强弱。",formula:"主力净流强度（%）= 主力净流额 ÷ 同口径成交额 × 100%。",interpretation:"例如净流额−20亿元、成交额1000亿元，则强度为−2%。这是示例，不是当日行情，也不表示全体资金实际流出2%。"},
 "主力净流额":{definition:"特定行情服务商估算的大额或主动交易买卖金额差额。",formula:"通常为估算买入金额−估算卖出金额，具体以供应商定义为准。",interpretation:"跨日比较须保持相同来源、相同证券范围和计算方法；不同服务商的数值不宜直接混用。"},
 "主力资金":{definition:"行情软件依据成交规模、交易方向等规则对部分交易进行的统计分类。",interpretation:"属于模型估算指标，不等于能追踪或识别机构账户的真实资金。"},
 "成交额":{definition:"统计期内所有成交交易按成交价格乘以成交数量计算的金额总和。",formula:"成交额 = ∑（每笔成交价格 × 成交数量）。",interpretation:"成交额衡量交易规模，既包含买方也包含卖方；不能简单将放量解释为净流入。"},
 "成交量":{definition:"统计期内撮合完成的股票数量，A股常用股或手表示，1手一般为100股。",interpretation:"与历史均量、价格变动、换手率结合分析，比孤立观察成交量更有意义。"},
 "换手率":{definition:"统计期内成交股数相对于可流通股数的比例，反映流通筹码的交易活跃程度。",formula:"换手率（%）= 成交股数 ÷ 对应口径流通股数 × 100%。",interpretation:"自由流通口径和一般流通股口径可能不同，比较前需要核对数据源。"},
 "放量承接":{definition:"成交规模放大的同时，股价面对抛压仍维持一定支撑的量价结构判断。",interpretation:"这是对交易行为的分析，不是严格统一的技术指标；应结合收盘位置、关键支撑位及后续确认。"},
 "放量":{definition:"当期成交量或成交额显著高于指定比较周期的水平。",formula:"量比或成交额环比需说明基准周期，不能把不同时间窗口直接比较。",interpretation:"放量上涨、放量下跌的含义不同，放量本身不构成买入信号。"},
 "缩量":{definition:"当期成交量或成交额低于指定比较周期的水平。",interpretation:"缩量可能发生在横盘、反弹或下跌中，必须结合价格结构判断。"},
 "净流强度":{definition:"资金净流额相对于相同统计范围内成交额的比例。",formula:"净流强度（%）= 估算净流额 ÷ 同范围成交额 × 100%。",interpretation:"供应商主力资金口径不同，先确认分子和分母是否同源、同范围。"},
 "冲高回落":{definition:"证券盘中创出相对较高价格后，收盘价明显低于盘中高点的走势形态。",interpretation:"可能意味着高位抛压增加，但应结合振幅、成交量和关键价位验证。"},
 "浮盈亏":{definition:"未平仓或未卖出持仓按当前参考价格计量的账面损益。",formula:"简化浮盈亏 = （参考价−持仓单位成本）× 持仓数量。",interpretation:"实际收益还应计入交易费用、公司行为及可能的税费；不等于已实现收益。"},
 "结构失效":{definition:"此前形成交易判断的关键价位、趋势或量价条件不再成立。",interpretation:"结构失效位是风险管理条件，不是保证能够在该价格成交的止损指令。"},
 "最大不利波动":{definition:"观察期间价格相对基准价格朝不利方向运行的最大幅度，用于评估策略持有风险。",formula:"多头示例：最大不利波动（%）≈（观察期最低价−参考入场价）÷参考入场价×100%。",interpretation:"应统一复权方式和统计窗口；它与组合最大回撤不是同一个概念。"},
 "相对指数收益":{definition:"标的收益率减去同期基准指数收益率，用于评估相对市场表现。",formula:"超额收益（百分点）= 个股同期收益率−基准指数同期收益率。",interpretation:"跑赢指数仍可能绝对亏损，必须同时观察绝对收益与风险。"},
 "回撤":{definition:"价格、净值或组合权益从历史或观察区间高点到后续低点的下降幅度。",formula:"回撤（%）=（当前值−此前峰值）÷此前峰值×100%；最大回撤为观察窗口内最深回撤。",interpretation:"回撤以峰值为基准，与以买入成本计算的收益率不同。"},
 "止盈":{definition:"在预定盈利或结构条件出现时，按计划部分或全部退出持仓的风险管理方法。",interpretation:"固定比例、移动止盈和分批止盈各有适用条件，需要结合波动率、流动性和交易成本。"},
 "止损":{definition:"在亏损阈值或策略失效条件触发时，尝试减少风险敞口的交易管理措施。",interpretation:"A股的隔夜跳空、跌停、流动性不足会使实际退出价与计划价不同。"},
 "T+1":{definition:"普通A股的股票交易制度：当日买入的股票，通常最早在下一个交易日卖出。",interpretation:"不能用盘中当天买卖来假设收益，回测也要包含隔夜风险与可交易性限制。"},
 "D+1":{definition:"以股票候选冻结的交易日为D日，其后的第一个交易日。",interpretation:"D+1绝对收益只是按约定价格基准回看结果，不等于已经按该价成交。"},
 "D+3":{definition:"以候选冻结交易日为D日，其后的第三个交易日。",interpretation:"D+3盘中触发条件必须按当期约定的最高价等规则核验，不可事后倒推买卖时点。"},
 "A池":{definition:"研究系统中证据相对充分、满足既定准入规则的重点观察候选。",interpretation:"A池代表筛选条件满足程度，不代表确定上涨或必须交易。"},
 "B池":{definition:"研究系统中部分条件已满足、仍需等待量价或资金等信号确认的候选。",interpretation:"等待确认与实际入场之间存在区别，不能把盘中触及观察价当作实盘买入。"},
 "C池":{definition:"被判定为过热、失效或暂时淘汰的研究样本。",interpretation:"保留C池及失败样本是避免幸存者偏差、客观复盘的必要条件。"},
 "催化":{definition:"可能触发市场对公司未来盈利、估值或风险定价重新评估的事件。",interpretation:"例如业绩公告、订单或政策变更；催化存在不等于行情尚未反映或后续一定上涨。"},
 "环比":{definition:"本期指标与紧邻上一可比时期指标进行比较。",formula:"环比变化率（%）=（本期值−上期值）÷上期值×100%。",interpretation:"对股票市场双日对比，应写清比较的是上一交易日，而不只是前一自然日。"}
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
 const entry=glossary[key];
 tip.append(make("strong","",key));
 tip.append(make("small","term-label","标准定义"));
 tip.append(make("p","",entry.definition));
 if(entry.formula){tip.append(make("small","term-label","计算方式"));tip.append(make("p","term-formula",entry.formula))}
 tip.append(make("small","term-label","分析要点"));
 tip.append(make("p","",entry.interpretation));
 tip.append(make("small","tip","术语说明是辅助学习资料，报告正文、原始数据与当期结论保持不变。"),close);
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
   b.setAttribute("aria-label",m[0]+"，查看专业定义和计算方法");
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
   summary.append(make("div","read-digest-head","本期要点 · 摘自原报告"),make("p","",preview),make("small","","以下是归档正文，未改变当时的观点和数据；历史摘要不等于原始全文。"));
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
   make("small","","保留专业术语与原文，按需查阅定义")
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