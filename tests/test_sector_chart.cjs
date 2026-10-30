/* Regression test against REAL dated reports; no simulated market amounts. */
"use strict";
const assert=require("node:assert/strict");
const fs=require("node:fs");
const vm=require("node:vm");
class Elem{
 constructor(tag){this.tagName=tag.toUpperCase();this.children=[];this.className="";this.style={};this.dataset={};this.attributes={};this.textContent="";}
 append(...children){this.children.push(...children);return this}
 setAttribute(name,value){this.attributes[name]=value}
}
const window={};
const document={createElement(tag){return new Elem(tag)}};
vm.runInNewContext(fs.readFileSync("assets/report-template.js","utf8"),{window,document});
const {sectorColumns,industryGraphic,formatFundDate}=window.RadarReportTemplate;
assert.equal(window.RadarReportTemplate.version,"2026.10-v1.3");
function actualMarkdownTable(day){
 const src=fs.readFileSync("reports/"+day+".md","utf8");
 const start=src.indexOf("## 三、10个申万一级行业双日对照");
 const end=src.indexOf("\n## 四、",start);
 assert(start>=0&&end>start,"missing sector chapter "+day);
 const lines=src.slice(start,end).split("\n");
 const at=lines.findIndex(x=>x.startsWith("|")&&x.includes("申万一级行业")&&x.includes("净额"));
 assert(at>=0,"missing sector table "+day);
 const split=x=>x.trim().replace(/^\||\|$/g,"").split("|").map(c=>c.trim().replace(/\*\*/g,""));
 const headings=split(lines[at]);
 const rows=[];
 for(let i=at+2;i<lines.length&&lines[i].startsWith("|");i++)rows.push(split(lines[i]));
 return {headings,rows};
}
function check(day,labels){
 const {headings,rows}=actualMarkdownTable(day);
 const table={
  querySelectorAll(sel){
   if(sel==="thead th")return headings.map(textContent=>({textContent}));
   if(sel==="tbody tr")return rows.map(cells=>({children:cells.map(textContent=>({textContent}))}));
   throw new Error("unsupported query: "+sel);
  },
  closest(){return wrapper;}
 };
 let chart=null;
 const wrapper={nextElementSibling:null,before(element){chart=element}};
 const slot={querySelectorAll(sel){assert.equal(sel,"table");return [table]}};
 const columns=sectorColumns(table);
 assert.equal(columns.indices.length,2,day+": expected exactly two dated net columns");
 assert.deepEqual([...columns.indices],[1,2],day+": must not confuse with delta and intensity");
 assert.deepEqual(Array.from(columns.indices,i=>formatFundDate(headings[i],day)),labels);
 industryGraphic(slot,day);
 assert(chart,day+": no chart generated");
 assert.equal(chart.dataset.rowCount,"10",day+": should chart all 10 verified industries");
 const displayed=chart.children.filter(x=>x.className==="frame-funds-row");
 assert.equal(displayed.length,10);
 const nums=rows.flatMap(x=>[Number(x[1]),Number(x[2])]);
 const max=Math.max(...nums.map(Math.abs));
 assert.equal(Number(chart.dataset.scaleMaximum),max);
 for(let i=0;i<10;i++){
  const group=displayed[i];
  assert.equal(group.children[0].textContent,rows[i][0]);
  const pairs=group.children[1].children;
  assert.equal(pairs.length,2);
  for(let j=0;j<2;j++){
   const [label,track,amount]=pairs[j].children;
   assert.equal(label.textContent,labels[j]);
   const value=Number(rows[i][j+1]);
   assert.equal(amount.textContent,(value>0?"+":"")+value.toFixed(2));
   const bar=track.children[0];
   assert(bar.className.includes(value<0?"negative":"positive"));
   assert(Math.abs(Number(bar.style.width.slice(0,-1))-Math.abs(value)/max*50)<=0.001,
      "all bars must share max across all 20 values; "+rows[i][0]);
  }
 }
 return {chart,rows};
}
check("2026-10-28",["10月27日主力净额","10月28日主力净额"]);
check("2026-10-26",["10月23日主力净额","10月26日主力净额"]);
check("2026-10-23",["10月22日主力净额","10月23日主力净额"]);
const prior=JSON.parse(fs.readFileSync("data/industry-flows/2026-10-27.json","utf8"));
const current=JSON.parse(fs.readFileSync("data/industry-flows/2026-10-28.json","utf8"));
const checkWindow=window.RadarReportTemplate.checkFundsWindow;
const pTime=checkWindow(prior,"2026-10-27"),cTime=checkWindow(current,"2026-10-28");
assert.equal(prior.source_id,current.source_id,"provider must match");
assert.equal(prior.industry_classification,current.industry_classification);
assert.equal(prior.metric,current.metric);
assert.equal(prior.unit,current.unit);
assert.deepEqual(prior.trading_session,current.trading_session,"industry trading windows must be exactly identical");
assert.equal(prior.trading_session.aggregation,"full_regular_session");
assert.equal(prior.trading_session.start,"09:30");
assert.equal(prior.trading_session.end,"15:00");
const corrupt=structuredClone(prior);
corrupt.trading_session.end="14:30";
assert.throws(()=>checkWindow(corrupt,"2026-10-27"),/数据源、申万分类或单位不一致/);
assert.equal(Math.round(Math.abs(pTime-cTime)/1000),24*3600-1065,"publish times vary by 17m45s across consecutive dates");
const day28=actualMarkdownTable("2026-10-28");
for(const row of day28.rows){
 const p=prior.industries.find(x=>x.name===row[0]);
 const c=current.industries.find(x=>x.name===row[0]);
 assert(p&&c,"sector must exist on both days");
 assert.equal(Number(row[1]),p.net_yi);
 assert.equal(Number(row[2]),c.net_yi);
}
const css=fs.readFileSync("assets/report-template.css","utf8");
for(const pattern of [
 /\.frame-funds\{[^}]*background:var\(--funds-bg\)/,
 /\.frame-funds-track:before\{[^}]*left:50%/,
 /\.frame-funds-bar\.positive\{left:50%/,
 /\.frame-funds-bar\.negative\{right:50%/,
 /\.frame-funds-row\{[^}]*grid-template-columns/,
 /\.frame-funds-evidence\{[^}]*display:flex/,
])assert(pattern.test(css),"Missing shared-centered chart style: "+pattern);
console.log("PASS: 28/26/23 original reports render full 10-sector true-scale centered-zero cards, precise labels and amounts.");
