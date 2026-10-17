/* ================= v3: 자동 갱신판 · 추천 Top 5 ================= */
const FN={trend:'추세',mom:'모멘텀',val:'가치·실적',flow:'수급',vol:'안정성'};
const FNM={US:{flow:'전문가 평가'},CR:{val:'거래 활력',flow:'파생 쏠림'},KR:{}};
const FDESC={
 US:{trend:'200일선 위·정배열',mom:'6개월 상승률·시장 대비',val:'예상 PER 역수+이익 증가',flow:'월가 애널리스트 평균',vol:'20일 변동성 낮을수록'},
 KR:{trend:'200일선 위·정배열',mom:'6개월 상승률·코스피 대비',val:'추정 PER 역수+이익 증가',flow:'외국인+기관 20일 순매수',vol:'20일 변동성 낮을수록'},
 CR:{trend:'200일선 위·정배열',mom:'6개월 상승률·BTC 대비',val:'거래대금 ÷ 시총',flow:'펀딩비 낮을수록(숏 쏠림)',vol:'20일 변동성 낮을수록'}};
const FW={trend:20,mom:25,val:20,flow:20,vol:15};
const fname=(mk,k)=>(FNM[mk]||{})[k]||FN[k];
function methodBox(mk,n){return `<div class="method">${Object.keys(FW).map(k=>`<div><b>${fname(mk,k)}<i>${FW[k]}%</i></b><span>${FDESC[mk][k]}</span></div>`).join('')}</div>
 <p class="note" style="margin:0 0 4px">시가총액 상위 <b>${n}개</b> 중에서 다섯 가지 기준마다 등수를 매겨 0~100점(백분위)으로 바꾸고, 위 비율로 합산했어요. 한 달 −30% 넘게 빠진 종목은 '떨어지는 칼날'이라 제외, 같은 산업은 최대 2개까지만.</p>`}
function fbars(p){return `<div class="fb">${Object.keys(FW).map(k=>{const v=p.f[k];return `<div><span>${fname(p.mk,k)}</span><div class="bar"><i class="${v>=80?'top':v>=60?'hi':''}" style="width:${Math.max(4,v)}%"></i></div><em>${v}</em></div>`}).join('')}</div>`}
function pickCard(p){const up=v=>((v/p.entry-1)*100);
 return `<div class="pick ${p.rank===1?'r1':''}" data-code="${p.code}">
  <div class="lt"><div class="rk"><span class="no">TOP ${p.rank}</span><span class="sec">${p.sec}</span></div>
   <div class="nm">${p.name}</div><div class="cd">${p.code}</div>
   <div class="px"><span class="ppx">${fmt(p.price,p.mk)}</span><small class="${cls(p.chg)} ppc">${pct(p.chg)}</small></div>
   <div class="sc"><b>${p.score}</b><span>추천 점수<br>/ 100</span></div><span class="hd">${p.head}</span>${fbars(p)}</div>
  <div class="rt"><div class="wt">왜 추천하나 — 점수가 높은 이유 3가지</div>
   <div class="why3">${p.why.map(w=>`<div><span class="k">${w.k}<i>${w.p}점</i></span><span>${w.t}</span></div>`).join('')}</div>
   <div class="pact"><span class="lb">ACTION</span>${p.act}</div>
   <div class="pnum"><div><div class="k">진입 (지정가)</div><div class="v e">${fmt(p.entry,p.mk)}</div></div>
    <div><div class="k">1차 / 2차 목표</div><div class="v t">${fmt(p.tp1,p.mk)}</div><div class="k" style="margin-top:1px">2차 ${fmt(p.tp2,p.mk)} (+${up(p.tp2).toFixed(0)}%)</div></div>
    <div><div class="k">손절가</div><div class="v s">${fmt(p.sl,p.mk)}</div></div><div><div class="k">손익비</div><div class="v r">1 : ${p.rr.toFixed(1)}</div></div></div>
   <div class="prisk">${p.risks.map(r=>`<div>${r}</div>`).join('')}</div></div></div>`}
function picks(list,mk,n){return methodBox(mk,n)+list.map(pickCard).join('')}
const autoTag=()=>DATA.meta.auto?'<span class="autotag">AUTO · 데이터 자동 해설</span>':'';
/* ---------- 카드 1 ---------- */
card1=function(){const m=DATA.mac;const W=m.world;
 const ixRow=([n,q])=>`<div class="ix"><span class="nm">${n}</span><span class="d ${cls(q.d1)}">${pct(q.d1)}</span><span class="m ${q.m1>=0?'m-up':'m-dn'}">${pct(q.m1)}</span></div>`;
 return `<section class="card" id="card1"><div class="pad">
 ${head(1,'Global Macro',m.title)}
 <div class="top3">${gaugeBox(m.score,'글로벌 매크로 점수',m.hist)}${parts(m.parts)}${diag(m.diag,'오늘의 인과관계 3줄 요약')}</div>
 ${scaleBar(m.score,m.hist,'매크로')}
 <div class="kpis">${m.kpis.map(([k,v,s,key])=>`<div class="kpi"><div class="k">${k}</div><div class="v">${v}</div><div class="s">${s}</div>${ruler(key)}</div>`).join('')}</div>
 <h2>세계 증시 지도<small>전일 · <span style="color:var(--amber2)">한 달</span></small></h2>
 <div class="world">${W.map(([r,L])=>`<div class="reg"><div class="t">${r}<small>전일 · 1개월</small></div>${L.map(ixRow).join('')}</div>`).join('')}</div>
 <div class="callout"><b>한 줄 해석</b> · ${m.worldmsg}</div>
 <h2>금리 · 중앙은행<small>돈의 가격이 모든 자산의 기준</small></h2>
 ${rateBlock(m)}
 <h2>원자재 · 환율<small>전일 · 한 달</small></h2>
 <div class="mini">${m.cmd.map(([n,q,u,dg])=>`<div><div class="k">${n}</div><div class="v">${u}${q.p.toLocaleString('en-US',{minimumFractionDigits:dg,maximumFractionDigits:dg})}</div><div class="s ${cls(q.d1)}">${pct(q.d1)} <span class="${cls(q.m1)}" style="opacity:.8">1M ${pct(q.m1)}</span></div></div>`).join('')}</div>
 <div class="mini five" style="margin-top:8px">${m.fx.map(([n,q,u,dg,hn])=>`<div><div class="k">${n}</div><div class="v">${q.p.toLocaleString('en-US',{minimumFractionDigits:dg,maximumFractionDigits:dg})}</div><div class="s ${cls(q.m1)}">1M ${pct(q.m1)}</div><div class="h">${hn}</div></div>`).join('')}</div>
 <p class="note">${m.cmdmsg}</p>
 ${m.vars?`<h2>3대 거시 변수<small>원인 → 연쇄 효과</small></h2><div class="vars">${m.vars.map(v=>`<div class="vbox"><div class="t">${v.t}</div><span class="tag">${v.tag}</span><p>${v.b}</p><div class="k">→ ${v.k}</div></div>`).join('')}</div>`:''}
 ${m.trends?`<h2>3대 산업 메가트렌드<small>AI · 전력 · 전기차</small></h2><div class="vars">${m.trends.map(v=>`<div class="vbox trend"><div class="t">${v.t}</div><div class="st">${v.st}</div><p>${v.b}</p><div class="k">${v.sig}</div></div>`).join('')}</div>`:''}
 <h2>수혜 산업 vs 회피 산업<small>최근 한 달 시총 가중 등락</small></h2>
 <table class="secT"><thead><tr><th>시장</th><th class="up">돈이 들어가는 곳</th><th class="dn">돈이 빠지는 곳</th></tr></thead><tbody>
 <tr><td>미국</td><td>${m.sectors.us.good}</td><td>${m.sectors.us.bad}</td></tr><tr><td>한국</td><td>${m.sectors.kr.good}</td><td>${m.sectors.kr.bad}</td></tr></tbody></table>
 <h2>다가오는 이벤트 캘린더<small>시장이 방향을 정할 날</small></h2>
 <div class="cal">${m.cal.map(([d,t,e,w])=>`<div><div class="d">${d}</div><span class="tg ${t==='금리'?'rate':''}">${t}</span><div class="e">${e}</div><div class="w">${w}</div></div>`).join('')}</div>
 ${foot(1)}</div></section>`};
/* ---------- 카드 2 ---------- */
card2=function(){const u=DATA.us;const s=[...u.tm.sectors];
 return `<section class="card" id="card2"><div class="pad">
 ${head(2,'US Market Intelligence',u.title,u.sub)}
 ${top3(u.score,'미국 시장 컨디션',u.parts,u.diag,u.hist)}
 ${scaleBar(u.score,u.hist,'미국')}
 <div class="kpis six">${kpiR(u.kpis)}</div>
 <h2>시가총액 Top 20 자금 흐름<small>트리맵 · 미국 상장 기준</small></h2>
 ${tmTop(u.tm,330,'t-us')}
 ${secBlock('us',5,400,`가장 강한 산업과 약한 산업의 한 달 격차는 ${(s[0].m1-s[s.length-1].m1).toFixed(1)}%p. 격차가 클수록 '어디에 있느냐'가 수익을 가릅니다.`)}
 <h2>퀀트 추천 Top 5${autoTag()}<small>5팩터 점수순 · 전부 지정가 · 손익비 1:2.5↑</small></h2>
 ${picks(u.top,'US',u.n)}
 <p class="note">진입가 = 현재가에서 하루 평균 흔들림 폭(ATR)의 0.6~1배 아래 눌림 자리. 손절가 = 최근 20일 바닥 또는 진입가 −1~1.6배 흔들림 폭. 체결 안 되면 그날은 '안 사는 게 수익'입니다.</p>
 ${foot(2)}</div></section>`};
/* ---------- 카드 3 ---------- */
card3=function(){const k=DATA.kr,g1=grade(k.score),g2=grade(k.score2);const s=[...k.tm.sectors];
 return `<section class="card" id="card3"><div class="pad">
 ${head(3,'KR Market Intelligence',k.title,k.sub)}
 ${sband(k.score,'코스피',k.hist,'코스피')}
 ${sband(k.score2,'코스닥',null,'코스닥')}
 <div class="two even">${parts(k.parts,'코스피 점수 산식')}${diag(k.diag)}</div>
 <div class="kpis">${kpiR(k.kpis)}</div>
 <h2>시가총액 Top 20 자금 흐름<small>트리맵 · 보통주 기준</small></h2>
 ${tmTop(k.tm,330,'t-kr')}
 ${secBlock('kr',8,420,`외국인(시총 상위 종목 합산)은 최근 5거래일 ${won(k.flow.f5)}원, 기관은 ${won(k.flow.i5)}원. 큰손이 산 산업과 판 산업을 트리맵 색으로 확인하세요.`)}
 <h2>퀀트 추천 Top 5${autoTag()}<small>5팩터 점수순 · 지정가 · 호가 단위 반영</small></h2>
 ${picks(k.top,'KR',k.n)}
 <p class="note">수급 = 네이버증권 종목별 외국인·기관 순매수 수량 × 종가로 환산한 20거래일 합계. 시총 대비 비율로 비교해 큰 회사가 무조건 유리하지 않게 했어요.</p>
 ${foot(3)}</div></section>`};
function won(v){const a=Math.abs(v);return (v>=0?'+':'−')+(a>=1e12?(a/1e12).toFixed(1)+'조':Math.round(a/1e8).toLocaleString()+'억')}
/* ---------- 카드 4 ---------- */
card4=function(){const c=DATA.cr;
 return `<section class="card" id="card4"><div class="pad">
 ${head(4,'Crypto Market Intelligence',c.title,'24시간 실시간 · '+DATA.meta.mode)}
 ${top3(c.score,'크립토 컨디션',c.parts,c.diag,c.hist)}
 ${scaleBar(c.score,c.hist,'크립토')}
 <div class="kpis" id="crk">${c.kpis.map(([n,v,s])=>typeof v==='number'?`<div class="kpi"><div class="k">${n}</div><div class="v" data-k="${s}">${fmt(v,'CR')}</div><div class="s ${cls(c.heat.find(h=>h.code===s).chg)}" data-kc="${s}">24시간 ${pct(c.heat.find(h=>h.code===s).chg)}</div></div>`:`<div class="kpi"><div class="k">${n}</div><div class="v">${v}</div><div class="s">${s}</div></div>`).join('')}</div>
 <div class="chainG">${c.gauges.map(([n,v,key,s])=>`<div class="kpi"><div class="k">${n}</div><div class="v">${v}</div><div class="s">${s}</div>${ruler(key)}</div>`).join('')}</div>
 <div class="chain">${c.onchain.slice(0,2).map(([k,v,s])=>`<div><div class="k">${k}</div><div class="v">${v}</div><div class="s">${s}</div></div>`).join('')}
   <div style="grid-column:span 2"><div class="k">파생·온체인 해석</div><div class="s" style="font-size:12px;margin-top:4px">${c.chainmsg}</div></div></div>
 <h2>시가총액 Top 20 자금 흐름<small>트리맵 · 스테이블코인 제외 · 실시간</small></h2>
 ${tmTop(c.tm,300,'t-cr')}
 ${secBlock('cr',8,380,'비트코인이 시총의 대부분이라 결국 BTC 방향이 전체를 결정합니다. 산업군 색은 BTC와 다르게 움직이는 테마를 찾는 용도로 보세요.')}
 <h2>퀀트 추천 Top 5${autoTag()}<small>5팩터 점수순 · 지정가 · 손익비 1:2.5↑</small></h2>
 ${picks(c.top,'CR',c.n)}
 <p class="note">펀딩비 = 선물에서 '오른다'에 건 쪽이 '내린다'에 건 쪽에 내는 이자(Hyperliquid 8시간 환산). 플러스가 크면 과열, 마이너스면 하락 베팅 쏠림입니다. 크립토는 24시간 거래라 지정가 체결이 주말에도 일어납니다.</p>
 ${foot(4)}</div></section>`};
/* ---------- 카드 5 ---------- */
card5=function(){const a=DATA.ar;const ret=(a.eq/a.start-1)*100;const live=a.ledger.filter(x=>x.st==='pending'||x.st==='open');
 return `<section class="card" id="card5"><div class="pad">
 ${head(5,"Heeyun's Argon · Virtual Portfolio",`1,000만 원 실전 가상계좌 <em>Day ${DATA.meta.day}</em>`,`${a.start_date} 개시 · 매일 자동 체결 판정`)}
 <div class="kpis" id="arK">
  <div class="kpi"><div class="k">초기 원금</div><div class="v">${a.start.toLocaleString()}</div><div class="s">${a.start_date} 개시</div></div>
  <div class="kpi"><div class="k">현재 총 평가자산</div><div class="v" id="arTot">${a.eq.toLocaleString()}</div><div class="s ${cls(ret)}" id="arTotS">수익률 ${pct(ret)} · 체결 ${a.n_fill}건</div></div>
  <div class="kpi"><div class="k">예약·보유 금액(비중)</div><div class="v">${a.reserved.toLocaleString()}</div><div class="s">${(a.reserved/a.eq*100).toFixed(1)}% · 지정가 그물+보유</div></div>
  <div class="kpi"><div class="k">자유 현금(비중)</div><div class="v">${a.cash.toLocaleString()}</div><div class="s">${(a.cash/a.eq*100).toFixed(1)}% · 예비 탄약 30%↑</div></div></div>
 <h2>자산 배분 맵 & 4대 운용 철칙</h2>
 <div class="mid2"><div class="alloc"><div class="ttl" style="font-size:12px;color:var(--mute);font-weight:700">현재 비중 (원화 환산 · 환율 ${FX.toFixed(1)}원)</div>
  <div class="stack">${a.alloc.map((x,i)=>`<i style="width:${x.w}%;background:${PAL[i%PAL.length]}"></i>`).join('')}</div>
  ${a.alloc.map((x,i)=>`<div class="arow"><span class="sw" style="background:${PAL[i%PAL.length]}"></span><span>${x.name}</span><span class="w">${x.w.toFixed(1)}%</span></div>`).join('')}</div>
  <div class="rules">${a.rules.map(([h,p],i)=>`<div class="rule"><span class="no num">0${i+1}</span><h4>${h}</h4><p>${p}</p></div>`).join('')}</div></div>
 <h2>포지션 원장<small>체결 시 1차 목표 50% 익절 → 손절선 매수가로 상향 · 10일 미체결 시 자동 취소</small></h2>
 <table class="tbl" id="ledger"><colgroup><col style="width:112px"><col style="width:96px"><col style="width:84px"><col style="width:92px"><col style="width:96px"><col style="width:90px"><col></colgroup>
 <thead><tr><th>자산</th><th>상태</th><th>매수단가</th><th>수량 · 금액</th><th>목표가 1차/2차</th><th>손절가(손익비)</th><th>근거 · 손익</th></tr></thead><tbody>
 ${a.ledger.map(x=>`<tr data-code="${x.code}"><td><div class="nm">${x.name}</div><div class="cd">${x.code} · ${x.w.toFixed(1)}%</div></td>
  <td><span class="st ${x.st==='pending'?'wait':x.st}">${x.status}</span><span class="gap">${x.px!=null&&x.st==='pending'?`진입까지 ${(-x.gap).toFixed(1)}%`:''}</span></td>
  <td class="m ent">${fmt(x.entry,x.mk)}</td>
  <td class="m">${x.mk==='CR'?x.qty:x.qty.toLocaleString()}${x.mk==='CR'?'개':'주'}<small>${x.amt.toLocaleString()}원</small></td>
  <td class="m tp">${fmt(x.tp1,x.mk)}<small>${fmt(x.tp2,x.mk)}</small></td>
  <td class="m sl">${fmt(x.sl,x.mk)}<br><span class="rr">1 : ${x.rr.toFixed(1)}</span></td>
  <td class="why">${x.why}${x.st!=='pending'&&x.st!=='cancelled'?`<br><b class="pnl ${cls(x.pnl)}">손익 ${x.pnl>=0?'+':''}${x.pnl.toLocaleString()}원</b>`:''}</td></tr>`).join('')}
  <tr><td><div class="nm">현금</div><div class="cd">KRW</div></td><td><span class="st hit">보유</span></td><td class="m">-</td><td class="m">${a.cash.toLocaleString()}원</td><td class="m">-</td><td class="m">-</td><td class="why">급락 시 2차 그물용 예비 탄약 (철칙 02)</td></tr>
 </tbody></table>
 <div class="logb">${a.log.map(l=>`<div><b>${l.d.slice(5)}</b>${l.t}</div>`).join('')}</div>
 <p class="disc">가상계좌 · 실제 투자 권유 아님. 해외자산은 환율 ${FX.toFixed(1)}원으로 원화 환산. 체결 판정: 다음 거래일 장중 저가가 지정가 이하이면 체결, 같은 날 손절가까지 내려가면 보수적으로 손절 처리. 출처: ${DATA.sources.join(' · ')}</p>
 ${foot(5)}</div></section>`};
