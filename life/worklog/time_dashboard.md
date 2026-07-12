# Time Dashboard

Updated: 2026-07-12T18:41:30+08:00

This dashboard is evidence for weekly journal review. It describes work time allocation; rest, entertainment, open sessions, and sessions needing review are excluded from totals, charts, and rankings.

<style>
.worklog-review-table {
  width: 100%;
  border-collapse: collapse;
  margin: 0.75rem 0 1rem;
}
.worklog-review-table th,
.worklog-review-table td {
  border-bottom: 1px solid var(--background-modifier-border);
  padding: 0.45rem 0.6rem;
  text-align: left;
}
.worklog-review-table th {
  border-top: 1px solid var(--background-modifier-border);
  color: var(--text-muted);
  font-size: 0.85em;
  font-weight: 650;
}
.worklog-review-table .num {
  text-align: right;
  font-variant-numeric: tabular-nums;
}
.worklog-review-table .empty {
  color: var(--text-muted);
  text-align: center;
}
</style>

## Outline

- [Current Session](#current-session)
- [Daily Overview](#daily-overview)
- [Weekly Overview](#weekly-overview)
- [Monthly Overview](#monthly-overview)
- [Trend Overview](#trend-overview)
- [Year Overview](#year-overview)
- [All-Time Overview](#all-time-overview)
- [Review Flags](#review-flags)

## Current Session

None

## Daily Overview

今日做事總量、目前 session、今日是否有正式做事紀錄。


```dataviewjs
const raw = await dv.io.load("life/worklog/data/time_daily_stats_2026-07.json");
const data = JSON.parse(raw);
let prevData = {days: []};
try {
  const prevRaw = await dv.io.load("life/worklog/data/time_daily_stats_2026-06.json");
  prevData = JSON.parse(prevRaw);
} catch (e) {}
const view = "daily";
const cats = ["course", "research", "self_study", "language", "leetcode", "admin", "other"];
const labels = data.category_labels || {};
const color = {course:"#4f83ff", research:"#2fbf71", self_study:"#8b6cff", language:"#e56ab3", leetcode:"#f59f00", admin:"#8a8f98", rest:"#41b6c4", entertainment:"#ff6b6b", other:"#6c757d"};
const fmt = (min) => { const h = Math.floor((min || 0) / 60); const m = (min || 0) % 60; return h ? `${h}h${m ? " " + m + "m" : ""}` : `${m}m`; };
const targets = {daily:240, weekly:1500, monthly:6000};
const targetText = (cur, goal) => `${fmt(cur)} / ${fmt(goal)} (${goal ? Math.round((cur / goal) * 100) : 0}%)`;
const restConfig = {
  weeklyRestDays: [],
  restDaysPerWeek: 1,
  decisionWeekday: 1,
  restDates: []
};
const weekday = (iso) => new Date(`${iso}T00:00:00+08:00`).getDay();
const weekStart = (iso) => { const dt = new Date(`${iso}T00:00:00+08:00`); dt.setDate(dt.getDate() - ((dt.getDay() + 6) % 7)); return dt.toISOString().slice(0,10); };
const currentWeekRestDates = (iso) => restConfig.restDates.filter(date => weekStart(date) === weekStart(iso));
const isPlannedRest = (d) => restConfig.restDates.includes(d.date) || restConfig.weeklyRestDays.includes(weekday(d.date));
const isDecisionDay = (d) => weekday(d.date) === restConfig.decisionWeekday;
const expectedWorkDays = (days) => { const selected=days.filter(isPlannedRest).length; if(selected) return days.length - selected; const weeks=new Set(days.map(d=>weekStart(d.date))).size; return Math.max(0, days.length - Math.min(days.length, weeks * restConfig.restDaysPerWeek)); };
const expectedRollingWorkDays = (days) => { const selected=days.filter(isPlannedRest).length; if(selected) return days.length - selected; return Math.max(0, days.length - Math.min(restConfig.restDaysPerWeek, days.length)); };
const completionText = (active, expected) => `${active} / ${expected} (${expected ? Math.round((active / expected) * 100) : 0}%)`;
const todayIso = new Date().toLocaleDateString("sv-SE", {timeZone: "Asia/Taipei"});
const allDays = [...(prevData.days || []), ...(data.days || [])].reduce((map,d)=>map.set(d.date,d),new Map());
const timeline = [...allDays.values()].sort((a,b)=>a.date.localeCompare(b.date));
let todayIndex = timeline.findIndex(d => d.date === todayIso); if (todayIndex < 0) todayIndex = timeline.length - 1;
const today = timeline.find(d => d.date === todayIso) || {total_min:0, by_category:{}, session_count:0, work_session_count:0, longest_session_min:0, work_longest_session_min:0};
const recent7 = timeline.slice(Math.max(0, todayIndex - 6), todayIndex + 1);
const recent14 = timeline.slice(Math.max(0, todayIndex - 13), todayIndex + 1);
const prev7 = timeline.slice(Math.max(0, todayIndex - 13), Math.max(0, todayIndex - 6));
const prev14 = timeline.slice(Math.max(0, todayIndex - 27), Math.max(0, todayIndex - 13));
const dayWorkMin = (d) => cats.reduce((sum,c)=>sum+(d.by_category?.[c]||0),0);
const categoryTotals = (days) => { const totals=Object.fromEntries(cats.map(c=>[c,0])); for (const day of days) for (const c of cats) totals[c] += day.by_category?.[c] || 0; return totals; };
const mainWorkCategory = (d) => cats.reduce((best,c)=>(d.by_category?.[c]||0)>(d.by_category?.[best]||0)?c:best,"other");
const monthTotal = data.days.reduce((sum,d)=>sum+dayWorkMin(d),0);
const activeDays = data.days.filter(d=>dayWorkMin(d)>0).length;
const expectedMonthDays = expectedWorkDays(data.days);
const dailyAvg = activeDays ? Math.round(monthTotal/activeDays) : 0;
const expectedAvg = expectedMonthDays ? Math.round(monthTotal/expectedMonthDays) : 0;
const best = data.days.reduce((a,b)=>dayWorkMin(b)>dayWorkMin(a)?b:a,{by_category:{},date:""});
const catTotals = categoryTotals(data.days);
const rankedDays = data.days.filter(d=>dayWorkMin(d)>0).sort((a,b)=>dayWorkMin(b)-dayWorkMin(a)).slice(0,5);
const rankedCats = cats.map(c=>({key:c,label:labels[c]||c,total:catTotals[c]||0})).filter(c=>c.total>0).sort((a,b)=>b.total-a.total).slice(0,5);
const sumDays = (days) => days.reduce((sum, d) => sum + dayWorkMin(d), 0);
const pct = (cur, prev) => prev ? `${cur >= prev ? "+" : ""}${Math.round(((cur - prev) / prev) * 100)}%` : (cur ? "new" : "0%");
const style = document.createElement("style");
style.textContent = `.time-summary{display:grid;grid-template-columns:repeat(4,minmax(120px,1fr));gap:10px;margin:10px 0 16px}.time-card{border:1px solid var(--background-modifier-border);border-radius:10px;padding:10px 12px;background:var(--background-secondary)}.time-card-k{color:var(--text-muted);font-size:12px}.time-card-v{font-size:22px;font-weight:750;margin-top:4px}.time-empty{border:1px dashed var(--background-modifier-border);border-radius:10px;padding:18px;color:var(--text-muted);background:var(--background-secondary);margin:10px 0}.time-legend{display:flex;flex-wrap:wrap;gap:8px 12px;margin:8px 0 12px;font-size:12px;color:var(--text-muted)}.time-dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:4px}.time-section-title{font-size:13px;font-weight:650;margin:14px 0 6px;color:var(--text-muted)}.time-month-grid{display:grid;grid-template-columns:repeat(7,minmax(48px,1fr));gap:6px;margin:8px 0 16px;max-width:780px}.time-day{border:1px solid var(--background-modifier-border);border-radius:8px;min-height:58px;padding:6px;background:var(--background-secondary);box-shadow:inset 0 1px 0 rgba(255,255,255,.04)}.time-day.rest{border-style:dashed}.time-date{font-size:11px;color:var(--text-muted)}.time-total{font-size:13px;font-weight:650;margin-top:4px}.time-cat{height:5px;border-radius:4px;margin-top:7px;opacity:.9}.time-chart{width:100%;max-width:780px;height:150px;border:1px solid var(--background-modifier-border);border-radius:10px;background:var(--background-secondary);margin:8px 0 16px;overflow:hidden}.time-chart.tall{height:190px}.time-stack{display:flex;height:24px;width:100%;max-width:780px;overflow:hidden;border-radius:999px;background:var(--background-secondary);border:1px solid var(--background-modifier-border)}.time-stack-part{height:100%;min-width:2px}.time-pie-wrap{display:grid;grid-template-columns:180px minmax(220px,1fr);gap:16px;align-items:center;max-width:780px;margin:8px 0 16px}.time-pie{width:160px;aspect-ratio:1;border-radius:50%;border:1px solid var(--background-modifier-border)}.time-pie-legend{border:1px solid var(--background-modifier-border);border-radius:8px;background:var(--background-secondary);overflow:hidden}.time-pie-row{display:grid;grid-template-columns:14px 1fr auto auto;gap:8px;align-items:center;padding:7px 10px;border-bottom:1px solid var(--background-modifier-border);font-size:13px}.time-pie-row:last-child{border-bottom:0}.time-pie-swatch{width:10px;height:10px;border-radius:50%}.time-pie-val,.time-pie-pct{font-variant-numeric:tabular-nums;font-weight:650}.time-pie-pct{color:var(--text-muted)}.time-rank-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;max-width:780px;margin:14px 0 16px}.time-rank-panel{min-width:0}.time-rank-title{font-size:13px;font-weight:650;margin:0 0 6px;color:var(--text-muted)}.time-rank{border:1px solid var(--background-modifier-border);border-radius:8px;background:var(--background-secondary);overflow:hidden}.time-rank-row{display:grid;grid-template-columns:34px minmax(0,1fr) auto;gap:10px;align-items:center;padding:8px 10px;border-bottom:1px solid var(--background-modifier-border)}.time-rank-row:last-child{border-bottom:0}.time-rank-no{font-weight:750;color:var(--text-accent)}.time-rank-name{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.time-rank-val{font-variant-numeric:tabular-nums;font-weight:650;white-space:nowrap}.time-bars{display:grid;gap:7px;max-width:780px;margin:8px 0 16px}.time-bar-row{display:grid;grid-template-columns:88px minmax(0,1fr) auto;gap:10px;align-items:center}.time-bar-name{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--text-muted);font-size:13px}.time-bar-track{height:10px;border-radius:999px;background:var(--background-secondary);border:1px solid var(--background-modifier-border);overflow:hidden}.time-bar-fill{height:100%;min-width:2px}.time-bar-val{font-variant-numeric:tabular-nums;font-weight:650;white-space:nowrap;font-size:13px}@media (max-width:650px){.time-summary{grid-template-columns:repeat(2,minmax(0,1fr))}.time-month-grid{grid-template-columns:repeat(4,minmax(0,1fr))}.time-pie-wrap,.time-rank-grid,.time-bars{grid-template-columns:1fr}.time-pie{justify-self:center}}.time-tip{position:fixed;z-index:9999;pointer-events:none;background:var(--background-primary);border:1px solid var(--background-modifier-border);box-shadow:0 8px 24px rgba(0,0,0,.18);border-radius:8px;padding:8px 10px;font-size:12px;color:var(--text-normal);max-width:240px;white-space:pre-line;opacity:0;transform:translate(10px,10px);transition:opacity .08s ease}`;
dv.container.appendChild(style);
const cards = (items) => { const el=dv.el("div","",{cls:"time-summary"}); el.innerHTML=items.map(([k,v])=>`<div class="time-card"><div class="time-card-k">${k}</div><div class="time-card-v">${v}</div></div>`).join(""); };
const empty = (msg) => dv.el("div", msg, {cls:"time-empty"});
const legend = () => { const el=dv.el("div","",{cls:"time-legend"}); el.innerHTML=cats.map(c=>`<span><i class="time-dot" style="background:${color[c]}"></i>${labels[c]||c}</span>`).join(""); };
const tip=dv.el("div","",{cls:"time-tip"});
const showTip=(text,ev)=>{tip.textContent=text||"";tip.style.left=ev.clientX+12+"px";tip.style.top=ev.clientY+12+"px";tip.style.opacity="1";};
const hideTip=()=>{tip.style.opacity="0";};
const bindTips=(root)=>{root.querySelectorAll("[data-tip]").forEach(el=>{el.addEventListener("mousemove",ev=>showTip(el.dataset.tip,ev));el.addEventListener("mouseleave",hideTip);});};
const stackBar = (totals) => { const total=Object.values(totals).reduce((a,b)=>a+b,0); const el=dv.el("div","",{cls:"time-stack"}); el.innerHTML=total?cats.filter(c=>(totals[c]||0)>0).map(c=>`<div class="time-stack-part" data-tip="${labels[c]||c}&#10;${fmt(totals[c])}&#10;${Math.round((totals[c]/total)*100)}%" style="width:${(totals[c]/total)*100}%;background:${color[c]}"></div>`).join(""):`<div class="time-stack-part" style="width:100%;background:var(--background-modifier-border)"></div>`; bindTips(el); };
const pieChart = (title, totals) => { const rows=cats.map(c=>({key:c,label:labels[c]||c,total:totals[c]||0})).filter(r=>r.total>0); const total=rows.reduce((s,r)=>s+r.total,0); dv.el("div",title,{cls:"time-section-title"}); const el=dv.el("div","",{cls:"time-pie-wrap"}); if(!total){el.innerHTML=`<div class="time-pie" style="background:var(--background-modifier-border)"></div><div class="time-pie-legend"><div class="time-pie-row">No data</div></div>`; return;} let acc=0; const gradient=rows.map(r=>{const start=(acc/total)*100; acc+=r.total; const end=(acc/total)*100; return `${color[r.key]} ${start}% ${end}%`;}).join(","); el.innerHTML=`<div class="time-pie" data-tip="${rows.map(r=>`${r.label} ${Math.round((r.total/total)*100)}%`).join("&#10;")}" style="background:conic-gradient(${gradient})"></div><div class="time-pie-legend">${rows.map(r=>`<div class="time-pie-row"><span class="time-pie-swatch" style="background:${color[r.key]}"></span><span>${r.label}</span><span class="time-pie-val">${fmt(r.total)}</span><span class="time-pie-pct">${Math.round((r.total/total)*100)}%</span></div>`).join("")}</div>`; bindTips(el); };
const categoryBars = (title, totals) => { const rows=cats.map(c=>({key:c,label:labels[c]||c,total:totals[c]||0})).filter(r=>r.total>0).sort((a,b)=>b.total-a.total); const max=Math.max(1,...rows.map(r=>r.total)); dv.el("div",title,{cls:"time-section-title"}); const el=dv.el("div","",{cls:"time-bars"}); el.innerHTML=rows.length?rows.map(r=>`<div class="time-bar-row"><div class="time-bar-name">${r.label}</div><div class="time-bar-track"><div class="time-bar-fill" style="width:${Math.max(2,(r.total/max)*100)}%;background:${color[r.key]}"></div></div><div class="time-bar-val">${fmt(r.total)}</div></div>`).join(""):`<div class="time-empty">No data</div>`; };
const rankRows = (title, rows) => `<div class="time-rank-panel"><div class="time-rank-title">${title}</div><div class="time-rank">${rows.length?rows.map((r,i)=>`<div class="time-rank-row"><div class="time-rank-no">#${i+1}</div><div class="time-rank-name">${r.name}</div><div class="time-rank-val">${fmt(r.total)}</div></div>`).join(""):`<div class="time-rank-row"><div class="time-rank-name">No data</div></div>`}</div></div>`;
const rankGrid = (groups) => { const grid=dv.el("div","",{cls:"time-rank-grid"}); grid.innerHTML=groups.map(g=>rankRows(g.title,g.rows)).join(""); };
const rankedCategoryRows = (totals) => cats.map(c=>({key:c,name:labels[c]||c,total:totals[c]||0})).filter(c=>c.total>0).sort((a,b)=>b.total-a.total).slice(0,5);
const dayRankRows = (days) => days.filter(d=>dayWorkMin(d)>0).sort((a,b)=>dayWorkMin(b)-dayWorkMin(a)).slice(0,5).map(d=>({name:d.date.slice(5),total:dayWorkMin(d)}));
const lineChart = (days, accessor, stroke="var(--text-accent)") => { const el=dv.el("div","",{cls:"time-chart"}); const w=780,h=150,pad=24; const max=Math.max(60,...days.map(accessor)); const points=days.map((d,i)=>{const x=pad+(days.length<=1?0:i*((w-pad*2)/(days.length-1))); const y=h-pad-(accessor(d)/max)*(h-pad*2); return [x,y,d,i];}); const poly=points.map(p=>`${p[0]},${p[1]}`).join(" "); const step=Math.max(1,Math.ceil(days.length/6)); const grid=[.25,.5,.75,1].map(r=>{const yy=h-pad-r*(h-pad*2); return `<line x1="${pad}" x2="${w-pad}" y1="${yy}" y2="${yy}" stroke="var(--background-modifier-border)" stroke-width="1" vector-effect="non-scaling-stroke"/><text x="4" y="${yy+4}" font-size="10" fill="var(--text-muted)">${fmt(Math.round(max*r))}</text>`;}).join(""); el.innerHTML=`<svg viewBox="0 0 ${w} ${h}" width="100%" height="150" preserveAspectRatio="none">${grid}<polyline points="${poly}" fill="none" stroke="${stroke}" stroke-width="3" vector-effect="non-scaling-stroke"/>${points.map(p=>`<circle cx="${p[0]}" cy="${p[1]}" r="5" fill="${stroke}" data-tip="${p[2].date}&#10;${fmt(accessor(p[2]))}"></circle>`).join("")}${points.filter(p=>p[3]===0||p[3]===points.length-1||p[3]%step===0).map(p=>`<text x="${p[0]}" y="${h-5}" font-size="10" text-anchor="middle" fill="var(--text-muted)">${p[2].date.slice(5)}</text>`).join("")}</svg>`; bindTips(el); };
if(view==="daily"){ const todayWork=dayWorkMin(today); const plannedRest=isPlannedRest(today); const weekRest=currentWeekRestDates(today.date); const restStatus=weekRest.length?weekRest.map(d=>d.slice(5)).join(", "):(isDecisionDay(today)?"Pick today":"Unset"); const plan=plannedRest?"Rest":(isDecisionDay(today)?"Decide":"Work"); cards([["Today",fmt(todayWork)],["Target",targetText(todayWork,targets.daily)],["Plan",plan],["Rest Rule",`${restConfig.restDaysPerWeek} / week`],["This Week Rest",restStatus],["Sessions",String(today.work_session_count||0)],["Longest",fmt(today.work_longest_session_min||0)],["Active",todayWork?"Yes":(plannedRest?"Rest":"No")]]); if(!todayWork) empty(plannedRest ? "今天是設定休息日，沒有正式做事時間紀錄。" : (isDecisionDay(today) ? "今天是本週休息日決策日，目前還沒有正式做事時間紀錄。" : "今天還沒有正式做事時間紀錄。")); else { legend(); const t=categoryTotals([today]); stackBar(t); rankGrid([{title:"今日類別排名",rows:rankedCategoryRows(t)}]); } }
if(view==="weekly"){ const total=sumDays(recent7); const active=recent7.filter(d=>dayWorkMin(d)>0).length; const expected=expectedRollingWorkDays(recent7); const t=categoryTotals(recent7); cards([["7 Days",fmt(total)],["Target",targetText(total,targets.weekly)],["Daily Avg",fmt(active?Math.round(total/active):0)],["Expected Avg",fmt(expected?Math.round(total/expected):0)],["Active Days",String(active)],["Expected",String(expected)],["Completion",completionText(active,expected)],["Best",fmt(Math.max(0,...recent7.map(d=>dayWorkMin(d))))]]); if(!total) empty("最近一週還沒有正式做事時間紀錄。"); else { lineChart(recent7,d=>dayWorkMin(d)); categoryBars("近 7 天類別長條", t); rankGrid([{title:"近 7 天日排名",rows:dayRankRows(recent7)},{title:"近 7 天類別排名",rows:rankedCategoryRows(t)}]); } }
if(view==="monthly"){ cards([["Month",fmt(monthTotal)],["Target",targetText(monthTotal,targets.monthly)],["Daily Avg",fmt(dailyAvg)],["Expected Avg",fmt(expectedAvg)],["Active Days",String(activeDays)],["Expected",String(expectedMonthDays)],["Completion",completionText(activeDays,expectedMonthDays)],["Best Day",best.date?best.date.slice(5):"-"]]); if(!monthTotal){empty("本月還沒有正式做事時間紀錄。"); return;} legend(); const max=Math.max(60,...data.days.map(d=>dayWorkMin(d))); const grid=dv.el("div","",{cls:"time-month-grid"}); for(const day of data.days){ const work=dayWorkMin(day); const main=mainWorkCategory(day); const intensity=Math.max(.12,work/max); const plannedRest=isPlannedRest(day); const cell=document.createElement("div"); cell.className=plannedRest?"time-day rest":"time-day"; cell.style.boxShadow=`inset 0 -3px 0 ${color[main]||color.other}`; cell.style.opacity=work?String(.55+intensity*.45):".45"; cell.dataset.tip=`${day.date}\n${plannedRest?"planned rest":"planned work"}\n${fmt(work)}\n${labels[main]||main}\n${day.session_count||0} sessions`; cell.innerHTML=`<div class="time-date">${day.date.slice(5)}</div><div class="time-total">${fmt(work)}</div><div class="time-cat" style="background:${color[main]||color.other}"></div>`; grid.appendChild(cell);} bindTips(grid); stackBar(catTotals); pieChart("本月類別占比", catTotals); categoryBars("本月類別長條", catTotals); rankGrid([{title:"本月日排名",rows:rankedDays.map(d=>({name:d.date.slice(5),total:dayWorkMin(d)}))},{title:"本月類別排名",rows:rankedCats.map(c=>({name:c.label,total:c.total}))}]); }
if(view==="trend"){
  if(!monthTotal){empty("有時間紀錄後，這裡會顯示週期比較、近 14 天、累積曲線、開始/結束時間。"); return;}
  const cur7 = sumDays(recent7), old7 = sumDays(prev7);
  const cur14 = sumDays(recent14), old14 = sumDays(prev14);
  const dayOfMonth = Number(todayIso.slice(8));
  const prevSamePeriod = prevData.days.slice(0, dayOfMonth);
  const prevMonthToDate = sumDays(prevSamePeriod);
  cards([
    ["7d vs prev", `${fmt(cur7)} / ${pct(cur7, old7)}`],
    ["14d vs prev", `${fmt(cur14)} / ${pct(cur14, old14)}`],
    ["MTD vs last", `${fmt(monthTotal)} / ${pct(monthTotal, prevMonthToDate)}`],
    ["Last MTD", fmt(prevMonthToDate)]
  ]);
  dv.el("div","近 14 天",{cls:"time-section-title"});
  lineChart(recent14,d=>dayWorkMin(d));
  rankGrid([{title:"近 14 天日排名",rows:dayRankRows(recent14)},{title:"近 14 天類別排名",rows:rankedCategoryRows(categoryTotals(recent14))}]);
  dv.el("div","本月累積",{cls:"time-section-title"});
  let running=0;
  const cumulative=data.days.map(d=>({date:d.date,total_min:running+=dayWorkMin(d),by_category:d.by_category}));
  lineChart(cumulative,d=>d.total_min,"#ff7a1a");
  dv.el("div","開始 / 結束時間",{cls:"time-section-title"});
  const rhythmDays=data.days.filter(d=>d.work_first_start_min!==null||d.work_last_end_min!==null);
  const el=dv.el("div","",{cls:"time-chart tall"});
  const w=780,h=190,pad=26,minClock=6*60,maxClock=26*60;
  const y=m=>pad+((m-minClock)/(maxClock-minClock))*(h-pad*2);
  const x=(i,n)=>pad+(n<=1?0:i*((w-pad*2)/(n-1)));
  const ticks=[8,12,16,20,24];
  el.innerHTML=`<svg viewBox="0 0 ${w} ${h}" width="100%" height="190" preserveAspectRatio="none">${ticks.map(hr=>`<line x1="${pad}" x2="${w-pad}" y1="${y(hr*60)}" y2="${y(hr*60)}" stroke="var(--background-modifier-border)" stroke-dasharray="4 5"/><text x="4" y="${y(hr*60)+4}" font-size="10" fill="var(--text-muted)">${hr}</text>`).join("")}${rhythmDays.map((d,i)=>{const xx=x(i,Math.max(1,rhythmDays.length)); const s=d.work_first_start_min??d.work_last_end_min; const e=d.work_last_end_min??d.work_first_start_min; const step=Math.max(1,Math.ceil(rhythmDays.length/6)); const label=(i===0||i===rhythmDays.length-1||i%step===0)?`<text x="${xx}" y="${h-5}" font-size="10" text-anchor="middle" fill="var(--text-muted)">${d.date.slice(8)}</text>`:""; return `<line x1="${xx}" x2="${xx}" y1="${y(s)}" y2="${y(e)}" stroke="#adb5bd" stroke-width="2"/><circle cx="${xx}" cy="${y(s)}" r="5" fill="#ff7a1a" data-tip="${d.date}&#10;start ${Math.floor(s/60)}:${String(s%60).padStart(2,'0')}"></circle><circle cx="${xx}" cy="${y(e)}" r="5" fill="#e9ecef" data-tip="${d.date}&#10;end ${Math.floor(e/60)}:${String(e%60).padStart(2,'0')}"></circle>${label}`;}).join("")}</svg>`; bindTips(el);
}
```


## Weekly Overview

最近一週的做事總量、活躍天數、類別占比與短期節奏。


```dataviewjs
const raw = await dv.io.load("life/worklog/data/time_daily_stats_2026-07.json");
const data = JSON.parse(raw);
let prevData = {days: []};
try {
  const prevRaw = await dv.io.load("life/worklog/data/time_daily_stats_2026-06.json");
  prevData = JSON.parse(prevRaw);
} catch (e) {}
const view = "weekly";
const cats = ["course", "research", "self_study", "language", "leetcode", "admin", "other"];
const labels = data.category_labels || {};
const color = {course:"#4f83ff", research:"#2fbf71", self_study:"#8b6cff", language:"#e56ab3", leetcode:"#f59f00", admin:"#8a8f98", rest:"#41b6c4", entertainment:"#ff6b6b", other:"#6c757d"};
const fmt = (min) => { const h = Math.floor((min || 0) / 60); const m = (min || 0) % 60; return h ? `${h}h${m ? " " + m + "m" : ""}` : `${m}m`; };
const targets = {daily:240, weekly:1500, monthly:6000};
const targetText = (cur, goal) => `${fmt(cur)} / ${fmt(goal)} (${goal ? Math.round((cur / goal) * 100) : 0}%)`;
const restConfig = {
  weeklyRestDays: [],
  restDaysPerWeek: 1,
  decisionWeekday: 1,
  restDates: []
};
const weekday = (iso) => new Date(`${iso}T00:00:00+08:00`).getDay();
const weekStart = (iso) => { const dt = new Date(`${iso}T00:00:00+08:00`); dt.setDate(dt.getDate() - ((dt.getDay() + 6) % 7)); return dt.toISOString().slice(0,10); };
const currentWeekRestDates = (iso) => restConfig.restDates.filter(date => weekStart(date) === weekStart(iso));
const isPlannedRest = (d) => restConfig.restDates.includes(d.date) || restConfig.weeklyRestDays.includes(weekday(d.date));
const isDecisionDay = (d) => weekday(d.date) === restConfig.decisionWeekday;
const expectedWorkDays = (days) => { const selected=days.filter(isPlannedRest).length; if(selected) return days.length - selected; const weeks=new Set(days.map(d=>weekStart(d.date))).size; return Math.max(0, days.length - Math.min(days.length, weeks * restConfig.restDaysPerWeek)); };
const expectedRollingWorkDays = (days) => { const selected=days.filter(isPlannedRest).length; if(selected) return days.length - selected; return Math.max(0, days.length - Math.min(restConfig.restDaysPerWeek, days.length)); };
const completionText = (active, expected) => `${active} / ${expected} (${expected ? Math.round((active / expected) * 100) : 0}%)`;
const todayIso = new Date().toLocaleDateString("sv-SE", {timeZone: "Asia/Taipei"});
const allDays = [...(prevData.days || []), ...(data.days || [])].reduce((map,d)=>map.set(d.date,d),new Map());
const timeline = [...allDays.values()].sort((a,b)=>a.date.localeCompare(b.date));
let todayIndex = timeline.findIndex(d => d.date === todayIso); if (todayIndex < 0) todayIndex = timeline.length - 1;
const today = timeline.find(d => d.date === todayIso) || {total_min:0, by_category:{}, session_count:0, work_session_count:0, longest_session_min:0, work_longest_session_min:0};
const recent7 = timeline.slice(Math.max(0, todayIndex - 6), todayIndex + 1);
const recent14 = timeline.slice(Math.max(0, todayIndex - 13), todayIndex + 1);
const prev7 = timeline.slice(Math.max(0, todayIndex - 13), Math.max(0, todayIndex - 6));
const prev14 = timeline.slice(Math.max(0, todayIndex - 27), Math.max(0, todayIndex - 13));
const dayWorkMin = (d) => cats.reduce((sum,c)=>sum+(d.by_category?.[c]||0),0);
const categoryTotals = (days) => { const totals=Object.fromEntries(cats.map(c=>[c,0])); for (const day of days) for (const c of cats) totals[c] += day.by_category?.[c] || 0; return totals; };
const mainWorkCategory = (d) => cats.reduce((best,c)=>(d.by_category?.[c]||0)>(d.by_category?.[best]||0)?c:best,"other");
const monthTotal = data.days.reduce((sum,d)=>sum+dayWorkMin(d),0);
const activeDays = data.days.filter(d=>dayWorkMin(d)>0).length;
const expectedMonthDays = expectedWorkDays(data.days);
const dailyAvg = activeDays ? Math.round(monthTotal/activeDays) : 0;
const expectedAvg = expectedMonthDays ? Math.round(monthTotal/expectedMonthDays) : 0;
const best = data.days.reduce((a,b)=>dayWorkMin(b)>dayWorkMin(a)?b:a,{by_category:{},date:""});
const catTotals = categoryTotals(data.days);
const rankedDays = data.days.filter(d=>dayWorkMin(d)>0).sort((a,b)=>dayWorkMin(b)-dayWorkMin(a)).slice(0,5);
const rankedCats = cats.map(c=>({key:c,label:labels[c]||c,total:catTotals[c]||0})).filter(c=>c.total>0).sort((a,b)=>b.total-a.total).slice(0,5);
const sumDays = (days) => days.reduce((sum, d) => sum + dayWorkMin(d), 0);
const pct = (cur, prev) => prev ? `${cur >= prev ? "+" : ""}${Math.round(((cur - prev) / prev) * 100)}%` : (cur ? "new" : "0%");
const style = document.createElement("style");
style.textContent = `.time-summary{display:grid;grid-template-columns:repeat(4,minmax(120px,1fr));gap:10px;margin:10px 0 16px}.time-card{border:1px solid var(--background-modifier-border);border-radius:10px;padding:10px 12px;background:var(--background-secondary)}.time-card-k{color:var(--text-muted);font-size:12px}.time-card-v{font-size:22px;font-weight:750;margin-top:4px}.time-empty{border:1px dashed var(--background-modifier-border);border-radius:10px;padding:18px;color:var(--text-muted);background:var(--background-secondary);margin:10px 0}.time-legend{display:flex;flex-wrap:wrap;gap:8px 12px;margin:8px 0 12px;font-size:12px;color:var(--text-muted)}.time-dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:4px}.time-section-title{font-size:13px;font-weight:650;margin:14px 0 6px;color:var(--text-muted)}.time-month-grid{display:grid;grid-template-columns:repeat(7,minmax(48px,1fr));gap:6px;margin:8px 0 16px;max-width:780px}.time-day{border:1px solid var(--background-modifier-border);border-radius:8px;min-height:58px;padding:6px;background:var(--background-secondary);box-shadow:inset 0 1px 0 rgba(255,255,255,.04)}.time-day.rest{border-style:dashed}.time-date{font-size:11px;color:var(--text-muted)}.time-total{font-size:13px;font-weight:650;margin-top:4px}.time-cat{height:5px;border-radius:4px;margin-top:7px;opacity:.9}.time-chart{width:100%;max-width:780px;height:150px;border:1px solid var(--background-modifier-border);border-radius:10px;background:var(--background-secondary);margin:8px 0 16px;overflow:hidden}.time-chart.tall{height:190px}.time-stack{display:flex;height:24px;width:100%;max-width:780px;overflow:hidden;border-radius:999px;background:var(--background-secondary);border:1px solid var(--background-modifier-border)}.time-stack-part{height:100%;min-width:2px}.time-pie-wrap{display:grid;grid-template-columns:180px minmax(220px,1fr);gap:16px;align-items:center;max-width:780px;margin:8px 0 16px}.time-pie{width:160px;aspect-ratio:1;border-radius:50%;border:1px solid var(--background-modifier-border)}.time-pie-legend{border:1px solid var(--background-modifier-border);border-radius:8px;background:var(--background-secondary);overflow:hidden}.time-pie-row{display:grid;grid-template-columns:14px 1fr auto auto;gap:8px;align-items:center;padding:7px 10px;border-bottom:1px solid var(--background-modifier-border);font-size:13px}.time-pie-row:last-child{border-bottom:0}.time-pie-swatch{width:10px;height:10px;border-radius:50%}.time-pie-val,.time-pie-pct{font-variant-numeric:tabular-nums;font-weight:650}.time-pie-pct{color:var(--text-muted)}.time-rank-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;max-width:780px;margin:14px 0 16px}.time-rank-panel{min-width:0}.time-rank-title{font-size:13px;font-weight:650;margin:0 0 6px;color:var(--text-muted)}.time-rank{border:1px solid var(--background-modifier-border);border-radius:8px;background:var(--background-secondary);overflow:hidden}.time-rank-row{display:grid;grid-template-columns:34px minmax(0,1fr) auto;gap:10px;align-items:center;padding:8px 10px;border-bottom:1px solid var(--background-modifier-border)}.time-rank-row:last-child{border-bottom:0}.time-rank-no{font-weight:750;color:var(--text-accent)}.time-rank-name{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.time-rank-val{font-variant-numeric:tabular-nums;font-weight:650;white-space:nowrap}.time-bars{display:grid;gap:7px;max-width:780px;margin:8px 0 16px}.time-bar-row{display:grid;grid-template-columns:88px minmax(0,1fr) auto;gap:10px;align-items:center}.time-bar-name{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--text-muted);font-size:13px}.time-bar-track{height:10px;border-radius:999px;background:var(--background-secondary);border:1px solid var(--background-modifier-border);overflow:hidden}.time-bar-fill{height:100%;min-width:2px}.time-bar-val{font-variant-numeric:tabular-nums;font-weight:650;white-space:nowrap;font-size:13px}@media (max-width:650px){.time-summary{grid-template-columns:repeat(2,minmax(0,1fr))}.time-month-grid{grid-template-columns:repeat(4,minmax(0,1fr))}.time-pie-wrap,.time-rank-grid,.time-bars{grid-template-columns:1fr}.time-pie{justify-self:center}}.time-tip{position:fixed;z-index:9999;pointer-events:none;background:var(--background-primary);border:1px solid var(--background-modifier-border);box-shadow:0 8px 24px rgba(0,0,0,.18);border-radius:8px;padding:8px 10px;font-size:12px;color:var(--text-normal);max-width:240px;white-space:pre-line;opacity:0;transform:translate(10px,10px);transition:opacity .08s ease}`;
dv.container.appendChild(style);
const cards = (items) => { const el=dv.el("div","",{cls:"time-summary"}); el.innerHTML=items.map(([k,v])=>`<div class="time-card"><div class="time-card-k">${k}</div><div class="time-card-v">${v}</div></div>`).join(""); };
const empty = (msg) => dv.el("div", msg, {cls:"time-empty"});
const legend = () => { const el=dv.el("div","",{cls:"time-legend"}); el.innerHTML=cats.map(c=>`<span><i class="time-dot" style="background:${color[c]}"></i>${labels[c]||c}</span>`).join(""); };
const tip=dv.el("div","",{cls:"time-tip"});
const showTip=(text,ev)=>{tip.textContent=text||"";tip.style.left=ev.clientX+12+"px";tip.style.top=ev.clientY+12+"px";tip.style.opacity="1";};
const hideTip=()=>{tip.style.opacity="0";};
const bindTips=(root)=>{root.querySelectorAll("[data-tip]").forEach(el=>{el.addEventListener("mousemove",ev=>showTip(el.dataset.tip,ev));el.addEventListener("mouseleave",hideTip);});};
const stackBar = (totals) => { const total=Object.values(totals).reduce((a,b)=>a+b,0); const el=dv.el("div","",{cls:"time-stack"}); el.innerHTML=total?cats.filter(c=>(totals[c]||0)>0).map(c=>`<div class="time-stack-part" data-tip="${labels[c]||c}&#10;${fmt(totals[c])}&#10;${Math.round((totals[c]/total)*100)}%" style="width:${(totals[c]/total)*100}%;background:${color[c]}"></div>`).join(""):`<div class="time-stack-part" style="width:100%;background:var(--background-modifier-border)"></div>`; bindTips(el); };
const pieChart = (title, totals) => { const rows=cats.map(c=>({key:c,label:labels[c]||c,total:totals[c]||0})).filter(r=>r.total>0); const total=rows.reduce((s,r)=>s+r.total,0); dv.el("div",title,{cls:"time-section-title"}); const el=dv.el("div","",{cls:"time-pie-wrap"}); if(!total){el.innerHTML=`<div class="time-pie" style="background:var(--background-modifier-border)"></div><div class="time-pie-legend"><div class="time-pie-row">No data</div></div>`; return;} let acc=0; const gradient=rows.map(r=>{const start=(acc/total)*100; acc+=r.total; const end=(acc/total)*100; return `${color[r.key]} ${start}% ${end}%`;}).join(","); el.innerHTML=`<div class="time-pie" data-tip="${rows.map(r=>`${r.label} ${Math.round((r.total/total)*100)}%`).join("&#10;")}" style="background:conic-gradient(${gradient})"></div><div class="time-pie-legend">${rows.map(r=>`<div class="time-pie-row"><span class="time-pie-swatch" style="background:${color[r.key]}"></span><span>${r.label}</span><span class="time-pie-val">${fmt(r.total)}</span><span class="time-pie-pct">${Math.round((r.total/total)*100)}%</span></div>`).join("")}</div>`; bindTips(el); };
const categoryBars = (title, totals) => { const rows=cats.map(c=>({key:c,label:labels[c]||c,total:totals[c]||0})).filter(r=>r.total>0).sort((a,b)=>b.total-a.total); const max=Math.max(1,...rows.map(r=>r.total)); dv.el("div",title,{cls:"time-section-title"}); const el=dv.el("div","",{cls:"time-bars"}); el.innerHTML=rows.length?rows.map(r=>`<div class="time-bar-row"><div class="time-bar-name">${r.label}</div><div class="time-bar-track"><div class="time-bar-fill" style="width:${Math.max(2,(r.total/max)*100)}%;background:${color[r.key]}"></div></div><div class="time-bar-val">${fmt(r.total)}</div></div>`).join(""):`<div class="time-empty">No data</div>`; };
const rankRows = (title, rows) => `<div class="time-rank-panel"><div class="time-rank-title">${title}</div><div class="time-rank">${rows.length?rows.map((r,i)=>`<div class="time-rank-row"><div class="time-rank-no">#${i+1}</div><div class="time-rank-name">${r.name}</div><div class="time-rank-val">${fmt(r.total)}</div></div>`).join(""):`<div class="time-rank-row"><div class="time-rank-name">No data</div></div>`}</div></div>`;
const rankGrid = (groups) => { const grid=dv.el("div","",{cls:"time-rank-grid"}); grid.innerHTML=groups.map(g=>rankRows(g.title,g.rows)).join(""); };
const rankedCategoryRows = (totals) => cats.map(c=>({key:c,name:labels[c]||c,total:totals[c]||0})).filter(c=>c.total>0).sort((a,b)=>b.total-a.total).slice(0,5);
const dayRankRows = (days) => days.filter(d=>dayWorkMin(d)>0).sort((a,b)=>dayWorkMin(b)-dayWorkMin(a)).slice(0,5).map(d=>({name:d.date.slice(5),total:dayWorkMin(d)}));
const lineChart = (days, accessor, stroke="var(--text-accent)") => { const el=dv.el("div","",{cls:"time-chart"}); const w=780,h=150,pad=24; const max=Math.max(60,...days.map(accessor)); const points=days.map((d,i)=>{const x=pad+(days.length<=1?0:i*((w-pad*2)/(days.length-1))); const y=h-pad-(accessor(d)/max)*(h-pad*2); return [x,y,d,i];}); const poly=points.map(p=>`${p[0]},${p[1]}`).join(" "); const step=Math.max(1,Math.ceil(days.length/6)); const grid=[.25,.5,.75,1].map(r=>{const yy=h-pad-r*(h-pad*2); return `<line x1="${pad}" x2="${w-pad}" y1="${yy}" y2="${yy}" stroke="var(--background-modifier-border)" stroke-width="1" vector-effect="non-scaling-stroke"/><text x="4" y="${yy+4}" font-size="10" fill="var(--text-muted)">${fmt(Math.round(max*r))}</text>`;}).join(""); el.innerHTML=`<svg viewBox="0 0 ${w} ${h}" width="100%" height="150" preserveAspectRatio="none">${grid}<polyline points="${poly}" fill="none" stroke="${stroke}" stroke-width="3" vector-effect="non-scaling-stroke"/>${points.map(p=>`<circle cx="${p[0]}" cy="${p[1]}" r="5" fill="${stroke}" data-tip="${p[2].date}&#10;${fmt(accessor(p[2]))}"></circle>`).join("")}${points.filter(p=>p[3]===0||p[3]===points.length-1||p[3]%step===0).map(p=>`<text x="${p[0]}" y="${h-5}" font-size="10" text-anchor="middle" fill="var(--text-muted)">${p[2].date.slice(5)}</text>`).join("")}</svg>`; bindTips(el); };
if(view==="daily"){ const todayWork=dayWorkMin(today); const plannedRest=isPlannedRest(today); const weekRest=currentWeekRestDates(today.date); const restStatus=weekRest.length?weekRest.map(d=>d.slice(5)).join(", "):(isDecisionDay(today)?"Pick today":"Unset"); const plan=plannedRest?"Rest":(isDecisionDay(today)?"Decide":"Work"); cards([["Today",fmt(todayWork)],["Target",targetText(todayWork,targets.daily)],["Plan",plan],["Rest Rule",`${restConfig.restDaysPerWeek} / week`],["This Week Rest",restStatus],["Sessions",String(today.work_session_count||0)],["Longest",fmt(today.work_longest_session_min||0)],["Active",todayWork?"Yes":(plannedRest?"Rest":"No")]]); if(!todayWork) empty(plannedRest ? "今天是設定休息日，沒有正式做事時間紀錄。" : (isDecisionDay(today) ? "今天是本週休息日決策日，目前還沒有正式做事時間紀錄。" : "今天還沒有正式做事時間紀錄。")); else { legend(); const t=categoryTotals([today]); stackBar(t); rankGrid([{title:"今日類別排名",rows:rankedCategoryRows(t)}]); } }
if(view==="weekly"){ const total=sumDays(recent7); const active=recent7.filter(d=>dayWorkMin(d)>0).length; const expected=expectedRollingWorkDays(recent7); const t=categoryTotals(recent7); cards([["7 Days",fmt(total)],["Target",targetText(total,targets.weekly)],["Daily Avg",fmt(active?Math.round(total/active):0)],["Expected Avg",fmt(expected?Math.round(total/expected):0)],["Active Days",String(active)],["Expected",String(expected)],["Completion",completionText(active,expected)],["Best",fmt(Math.max(0,...recent7.map(d=>dayWorkMin(d))))]]); if(!total) empty("最近一週還沒有正式做事時間紀錄。"); else { lineChart(recent7,d=>dayWorkMin(d)); categoryBars("近 7 天類別長條", t); rankGrid([{title:"近 7 天日排名",rows:dayRankRows(recent7)},{title:"近 7 天類別排名",rows:rankedCategoryRows(t)}]); } }
if(view==="monthly"){ cards([["Month",fmt(monthTotal)],["Target",targetText(monthTotal,targets.monthly)],["Daily Avg",fmt(dailyAvg)],["Expected Avg",fmt(expectedAvg)],["Active Days",String(activeDays)],["Expected",String(expectedMonthDays)],["Completion",completionText(activeDays,expectedMonthDays)],["Best Day",best.date?best.date.slice(5):"-"]]); if(!monthTotal){empty("本月還沒有正式做事時間紀錄。"); return;} legend(); const max=Math.max(60,...data.days.map(d=>dayWorkMin(d))); const grid=dv.el("div","",{cls:"time-month-grid"}); for(const day of data.days){ const work=dayWorkMin(day); const main=mainWorkCategory(day); const intensity=Math.max(.12,work/max); const plannedRest=isPlannedRest(day); const cell=document.createElement("div"); cell.className=plannedRest?"time-day rest":"time-day"; cell.style.boxShadow=`inset 0 -3px 0 ${color[main]||color.other}`; cell.style.opacity=work?String(.55+intensity*.45):".45"; cell.dataset.tip=`${day.date}\n${plannedRest?"planned rest":"planned work"}\n${fmt(work)}\n${labels[main]||main}\n${day.session_count||0} sessions`; cell.innerHTML=`<div class="time-date">${day.date.slice(5)}</div><div class="time-total">${fmt(work)}</div><div class="time-cat" style="background:${color[main]||color.other}"></div>`; grid.appendChild(cell);} bindTips(grid); stackBar(catTotals); pieChart("本月類別占比", catTotals); categoryBars("本月類別長條", catTotals); rankGrid([{title:"本月日排名",rows:rankedDays.map(d=>({name:d.date.slice(5),total:dayWorkMin(d)}))},{title:"本月類別排名",rows:rankedCats.map(c=>({name:c.label,total:c.total}))}]); }
if(view==="trend"){
  if(!monthTotal){empty("有時間紀錄後，這裡會顯示週期比較、近 14 天、累積曲線、開始/結束時間。"); return;}
  const cur7 = sumDays(recent7), old7 = sumDays(prev7);
  const cur14 = sumDays(recent14), old14 = sumDays(prev14);
  const dayOfMonth = Number(todayIso.slice(8));
  const prevSamePeriod = prevData.days.slice(0, dayOfMonth);
  const prevMonthToDate = sumDays(prevSamePeriod);
  cards([
    ["7d vs prev", `${fmt(cur7)} / ${pct(cur7, old7)}`],
    ["14d vs prev", `${fmt(cur14)} / ${pct(cur14, old14)}`],
    ["MTD vs last", `${fmt(monthTotal)} / ${pct(monthTotal, prevMonthToDate)}`],
    ["Last MTD", fmt(prevMonthToDate)]
  ]);
  dv.el("div","近 14 天",{cls:"time-section-title"});
  lineChart(recent14,d=>dayWorkMin(d));
  rankGrid([{title:"近 14 天日排名",rows:dayRankRows(recent14)},{title:"近 14 天類別排名",rows:rankedCategoryRows(categoryTotals(recent14))}]);
  dv.el("div","本月累積",{cls:"time-section-title"});
  let running=0;
  const cumulative=data.days.map(d=>({date:d.date,total_min:running+=dayWorkMin(d),by_category:d.by_category}));
  lineChart(cumulative,d=>d.total_min,"#ff7a1a");
  dv.el("div","開始 / 結束時間",{cls:"time-section-title"});
  const rhythmDays=data.days.filter(d=>d.work_first_start_min!==null||d.work_last_end_min!==null);
  const el=dv.el("div","",{cls:"time-chart tall"});
  const w=780,h=190,pad=26,minClock=6*60,maxClock=26*60;
  const y=m=>pad+((m-minClock)/(maxClock-minClock))*(h-pad*2);
  const x=(i,n)=>pad+(n<=1?0:i*((w-pad*2)/(n-1)));
  const ticks=[8,12,16,20,24];
  el.innerHTML=`<svg viewBox="0 0 ${w} ${h}" width="100%" height="190" preserveAspectRatio="none">${ticks.map(hr=>`<line x1="${pad}" x2="${w-pad}" y1="${y(hr*60)}" y2="${y(hr*60)}" stroke="var(--background-modifier-border)" stroke-dasharray="4 5"/><text x="4" y="${y(hr*60)+4}" font-size="10" fill="var(--text-muted)">${hr}</text>`).join("")}${rhythmDays.map((d,i)=>{const xx=x(i,Math.max(1,rhythmDays.length)); const s=d.work_first_start_min??d.work_last_end_min; const e=d.work_last_end_min??d.work_first_start_min; const step=Math.max(1,Math.ceil(rhythmDays.length/6)); const label=(i===0||i===rhythmDays.length-1||i%step===0)?`<text x="${xx}" y="${h-5}" font-size="10" text-anchor="middle" fill="var(--text-muted)">${d.date.slice(8)}</text>`:""; return `<line x1="${xx}" x2="${xx}" y1="${y(s)}" y2="${y(e)}" stroke="#adb5bd" stroke-width="2"/><circle cx="${xx}" cy="${y(s)}" r="5" fill="#ff7a1a" data-tip="${d.date}&#10;start ${Math.floor(s/60)}:${String(s%60).padStart(2,'0')}"></circle><circle cx="${xx}" cy="${y(e)}" r="5" fill="#e9ecef" data-tip="${d.date}&#10;end ${Math.floor(e/60)}:${String(e%60).padStart(2,'0')}"></circle>${label}`;}).join("")}</svg>`; bindTips(el);
}
```


## Monthly Overview

月曆熱度、本月類別占比與排名。


```dataviewjs
const raw = await dv.io.load("life/worklog/data/time_daily_stats_2026-07.json");
const data = JSON.parse(raw);
let prevData = {days: []};
try {
  const prevRaw = await dv.io.load("life/worklog/data/time_daily_stats_2026-06.json");
  prevData = JSON.parse(prevRaw);
} catch (e) {}
const view = "monthly";
const cats = ["course", "research", "self_study", "language", "leetcode", "admin", "other"];
const labels = data.category_labels || {};
const color = {course:"#4f83ff", research:"#2fbf71", self_study:"#8b6cff", language:"#e56ab3", leetcode:"#f59f00", admin:"#8a8f98", rest:"#41b6c4", entertainment:"#ff6b6b", other:"#6c757d"};
const fmt = (min) => { const h = Math.floor((min || 0) / 60); const m = (min || 0) % 60; return h ? `${h}h${m ? " " + m + "m" : ""}` : `${m}m`; };
const targets = {daily:240, weekly:1500, monthly:6000};
const targetText = (cur, goal) => `${fmt(cur)} / ${fmt(goal)} (${goal ? Math.round((cur / goal) * 100) : 0}%)`;
const restConfig = {
  weeklyRestDays: [],
  restDaysPerWeek: 1,
  decisionWeekday: 1,
  restDates: []
};
const weekday = (iso) => new Date(`${iso}T00:00:00+08:00`).getDay();
const weekStart = (iso) => { const dt = new Date(`${iso}T00:00:00+08:00`); dt.setDate(dt.getDate() - ((dt.getDay() + 6) % 7)); return dt.toISOString().slice(0,10); };
const currentWeekRestDates = (iso) => restConfig.restDates.filter(date => weekStart(date) === weekStart(iso));
const isPlannedRest = (d) => restConfig.restDates.includes(d.date) || restConfig.weeklyRestDays.includes(weekday(d.date));
const isDecisionDay = (d) => weekday(d.date) === restConfig.decisionWeekday;
const expectedWorkDays = (days) => { const selected=days.filter(isPlannedRest).length; if(selected) return days.length - selected; const weeks=new Set(days.map(d=>weekStart(d.date))).size; return Math.max(0, days.length - Math.min(days.length, weeks * restConfig.restDaysPerWeek)); };
const expectedRollingWorkDays = (days) => { const selected=days.filter(isPlannedRest).length; if(selected) return days.length - selected; return Math.max(0, days.length - Math.min(restConfig.restDaysPerWeek, days.length)); };
const completionText = (active, expected) => `${active} / ${expected} (${expected ? Math.round((active / expected) * 100) : 0}%)`;
const todayIso = new Date().toLocaleDateString("sv-SE", {timeZone: "Asia/Taipei"});
const allDays = [...(prevData.days || []), ...(data.days || [])].reduce((map,d)=>map.set(d.date,d),new Map());
const timeline = [...allDays.values()].sort((a,b)=>a.date.localeCompare(b.date));
let todayIndex = timeline.findIndex(d => d.date === todayIso); if (todayIndex < 0) todayIndex = timeline.length - 1;
const today = timeline.find(d => d.date === todayIso) || {total_min:0, by_category:{}, session_count:0, work_session_count:0, longest_session_min:0, work_longest_session_min:0};
const recent7 = timeline.slice(Math.max(0, todayIndex - 6), todayIndex + 1);
const recent14 = timeline.slice(Math.max(0, todayIndex - 13), todayIndex + 1);
const prev7 = timeline.slice(Math.max(0, todayIndex - 13), Math.max(0, todayIndex - 6));
const prev14 = timeline.slice(Math.max(0, todayIndex - 27), Math.max(0, todayIndex - 13));
const dayWorkMin = (d) => cats.reduce((sum,c)=>sum+(d.by_category?.[c]||0),0);
const categoryTotals = (days) => { const totals=Object.fromEntries(cats.map(c=>[c,0])); for (const day of days) for (const c of cats) totals[c] += day.by_category?.[c] || 0; return totals; };
const mainWorkCategory = (d) => cats.reduce((best,c)=>(d.by_category?.[c]||0)>(d.by_category?.[best]||0)?c:best,"other");
const monthTotal = data.days.reduce((sum,d)=>sum+dayWorkMin(d),0);
const activeDays = data.days.filter(d=>dayWorkMin(d)>0).length;
const expectedMonthDays = expectedWorkDays(data.days);
const dailyAvg = activeDays ? Math.round(monthTotal/activeDays) : 0;
const expectedAvg = expectedMonthDays ? Math.round(monthTotal/expectedMonthDays) : 0;
const best = data.days.reduce((a,b)=>dayWorkMin(b)>dayWorkMin(a)?b:a,{by_category:{},date:""});
const catTotals = categoryTotals(data.days);
const rankedDays = data.days.filter(d=>dayWorkMin(d)>0).sort((a,b)=>dayWorkMin(b)-dayWorkMin(a)).slice(0,5);
const rankedCats = cats.map(c=>({key:c,label:labels[c]||c,total:catTotals[c]||0})).filter(c=>c.total>0).sort((a,b)=>b.total-a.total).slice(0,5);
const sumDays = (days) => days.reduce((sum, d) => sum + dayWorkMin(d), 0);
const pct = (cur, prev) => prev ? `${cur >= prev ? "+" : ""}${Math.round(((cur - prev) / prev) * 100)}%` : (cur ? "new" : "0%");
const style = document.createElement("style");
style.textContent = `.time-summary{display:grid;grid-template-columns:repeat(4,minmax(120px,1fr));gap:10px;margin:10px 0 16px}.time-card{border:1px solid var(--background-modifier-border);border-radius:10px;padding:10px 12px;background:var(--background-secondary)}.time-card-k{color:var(--text-muted);font-size:12px}.time-card-v{font-size:22px;font-weight:750;margin-top:4px}.time-empty{border:1px dashed var(--background-modifier-border);border-radius:10px;padding:18px;color:var(--text-muted);background:var(--background-secondary);margin:10px 0}.time-legend{display:flex;flex-wrap:wrap;gap:8px 12px;margin:8px 0 12px;font-size:12px;color:var(--text-muted)}.time-dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:4px}.time-section-title{font-size:13px;font-weight:650;margin:14px 0 6px;color:var(--text-muted)}.time-month-grid{display:grid;grid-template-columns:repeat(7,minmax(48px,1fr));gap:6px;margin:8px 0 16px;max-width:780px}.time-day{border:1px solid var(--background-modifier-border);border-radius:8px;min-height:58px;padding:6px;background:var(--background-secondary);box-shadow:inset 0 1px 0 rgba(255,255,255,.04)}.time-day.rest{border-style:dashed}.time-date{font-size:11px;color:var(--text-muted)}.time-total{font-size:13px;font-weight:650;margin-top:4px}.time-cat{height:5px;border-radius:4px;margin-top:7px;opacity:.9}.time-chart{width:100%;max-width:780px;height:150px;border:1px solid var(--background-modifier-border);border-radius:10px;background:var(--background-secondary);margin:8px 0 16px;overflow:hidden}.time-chart.tall{height:190px}.time-stack{display:flex;height:24px;width:100%;max-width:780px;overflow:hidden;border-radius:999px;background:var(--background-secondary);border:1px solid var(--background-modifier-border)}.time-stack-part{height:100%;min-width:2px}.time-pie-wrap{display:grid;grid-template-columns:180px minmax(220px,1fr);gap:16px;align-items:center;max-width:780px;margin:8px 0 16px}.time-pie{width:160px;aspect-ratio:1;border-radius:50%;border:1px solid var(--background-modifier-border)}.time-pie-legend{border:1px solid var(--background-modifier-border);border-radius:8px;background:var(--background-secondary);overflow:hidden}.time-pie-row{display:grid;grid-template-columns:14px 1fr auto auto;gap:8px;align-items:center;padding:7px 10px;border-bottom:1px solid var(--background-modifier-border);font-size:13px}.time-pie-row:last-child{border-bottom:0}.time-pie-swatch{width:10px;height:10px;border-radius:50%}.time-pie-val,.time-pie-pct{font-variant-numeric:tabular-nums;font-weight:650}.time-pie-pct{color:var(--text-muted)}.time-rank-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;max-width:780px;margin:14px 0 16px}.time-rank-panel{min-width:0}.time-rank-title{font-size:13px;font-weight:650;margin:0 0 6px;color:var(--text-muted)}.time-rank{border:1px solid var(--background-modifier-border);border-radius:8px;background:var(--background-secondary);overflow:hidden}.time-rank-row{display:grid;grid-template-columns:34px minmax(0,1fr) auto;gap:10px;align-items:center;padding:8px 10px;border-bottom:1px solid var(--background-modifier-border)}.time-rank-row:last-child{border-bottom:0}.time-rank-no{font-weight:750;color:var(--text-accent)}.time-rank-name{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.time-rank-val{font-variant-numeric:tabular-nums;font-weight:650;white-space:nowrap}.time-bars{display:grid;gap:7px;max-width:780px;margin:8px 0 16px}.time-bar-row{display:grid;grid-template-columns:88px minmax(0,1fr) auto;gap:10px;align-items:center}.time-bar-name{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--text-muted);font-size:13px}.time-bar-track{height:10px;border-radius:999px;background:var(--background-secondary);border:1px solid var(--background-modifier-border);overflow:hidden}.time-bar-fill{height:100%;min-width:2px}.time-bar-val{font-variant-numeric:tabular-nums;font-weight:650;white-space:nowrap;font-size:13px}@media (max-width:650px){.time-summary{grid-template-columns:repeat(2,minmax(0,1fr))}.time-month-grid{grid-template-columns:repeat(4,minmax(0,1fr))}.time-pie-wrap,.time-rank-grid,.time-bars{grid-template-columns:1fr}.time-pie{justify-self:center}}.time-tip{position:fixed;z-index:9999;pointer-events:none;background:var(--background-primary);border:1px solid var(--background-modifier-border);box-shadow:0 8px 24px rgba(0,0,0,.18);border-radius:8px;padding:8px 10px;font-size:12px;color:var(--text-normal);max-width:240px;white-space:pre-line;opacity:0;transform:translate(10px,10px);transition:opacity .08s ease}`;
dv.container.appendChild(style);
const cards = (items) => { const el=dv.el("div","",{cls:"time-summary"}); el.innerHTML=items.map(([k,v])=>`<div class="time-card"><div class="time-card-k">${k}</div><div class="time-card-v">${v}</div></div>`).join(""); };
const empty = (msg) => dv.el("div", msg, {cls:"time-empty"});
const legend = () => { const el=dv.el("div","",{cls:"time-legend"}); el.innerHTML=cats.map(c=>`<span><i class="time-dot" style="background:${color[c]}"></i>${labels[c]||c}</span>`).join(""); };
const tip=dv.el("div","",{cls:"time-tip"});
const showTip=(text,ev)=>{tip.textContent=text||"";tip.style.left=ev.clientX+12+"px";tip.style.top=ev.clientY+12+"px";tip.style.opacity="1";};
const hideTip=()=>{tip.style.opacity="0";};
const bindTips=(root)=>{root.querySelectorAll("[data-tip]").forEach(el=>{el.addEventListener("mousemove",ev=>showTip(el.dataset.tip,ev));el.addEventListener("mouseleave",hideTip);});};
const stackBar = (totals) => { const total=Object.values(totals).reduce((a,b)=>a+b,0); const el=dv.el("div","",{cls:"time-stack"}); el.innerHTML=total?cats.filter(c=>(totals[c]||0)>0).map(c=>`<div class="time-stack-part" data-tip="${labels[c]||c}&#10;${fmt(totals[c])}&#10;${Math.round((totals[c]/total)*100)}%" style="width:${(totals[c]/total)*100}%;background:${color[c]}"></div>`).join(""):`<div class="time-stack-part" style="width:100%;background:var(--background-modifier-border)"></div>`; bindTips(el); };
const pieChart = (title, totals) => { const rows=cats.map(c=>({key:c,label:labels[c]||c,total:totals[c]||0})).filter(r=>r.total>0); const total=rows.reduce((s,r)=>s+r.total,0); dv.el("div",title,{cls:"time-section-title"}); const el=dv.el("div","",{cls:"time-pie-wrap"}); if(!total){el.innerHTML=`<div class="time-pie" style="background:var(--background-modifier-border)"></div><div class="time-pie-legend"><div class="time-pie-row">No data</div></div>`; return;} let acc=0; const gradient=rows.map(r=>{const start=(acc/total)*100; acc+=r.total; const end=(acc/total)*100; return `${color[r.key]} ${start}% ${end}%`;}).join(","); el.innerHTML=`<div class="time-pie" data-tip="${rows.map(r=>`${r.label} ${Math.round((r.total/total)*100)}%`).join("&#10;")}" style="background:conic-gradient(${gradient})"></div><div class="time-pie-legend">${rows.map(r=>`<div class="time-pie-row"><span class="time-pie-swatch" style="background:${color[r.key]}"></span><span>${r.label}</span><span class="time-pie-val">${fmt(r.total)}</span><span class="time-pie-pct">${Math.round((r.total/total)*100)}%</span></div>`).join("")}</div>`; bindTips(el); };
const categoryBars = (title, totals) => { const rows=cats.map(c=>({key:c,label:labels[c]||c,total:totals[c]||0})).filter(r=>r.total>0).sort((a,b)=>b.total-a.total); const max=Math.max(1,...rows.map(r=>r.total)); dv.el("div",title,{cls:"time-section-title"}); const el=dv.el("div","",{cls:"time-bars"}); el.innerHTML=rows.length?rows.map(r=>`<div class="time-bar-row"><div class="time-bar-name">${r.label}</div><div class="time-bar-track"><div class="time-bar-fill" style="width:${Math.max(2,(r.total/max)*100)}%;background:${color[r.key]}"></div></div><div class="time-bar-val">${fmt(r.total)}</div></div>`).join(""):`<div class="time-empty">No data</div>`; };
const rankRows = (title, rows) => `<div class="time-rank-panel"><div class="time-rank-title">${title}</div><div class="time-rank">${rows.length?rows.map((r,i)=>`<div class="time-rank-row"><div class="time-rank-no">#${i+1}</div><div class="time-rank-name">${r.name}</div><div class="time-rank-val">${fmt(r.total)}</div></div>`).join(""):`<div class="time-rank-row"><div class="time-rank-name">No data</div></div>`}</div></div>`;
const rankGrid = (groups) => { const grid=dv.el("div","",{cls:"time-rank-grid"}); grid.innerHTML=groups.map(g=>rankRows(g.title,g.rows)).join(""); };
const rankedCategoryRows = (totals) => cats.map(c=>({key:c,name:labels[c]||c,total:totals[c]||0})).filter(c=>c.total>0).sort((a,b)=>b.total-a.total).slice(0,5);
const dayRankRows = (days) => days.filter(d=>dayWorkMin(d)>0).sort((a,b)=>dayWorkMin(b)-dayWorkMin(a)).slice(0,5).map(d=>({name:d.date.slice(5),total:dayWorkMin(d)}));
const lineChart = (days, accessor, stroke="var(--text-accent)") => { const el=dv.el("div","",{cls:"time-chart"}); const w=780,h=150,pad=24; const max=Math.max(60,...days.map(accessor)); const points=days.map((d,i)=>{const x=pad+(days.length<=1?0:i*((w-pad*2)/(days.length-1))); const y=h-pad-(accessor(d)/max)*(h-pad*2); return [x,y,d,i];}); const poly=points.map(p=>`${p[0]},${p[1]}`).join(" "); const step=Math.max(1,Math.ceil(days.length/6)); const grid=[.25,.5,.75,1].map(r=>{const yy=h-pad-r*(h-pad*2); return `<line x1="${pad}" x2="${w-pad}" y1="${yy}" y2="${yy}" stroke="var(--background-modifier-border)" stroke-width="1" vector-effect="non-scaling-stroke"/><text x="4" y="${yy+4}" font-size="10" fill="var(--text-muted)">${fmt(Math.round(max*r))}</text>`;}).join(""); el.innerHTML=`<svg viewBox="0 0 ${w} ${h}" width="100%" height="150" preserveAspectRatio="none">${grid}<polyline points="${poly}" fill="none" stroke="${stroke}" stroke-width="3" vector-effect="non-scaling-stroke"/>${points.map(p=>`<circle cx="${p[0]}" cy="${p[1]}" r="5" fill="${stroke}" data-tip="${p[2].date}&#10;${fmt(accessor(p[2]))}"></circle>`).join("")}${points.filter(p=>p[3]===0||p[3]===points.length-1||p[3]%step===0).map(p=>`<text x="${p[0]}" y="${h-5}" font-size="10" text-anchor="middle" fill="var(--text-muted)">${p[2].date.slice(5)}</text>`).join("")}</svg>`; bindTips(el); };
if(view==="daily"){ const todayWork=dayWorkMin(today); const plannedRest=isPlannedRest(today); const weekRest=currentWeekRestDates(today.date); const restStatus=weekRest.length?weekRest.map(d=>d.slice(5)).join(", "):(isDecisionDay(today)?"Pick today":"Unset"); const plan=plannedRest?"Rest":(isDecisionDay(today)?"Decide":"Work"); cards([["Today",fmt(todayWork)],["Target",targetText(todayWork,targets.daily)],["Plan",plan],["Rest Rule",`${restConfig.restDaysPerWeek} / week`],["This Week Rest",restStatus],["Sessions",String(today.work_session_count||0)],["Longest",fmt(today.work_longest_session_min||0)],["Active",todayWork?"Yes":(plannedRest?"Rest":"No")]]); if(!todayWork) empty(plannedRest ? "今天是設定休息日，沒有正式做事時間紀錄。" : (isDecisionDay(today) ? "今天是本週休息日決策日，目前還沒有正式做事時間紀錄。" : "今天還沒有正式做事時間紀錄。")); else { legend(); const t=categoryTotals([today]); stackBar(t); rankGrid([{title:"今日類別排名",rows:rankedCategoryRows(t)}]); } }
if(view==="weekly"){ const total=sumDays(recent7); const active=recent7.filter(d=>dayWorkMin(d)>0).length; const expected=expectedRollingWorkDays(recent7); const t=categoryTotals(recent7); cards([["7 Days",fmt(total)],["Target",targetText(total,targets.weekly)],["Daily Avg",fmt(active?Math.round(total/active):0)],["Expected Avg",fmt(expected?Math.round(total/expected):0)],["Active Days",String(active)],["Expected",String(expected)],["Completion",completionText(active,expected)],["Best",fmt(Math.max(0,...recent7.map(d=>dayWorkMin(d))))]]); if(!total) empty("最近一週還沒有正式做事時間紀錄。"); else { lineChart(recent7,d=>dayWorkMin(d)); categoryBars("近 7 天類別長條", t); rankGrid([{title:"近 7 天日排名",rows:dayRankRows(recent7)},{title:"近 7 天類別排名",rows:rankedCategoryRows(t)}]); } }
if(view==="monthly"){ cards([["Month",fmt(monthTotal)],["Target",targetText(monthTotal,targets.monthly)],["Daily Avg",fmt(dailyAvg)],["Expected Avg",fmt(expectedAvg)],["Active Days",String(activeDays)],["Expected",String(expectedMonthDays)],["Completion",completionText(activeDays,expectedMonthDays)],["Best Day",best.date?best.date.slice(5):"-"]]); if(!monthTotal){empty("本月還沒有正式做事時間紀錄。"); return;} legend(); const max=Math.max(60,...data.days.map(d=>dayWorkMin(d))); const grid=dv.el("div","",{cls:"time-month-grid"}); for(const day of data.days){ const work=dayWorkMin(day); const main=mainWorkCategory(day); const intensity=Math.max(.12,work/max); const plannedRest=isPlannedRest(day); const cell=document.createElement("div"); cell.className=plannedRest?"time-day rest":"time-day"; cell.style.boxShadow=`inset 0 -3px 0 ${color[main]||color.other}`; cell.style.opacity=work?String(.55+intensity*.45):".45"; cell.dataset.tip=`${day.date}\n${plannedRest?"planned rest":"planned work"}\n${fmt(work)}\n${labels[main]||main}\n${day.session_count||0} sessions`; cell.innerHTML=`<div class="time-date">${day.date.slice(5)}</div><div class="time-total">${fmt(work)}</div><div class="time-cat" style="background:${color[main]||color.other}"></div>`; grid.appendChild(cell);} bindTips(grid); stackBar(catTotals); pieChart("本月類別占比", catTotals); categoryBars("本月類別長條", catTotals); rankGrid([{title:"本月日排名",rows:rankedDays.map(d=>({name:d.date.slice(5),total:dayWorkMin(d)}))},{title:"本月類別排名",rows:rankedCats.map(c=>({name:c.label,total:c.total}))}]); }
if(view==="trend"){
  if(!monthTotal){empty("有時間紀錄後，這裡會顯示週期比較、近 14 天、累積曲線、開始/結束時間。"); return;}
  const cur7 = sumDays(recent7), old7 = sumDays(prev7);
  const cur14 = sumDays(recent14), old14 = sumDays(prev14);
  const dayOfMonth = Number(todayIso.slice(8));
  const prevSamePeriod = prevData.days.slice(0, dayOfMonth);
  const prevMonthToDate = sumDays(prevSamePeriod);
  cards([
    ["7d vs prev", `${fmt(cur7)} / ${pct(cur7, old7)}`],
    ["14d vs prev", `${fmt(cur14)} / ${pct(cur14, old14)}`],
    ["MTD vs last", `${fmt(monthTotal)} / ${pct(monthTotal, prevMonthToDate)}`],
    ["Last MTD", fmt(prevMonthToDate)]
  ]);
  dv.el("div","近 14 天",{cls:"time-section-title"});
  lineChart(recent14,d=>dayWorkMin(d));
  rankGrid([{title:"近 14 天日排名",rows:dayRankRows(recent14)},{title:"近 14 天類別排名",rows:rankedCategoryRows(categoryTotals(recent14))}]);
  dv.el("div","本月累積",{cls:"time-section-title"});
  let running=0;
  const cumulative=data.days.map(d=>({date:d.date,total_min:running+=dayWorkMin(d),by_category:d.by_category}));
  lineChart(cumulative,d=>d.total_min,"#ff7a1a");
  dv.el("div","開始 / 結束時間",{cls:"time-section-title"});
  const rhythmDays=data.days.filter(d=>d.work_first_start_min!==null||d.work_last_end_min!==null);
  const el=dv.el("div","",{cls:"time-chart tall"});
  const w=780,h=190,pad=26,minClock=6*60,maxClock=26*60;
  const y=m=>pad+((m-minClock)/(maxClock-minClock))*(h-pad*2);
  const x=(i,n)=>pad+(n<=1?0:i*((w-pad*2)/(n-1)));
  const ticks=[8,12,16,20,24];
  el.innerHTML=`<svg viewBox="0 0 ${w} ${h}" width="100%" height="190" preserveAspectRatio="none">${ticks.map(hr=>`<line x1="${pad}" x2="${w-pad}" y1="${y(hr*60)}" y2="${y(hr*60)}" stroke="var(--background-modifier-border)" stroke-dasharray="4 5"/><text x="4" y="${y(hr*60)+4}" font-size="10" fill="var(--text-muted)">${hr}</text>`).join("")}${rhythmDays.map((d,i)=>{const xx=x(i,Math.max(1,rhythmDays.length)); const s=d.work_first_start_min??d.work_last_end_min; const e=d.work_last_end_min??d.work_first_start_min; const step=Math.max(1,Math.ceil(rhythmDays.length/6)); const label=(i===0||i===rhythmDays.length-1||i%step===0)?`<text x="${xx}" y="${h-5}" font-size="10" text-anchor="middle" fill="var(--text-muted)">${d.date.slice(8)}</text>`:""; return `<line x1="${xx}" x2="${xx}" y1="${y(s)}" y2="${y(e)}" stroke="#adb5bd" stroke-width="2"/><circle cx="${xx}" cy="${y(s)}" r="5" fill="#ff7a1a" data-tip="${d.date}&#10;start ${Math.floor(s/60)}:${String(s%60).padStart(2,'0')}"></circle><circle cx="${xx}" cy="${y(e)}" r="5" fill="#e9ecef" data-tip="${d.date}&#10;end ${Math.floor(e/60)}:${String(e%60).padStart(2,'0')}"></circle>${label}`;}).join("")}</svg>`; bindTips(el);
}
```


## Trend Overview

近 14 天、本月累積曲線、排名、開始 / 結束時間。

Month: 2026-07  
Week: 2026-07-06 to 2026-07-12


```dataviewjs
const raw = await dv.io.load("life/worklog/data/time_daily_stats_2026-07.json");
const data = JSON.parse(raw);
let prevData = {days: []};
try {
  const prevRaw = await dv.io.load("life/worklog/data/time_daily_stats_2026-06.json");
  prevData = JSON.parse(prevRaw);
} catch (e) {}
const view = "trend";
const cats = ["course", "research", "self_study", "language", "leetcode", "admin", "other"];
const labels = data.category_labels || {};
const color = {course:"#4f83ff", research:"#2fbf71", self_study:"#8b6cff", language:"#e56ab3", leetcode:"#f59f00", admin:"#8a8f98", rest:"#41b6c4", entertainment:"#ff6b6b", other:"#6c757d"};
const fmt = (min) => { const h = Math.floor((min || 0) / 60); const m = (min || 0) % 60; return h ? `${h}h${m ? " " + m + "m" : ""}` : `${m}m`; };
const targets = {daily:240, weekly:1500, monthly:6000};
const targetText = (cur, goal) => `${fmt(cur)} / ${fmt(goal)} (${goal ? Math.round((cur / goal) * 100) : 0}%)`;
const restConfig = {
  weeklyRestDays: [],
  restDaysPerWeek: 1,
  decisionWeekday: 1,
  restDates: []
};
const weekday = (iso) => new Date(`${iso}T00:00:00+08:00`).getDay();
const weekStart = (iso) => { const dt = new Date(`${iso}T00:00:00+08:00`); dt.setDate(dt.getDate() - ((dt.getDay() + 6) % 7)); return dt.toISOString().slice(0,10); };
const currentWeekRestDates = (iso) => restConfig.restDates.filter(date => weekStart(date) === weekStart(iso));
const isPlannedRest = (d) => restConfig.restDates.includes(d.date) || restConfig.weeklyRestDays.includes(weekday(d.date));
const isDecisionDay = (d) => weekday(d.date) === restConfig.decisionWeekday;
const expectedWorkDays = (days) => { const selected=days.filter(isPlannedRest).length; if(selected) return days.length - selected; const weeks=new Set(days.map(d=>weekStart(d.date))).size; return Math.max(0, days.length - Math.min(days.length, weeks * restConfig.restDaysPerWeek)); };
const expectedRollingWorkDays = (days) => { const selected=days.filter(isPlannedRest).length; if(selected) return days.length - selected; return Math.max(0, days.length - Math.min(restConfig.restDaysPerWeek, days.length)); };
const completionText = (active, expected) => `${active} / ${expected} (${expected ? Math.round((active / expected) * 100) : 0}%)`;
const todayIso = new Date().toLocaleDateString("sv-SE", {timeZone: "Asia/Taipei"});
const allDays = [...(prevData.days || []), ...(data.days || [])].reduce((map,d)=>map.set(d.date,d),new Map());
const timeline = [...allDays.values()].sort((a,b)=>a.date.localeCompare(b.date));
let todayIndex = timeline.findIndex(d => d.date === todayIso); if (todayIndex < 0) todayIndex = timeline.length - 1;
const today = timeline.find(d => d.date === todayIso) || {total_min:0, by_category:{}, session_count:0, work_session_count:0, longest_session_min:0, work_longest_session_min:0};
const recent7 = timeline.slice(Math.max(0, todayIndex - 6), todayIndex + 1);
const recent14 = timeline.slice(Math.max(0, todayIndex - 13), todayIndex + 1);
const prev7 = timeline.slice(Math.max(0, todayIndex - 13), Math.max(0, todayIndex - 6));
const prev14 = timeline.slice(Math.max(0, todayIndex - 27), Math.max(0, todayIndex - 13));
const dayWorkMin = (d) => cats.reduce((sum,c)=>sum+(d.by_category?.[c]||0),0);
const categoryTotals = (days) => { const totals=Object.fromEntries(cats.map(c=>[c,0])); for (const day of days) for (const c of cats) totals[c] += day.by_category?.[c] || 0; return totals; };
const mainWorkCategory = (d) => cats.reduce((best,c)=>(d.by_category?.[c]||0)>(d.by_category?.[best]||0)?c:best,"other");
const monthTotal = data.days.reduce((sum,d)=>sum+dayWorkMin(d),0);
const activeDays = data.days.filter(d=>dayWorkMin(d)>0).length;
const expectedMonthDays = expectedWorkDays(data.days);
const dailyAvg = activeDays ? Math.round(monthTotal/activeDays) : 0;
const expectedAvg = expectedMonthDays ? Math.round(monthTotal/expectedMonthDays) : 0;
const best = data.days.reduce((a,b)=>dayWorkMin(b)>dayWorkMin(a)?b:a,{by_category:{},date:""});
const catTotals = categoryTotals(data.days);
const rankedDays = data.days.filter(d=>dayWorkMin(d)>0).sort((a,b)=>dayWorkMin(b)-dayWorkMin(a)).slice(0,5);
const rankedCats = cats.map(c=>({key:c,label:labels[c]||c,total:catTotals[c]||0})).filter(c=>c.total>0).sort((a,b)=>b.total-a.total).slice(0,5);
const sumDays = (days) => days.reduce((sum, d) => sum + dayWorkMin(d), 0);
const pct = (cur, prev) => prev ? `${cur >= prev ? "+" : ""}${Math.round(((cur - prev) / prev) * 100)}%` : (cur ? "new" : "0%");
const style = document.createElement("style");
style.textContent = `.time-summary{display:grid;grid-template-columns:repeat(4,minmax(120px,1fr));gap:10px;margin:10px 0 16px}.time-card{border:1px solid var(--background-modifier-border);border-radius:10px;padding:10px 12px;background:var(--background-secondary)}.time-card-k{color:var(--text-muted);font-size:12px}.time-card-v{font-size:22px;font-weight:750;margin-top:4px}.time-empty{border:1px dashed var(--background-modifier-border);border-radius:10px;padding:18px;color:var(--text-muted);background:var(--background-secondary);margin:10px 0}.time-legend{display:flex;flex-wrap:wrap;gap:8px 12px;margin:8px 0 12px;font-size:12px;color:var(--text-muted)}.time-dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:4px}.time-section-title{font-size:13px;font-weight:650;margin:14px 0 6px;color:var(--text-muted)}.time-month-grid{display:grid;grid-template-columns:repeat(7,minmax(48px,1fr));gap:6px;margin:8px 0 16px;max-width:780px}.time-day{border:1px solid var(--background-modifier-border);border-radius:8px;min-height:58px;padding:6px;background:var(--background-secondary);box-shadow:inset 0 1px 0 rgba(255,255,255,.04)}.time-day.rest{border-style:dashed}.time-date{font-size:11px;color:var(--text-muted)}.time-total{font-size:13px;font-weight:650;margin-top:4px}.time-cat{height:5px;border-radius:4px;margin-top:7px;opacity:.9}.time-chart{width:100%;max-width:780px;height:150px;border:1px solid var(--background-modifier-border);border-radius:10px;background:var(--background-secondary);margin:8px 0 16px;overflow:hidden}.time-chart.tall{height:190px}.time-stack{display:flex;height:24px;width:100%;max-width:780px;overflow:hidden;border-radius:999px;background:var(--background-secondary);border:1px solid var(--background-modifier-border)}.time-stack-part{height:100%;min-width:2px}.time-pie-wrap{display:grid;grid-template-columns:180px minmax(220px,1fr);gap:16px;align-items:center;max-width:780px;margin:8px 0 16px}.time-pie{width:160px;aspect-ratio:1;border-radius:50%;border:1px solid var(--background-modifier-border)}.time-pie-legend{border:1px solid var(--background-modifier-border);border-radius:8px;background:var(--background-secondary);overflow:hidden}.time-pie-row{display:grid;grid-template-columns:14px 1fr auto auto;gap:8px;align-items:center;padding:7px 10px;border-bottom:1px solid var(--background-modifier-border);font-size:13px}.time-pie-row:last-child{border-bottom:0}.time-pie-swatch{width:10px;height:10px;border-radius:50%}.time-pie-val,.time-pie-pct{font-variant-numeric:tabular-nums;font-weight:650}.time-pie-pct{color:var(--text-muted)}.time-rank-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;max-width:780px;margin:14px 0 16px}.time-rank-panel{min-width:0}.time-rank-title{font-size:13px;font-weight:650;margin:0 0 6px;color:var(--text-muted)}.time-rank{border:1px solid var(--background-modifier-border);border-radius:8px;background:var(--background-secondary);overflow:hidden}.time-rank-row{display:grid;grid-template-columns:34px minmax(0,1fr) auto;gap:10px;align-items:center;padding:8px 10px;border-bottom:1px solid var(--background-modifier-border)}.time-rank-row:last-child{border-bottom:0}.time-rank-no{font-weight:750;color:var(--text-accent)}.time-rank-name{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.time-rank-val{font-variant-numeric:tabular-nums;font-weight:650;white-space:nowrap}.time-bars{display:grid;gap:7px;max-width:780px;margin:8px 0 16px}.time-bar-row{display:grid;grid-template-columns:88px minmax(0,1fr) auto;gap:10px;align-items:center}.time-bar-name{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--text-muted);font-size:13px}.time-bar-track{height:10px;border-radius:999px;background:var(--background-secondary);border:1px solid var(--background-modifier-border);overflow:hidden}.time-bar-fill{height:100%;min-width:2px}.time-bar-val{font-variant-numeric:tabular-nums;font-weight:650;white-space:nowrap;font-size:13px}@media (max-width:650px){.time-summary{grid-template-columns:repeat(2,minmax(0,1fr))}.time-month-grid{grid-template-columns:repeat(4,minmax(0,1fr))}.time-pie-wrap,.time-rank-grid,.time-bars{grid-template-columns:1fr}.time-pie{justify-self:center}}.time-tip{position:fixed;z-index:9999;pointer-events:none;background:var(--background-primary);border:1px solid var(--background-modifier-border);box-shadow:0 8px 24px rgba(0,0,0,.18);border-radius:8px;padding:8px 10px;font-size:12px;color:var(--text-normal);max-width:240px;white-space:pre-line;opacity:0;transform:translate(10px,10px);transition:opacity .08s ease}`;
dv.container.appendChild(style);
const cards = (items) => { const el=dv.el("div","",{cls:"time-summary"}); el.innerHTML=items.map(([k,v])=>`<div class="time-card"><div class="time-card-k">${k}</div><div class="time-card-v">${v}</div></div>`).join(""); };
const empty = (msg) => dv.el("div", msg, {cls:"time-empty"});
const legend = () => { const el=dv.el("div","",{cls:"time-legend"}); el.innerHTML=cats.map(c=>`<span><i class="time-dot" style="background:${color[c]}"></i>${labels[c]||c}</span>`).join(""); };
const tip=dv.el("div","",{cls:"time-tip"});
const showTip=(text,ev)=>{tip.textContent=text||"";tip.style.left=ev.clientX+12+"px";tip.style.top=ev.clientY+12+"px";tip.style.opacity="1";};
const hideTip=()=>{tip.style.opacity="0";};
const bindTips=(root)=>{root.querySelectorAll("[data-tip]").forEach(el=>{el.addEventListener("mousemove",ev=>showTip(el.dataset.tip,ev));el.addEventListener("mouseleave",hideTip);});};
const stackBar = (totals) => { const total=Object.values(totals).reduce((a,b)=>a+b,0); const el=dv.el("div","",{cls:"time-stack"}); el.innerHTML=total?cats.filter(c=>(totals[c]||0)>0).map(c=>`<div class="time-stack-part" data-tip="${labels[c]||c}&#10;${fmt(totals[c])}&#10;${Math.round((totals[c]/total)*100)}%" style="width:${(totals[c]/total)*100}%;background:${color[c]}"></div>`).join(""):`<div class="time-stack-part" style="width:100%;background:var(--background-modifier-border)"></div>`; bindTips(el); };
const pieChart = (title, totals) => { const rows=cats.map(c=>({key:c,label:labels[c]||c,total:totals[c]||0})).filter(r=>r.total>0); const total=rows.reduce((s,r)=>s+r.total,0); dv.el("div",title,{cls:"time-section-title"}); const el=dv.el("div","",{cls:"time-pie-wrap"}); if(!total){el.innerHTML=`<div class="time-pie" style="background:var(--background-modifier-border)"></div><div class="time-pie-legend"><div class="time-pie-row">No data</div></div>`; return;} let acc=0; const gradient=rows.map(r=>{const start=(acc/total)*100; acc+=r.total; const end=(acc/total)*100; return `${color[r.key]} ${start}% ${end}%`;}).join(","); el.innerHTML=`<div class="time-pie" data-tip="${rows.map(r=>`${r.label} ${Math.round((r.total/total)*100)}%`).join("&#10;")}" style="background:conic-gradient(${gradient})"></div><div class="time-pie-legend">${rows.map(r=>`<div class="time-pie-row"><span class="time-pie-swatch" style="background:${color[r.key]}"></span><span>${r.label}</span><span class="time-pie-val">${fmt(r.total)}</span><span class="time-pie-pct">${Math.round((r.total/total)*100)}%</span></div>`).join("")}</div>`; bindTips(el); };
const categoryBars = (title, totals) => { const rows=cats.map(c=>({key:c,label:labels[c]||c,total:totals[c]||0})).filter(r=>r.total>0).sort((a,b)=>b.total-a.total); const max=Math.max(1,...rows.map(r=>r.total)); dv.el("div",title,{cls:"time-section-title"}); const el=dv.el("div","",{cls:"time-bars"}); el.innerHTML=rows.length?rows.map(r=>`<div class="time-bar-row"><div class="time-bar-name">${r.label}</div><div class="time-bar-track"><div class="time-bar-fill" style="width:${Math.max(2,(r.total/max)*100)}%;background:${color[r.key]}"></div></div><div class="time-bar-val">${fmt(r.total)}</div></div>`).join(""):`<div class="time-empty">No data</div>`; };
const rankRows = (title, rows) => `<div class="time-rank-panel"><div class="time-rank-title">${title}</div><div class="time-rank">${rows.length?rows.map((r,i)=>`<div class="time-rank-row"><div class="time-rank-no">#${i+1}</div><div class="time-rank-name">${r.name}</div><div class="time-rank-val">${fmt(r.total)}</div></div>`).join(""):`<div class="time-rank-row"><div class="time-rank-name">No data</div></div>`}</div></div>`;
const rankGrid = (groups) => { const grid=dv.el("div","",{cls:"time-rank-grid"}); grid.innerHTML=groups.map(g=>rankRows(g.title,g.rows)).join(""); };
const rankedCategoryRows = (totals) => cats.map(c=>({key:c,name:labels[c]||c,total:totals[c]||0})).filter(c=>c.total>0).sort((a,b)=>b.total-a.total).slice(0,5);
const dayRankRows = (days) => days.filter(d=>dayWorkMin(d)>0).sort((a,b)=>dayWorkMin(b)-dayWorkMin(a)).slice(0,5).map(d=>({name:d.date.slice(5),total:dayWorkMin(d)}));
const lineChart = (days, accessor, stroke="var(--text-accent)") => { const el=dv.el("div","",{cls:"time-chart"}); const w=780,h=150,pad=24; const max=Math.max(60,...days.map(accessor)); const points=days.map((d,i)=>{const x=pad+(days.length<=1?0:i*((w-pad*2)/(days.length-1))); const y=h-pad-(accessor(d)/max)*(h-pad*2); return [x,y,d,i];}); const poly=points.map(p=>`${p[0]},${p[1]}`).join(" "); const step=Math.max(1,Math.ceil(days.length/6)); const grid=[.25,.5,.75,1].map(r=>{const yy=h-pad-r*(h-pad*2); return `<line x1="${pad}" x2="${w-pad}" y1="${yy}" y2="${yy}" stroke="var(--background-modifier-border)" stroke-width="1" vector-effect="non-scaling-stroke"/><text x="4" y="${yy+4}" font-size="10" fill="var(--text-muted)">${fmt(Math.round(max*r))}</text>`;}).join(""); el.innerHTML=`<svg viewBox="0 0 ${w} ${h}" width="100%" height="150" preserveAspectRatio="none">${grid}<polyline points="${poly}" fill="none" stroke="${stroke}" stroke-width="3" vector-effect="non-scaling-stroke"/>${points.map(p=>`<circle cx="${p[0]}" cy="${p[1]}" r="5" fill="${stroke}" data-tip="${p[2].date}&#10;${fmt(accessor(p[2]))}"></circle>`).join("")}${points.filter(p=>p[3]===0||p[3]===points.length-1||p[3]%step===0).map(p=>`<text x="${p[0]}" y="${h-5}" font-size="10" text-anchor="middle" fill="var(--text-muted)">${p[2].date.slice(5)}</text>`).join("")}</svg>`; bindTips(el); };
if(view==="daily"){ const todayWork=dayWorkMin(today); const plannedRest=isPlannedRest(today); const weekRest=currentWeekRestDates(today.date); const restStatus=weekRest.length?weekRest.map(d=>d.slice(5)).join(", "):(isDecisionDay(today)?"Pick today":"Unset"); const plan=plannedRest?"Rest":(isDecisionDay(today)?"Decide":"Work"); cards([["Today",fmt(todayWork)],["Target",targetText(todayWork,targets.daily)],["Plan",plan],["Rest Rule",`${restConfig.restDaysPerWeek} / week`],["This Week Rest",restStatus],["Sessions",String(today.work_session_count||0)],["Longest",fmt(today.work_longest_session_min||0)],["Active",todayWork?"Yes":(plannedRest?"Rest":"No")]]); if(!todayWork) empty(plannedRest ? "今天是設定休息日，沒有正式做事時間紀錄。" : (isDecisionDay(today) ? "今天是本週休息日決策日，目前還沒有正式做事時間紀錄。" : "今天還沒有正式做事時間紀錄。")); else { legend(); const t=categoryTotals([today]); stackBar(t); rankGrid([{title:"今日類別排名",rows:rankedCategoryRows(t)}]); } }
if(view==="weekly"){ const total=sumDays(recent7); const active=recent7.filter(d=>dayWorkMin(d)>0).length; const expected=expectedRollingWorkDays(recent7); const t=categoryTotals(recent7); cards([["7 Days",fmt(total)],["Target",targetText(total,targets.weekly)],["Daily Avg",fmt(active?Math.round(total/active):0)],["Expected Avg",fmt(expected?Math.round(total/expected):0)],["Active Days",String(active)],["Expected",String(expected)],["Completion",completionText(active,expected)],["Best",fmt(Math.max(0,...recent7.map(d=>dayWorkMin(d))))]]); if(!total) empty("最近一週還沒有正式做事時間紀錄。"); else { lineChart(recent7,d=>dayWorkMin(d)); categoryBars("近 7 天類別長條", t); rankGrid([{title:"近 7 天日排名",rows:dayRankRows(recent7)},{title:"近 7 天類別排名",rows:rankedCategoryRows(t)}]); } }
if(view==="monthly"){ cards([["Month",fmt(monthTotal)],["Target",targetText(monthTotal,targets.monthly)],["Daily Avg",fmt(dailyAvg)],["Expected Avg",fmt(expectedAvg)],["Active Days",String(activeDays)],["Expected",String(expectedMonthDays)],["Completion",completionText(activeDays,expectedMonthDays)],["Best Day",best.date?best.date.slice(5):"-"]]); if(!monthTotal){empty("本月還沒有正式做事時間紀錄。"); return;} legend(); const max=Math.max(60,...data.days.map(d=>dayWorkMin(d))); const grid=dv.el("div","",{cls:"time-month-grid"}); for(const day of data.days){ const work=dayWorkMin(day); const main=mainWorkCategory(day); const intensity=Math.max(.12,work/max); const plannedRest=isPlannedRest(day); const cell=document.createElement("div"); cell.className=plannedRest?"time-day rest":"time-day"; cell.style.boxShadow=`inset 0 -3px 0 ${color[main]||color.other}`; cell.style.opacity=work?String(.55+intensity*.45):".45"; cell.dataset.tip=`${day.date}\n${plannedRest?"planned rest":"planned work"}\n${fmt(work)}\n${labels[main]||main}\n${day.session_count||0} sessions`; cell.innerHTML=`<div class="time-date">${day.date.slice(5)}</div><div class="time-total">${fmt(work)}</div><div class="time-cat" style="background:${color[main]||color.other}"></div>`; grid.appendChild(cell);} bindTips(grid); stackBar(catTotals); pieChart("本月類別占比", catTotals); categoryBars("本月類別長條", catTotals); rankGrid([{title:"本月日排名",rows:rankedDays.map(d=>({name:d.date.slice(5),total:dayWorkMin(d)}))},{title:"本月類別排名",rows:rankedCats.map(c=>({name:c.label,total:c.total}))}]); }
if(view==="trend"){
  if(!monthTotal){empty("有時間紀錄後，這裡會顯示週期比較、近 14 天、累積曲線、開始/結束時間。"); return;}
  const cur7 = sumDays(recent7), old7 = sumDays(prev7);
  const cur14 = sumDays(recent14), old14 = sumDays(prev14);
  const dayOfMonth = Number(todayIso.slice(8));
  const prevSamePeriod = prevData.days.slice(0, dayOfMonth);
  const prevMonthToDate = sumDays(prevSamePeriod);
  cards([
    ["7d vs prev", `${fmt(cur7)} / ${pct(cur7, old7)}`],
    ["14d vs prev", `${fmt(cur14)} / ${pct(cur14, old14)}`],
    ["MTD vs last", `${fmt(monthTotal)} / ${pct(monthTotal, prevMonthToDate)}`],
    ["Last MTD", fmt(prevMonthToDate)]
  ]);
  dv.el("div","近 14 天",{cls:"time-section-title"});
  lineChart(recent14,d=>dayWorkMin(d));
  rankGrid([{title:"近 14 天日排名",rows:dayRankRows(recent14)},{title:"近 14 天類別排名",rows:rankedCategoryRows(categoryTotals(recent14))}]);
  dv.el("div","本月累積",{cls:"time-section-title"});
  let running=0;
  const cumulative=data.days.map(d=>({date:d.date,total_min:running+=dayWorkMin(d),by_category:d.by_category}));
  lineChart(cumulative,d=>d.total_min,"#ff7a1a");
  dv.el("div","開始 / 結束時間",{cls:"time-section-title"});
  const rhythmDays=data.days.filter(d=>d.work_first_start_min!==null||d.work_last_end_min!==null);
  const el=dv.el("div","",{cls:"time-chart tall"});
  const w=780,h=190,pad=26,minClock=6*60,maxClock=26*60;
  const y=m=>pad+((m-minClock)/(maxClock-minClock))*(h-pad*2);
  const x=(i,n)=>pad+(n<=1?0:i*((w-pad*2)/(n-1)));
  const ticks=[8,12,16,20,24];
  el.innerHTML=`<svg viewBox="0 0 ${w} ${h}" width="100%" height="190" preserveAspectRatio="none">${ticks.map(hr=>`<line x1="${pad}" x2="${w-pad}" y1="${y(hr*60)}" y2="${y(hr*60)}" stroke="var(--background-modifier-border)" stroke-dasharray="4 5"/><text x="4" y="${y(hr*60)+4}" font-size="10" fill="var(--text-muted)">${hr}</text>`).join("")}${rhythmDays.map((d,i)=>{const xx=x(i,Math.max(1,rhythmDays.length)); const s=d.work_first_start_min??d.work_last_end_min; const e=d.work_last_end_min??d.work_first_start_min; const step=Math.max(1,Math.ceil(rhythmDays.length/6)); const label=(i===0||i===rhythmDays.length-1||i%step===0)?`<text x="${xx}" y="${h-5}" font-size="10" text-anchor="middle" fill="var(--text-muted)">${d.date.slice(8)}</text>`:""; return `<line x1="${xx}" x2="${xx}" y1="${y(s)}" y2="${y(e)}" stroke="#adb5bd" stroke-width="2"/><circle cx="${xx}" cy="${y(s)}" r="5" fill="#ff7a1a" data-tip="${d.date}&#10;start ${Math.floor(s/60)}:${String(s%60).padStart(2,'0')}"></circle><circle cx="${xx}" cy="${y(e)}" r="5" fill="#e9ecef" data-tip="${d.date}&#10;end ${Math.floor(e/60)}:${String(e%60).padStart(2,'0')}"></circle>${label}`;}).join("")}</svg>`; bindTips(el);
}
```


## Year Overview

今年做事時間總覽、類別占比與排名。


```dataviewjs
const months = ["2026-03", "2026-04", "2026-05", "2026-06", "2026-07"];
const view = "year";
const targetYear = "2026";
const cats = ["course", "research", "self_study", "language", "leetcode", "admin", "other"];
const color = {course:"#4f83ff", research:"#2fbf71", self_study:"#8b6cff", language:"#e56ab3", leetcode:"#f59f00", admin:"#8a8f98", other:"#6c757d"};
const fmt = (min) => { const h = Math.floor((min || 0) / 60); const m = (min || 0) % 60; return h ? `${h}h${m ? " " + m + "m" : ""}` : `${m}m`; };
const restConfig = {
  weeklyRestDays: [],
  restDaysPerWeek: 1,
  decisionWeekday: 1,
  restDates: []
};
const weekday = (iso) => new Date(`${iso}T00:00:00+08:00`).getDay();
const weekStart = (iso) => { const dt = new Date(`${iso}T00:00:00+08:00`); dt.setDate(dt.getDate() - ((dt.getDay() + 6) % 7)); return dt.toISOString().slice(0,10); };
const isPlannedRest = (d) => restConfig.restDates.includes(d.date) || restConfig.weeklyRestDays.includes(weekday(d.date));
const expectedWorkDays = (items) => { const selected=items.filter(isPlannedRest).length; if(selected) return items.length - selected; const weeks=new Set(items.map(d=>weekStart(d.date))).size; return Math.max(0, items.length - Math.min(items.length, weeks * restConfig.restDaysPerWeek)); };
const completionText = (active, expected) => `${active} / ${expected} (${expected ? Math.round((active / expected) * 100) : 0}%)`;
const loaded = [];
for (const month of months) {
  try {
    const raw = await dv.io.load(`life/worklog/data/time_daily_stats_${month}.json`);
    loaded.push(JSON.parse(raw));
  } catch (e) {}
}
const labels = loaded[0]?.category_labels || {};
const allDays = loaded.flatMap(m => m.days || []);
const days = view === "year" ? allDays.filter(d => d.date.startsWith(targetYear + "-")) : allDays;
const dayWorkMin = (d) => cats.reduce((sum,c)=>sum+(d.by_category?.[c]||0),0);
const categoryTotals = (items) => { const totals=Object.fromEntries(cats.map(c=>[c,0])); for (const day of items) for (const c of cats) totals[c] += day.by_category?.[c] || 0; return totals; };
const byMonth = (items) => {
  const map = new Map();
  for (const day of items) map.set(day.date.slice(0,7), (map.get(day.date.slice(0,7)) || 0) + dayWorkMin(day));
  return [...map.entries()].sort((a,b)=>a[0].localeCompare(b[0])).map(([name,total])=>({name,total}));
};
const total = days.reduce((sum,d)=>sum+dayWorkMin(d),0);
const activeDays = days.filter(d=>dayWorkMin(d)>0).length;
const expectedDays = expectedWorkDays(days);
const expectedAvg = expectedDays ? Math.round(total / expectedDays) : 0;
const bestDay = days.reduce((a,b)=>dayWorkMin(b)>dayWorkMin(a)?b:a,{date:"-",by_category:{}});
const totals = categoryTotals(days);
const pieCats = cats.map(c=>({name:labels[c]||c,total:totals[c]||0,key:c})).filter(r=>r.total>0).sort((a,b)=>b.total-a.total);
const rankedCats = pieCats.slice(0,6);
const rankedDays = days.filter(d=>dayWorkMin(d)>0).sort((a,b)=>dayWorkMin(b)-dayWorkMin(a)).slice(0,6).map(d=>({name:d.date,total:dayWorkMin(d)}));
const rankedMonths = byMonth(days).filter(r=>r.total>0).sort((a,b)=>b.total-a.total).slice(0,6);
const style = document.createElement("style");
style.textContent = `.time-summary{display:grid;grid-template-columns:repeat(4,minmax(120px,1fr));gap:10px;margin:10px 0 16px}.time-card{border:1px solid var(--background-modifier-border);border-radius:10px;padding:10px 12px;background:var(--background-secondary)}.time-card-k{color:var(--text-muted);font-size:12px}.time-card-v{font-size:22px;font-weight:750;margin-top:4px}.time-section-title{font-size:13px;font-weight:650;margin:14px 0 6px;color:var(--text-muted)}.time-empty{border:1px dashed var(--background-modifier-border);border-radius:10px;padding:18px;color:var(--text-muted);background:var(--background-secondary);margin:10px 0}.time-pie-wrap{display:grid;grid-template-columns:180px minmax(220px,1fr);gap:16px;align-items:center;max-width:780px;margin:8px 0 16px}.time-pie{width:160px;aspect-ratio:1;border-radius:50%;border:1px solid var(--background-modifier-border)}.time-pie-legend,.time-rank{border:1px solid var(--background-modifier-border);border-radius:8px;background:var(--background-secondary);overflow:hidden}.time-pie-row{display:grid;grid-template-columns:14px 1fr auto auto;gap:8px;align-items:center;padding:7px 10px;border-bottom:1px solid var(--background-modifier-border);font-size:13px}.time-pie-row:last-child{border-bottom:0}.time-pie-swatch{width:10px;height:10px;border-radius:50%}.time-pie-val,.time-pie-pct,.time-rank-val{font-variant-numeric:tabular-nums;font-weight:650;white-space:nowrap}.time-pie-pct{color:var(--text-muted)}.time-rank-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;max-width:980px;margin:14px 0 16px}.time-rank-title{font-size:13px;font-weight:650;margin:0 0 6px;color:var(--text-muted)}.time-rank-row{display:grid;grid-template-columns:34px minmax(0,1fr) auto;gap:10px;align-items:center;padding:8px 10px;border-bottom:1px solid var(--background-modifier-border)}.time-rank-row:last-child{border-bottom:0}.time-rank-no{font-weight:750;color:var(--text-accent)}.time-rank-name{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}@media (max-width:760px){.time-summary{grid-template-columns:repeat(2,minmax(0,1fr))}.time-pie-wrap,.time-rank-grid,.time-bars{grid-template-columns:1fr}.time-pie{justify-self:center}}`;
dv.container.appendChild(style);
const cards = (items) => { const el=dv.el("div","",{cls:"time-summary"}); el.innerHTML=items.map(([k,v])=>`<div class="time-card"><div class="time-card-k">${k}</div><div class="time-card-v">${v}</div></div>`).join(""); };
const rankRows = (title, rows) => `<div><div class="time-rank-title">${title}</div><div class="time-rank">${rows.length?rows.map((r,i)=>`<div class="time-rank-row"><div class="time-rank-no">#${i+1}</div><div class="time-rank-name">${r.name}</div><div class="time-rank-val">${fmt(r.total)}</div></div>`).join(""):`<div class="time-rank-row"><div class="time-rank-name">No data</div></div>`}</div></div>`;
const rankGrid = (groups) => { const grid=dv.el("div","",{cls:"time-rank-grid"}); grid.innerHTML=groups.map(g=>rankRows(g.title,g.rows)).join(""); };
const pieChart = (title) => { const rows=pieCats; dv.el("div",title,{cls:"time-section-title"}); const el=dv.el("div","",{cls:"time-pie-wrap"}); if(!total){el.innerHTML=`<div class="time-pie" style="background:var(--background-modifier-border)"></div><div class="time-pie-legend"><div class="time-pie-row">No data</div></div>`; return;} let acc=0; const gradient=rows.map(r=>{const start=(acc/total)*100; acc+=r.total; const end=(acc/total)*100; return `${color[r.key]} ${start}% ${end}%`;}).join(","); el.innerHTML=`<div class="time-pie" style="background:conic-gradient(${gradient})"></div><div class="time-pie-legend">${rows.map(r=>`<div class="time-pie-row"><span class="time-pie-swatch" style="background:${color[r.key]}"></span><span>${r.name}</span><span class="time-pie-val">${fmt(r.total)}</span><span class="time-pie-pct">${Math.round((r.total/total)*100)}%</span></div>`).join("")}</div>`; };
cards([
  [view === "year" ? "Year" : "All Time", fmt(total)],
  ["Daily Avg", fmt(activeDays ? Math.round(total / activeDays) : 0)],
  ["Expected Avg", fmt(expectedAvg)],
  ["Active Days", String(activeDays)],
  ["Expected", String(expectedDays)],
  ["Completion", completionText(activeDays, expectedDays)],
  ["Best Day", bestDay.date === "-" ? "-" : bestDay.date.slice(5)]
]);
if(!total){ dv.el("div", view === "year" ? "今年還沒有正式做事時間紀錄。" : "目前還沒有正式做事時間紀錄。", {cls:"time-empty"}); return; }
pieChart(view === "year" ? "今年類別占比" : "總累積類別占比");
rankGrid([
  {title: view === "year" ? "今年月份排名" : "總月份排名", rows: rankedMonths},
  {title: view === "year" ? "今年日排名" : "總日排名", rows: rankedDays},
  {title: view === "year" ? "今年類別排名" : "總類別排名", rows: rankedCats}
]);
```


## All-Time Overview

所有已同步月份的做事時間總覽、類別占比與排名。


```dataviewjs
const months = ["2026-03", "2026-04", "2026-05", "2026-06", "2026-07"];
const view = "total";
const targetYear = "2026";
const cats = ["course", "research", "self_study", "language", "leetcode", "admin", "other"];
const color = {course:"#4f83ff", research:"#2fbf71", self_study:"#8b6cff", language:"#e56ab3", leetcode:"#f59f00", admin:"#8a8f98", other:"#6c757d"};
const fmt = (min) => { const h = Math.floor((min || 0) / 60); const m = (min || 0) % 60; return h ? `${h}h${m ? " " + m + "m" : ""}` : `${m}m`; };
const restConfig = {
  weeklyRestDays: [],
  restDaysPerWeek: 1,
  decisionWeekday: 1,
  restDates: []
};
const weekday = (iso) => new Date(`${iso}T00:00:00+08:00`).getDay();
const weekStart = (iso) => { const dt = new Date(`${iso}T00:00:00+08:00`); dt.setDate(dt.getDate() - ((dt.getDay() + 6) % 7)); return dt.toISOString().slice(0,10); };
const isPlannedRest = (d) => restConfig.restDates.includes(d.date) || restConfig.weeklyRestDays.includes(weekday(d.date));
const expectedWorkDays = (items) => { const selected=items.filter(isPlannedRest).length; if(selected) return items.length - selected; const weeks=new Set(items.map(d=>weekStart(d.date))).size; return Math.max(0, items.length - Math.min(items.length, weeks * restConfig.restDaysPerWeek)); };
const completionText = (active, expected) => `${active} / ${expected} (${expected ? Math.round((active / expected) * 100) : 0}%)`;
const loaded = [];
for (const month of months) {
  try {
    const raw = await dv.io.load(`life/worklog/data/time_daily_stats_${month}.json`);
    loaded.push(JSON.parse(raw));
  } catch (e) {}
}
const labels = loaded[0]?.category_labels || {};
const allDays = loaded.flatMap(m => m.days || []);
const days = view === "year" ? allDays.filter(d => d.date.startsWith(targetYear + "-")) : allDays;
const dayWorkMin = (d) => cats.reduce((sum,c)=>sum+(d.by_category?.[c]||0),0);
const categoryTotals = (items) => { const totals=Object.fromEntries(cats.map(c=>[c,0])); for (const day of items) for (const c of cats) totals[c] += day.by_category?.[c] || 0; return totals; };
const byMonth = (items) => {
  const map = new Map();
  for (const day of items) map.set(day.date.slice(0,7), (map.get(day.date.slice(0,7)) || 0) + dayWorkMin(day));
  return [...map.entries()].sort((a,b)=>a[0].localeCompare(b[0])).map(([name,total])=>({name,total}));
};
const total = days.reduce((sum,d)=>sum+dayWorkMin(d),0);
const activeDays = days.filter(d=>dayWorkMin(d)>0).length;
const expectedDays = expectedWorkDays(days);
const expectedAvg = expectedDays ? Math.round(total / expectedDays) : 0;
const bestDay = days.reduce((a,b)=>dayWorkMin(b)>dayWorkMin(a)?b:a,{date:"-",by_category:{}});
const totals = categoryTotals(days);
const pieCats = cats.map(c=>({name:labels[c]||c,total:totals[c]||0,key:c})).filter(r=>r.total>0).sort((a,b)=>b.total-a.total);
const rankedCats = pieCats.slice(0,6);
const rankedDays = days.filter(d=>dayWorkMin(d)>0).sort((a,b)=>dayWorkMin(b)-dayWorkMin(a)).slice(0,6).map(d=>({name:d.date,total:dayWorkMin(d)}));
const rankedMonths = byMonth(days).filter(r=>r.total>0).sort((a,b)=>b.total-a.total).slice(0,6);
const style = document.createElement("style");
style.textContent = `.time-summary{display:grid;grid-template-columns:repeat(4,minmax(120px,1fr));gap:10px;margin:10px 0 16px}.time-card{border:1px solid var(--background-modifier-border);border-radius:10px;padding:10px 12px;background:var(--background-secondary)}.time-card-k{color:var(--text-muted);font-size:12px}.time-card-v{font-size:22px;font-weight:750;margin-top:4px}.time-section-title{font-size:13px;font-weight:650;margin:14px 0 6px;color:var(--text-muted)}.time-empty{border:1px dashed var(--background-modifier-border);border-radius:10px;padding:18px;color:var(--text-muted);background:var(--background-secondary);margin:10px 0}.time-pie-wrap{display:grid;grid-template-columns:180px minmax(220px,1fr);gap:16px;align-items:center;max-width:780px;margin:8px 0 16px}.time-pie{width:160px;aspect-ratio:1;border-radius:50%;border:1px solid var(--background-modifier-border)}.time-pie-legend,.time-rank{border:1px solid var(--background-modifier-border);border-radius:8px;background:var(--background-secondary);overflow:hidden}.time-pie-row{display:grid;grid-template-columns:14px 1fr auto auto;gap:8px;align-items:center;padding:7px 10px;border-bottom:1px solid var(--background-modifier-border);font-size:13px}.time-pie-row:last-child{border-bottom:0}.time-pie-swatch{width:10px;height:10px;border-radius:50%}.time-pie-val,.time-pie-pct,.time-rank-val{font-variant-numeric:tabular-nums;font-weight:650;white-space:nowrap}.time-pie-pct{color:var(--text-muted)}.time-rank-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;max-width:980px;margin:14px 0 16px}.time-rank-title{font-size:13px;font-weight:650;margin:0 0 6px;color:var(--text-muted)}.time-rank-row{display:grid;grid-template-columns:34px minmax(0,1fr) auto;gap:10px;align-items:center;padding:8px 10px;border-bottom:1px solid var(--background-modifier-border)}.time-rank-row:last-child{border-bottom:0}.time-rank-no{font-weight:750;color:var(--text-accent)}.time-rank-name{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}@media (max-width:760px){.time-summary{grid-template-columns:repeat(2,minmax(0,1fr))}.time-pie-wrap,.time-rank-grid,.time-bars{grid-template-columns:1fr}.time-pie{justify-self:center}}`;
dv.container.appendChild(style);
const cards = (items) => { const el=dv.el("div","",{cls:"time-summary"}); el.innerHTML=items.map(([k,v])=>`<div class="time-card"><div class="time-card-k">${k}</div><div class="time-card-v">${v}</div></div>`).join(""); };
const rankRows = (title, rows) => `<div><div class="time-rank-title">${title}</div><div class="time-rank">${rows.length?rows.map((r,i)=>`<div class="time-rank-row"><div class="time-rank-no">#${i+1}</div><div class="time-rank-name">${r.name}</div><div class="time-rank-val">${fmt(r.total)}</div></div>`).join(""):`<div class="time-rank-row"><div class="time-rank-name">No data</div></div>`}</div></div>`;
const rankGrid = (groups) => { const grid=dv.el("div","",{cls:"time-rank-grid"}); grid.innerHTML=groups.map(g=>rankRows(g.title,g.rows)).join(""); };
const pieChart = (title) => { const rows=pieCats; dv.el("div",title,{cls:"time-section-title"}); const el=dv.el("div","",{cls:"time-pie-wrap"}); if(!total){el.innerHTML=`<div class="time-pie" style="background:var(--background-modifier-border)"></div><div class="time-pie-legend"><div class="time-pie-row">No data</div></div>`; return;} let acc=0; const gradient=rows.map(r=>{const start=(acc/total)*100; acc+=r.total; const end=(acc/total)*100; return `${color[r.key]} ${start}% ${end}%`;}).join(","); el.innerHTML=`<div class="time-pie" style="background:conic-gradient(${gradient})"></div><div class="time-pie-legend">${rows.map(r=>`<div class="time-pie-row"><span class="time-pie-swatch" style="background:${color[r.key]}"></span><span>${r.name}</span><span class="time-pie-val">${fmt(r.total)}</span><span class="time-pie-pct">${Math.round((r.total/total)*100)}%</span></div>`).join("")}</div>`; };
cards([
  [view === "year" ? "Year" : "All Time", fmt(total)],
  ["Daily Avg", fmt(activeDays ? Math.round(total / activeDays) : 0)],
  ["Expected Avg", fmt(expectedAvg)],
  ["Active Days", String(activeDays)],
  ["Expected", String(expectedDays)],
  ["Completion", completionText(activeDays, expectedDays)],
  ["Best Day", bestDay.date === "-" ? "-" : bestDay.date.slice(5)]
]);
if(!total){ dv.el("div", view === "year" ? "今年還沒有正式做事時間紀錄。" : "目前還沒有正式做事時間紀錄。", {cls:"time-empty"}); return; }
pieChart(view === "year" ? "今年類別占比" : "總累積類別占比");
rankGrid([
  {title: view === "year" ? "今年月份排名" : "總月份排名", rows: rankedMonths},
  {title: view === "year" ? "今年日排名" : "總日排名", rows: rankedDays},
  {title: view === "year" ? "今年類別排名" : "總類別排名", rows: rankedCats}
]);
```


## Review Flags

### Open Sessions

<table class="worklog-review-table">
<thead><tr><th>Date</th><th>Start</th><th>End</th><th>Duration</th><th>Category</th><th>Label</th><th>Status</th></tr></thead>
<tbody>
<tr><td colspan="7" class="empty">None</td></tr>
</tbody>
</table>

### Needs Review

<table class="worklog-review-table">
<thead><tr><th>Date</th><th>Start</th><th>End</th><th>Duration</th><th>Category</th><th>Label</th><th>Status</th></tr></thead>
<tbody>
<tr><td>2026-05-14</td><td>23:24</td><td>13:14</td><td class="num">37h 50m</td><td>課業</td><td></td><td>needs_review</td></tr>
</tbody>
</table>
