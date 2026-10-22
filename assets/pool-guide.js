/* This is a definition of THIS radar's internal stock watch pools,
   not a trading recommendation or an exchange's official classification. */
(()=>{
"use strict";
const make=(tag,cls,text)=>{const e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=text;return e};
const pools=[
 {letter:"A",meaning:"优先跟踪 · 证据较充分",
  explain:"价量结构、板块资金、明确催化等核心证据中至少三项能够核验，并通过流动性及重大风险排查。",
  action:"交易含义：优先核对下一交易日的明确买入触发条件；不是直接买入指令。"},
 {letter:"B",meaning:"重点观察 · 等待确认",
  explain:"方向或催化具有观察价值，但突破收盘确认、量能、行业协同等条件尚未全部满足。",
  action:"交易含义：保持跟踪，等待条件触发；未确认不能当作已经入场。"},
 {letter:"C",meaning:"风险/过热/失效 · 暂缓",
  explain:"原观察结构失效、行情明显拥挤或风险上升，暂不符合当前策略的新增入场条件。",
  action:"交易含义：停止按旧信号追入；已有持仓仍按实际成本和退出规则独立管理。"}
];
function mount(target){
 if(!target||target.dataset.poolGuideReady==="1")return;
 target.dataset.poolGuideReady="1";
 const guide=make("section","pool-guide");
 guide.setAttribute("aria-label","A池 B池 C池定义及使用方法");
 if(target.dataset.poolGuideTheme==="light")guide.classList.add("pool-guide-light");
 const head=make("div","pool-guide-head");
 head.append(make("h4","pool-guide-title","A / B / C 池是什么？"),
   make("small","","按选股信号成熟度和风险状态分层"));
 guide.append(head);
 const grid=make("div","pool-guide-grid");
 for(const p of pools){
   const card=make("div","pool-guide-card pool-"+p.letter);
   card.append(make("strong","name",p.letter+"池"),make("span","meaning",p.meaning),
     make("p","explain",p.explain),make("p","action",p.action));
   grid.append(card);
 }
 guide.append(grid);
 const detail=make("details","pool-guide-details");
 detail.append(make("summary","","查看分池、升级与降级规则"));
 detail.append(
  make("p","","B → A：价格突破与成交量、行业资金和催化证据达到当期要求，且风险排查通过；即使升级，也必须满足单独的买入条件。"),
  make("p","","A/B → C：关键支撑或结构失效、预期催化落空、流动性恶化，或上涨过快导致风险收益比明显变差。"),
  make("p","","C → B：原失效原因得到新的数据验证后，才能重新成为观察候选；不凭股价反弹自动恢复。"),
  make("p","","池别按每一期报告记录，之后可以变化；历史报告不因后来的行情改写。缺少原始分池证据时显示「未注明池别」，不强制归类。")
 );
 guide.append(detail);
 guide.append(make("p","pool-guide-note","说明：A/B/C是本工具的研究分类，不是交易所评级、股票评级或盈利概率。历史候选不代表真实持仓；「没有新候选」不等于数据缺失。"));
 target.append(guide);
}
function init(){document.querySelectorAll("[data-pool-guide]").forEach(mount)}
window.RadarPoolGuide={mount,init};
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",init,{once:true});else init();
})();