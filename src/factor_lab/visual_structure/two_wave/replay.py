# ruff: noqa: E501
# The self-contained HTML/CSS/JavaScript template retains its own line formatting.
"""Self-contained, network-free OHLC prefix replay and independent annotation.

The file embeds historical data for local replay. Cutoff controls prevent visual
future leakage, not a determined reviewer inspecting the HTML source. Engine
overlays are hidden by default and any exposure marks subsequent annotations as
non-independent. Bar-prefix causality does not certify historical source PIT.
"""

from __future__ import annotations

import base64
import gzip
import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any


def _records(values: Any) -> list[dict[str, Any]]:
    if hasattr(values, "to_dict"):
        return values.to_dict(orient="records")
    return [dict(item) for item in values]


def write_replay(path: str | Path, bars: Iterable[Mapping[str, Any]], export: Mapping[str, Any], snapshots: Any = None) -> Path:
    """Write one scale's replay HTML and return its path."""
    return write_replay_bundle(path, [{"name": export.get("scale_id", "two-wave"), "bars": bars, "export": export, "snapshots": snapshots}])


def write_replay_bundle(path: str | Path, runs: Iterable[Mapping[str, Any]]) -> Path:
    """Write selectable precomputed timeframes/scales, with no frontend build.

    ``runs`` items contain ``name``, ``bars``, ``export``, and optional per-bar
    ``snapshots``. A missing snapshot deliberately hides the candidate instead
    of reconstructing it using later confirmed pivots.
    """
    payload = []
    for run in runs:
        export = dict(run["export"])
        bars = _records(run.get("bars", export.get("bars", [])))
        # Bars belong to the viewer run once, not twice in every embedded export.
        export.pop("bars", None)
        if not bars:
            raise ValueError("Replay requires at least one OHLC bar")
        snapshots = run.get("snapshots")
        if snapshots is None:
            snapshots = []
        payload.append(
            {"name": str(run.get("name", export.get("scale_id", "two-wave"))), "bars": bars, "export": export, "snapshots": snapshots}
        )
    if not payload:
        raise ValueError("At least one replay run is required")
    encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False, default=str, separators=(",", ":"))
    # Gzip is decoded by the browser's built-in DecompressionStream; there are
    # no CDN dependencies. Base64 cannot inject a closing script tag.
    encoded = base64.b64encode(gzip.compress(encoded.encode("utf-8"), mtime=0)).decode("ascii")
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(_HTML.replace("__REPLAY_DATA__", encoded), encoding="utf-8")
    return target


_HTML = r"""<!doctype html>
<html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>两浪形态 · 逐根审查</title>
<style>
:root{color-scheme:dark;font-family:system-ui,-apple-system,"Segoe UI",sans-serif;background:#0c1320;color:#e4eaf4}*{box-sizing:border-box}body{margin:0;padding:22px;max-width:1700px;margin:auto}h1{font-size:24px;margin:0 0 7px}p{line-height:1.6;margin:6px 0}.muted{color:#9facbf;font-size:13px}.notice{background:#202b3c;border-left:3px solid #e4b566;padding:10px 14px;margin:16px 0}.toolbar,.panel{background:#121e30;border:1px solid #29394e;border-radius:9px;padding:12px;margin-top:12px}.row{display:flex;align-items:center;flex-wrap:wrap;gap:10px}label{font-size:13px;color:#bac9dd}button,input,select{background:#1b2d44;color:#e4eaf4;border:1px solid #425873;border-radius:5px;padding:7px;font:inherit;font-size:13px}button{cursor:pointer}button:hover{background:#294463}input[type=checkbox]{accent-color:#6cc0ef}input[type=range]{flex:1;min-width:180px}canvas{width:100%;height:490px;display:block;background:#0d1829;border-radius:8px;margin-top:12px;touch-action:manipulation}.grid{display:grid;grid-template-columns:minmax(250px,1fr) minmax(300px,1.1fr);gap:12px}.grid>.panel{min-width:0}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px;color:#b9cce2;max-height:330px;overflow:auto}.status{font-size:13px;line-height:1.8;overflow-wrap:anywhere}.chip{color:#7bddc5;font-size:12px}.bad{color:#ffbe81}#points{width:220px}#reviewer{width:150px}#annotations{max-height:140px}#tooltip{position:fixed;display:none;pointer-events:none;padding:9px;background:#223650;border:1px solid #557aa4;border-radius:5px;font-size:12px;z-index:5;white-space:pre-line}table{border-collapse:collapse;width:100%;font-size:12px}td,th{text-align:left;padding:5px;border-bottom:1px solid #283950}@media(max-width:760px){body{padding:10px}.grid{grid-template-columns:1fr}canvas{height:390px}}
</style>
<h1>两浪形态 · 逐根审查</h1>
<p class="muted">研究候选 / 形态复刻尚未验收 / 无交易与第三浪统计授权</p>
<div class="notice">默认隐藏算法，供独立人工参考标注。人工标签是待审查的参考，算法分类也不是正确答案。当前“在线”仅指 <b>K 线前缀截断</b>；历史数据实际可得时点未核验（historical_PIT_not_verified）。完整图回看、回退到已见未来的较早时点、跨尺度回退和算法曝光都会被记录。</div>
<div class="toolbar">
<div class="row"><label>周期 / 尺度 <select id="run"></select></label><label>区间起始 UTC <input id="startDate" placeholder="YYYY-MM-DD 或 ISO 时间"></label><label>区间结束 UTC <input id="endDate" placeholder="留空至样本末尾"></label><button id="applyDates">应用区间</button><label><input type="checkbox" id="full">完整历史图回看</label><label><input type="checkbox" id="overlay">显示算法结果</label></div>
<div class="row" style="margin-top:10px"><button id="previous">上一根</button><button id="play">播放</button><button id="next">下一根</button><input type="range" id="cutoff" min="0" max="1" value="0"><label>截止序号 <input type="number" id="cutoffNumber" min="0" value="0" style="width:90px"></label><select id="speed"><option value="600">慢速</option><option value="160" selected>常速</option><option value="40">快速</option></select></div>
<div id="clock" class="status" style="margin-top:8px"></div>
</div>
<canvas id="chart" aria-label="截至所选K线的OHLC行情，点击选择人工极值序号"></canvas>
<p class="muted" id="legend">K 线上涨为青色、下跌为橙色。点击图表选择人工极值；纵轴和横轴只使用当前可见前缀。查看更早区间可改变起始日期。</p>
<div class="grid">
<div class="panel"><div class="row"><b>当时已知的结构</b><select id="structure" style="max-width:90%"></select></div><div id="state" class="status"></div><pre id="details"></pre></div>
<div class="panel"><b>已确认事件</b><p class="muted">最多显示最近 80 条。发生时间与确认时间分别列出；确认后的极值标记回画到发生位置，不意味着当时已知。</p><pre id="events"></pre></div>
</div>
<div class="panel"><b>独立人工标注</b><p class="muted">结构选五个交替极值，完整周期选三个；使用原始 bar 序号。需明确标注人与类别，不从算法自动填充。显示过算法的本次会话标注会被排除出独立参考评估。</p>
<div class="row"><label>标注人 <input id="reviewer" placeholder="姓名或稳定代号"></label><label>对象 <select id="kind"><option value="structure">连续两浪 · 5 点</option><option value="cycle">完整周期 · 3 点</option></select></label><label>相位 <select id="phase"><option value="low">低点起算</option><option value="high">高点起算</option></select></label><label>人工分类 <select id="label"><option value="">请选择</option><option value="range">震荡</option><option value="uptrend">上涨趋势</option><option value="downtrend">下跌趋势</option><option value="uncertain">不能稳定归类</option></select></label></div>
<div class="row" style="margin-top:10px"><label>极值序号 <input id="points" placeholder="例如 10, 20, 30, 40, 50"></label><button id="clearPoints">清空选点</button><button id="addAnnotation">保存此标注</button><button id="addWindow">声明当前可见区间已完整审查</button><button id="download">下载标注 JSON</button></div>
<p id="annotationStatus" class="muted">尚未标注。完整审查声明仅针对当前选择的对象（两浪结构或完整周期）。</p><pre id="annotations"></pre></div>
<div id="tooltip"></div>
<script id="replayData" type="application/octet-stream" data-encoding="base64-gzip">__REPLAY_DATA__</script>
<script>
'use strict';
async function startReplay(){
if(typeof DecompressionStream==='undefined')throw Error('浏览器需支持 DecompressionStream，请使用近期版本的 Chrome、Edge、Firefox 或 Safari。');
const packed=Uint8Array.from(atob(document.getElementById('replayData').textContent),c=>c.charCodeAt(0));
const decoded=await new Response(new Blob([packed]).stream().pipeThrough(new DecompressionStream('gzip'))).text();
const runs=JSON.parse(decoded), $=id=>document.getElementById(id);
let runIndex=0, lo=0, hi=0, cutoff=0, timer=null, geometry=null, overlayExposed=false, fullExposed=false;
const highestSeenByInstrument={};
const annotations=[],windows=[];
const fmt=n=>Number.isFinite(Number(n))?Number(n).toFixed(4):'—';
const json=x=>JSON.stringify(x,null,2);
const current=()=>runs[runIndex];
const stop=()=>{if(timer)clearInterval(timer);timer=null;$('play').textContent='播放'};
const known=(x,k)=>Number.isInteger(x.confirmation_bar)&&x.confirmation_bar<=k;
const visibleCutoff=()=> $('full').checked?hi:cutoff;
const pointIndex=p=>Number(p.occurrence_bar);
const clockText=t=>t===undefined||t===null?'未提供':String(t);
const mode=()=>fullExposed?'offline':'online';
function identity(){const e=current().export;return {config_id:e.config_hash,timeframe:e.config.timeframe,scale_id:e.scale_id}}
function snapshot(k){const s=current().snapshots;if(Array.isArray(s)){const v=s[k];return v&&v.bar_index===k?v:s.find(x=>x.bar_index===k)}return s[String(k)]||null}
function baseClock(k){const b=current().bars[k],s=snapshot(k),e=current().export;const available=s&&s.information_available_time||b.information_available_time||b.available_at;return `K线 #${k} · 结束 ${clockText(b.timestamp)} · 信息可得 ${clockText(available)} · ${$('full').checked?'完整图回看':'K线前缀截断'} · ${e.config.timeframe} / ${e.scale_id}`}
function resetRun(){stop();const r=current();lo=0;hi=r.bars.length-1;cutoff=Math.min(99,hi);$('cutoff').max=hi;$('cutoffNumber').max=hi;$('startDate').value='';$('endDate').value='';$('points').value='';$('structure').innerHTML='';draw()}
runs.forEach((r,i)=>{const o=document.createElement('option');o.value=i;o.textContent=r.name;$('run').appendChild(o)});
$('run').onchange=()=>{runIndex=Number($('run').value);resetRun()};
function setCutoff(k){cutoff=Math.max(lo,Math.min(hi,Math.round(k)));draw()}
$('cutoff').oninput=()=>setCutoff(Number($('cutoff').value));$('cutoffNumber').onchange=()=>setCutoff(Number($('cutoffNumber').value));
$('previous').onclick=()=>{stop();setCutoff(cutoff-1)};$('next').onclick=()=>{stop();setCutoff(cutoff+1)};
$('play').onclick=()=>{if(timer){stop();return}if($('full').checked){$('full').checked=false}if(cutoff===hi)cutoff=lo;$('play').textContent='暂停';timer=setInterval(()=>{if(cutoff>=hi){stop();return}setCutoff(cutoff+1)},Number($('speed').value))};
$('speed').onchange=()=>{if(timer){stop();$('play').click()}};
$('full').onchange=()=>{if($('full').checked){fullExposed=true;stop()}draw()};
$('overlay').onchange=()=>{if($('overlay').checked)overlayExposed=true;draw()};
$('structure').onchange=()=>draw();
function parseDate(value,end){if(!value.trim())return null;let s=value.trim();if(/^\d{4}-\d{2}-\d{2}$/.test(s))s+=end?'T23:59:59.999Z':'T00:00:00Z';const t=Date.parse(s);if(!Number.isFinite(t))throw Error('日期无效，请使用 YYYY-MM-DD 或带时区的 ISO 时间');return t}
$('applyDates').onclick=()=>{try{const bars=current().bars,a=parseDate($('startDate').value,false),b=parseDate($('endDate').value,true);let left=0,right=bars.length-1;if(a!==null){left=bars.findIndex(v=>Date.parse(v.timestamp)>=a);if(left<0)throw Error('起始日期超出样本')}if(b!==null){while(right>=0&&Date.parse(bars[right].timestamp)>b)right--}if(right<left)throw Error('区间内没有K线');lo=left;hi=right;$('cutoff').min=lo;$('cutoff').max=hi;$('cutoffNumber').min=lo;$('cutoffNumber').max=hi;setCutoff(Math.max(lo,Math.min(cutoff,hi)))}catch(e){alert(e.message)}};
function visibleStructures(k){return current().export.structures.filter(s=>known(s,k))}
function stateAt(s,k){const snap=snapshot(k);if(snap&&snap.structure_states&&snap.structure_states[s.structure_id])return snap.structure_states[s.structure_id];const events=current().export.events.filter(e=>known(e,k)&&e.structure_id===s.structure_id);const broken=events.find(e=>e.type==='structure_breakout');return {geometry_alive:Boolean(s.geometry&&s.geometry.valid)&&!broken,first_breakout_event_id:broken?broken.event_id:null,first_breakout_bar:broken?broken.confirmation_bar:null,cycle_count:2+events.filter(e=>e.type==='structure_cycle_confirmed').length}}
function refreshPanels(k){const show=$('overlay').checked;$('clock').textContent=baseClock(k);$('cutoff').value=cutoff;$('cutoffNumber').value=cutoff;
 if(!show){$('structure').hidden=true;$('state').textContent='盲标模式：算法状态、结构、指标和事件均隐藏。';$('details').textContent='';$('events').textContent='算法结果隐藏。';return null}
 $('structure').hidden=false;const structures=visibleStructures(k),old=$('structure').value;let selected=structures.find(s=>s.structure_id===old)||structures[structures.length-1];$('structure').innerHTML='';
 structures.slice(-300).reverse().forEach(s=>{const option=document.createElement('option');option.value=s.structure_id;option.textContent=s.structure_id+' · '+s.classification;$('structure').appendChild(option)});
 if(selected)$('structure').value=selected.structure_id;
 const snap=snapshot(k);$('state').textContent=snap?`状态：${snap.state||snap.direction||'逐根快照可用'}；候选拐点会随后续K线变化。`:'无逐根快照：不使用未来拐点倒推当时候选。';
 if(selected){const g=selected.geometry||{};$('details').textContent=json({structure_id:selected.structure_id,phase:selected.phase,cycle_ids:selected.cycle_ids,pivot_ids:selected.pivot_ids,extremum_end_bar:selected.end_bar,confirmation_bar:selected.confirmation_bar,confirmation_time:selected.confirmation_time,information_available_time:selected.information_available_time,classification:selected.classification,D:g.D,E:g.E,width:g.width,nominal_coverage:g.nominal_coverage,envelope_coverage:g.envelope_coverage,attributes:selected.attributes,state_at_cutoff:stateAt(selected,k),frozen_geometry:g})}else $('details').textContent='当前前缀尚无已确认两浪结构。';
 $('events').textContent=current().export.events.filter(e=>known(e,k)).slice(-80).reverse().map(e=>json(e)).join('\n\n')||'尚无已确认事件。';return selected}
function recordExposure(r,k){const instrument=r.export.config.instrument||'shared_instrument',time=Date.parse(r.bars[k].timestamp),seen=highestSeenByInstrument[instrument];if(Number.isFinite(seen)&&time<seen)fullExposed=true;if(Number.isFinite(time))highestSeenByInstrument[instrument]=Math.max(seen||-Infinity,time)}
function draw(){const k=visibleCutoff(),r=current(),bars=r.bars;recordExposure(r,k);const selected=refreshPanels(k),canvas=$('chart'),rect=canvas.getBoundingClientRect(),dpr=window.devicePixelRatio||1,w=rect.width,h=rect.height;canvas.width=w*dpr;canvas.height=h*dpr;const c=canvas.getContext('2d');c.scale(dpr,dpr);c.clearRect(0,0,w,h);const left=67,right=w-22,top=30,bottom=h-46,n=k-lo+1;
 let ymin=Infinity,ymax=-Infinity;for(let i=lo;i<=k;i++){ymin=Math.min(ymin,Number(bars[i].low));ymax=Math.max(ymax,Number(bars[i].high))}let span=ymax-ymin;if(span<=0)span=Math.max(ymax*.01,1);ymin-=span*.09;ymax+=span*.09;
 const x=i=>left+(i-lo+.5)/n*(right-left),y=p=>bottom-(p-ymin)/(ymax-ymin)*(bottom-top);geometry={left,right,top,bottom,lo,k,x,y,w,h};
 c.font='11px system-ui';c.textAlign='right';for(let j=0;j<=5;j++){const p=ymin+(ymax-ymin)*j/5,yy=y(p);c.strokeStyle='#24324a';c.beginPath();c.moveTo(left,yy);c.lineTo(right,yy);c.stroke();c.fillStyle='#a7b8cf';c.fillText(p.toFixed(2),left-8,yy+4)}
 c.textAlign='center';for(let j=0;j<=4;j++){const i=Math.round(lo+(k-lo)*j/4);c.fillStyle='#9cadc4';c.fillText('#'+i+' '+String(bars[i].timestamp).slice(0,10),x(i),h-18)}
 c.save();c.beginPath();c.rect(left,top,right-left,bottom-top);c.clip();
 const bw=Math.max(.8,Math.min(12,(right-left)/n*.65));
 if(n>4500){c.strokeStyle='#8fc6c3';c.lineWidth=1;c.beginPath();for(let i=lo;i<=k;i++){const xx=x(i),yy=y(Number(bars[i].close));if(i===lo)c.moveTo(xx,yy);else c.lineTo(xx,yy)}c.stroke()}else for(let i=lo;i<=k;i++){const b=bars[i],xx=x(i);c.strokeStyle=c.fillStyle=Number(b.close)>=Number(b.open)?'#66d5c1':'#eda575';c.beginPath();c.moveTo(xx,y(Number(b.low)));c.lineTo(xx,y(Number(b.high)));c.stroke();const a=y(Number(b.open)),z=y(Number(b.close));c.fillRect(xx-bw/2,Math.min(a,z),bw,Math.max(1,Math.abs(a-z)))}
 if($('overlay').checked){const pivots=r.export.pivots.filter(p=>known(p,k));
 if(selected){const g=selected.geometry||{},alive=stateAt(selected,k),valid=g.valid!==false&&Number.isFinite(g.b)&&Number.isFinite(g.lower_offset)&&Number.isFinite(g.upper_offset);if(valid){let end=k;if(alive.first_breakout_bar!==null&&alive.first_breakout_bar!==undefined)end=Math.min(end,alive.first_breakout_bar);const start=Math.max(lo,selected.start_bar);c.strokeStyle='#e6ca76';c.lineWidth=1.5;c.setLineDash([6,4]);for(const offset of [g.lower_offset,g.upper_offset]){c.beginPath();c.moveTo(x(start),y(Math.exp(offset+g.b*(start-g.origin_bar))));c.lineTo(x(end),y(Math.exp(offset+g.b*(end-g.origin_bar))));c.stroke()}c.setLineDash([])}
 const members=selected.pivot_ids.map(id=>pivots.find(p=>p.pivot_id===id)).filter(Boolean);c.strokeStyle='#91aaff';c.lineWidth=2;c.beginPath();members.forEach((p,j)=>{if(j===0)c.moveTo(x(pointIndex(p)),y(p.price));else c.lineTo(x(pointIndex(p)),y(p.price))});c.stroke();members.forEach((p,j)=>{if(pointIndex(p)>=lo){c.fillStyle='#c0ceff';c.fillText('P'+j,x(pointIndex(p)),y(p.price)+(p.kind==='high'?-12:20))}})
 }
 for(const p of pivots){const i=pointIndex(p);if(i<lo)continue;const xx=x(i),yy=y(p.price);c.fillStyle=p.kind==='high'?'#bda5ff':'#78caff';c.beginPath();c.moveTo(xx,yy-4);c.lineTo(xx+4,yy);c.lineTo(xx,yy+4);c.lineTo(xx-4,yy);c.closePath();c.fill();if(p.confirmation_bar>=lo){const cx=x(p.confirmation_bar);c.strokeStyle='#7892b966';c.lineWidth=1;c.setLineDash([2,4]);c.beginPath();c.moveTo(xx,yy);c.lineTo(cx,top+10);c.stroke();c.setLineDash([]);c.fillStyle='#d5dfef';c.fillRect(cx-2,top+5,4,7)}}
 const snap=snapshot(k),candidate=snap&&snap.candidate_pivot;if(candidate&&Number.isFinite(candidate.price)&&candidate.occurrence_bar<=k&&candidate.occurrence_bar>=lo){c.strokeStyle='#f4f2a4';c.lineWidth=2;c.beginPath();c.arc(x(candidate.occurrence_bar),y(candidate.price),6,0,Math.PI*2);c.stroke();c.fillStyle='#f4f2a4';c.fillText('候选',x(candidate.occurrence_bar),y(candidate.price)-13)}
 }
 const points=$('points').value.split(',').map(s=>s.trim()).filter(Boolean).map(Number);for(const i of points){if(Number.isInteger(i)&&i>=lo&&i<=k){c.strokeStyle='#ffffff';c.lineWidth=1;c.beginPath();c.arc(x(i),y(Number(bars[i].close)),8,0,Math.PI*2);c.stroke()}}
 c.restore();c.fillStyle='#93a8c7';c.textAlign='left';c.fillText(n>4500?'区间过密，显示收盘线；缩小区间可查看OHLC':'OHLC · 所见前缀独立缩放',left,18);
 $('legend').textContent=$('overlay').checked?'青色上涨、橙色下跌。菱形为已确认极值的发生位置；顶部短标记为确认bar，虚线连接二者；空心黄色圆为当时候选。紫线连接所选两浪成员；金色虚线是已冻结边界（仅在结构确认后可知），首次几何突破后停止延展。':'盲标模式：青色上涨、橙色下跌。点击图表选择人工极值。横纵轴仅由当前可见区间决定，隐藏未来价格、分类与候选。';
 updateAnnotationStatus()
}
$('chart').onclick=e=>{if(!geometry)return;const rect=$('chart').getBoundingClientRect(),xx=e.clientX-rect.left;if(xx<geometry.left||xx>geometry.right)return;const i=Math.max(lo,Math.min(visibleCutoff(),Math.floor((xx-geometry.left)/(geometry.right-geometry.left)*(visibleCutoff()-lo+1)+lo)));const points=$('points').value.split(',').map(s=>s.trim()).filter(Boolean).map(Number);const expected=$('kind').value==='cycle'?3:5;if(points.length>=expected)return;points.push(i);$('points').value=points.join(', ');draw()};
$('chart').onmousemove=e=>{if(!geometry)return;const rect=$('chart').getBoundingClientRect(),xx=e.clientX-rect.left;if(xx<geometry.left||xx>geometry.right){$('tooltip').style.display='none';return}const i=Math.max(lo,Math.min(visibleCutoff(),Math.floor((xx-geometry.left)/(geometry.right-geometry.left)*(visibleCutoff()-lo+1)+lo))),b=current().bars[i];$('tooltip').textContent=`#${i} ${b.timestamp}\nO ${b.open} H ${b.high} L ${b.low} C ${b.close}`;$('tooltip').style.display='block';$('tooltip').style.left=Math.min(window.innerWidth-320,e.clientX+12)+'px';$('tooltip').style.top=Math.min(window.innerHeight-90,e.clientY+12)+'px'};
$('chart').onmouseleave=()=>{$('tooltip').style.display='none'};
function reviewer(){const name=$('reviewer').value.trim();if(!name||['algorithm','engine','model','auto','automatic','算法'].includes(name.toLowerCase()))throw Error('请填写独立人工标注人的稳定代号');return name}
function updateAnnotationStatus(){const exposure=overlayExposed?'本次会话已显示算法，后续标注不作为独立参考。':'本次会话尚未显示算法。';$('annotationStatus').textContent=`已保存 ${annotations.length} 条标注，${windows.length} 个完整审查窗口。${exposure} 参考模式：${mode()}（完整图或回退产生未来曝光后保持 offline）。`;$('annotations').textContent=json({annotations,review_windows:windows})}
$('clearPoints').onclick=()=>{$('points').value='';draw()};$('points').onchange=()=>draw();$('kind').onchange=()=>{$('points').value='';draw()};
$('addAnnotation').onclick=()=>{try{const name=reviewer(),kind=$('kind').value,points=$('points').value.split(',').map(s=>s.trim()).filter(Boolean).map(Number),expected=kind==='cycle'?3:5,k=visibleCutoff();if(points.length!==expected||points.some((p,i)=>!Number.isInteger(p)||p<0||p>k||(i&&p<=points[i-1])))throw Error(`请选择 ${expected} 个严格递增且不超过当前截止bar的序号`);if(kind==='structure'&&!$('label').value)throw Error('请选择人工分类');annotations.push({...identity(),annotation_id:'human-'+Date.now()+'-'+annotations.length,reviewer:name,reference_mode:mode(),kind,phase:$('phase').value,pivot_indices:points,label:kind==='structure'?$('label').value:null,visible_cutoff:k,visible_start:lo,algorithm_visible:overlayExposed,independent_reference:!overlayExposed,historical_point_in_time_status:'historical_PIT_not_verified'});$('points').value='';draw()}catch(e){alert(e.message)}};
$('addWindow').onclick=()=>{try{const name=reviewer();if(overlayExposed)throw Error('已曝光算法，不能在本次会话声明独立完整审查窗口');windows.push({...identity(),reviewer:name,reference_mode:mode(),kind:$('kind').value,start_index:lo,end_index:visibleCutoff(),visible_cutoff:visibleCutoff(),fully_reviewed:true});updateAnnotationStatus()}catch(e){alert(e.message)}};
$('download').onclick=()=>{try{const name=reviewer();const data={schema_version:'two_wave_annotations@1.0',reviewer:name,reference_mode:mode(),annotations,review_windows:windows,notice:'Independent human references; online means bar-prefix only. Historical PIT not verified.'};const blob=new Blob([json(data)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='two_wave_human_annotations.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}catch(e){alert(e.message)}};
window.addEventListener('resize',draw);resetRun();
}
startReplay().catch(error=>{document.getElementById('clock').textContent='无法加载回放：'+error.message;console.error(error)});
</script></html>"""
