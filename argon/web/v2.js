/* ================= v2 오버라이드 ================= */
const ZC={g:'z-g',n:'z-n',w:'z-w',b:'z-b'};
function ruler(key){const r=DATA.rul[key];if(!r)return '';let prev=r.lo,span=r.hi-r.lo;
  const pos=Math.max(1,Math.min(99,(r.v-r.lo)/span*100));
  let zs='',zt='';r.z.forEach(([u,l,c])=>{const w=(Math.min(u,r.hi)-prev)/span*100;const on=r.v>=prev&&(r.v<u||u>=r.hi);
    zs+=`<i class="${ZC[c]}" style="width:${w}%"></i>`;zt+=`<span class="${on?'on':''}" style="width:${w}%">${(on||w>=22)?l:''}</span>`;prev=u});
  return `<div class="rl"><div class="zs">${zs}</div><div class="pin" style="left:${pos}%"></div><div class="zt">${zt}</div></div>`}
function parts(p,ttl){return `<div class="parts"><div class="ttl">${ttl||'점수는 이렇게 매겼어요'}</div>${p.map(([n,m,s,rule])=>`<div class="prow"><span>${n}</span><span class="s">${s}${m?'/'+m:'+'}</span><div class="bar"><i style="width:${m?s/m*100:100}%"></i></div>${rule?`<div class="rule-t">${rule}</div>`:''}</div>`).join('')}</div>`}
function histTxt(h,s){if(!h)return '';if(h.avg==null)return `<div class="hist">${h.label}<br>최근 1년 중 하위 <b>${h.pct}%</b></div>`;
  const diff=Math.round((h.now??s)-h.avg);return `<div class="hist">${h.label}<br>평균 <b>${h.avg}</b> · 범위 <b>${h.lo}~${h.hi}</b><br>평소보다 <b style="color:${diff<0?'var(--down)':'var(--up)'}">${diff>0?'+':''}${diff}점</b> · 하위 <b>${h.pct}%</b></div>`}
function gaugeBox(score,label,h){const g=grade(score);return `<div class="gauge"><div class="lbl">${label}</div>${dial(score)}<div class="grade" style="color:${g[1]}">${g[0]}</div>${histTxt(h,score)}</div>`}
function top3(score,label,p,dg,h){return `<div class="top3">${gaugeBox(score,label,h)}${parts(p)}${diag(dg)}</div>`}
function scaleBar(score,h,what){const avg=h&&h.avg!=null?h.avg:null;const ref=h&&h.now!=null?h.now:score;const per=h&&h.n<250?h.n+'일':'1년';
  const zones=[['방어 우선 0~39','z-b',40],['경계 40~54','z-w',15],['선별 55~69','z-n',15],['강세 70~100','z-g',30]];
  let msg=`${what} ${score}점은 '${grade(score)[0]}'.`;
  if(avg!=null) msg+= h.now!=null?` 같은 방식으로 환산한 오늘 ${ref}점 vs ${per} 평균 ${avg}점 → ${ref<avg-10?'평소보다 훨씬 나쁜 환경':ref<avg?'평소보다 조금 나쁜 환경':ref<avg+10?'평소보다 조금 좋은 환경':'평소보다 훨씬 좋은 환경'}.`:` ${per} 평균 ${avg}점${score<avg?'보다 낮아 평소보다 조심할 때.':'보다 높아 평소보다 우호적.'}`;
  return `<div class="scale"><div class="lab">점수 읽는 법<small>${msg}</small></div><div class="sbar">
   <div class="zones">${zones.map(([l,c,w])=>`<i class="${c}" style="${c==='z-n'?'background:#a16207':''}">${l}</i>`).join('')}</div>
   ${avg!=null?`<div class="mk avg" style="left:${avg}%"><i></i><span>${per} 평균 ${avg}</span></div>`:''}
   <div class="mk now" style="left:${score}%"><span>오늘 ${score}</span><i></i></div></div></div>`}
function kpiR(k){return k.map(([n,v,c,key,hint])=>`<div class="kpi"><div class="k">${n}</div><div class="v">${v}</div><div class="s ${c==null?'':cls(c)}">${c==null?'':pct(c)}${hint?`<span class="hn">${hint}</span>`:''}</div>${key?ruler(key):''}</div>`).join('')}
/* ---------- squarified treemap ---------- */
function squarify(items,x,y,w,h){const total=items.reduce((a,b)=>a+b.v,0);if(!items.length||total<=0)return[];
  const area=w*h;const it=items.map(o=>({...o,a:o.v/total*area}));const out=[];
  function worst(row,side){const s=row.reduce((a,b)=>a+b.a,0),mx=Math.max(...row.map(r=>r.a)),mn=Math.min(...row.map(r=>r.a));return Math.max(side*side*mx/(s*s),(s*s)/(side*side*mn))}
  function lay(row,rx,ry,rw,rh){const s=row.reduce((a,b)=>a+b.a,0);if(rw>=rh){const cw=s/rh;let cy=ry;row.forEach(r=>{const ch=r.a/cw;out.push({...r,x:rx,y:cy,w:cw,h:ch});cy+=ch});return[rx+cw,ry,rw-cw,rh]}
    else{const ch=s/rw;let cx=rx;row.forEach(r=>{const cw2=r.a/ch;out.push({...r,x:cx,y:ry,w:cw2,h:ch});cx+=cw2});return[rx,ry+ch,rw,rh-ch]}}
  let rect=[x,y,w,h],row=[],i=0;
  while(i<it.length){const side=Math.min(rect[2],rect[3]);const c=it[i];
    if(!row.length||worst([...row,c],side)<=worst(row,side)){row.push(c);i++}else{rect=lay(row,...rect);row=[]}}
  if(row.length)lay(row,...rect);return out}
function ccls(c,strong){return c>=strong?'c-su':c>0?'c-u':c===0?'c-f':c>-strong?'c-d':'c-sd'}
function fitPct(c,w,ps){let s=pct(c);if(s.length*ps*0.62>w-6){s=(c>0?'+':'')+c.toFixed(1)+'%';}if(s.length*ps*0.62>w-4){s=(c>0?'+':'')+Math.round(c)+'%';}return s.length*ps*0.6>w-2?'':s}
function tileHTML(r,chgKey,strong,showPx){const a=r.w*r.h,c=r[chgKey];let fs=Math.max(10,Math.min(26,Math.sqrt(a)/6.2));
  const nm=r.name;if(nm.length*fs*0.95>r.w-8)fs=(r.w-8)/(nm.length*0.95);
  let inner='';const ps=Math.max(9,Math.min(15,Math.max(fs,10)*0.62));
  if(fs>=8.5&&r.h>=26){inner=`<div class="n" style="font-size:${fs}px">${nm}</div>`;
    if(r.h>=fs*1.3+30&&r.w>=64)inner+=`<div class="c">${r.code}</div>`;
    const pv=fitPct(c,r.w,ps);
    if(pv&&r.h>=fs*1.3+15)inner+=`<div class="p" style="font-size:${ps}px">${showPx&&r.w>=110&&r.h>=fs*1.3+40?fmt(r.p,r.mk)+' ':''}${pv}</div>`}
  else if(r.h>=16){const pv=fitPct(c,r.w,9);if(pv)inner=`<div class="p" style="font-size:9px">${pv}</div>`}
  return `<div class="tl ${ccls(c,strong)}" data-code="${r.code}" style="left:${r.x}px;top:${r.y}px;width:${r.w}px;height:${r.h}px" title="${nm} ${pct(c)}">${inner}</div>`}
const TMW=784;
const SC=k=>k==='cr'?(v=>Math.sqrt(v)):(v=>v);
function tmTop(tm,h,id){const sq=id==='t-cr';const list=tm.top20.map(c=>tm.items.find(x=>x.code===c)).filter(Boolean).map(x=>({...x,v:sq?Math.sqrt(x.cap):x.cap}));
  const rs=squarify(list,0,0,TMW,h);
  return `<div class="tm" id="${id}" style="width:${TMW}px;height:${h}px">${rs.map(r=>tileHTML(r,'d1',2.5,true)).join('')}</div>
  <div class="legend"><span>${sq?'박스 크기 = 시가총액의 제곱근(비트코인이 60%라 작은 코인도 보이게 압축)':'박스 크기 = 시가총액'} · 색 = 전일 대비</span><span><i style="background:#047857"></i>+2.5%↑</span><span><i style="background:#15803d"></i>상승</span><span><i style="background:#334155"></i>보합</span><span><i style="background:#c2410c"></i>하락</span><span><i style="background:#9a3412"></i>-2.5%↓</span></div>`}
function tmSec(tm,h,id,strong){const secs=[...tm.sectors].sort((a,b)=>b.cap-a.cap).map(s=>({...s,v:s.cap}));
  const srs=squarify(secs,0,0,TMW,h);let html='';
  srs.forEach(s=>{const kids=tm.items.filter(x=>x.sec===s.sec).sort((a,b)=>b.cap-a.cap).map(x=>({...x,v:x.cap}));
    const hh=s.h>60&&s.w>90?20:0;const rs=squarify(kids,0,hh,s.w-4,s.h-4-hh);
    html+=`<div class="sec" style="left:${s.x}px;top:${s.y}px;width:${s.w}px;height:${s.h}px">${hh?`<div class="sh"><span>${s.sec}</span><b class="${cls(s.m1)}">${pct(s.m1)}</b></div>`:''}${rs.map(r=>tileHTML(r,'m1',strong,false)).join('')}</div>`});
  return `<div class="tm" id="${id}" style="width:${TMW}px;height:${h}px">${html}</div>`}
function secRank(tm,strong){const s=[...tm.sectors].sort((a,b)=>b.m1-a.m1);const mx=Math.max(...s.map(x=>Math.abs(x.m1)),1);
  return `<div class="rank-l"><div class="ttl">산업군 한 달 성적 — 시가총액 가중 평균 (큰 회사일수록 영향 큼)</div><div class="rkg">${s.map(x=>`<div class="rk"><span>${x.sec}</span><span class="v ${cls(x.m1)}">${pct(x.m1)}</span><div class="b"><i style="${x.m1>=0?'left:50%':'right:50%'};width:${Math.abs(x.m1)/mx*50}%;background:${x.m1>=0?'var(--up)':'var(--down)'}"></i></div></div>`).join('')}</div></div>`}
function secBlock(key,strong,h,note){const tm=DATA[key].tm;const s=[...tm.sectors].sort((a,b)=>b.m1-a.m1);
  return `<h2>산업군 트렌드 맵<small>큰 박스 = 산업 · 작은 박스 = 종목 · 색 = 최근 한 달 등락</small></h2>
  ${tmSec(tm,h,'s-'+key,strong)}${secRank(tm,strong)}
  <div class="legend"><span>${key==='cr'?'박스 크기 = 시총 제곱근 · ':''}한 달 기준 진한 색 = ±${strong}% 이상</span><span><i style="background:#047857"></i>+${strong}%↑</span><span><i style="background:#15803d"></i>상승</span><span><i style="background:#c2410c"></i>하락</span><span><i style="background:#9a3412"></i>-${strong}%↓</span></div>
  <div class="insight"><b>한 달 흐름 읽기</b> · 가장 강한 곳 <b>${s[0].sec} ${pct(s[0].m1)}</b>, 가장 약한 곳 <b>${s[s.length-1].sec} ${pct(s[s.length-1].m1)}</b>. ${note}</div>`}
/* 트리맵 폭이 236px 사이드바만큼 줄어드는 섹터 맵 */
function tmSecW(){return TMW}
const _tmSec=tmSec;tmSec=function(tm,h,id,strong){const save=TMW;return _tmSecW(tm,h,id,strong)};
function _tmSecW(tm,h,id,strong){const W=tmSecW();const sq=id==='s-cr';const f=sq?Math.sqrt:(v=>v);const secs=[...tm.sectors].sort((a,b)=>b.cap-a.cap).map(s=>({...s,v:sq?tm.items.filter(x=>x.sec===s.sec).reduce((a,x)=>a+f(x.cap),0):s.cap}));
  const srs=squarify(secs,0,0,W,h);let html='';
  srs.forEach(s=>{const kids=tm.items.filter(x=>x.sec===s.sec).sort((a,b)=>b.cap-a.cap).map(x=>({...x,v:f(x.cap)}));
    const hh=(s.h>54&&s.w>56)?20:0;const rs=squarify(kids,0,hh,s.w-4,s.h-4-hh);const showP=s.sec.length*11+60<s.w;
    html+=`<div class="sec" style="left:${s.x}px;top:${s.y}px;width:${s.w}px;height:${s.h}px">${hh?`<div class="sh"><span style="overflow:hidden;text-overflow:ellipsis">${s.sec}</span>${showP?`<b class="${cls(s.m1)}">${pct(s.m1)}</b>`:''}</div>`:''}${rs.map(r=>tileHTML(r,'m1',strong,false)).join('')}</div>`});
  return `<div class="tm" id="${id}" style="width:${W}px;height:${h}px">${html}</div>`}

/* ---------- 카드 1 (보강) ---------- */
function curveSVG(c){const W=300,H=130,P=26;const all=[...c.now,...c.prev].map(x=>x[1]);const lo=Math.floor(Math.min(...all)*10)/10-0.1,hi=Math.ceil(Math.max(...all)*10)/10+0.1;
  const X=i=>P+i*(W-P*2)/3,Y=v=>H-22-(v-lo)/(hi-lo)*(H-40);
  const path=a=>a.map((p,i)=>`${i?'L':'M'}${X(i)},${Y(p[1])}`).join(' ');
  return `<svg viewBox="0 0 ${W} ${H}" width="100%" height="${H}"><path d="${path(c.prev)}" fill="none" stroke="#64748b" stroke-width="2" stroke-dasharray="4 4"/>
   <path d="${path(c.now)}" fill="none" stroke="var(--amber)" stroke-width="3"/>
   ${c.now.map((p,i)=>`<circle cx="${X(i)}" cy="${Y(p[1])}" r="4" fill="var(--amber2)"/><text x="${X(i)}" y="${Y(p[1])-9}" fill="#ebe7df" font-size="11" font-family="IBM Plex Mono" font-weight="700" text-anchor="middle">${p[1].toFixed(2)}</text><text x="${X(i)}" y="${H-5}" fill="#8d96a5" font-size="10.5" text-anchor="middle">${p[0]}</text>`).join('')}</svg>`}
function card1(){const m=DATA.mac;const W=m.world;
 const ixRow=([n,q])=>`<div class="ix"><span class="nm">${n}</span><span class="d ${cls(q.d1)}">${pct(q.d1)}</span><span class="m ${q.m1>=0?'m-up':'m-dn'}">${pct(q.m1)}</span></div>`;
 return `<section class="card" id="card1"><div class="pad">
 ${head(1,'Global Macro','오늘 세계 시장을 움직인 <em>세 개의 레버</em>')}
 <div class="top3">${gaugeBox(m.score,'글로벌 매크로 점수',m.hist)}${parts(m.parts)}${diag(m.diag,'오늘의 인과관계 3줄 요약')}</div>
 ${scaleBar(m.score,m.hist,'매크로')}
 <div class="kpis">${m.kpis.map(([k,v,s,key])=>`<div class="kpi"><div class="k">${k}</div><div class="v">${v}</div><div class="s">${s}</div>${ruler(key)}</div>`).join('')}</div>
 <h2>세계 증시 지도<small>전일 · <span style="color:var(--amber2)">한 달</span></small></h2>
 <div class="world">${W.map(([r,L])=>`<div class="reg"><div class="t">${r}<small>전일 · 1개월</small></div>${L.map(ixRow).join('')}</div>`).join('')}</div>
 <div class="callout"><b>한 줄 해석</b> · ${m.worldmsg}</div>
 <h2>금리 · 중앙은행<small>돈의 가격이 모든 자산의 기준</small></h2>
 <div class="two"><div class="panel"><div class="ttl">미국 국채 금리 곡선 <span style="color:var(--amber2)">━ 오늘</span> <span style="color:#64748b">┅ 한 달 전</span></div>${curveSVG(m.curve)}
   <p class="s">한 달 새 전 구간이 0.1~0.15%p 올랐어요. 3개월(4.07%)보다 10년(5.10%)이 높은 정상 곡선이라 '침체 신호'보다는 '물가·재정 부담' 신호에 가깝습니다.</p></div>
  <div class="panel"><div class="ttl">중앙은행 체크</div><table class="cbT"><thead><tr><th>은행</th><th>기준금리</th><th>최근 결정</th><th>다음 회의</th></tr></thead><tbody>
   ${m.cb.map(([b,r,l,n,x])=>`<tr><td>${b}</td><td class="r">${r}</td><td>${l}</td><td>${n}<br><span style="color:var(--mute);font-size:11px">${x}</span></td></tr>`).join('')}</tbody></table>
   <p class="s">미국 금리(3.75~4.00%)가 한국(3.00%)보다 높으면 돈이 미국으로 쏠리기 쉬워요. 그런데 지금은 원화가 오히려 강세(1,329원) — 외국인이 한국 주식을 판 돈이 환전되지 않고 머무는 등 단순 공식이 깨진 상태입니다.</p></div></div>
 <h2>원자재 · 환율<small>전일 · 한 달</small></h2>
 <div class="mini">${m.cmd.map(([n,q,u,dg])=>`<div><div class="k">${n}</div><div class="v">${u}${q.p.toLocaleString('en-US',{minimumFractionDigits:dg,maximumFractionDigits:dg})}</div><div class="s ${cls(q.d1)}">${pct(q.d1)} <span class="${cls(q.m1)}" style="opacity:.8">1M ${pct(q.m1)}</span></div></div>`).join('')}</div>
 <div class="mini five" style="margin-top:8px">${m.fx.map(([n,q,u,dg,hn])=>`<div><div class="k">${n}</div><div class="v">${q.p.toLocaleString('en-US',{minimumFractionDigits:dg,maximumFractionDigits:dg})}</div><div class="s ${cls(q.m1)}">1M ${pct(q.m1)}</div><div class="h">${hn}</div></div>`).join('')}</div>
 <p class="note">구리(경기 체온계)는 한 달 −0.8%로 보합 → 실물 경기는 아직 꺾이지 않았다는 뜻. 은 −12.9%·금 −5.0%는 '고금리에 이자 안 주는 자산이 불리'하다는 신호입니다.</p>
 <h2>3대 거시 변수<small>원인 → 연쇄 효과</small></h2>
 <div class="vars">${m.vars.map(v=>`<div class="vbox"><div class="t">${v.t}</div><span class="tag">${v.tag}</span><p>${v.b}</p><div class="k">→ ${v.k}</div></div>`).join('')}</div>
 <h2>3대 산업 메가트렌드<small>AI · 전력 · 전기차</small></h2>
 <div class="vars">${m.trends.map(v=>`<div class="vbox trend"><div class="t">${v.t}</div><div class="st">${v.st}</div><p>${v.b}</p><div class="k">${v.sig}</div></div>`).join('')}</div>
 <h2>수혜 섹터 vs 회피 섹터<small>미국 강세 ↔ 한국 선별</small></h2>
 <table class="secT"><thead><tr><th>시장</th><th class="up">돈이 들어가는 곳 (수혜)</th><th class="dn">돈이 빠지는 곳 (회피)</th></tr></thead><tbody>
 <tr><td>미국 · 방어 순환</td><td>${m.sectors.us.good}</td><td>${m.sectors.us.bad}</td></tr>
 <tr><td>한국 · 선별</td><td>${m.sectors.kr.good}</td><td>${m.sectors.kr.bad}</td></tr></tbody></table>
 <h2>다가오는 이벤트 캘린더<small>시장이 방향을 정할 날</small></h2>
 <div class="cal">${m.cal.map(([d,t,e,w])=>`<div><div class="d">${d}</div><span class="tg ${t==='금리'?'rate':''}">${t}</span><div class="e">${e}</div><div class="w">${w}</div></div>`).join('')}</div>
 ${foot(1)}</div></section>`}
/* ---------- 카드 2 ---------- */
function card2(){const u=DATA.us;return `<section class="card" id="card2"><div class="pad">
 ${head(2,'US Market Intelligence','미국 증시 · <em>기술주에서 방어주로</em>','10/16(금) 본장 마감 · 주말 휴장')}
 ${top3(u.score,'미국 시장 컨디션',u.parts,u.diag,u.hist)}
 ${scaleBar(u.score,u.hist,'미국')}
 <div class="kpis six">${kpiR(u.kpis)}</div>
 <h2>시가총액 Top 20 자금 흐름<small>트리맵 · 미국 상장 기준</small></h2>
 ${tmTop(u.tm,430,'t-us')}
 ${secBlock('us',5,400,'반도체·소프트웨어(빚으로 AI 투자한 곳)는 빠지고, 필수소비·에너지·헬스케어로 돈이 옮겨갔습니다. 다만 빅테크 플랫폼(애플·MS)은 여전히 플러스 — 현금 많은 회사는 버팁니다.')}
 <h2>Top 10 액션 플랜<small>전부 지정가 · 손익비 1:2.5 이상만</small></h2>
 ${table(u.top,'US')}
 <p class="note">진입가 = 현재가에서 하루 평균 흔들림 폭의 0.6~1배 아래 눌림 자리. 손절가 = 최근 20일 바닥 또는 진입가 −1~1.6배 흔들림 폭. 체결 안 되면 그날은 '안 사는 게 수익'입니다.</p>
 ${foot(2)}</div></section>`}
/* ---------- 카드 3 ---------- */
function card3(){const k=DATA.kr,g1=grade(k.score),g2=grade(k.score2);return `<section class="card" id="card3"><div class="pad">
 ${head(3,'KR Market Intelligence','한국 증시 · <em>서킷브레이커 다음 날</em>','10/16(금) 마감 복기 · 주말 휴장')}
 <div class="top3"><div class="gauge dual"><div class="lbl">한국 시장 컨디션</div><div class="duo">
   <div><div class="lbl">코스피</div>${dial(k.score,false)}<div class="grade" style="color:${g1[1]};font-size:11px">${g1[0]}</div></div>
   <div><div class="lbl">코스닥</div>${dial(k.score2,false)}<div class="grade" style="color:${g2[1]};font-size:11px">${g2[0]}</div></div></div>
   <div class="hist">코스피 추세 항목은<br>최근 1년 중 <b style="color:var(--down)">최저</b> 수준</div></div>
 ${parts(k.parts,'코스피 점수 산식')}${diag(k.diag)}</div>
 ${scaleBar(k.score,null,'코스피')}
 <div class="kpis">${kpiR(k.kpis)}</div>
 <h2>시가총액 Top 20 자금 흐름<small>트리맵 · 보통주 기준</small></h2>
 ${tmTop(k.tm,430,'t-kr')}
 ${secBlock('kr',8,420,'한 달 동안 반도체·전력기기·지주사가 −19~−22%로 가장 크게 빠졌고, 2차전지만 플러스. 외국인이 "AI 수혜로 많이 오른 것"부터 팔았다는 뜻입니다.')}
 <h2>Top 10 실전 가격표<small>지정가 · 호가 단위 반영</small></h2>
 ${table(k.top,'KR')}
 <p class="note">수급 근거: 한국거래소 10/12~16 주간 순매수 상위(주간동아 정리). 공포 심리로 기업 가치 대비 지나치게 싸게 팔리는 '과매도' 종목은 한 번에 사지 말고 1/3씩 나눠 그물을 칩니다.</p>
 ${foot(3)}</div></section>`}
/* ---------- 카드 4 ---------- */
function card4(){const c=DATA.cr;return `<section class="card" id="card4"><div class="pad">
 ${head(4,'Crypto Market Intelligence','크립토 · <em>박스권 안의 롱 쏠림</em>','24시간 실시간 · 주말 집중 모드')}
 ${top3(c.score,'크립토 컨디션',c.parts,c.diag,c.hist)}
 ${scaleBar(c.score,c.hist,'크립토')}
 <div class="kpis" id="crk">${c.kpis.map(([n,v,s])=>typeof v==='number'?`<div class="kpi"><div class="k">${n}</div><div class="v" data-k="${s}">${fmt(v,'CR')}</div><div class="s ${cls(c.heat.find(h=>h.code===s).chg)}" data-kc="${s}">24시간 ${pct(c.heat.find(h=>h.code===s).chg)}</div></div>`:`<div class="kpi"><div class="k">${n}</div><div class="v">${v}</div><div class="s">${s}</div></div>`).join('')}</div>
 <div class="chainG">${c.gauges.map(([n,v,key,s])=>`<div class="kpi"><div class="k">${n}</div><div class="v">${v}</div><div class="s">${s}</div>${ruler(key)}</div>`).join('')}</div>
 <div class="chain">${c.onchain.slice(0,2).map(([k,v,s])=>`<div><div class="k">${k}</div><div class="v">${v}</div><div class="s">${s}</div></div>`).join('')}
   <div style="grid-column:span 2"><div class="k">온체인 해석</div><div class="s" style="font-size:12px;margin-top:4px">거래소에 쌓인 코인이 줄고 고래가 안 팔았다 = 팔려는 물량은 적다. 그런데 ETF 돈이 안 들어와 위로 밀어줄 힘도 없다 → 박스권.</div></div></div>
 <h2>시가총액 Top 20 자금 흐름<small>트리맵 · 스테이블코인 제외 · 실시간</small></h2>
 ${tmTop(c.tm,400,'t-cr')}
 ${secBlock('cr',8,380,'AI 코인(비트텐서 등)과 디파이가 한 달 강세, 프라이버시 코인은 약세. 비트코인이 시총의 대부분이라 결국 BTC 방향이 전체를 결정합니다.')}
 <h2>Top 10 매매 타점<small>지정가 · 손익비 1:2.5 이상</small></h2>
 ${table(c.top,'CR')}
 <p class="note">펀딩비 = 선물에서 '오른다'에 건 쪽이 '내린다'에 건 쪽에 내는 이자. 플러스가 크면 과열, 마이너스면 하락 베팅 쏠림입니다. 롱 계좌 비율이 1주 새 크게 올라 한 번 흔들어 털고 가는 급락(휩쏘)이 나올 수 있어 손절선은 반드시 지정해 둡니다.</p>
 ${foot(4)}</div></section>`}
/* ---------- 실시간: 트리맵 재그리기 포함 ---------- */
async function refreshLive(){
  if(!document.getElementById('card4')&&!document.getElementById('card5')) return;
  const ids=[...new Set(Object.values(DATA.meta.idmap))].join(',');
  try{const r=await fetch(`https://api.coingecko.com/api/v3/simple/price?ids=${ids}&vs_currencies=usd&include_24hr_change=true`);
    if(!r.ok) throw new Error('HTTP '+r.status);const j=await r.json();const P={};
    for(const [sym,id] of Object.entries(DATA.meta.idmap)) if(j[id]) P[sym]={p:j[id].usd,c:+(j[id].usd_24h_change||0).toFixed(2)};
    DATA.cr.heat.forEach(h=>{if(P[h.code]){h.price=P[h.code].p;h.chg=P[h.code].c}});
    DATA.cr.tm.items.forEach(x=>{if(P[x.code]){x.p=P[x.code].p;x.d1=P[x.code].c}});
    const t=document.getElementById('t-cr');if(t)t.outerHTML=tmTop(DATA.cr.tm,400,'t-cr').split('<div class="legend">')[0];
    document.querySelectorAll('#card4 .tbl tr[data-code]').forEach(tr=>{const q=P[tr.dataset.code];if(!q)return;(tr.querySelector('.px')||{}).textContent=fmt(q.p,'CR');const pc=tr.querySelector('.pc');pc.textContent=pct(q.c);pc.className='pc '+cls(q.c)});
    document.querySelectorAll('#card4 .pick[data-code]').forEach(el=>{const q=P[el.dataset.code];if(!q)return;el.querySelector('.ppx').textContent=fmt(q.p,'CR');const pc=el.querySelector('.ppc');pc.textContent=pct(q.c);pc.className='ppc '+cls(q.c)});
    document.querySelectorAll('#crk [data-k]').forEach(el=>{const q=P[el.dataset.k];if(q)el.textContent=fmt(q.p,'CR')});
    document.querySelectorAll('#crk [data-kc]').forEach(el=>{const q=P[el.dataset.kc];if(q){el.textContent='24시간 '+pct(q.c);el.className='s '+cls(q.c)}});
    document.querySelectorAll('#ledger tr[data-code]').forEach(tr=>{const x=DATA.ar.ledger.find(l=>l.code===tr.dataset.code);const q=P[x.code];if(!q||x.mk!=='CR')return;
      const g=(q.p/x.entry-1)*100,st=tr.querySelector('.st'),gp=tr.querySelector('.gap');if(q.p<=x.entry){st.textContent='가격 도달';st.className='st hit'}gp.textContent=`현재가 ${fmt(q.p,'CR')} · 진입까지 ${g>0?'-':''}${Math.abs(g).toFixed(1)}%`});
    const now=new Date();document.getElementById('ldot').classList.add('on');
    document.getElementById('lmsg').textContent=`크립토 실시간 · ${now.toLocaleTimeString('ko-KR')} 갱신(60초 자동) · 주식·매크로는 발행 시점 고정`;
  }catch(e){document.getElementById('ldot').classList.remove('on');document.getElementById('lmsg').textContent='실시간 연결 실패('+e.message+') · 발행 시점 데이터 표시 중'}}
