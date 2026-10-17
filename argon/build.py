# -*- coding: utf-8 -*-
"""Argon 빌더 — cache/raw.json + config.json + state/ledger.json → site/index.html, site/card1~5.html
매일 자동 실행용: 사람이 쓴 해설(config.notes)이 오늘 날짜에 없으면 데이터로 해설을 자동 생성한다.
"""
import json, os, math, statistics, datetime as dt
from quant import ind, plan, rnd, score_universe, pick_top, build_pick, explain, rating_num, fmt, won, depth_for

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.dirname(os.path.abspath(__file__))
R = json.load(open(os.path.join(ROOT, "cache", "raw.json"), encoding="utf-8"))
CFG = json.load(open(os.path.join(HERE, "config.json"), encoding="utf-8"))
LP = os.path.join(ROOT, "state", "ledger.json")
ST = json.load(open(LP, encoding="utf-8"))
clamp = lambda v, a, b: max(a, min(b, v))
WD = "월화수목금토일"
def _utc(t): return dt.datetime.fromtimestamp(t, dt.timezone.utc).replace(tzinfo=None)

NOW = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None) + dt.timedelta(hours=9)
if os.environ.get("ARGON_NOW"): NOW = dt.datetime.fromisoformat(os.environ["ARGON_NOW"])
TODAY = NOW.date(); TODAY_S = TODAY.isoformat()
NOTE = CFG.get("notes", {}).get(TODAY_S, {})
G = R["glob"]


def rows(sym): return (G.get(sym) or {}).get("rows") or []
def I(sym): return ind(rows(sym))
def last(sym): return rows(sym)[-1][4]
def dev(x): return (x["p"] / x["m60"] - 1) * 100
def pct(v): return f"{v:+.2f}%"
def f1(v): return f"{v:+.1f}%"
def mdate(sym, off):
    t = rows(sym)[-1][0]; d = _utc(t + off * 3600).date(); return d
def kd(d): return f"{d.month}/{d.day}({WD[d.weekday()]})"


FX = last("KRW=X")
spx, ndx, ks, kq, btcI = I("^GSPC"), I("^NDX"), I("^KS11"), I("^KQ11"), I("BTC-USD")
vix, tnx, wti, dxy, brent = last("^VIX"), last("^TNX"), last("CL=F"), last("DX-Y.NYB"), last("BZ=F")
cpi = R.get("cpi") or {}
CPI = cpi.get("yoy", CFG["fallback"]["cpi"]); CPI_PREV = cpi.get("prev", CFG["fallback"]["cpi_prev"])
CPI_M = cpi.get("month", 9)
fng_d = (R.get("fng") or {}).get("data", [])
fng = int(fng_d[0]["value"]) if fng_d else 50; fng_prev = int(fng_d[1]["value"]) if len(fng_d) > 1 else fng
lsr_d = (R.get("lsr") or {}).get("data", [])
lsr = float(lsr_d[0][1]) if lsr_d else 1.3; lsr_w = float(lsr_d[6][1]) if len(lsr_d) > 6 else lsr
HL = R.get("hl", {})
fundB = HL.get("BTC", {}).get("f", 0.01); fundE = HL.get("ETH", {}).get("f", 0.01); fundS = HL.get("SOL", {}).get("f", 0.01)
US_D, KR_D = mdate("^GSPC", -4), mdate("^KS11", 9)

# VKOSPI: 수동값이 3일 이내면 사용, 아니면 코스피 실제 변동성으로 대체
vk_date = dt.date.fromisoformat(CFG["fallback"]["vkospi_date"])
if (TODAY - vk_date).days <= 3:
    VK, VK_LBL = CFG["fallback"]["vkospi"], "VKOSPI 변동성"
else:
    VK, VK_LBL = round(ks["vol20"], 2), "코스피 실제 변동성(20일)"

# ---------------- 한국 수급 (상위 종목 외국인+기관 합산) ----------------
KDET = R.get("kdet", {})
capk = {x["code"]: x["cap"] for x in R["kr"]}
def flow_sum(days, who="fi", codes=None):
    s = 0
    for c, v in KDET.items():
        if codes and c not in codes: continue
        for f in (v.get("flows") or [])[:days]:
            s += (f["f"] if "f" in who else 0) + (f["i"] if "i" in who else 0)
    return s
kospi_codes = {x["code"] for x in R["kr"] if x.get("mkt") == "KOSPI"}; kosdaq_codes = {x["code"] for x in R["kr"] if x.get("mkt") == "KOSDAQ"}
fr5 = flow_sum(5, "f", kospi_codes); fr1 = flow_sum(1, "f", kospi_codes); in5 = flow_sum(5, "i", kospi_codes)
kq5 = flow_sum(5, "fi", kosdaq_codes)

# ---------------- 점수 (100점) ----------------
us_parts = [("추세(지수 vs 60일 평균)", 40, round(20 + clamp((dev(spx) + dev(ndx)) / 2 * 5, -20, 20))),
            ("변동성(VIX 공포지수)", 30, round(clamp(30 - (vix - 12) * 1.5, 0, 30))),
            ("금리·유가 부담", 30, round(clamp(30 - (tnx - 4) * 10 - (wti - 80) * 0.3, 0, 30)))]
kospi_parts = [("추세", 40, round(clamp(20 + dev(ks) * 1.5, 0, 40))), (f"변동성({'VKOSPI' if 'VKOSPI' in VK_LBL else '실제 변동성'})", 30, round(clamp(30 - (VK - 15) * 0.6, 0, 30))),
               ("수급(외국인 5일·당일)", 30, round(clamp(15 + fr5 / 1e12 * 1.2 + (3 if fr1 > 0 else -3), 0, 30))), ("과매도 반발 보너스", 0, 8 if ks["rsi"] < 25 else 0)]
kosdaq_parts = [("추세", 40, round(clamp(20 + dev(kq) * 1.5, 0, 40))), ("변동성", 30, round(clamp(30 - (kq["vol20"] - 15) * 0.6, 0, 30))),
                ("수급(외국인+기관 5일)", 30, round(clamp(15 + kq5 / 1e11 * 2, 0, 30)))]
cr_parts = [("추세(BTC vs 60일 평균)", 40, round(clamp(20 + dev(btcI) * 5, 0, 40))),
            ("심리(공포·탐욕 지수 균형)", 30, round(clamp(30 - abs(fng - 50) * 0.4, 0, 30))),
            ("수급(레버리지 쏠림)", 30, round(clamp(15 - (lsr - 1.3) * 10 + (3 if abs(fundB) <= 0.01 else 0), 0, 30)))]
mac_parts = [(f"물가(CPI {CPI}%)", 25, round(clamp(25 - (CPI - 2) * 8, 0, 25))), (f"금리(10년물 {tnx:.2f}%)", 25, round(clamp(25 - (tnx - 4) * 12, 0, 25))),
             (f"유가·지정학(WTI ${wti:.0f})", 25, round(clamp(25 - (wti - 75) * 0.6, 0, 25))), ("달러·유동성", 25, round(clamp(25 - (dxy - 98) * 2, 0, 25)))]
sc = lambda p: sum(x[2] for x in p)
S = dict(us=sc(us_parts), kospi=sc(kospi_parts), kosdaq=sc(kosdaq_parts), cr=sc(cr_parts), mac=sc(mac_parts))
grade = lambda s: "강세" if s >= 70 else "선별 매수" if s >= 55 else "경계" if s >= 40 else "방어 우선"
RULES = dict(
    mac=["CPI 2%(연준 목표)면 25점, 1%p 오를 때마다 −8점", "10년물 4%면 25점, 0.1%p 오를 때마다 −1.2점", "WTI $75면 25점, $1 오를 때마다 −0.6점", "달러지수 98이면 25점, 1 오를 때마다 −2점"],
    us=["S&P·나스닥이 60일 평균선과 같으면 20점, 1% 위마다 +5 / 아래마다 −5", "VIX 12 이하면 30점, 1 오를 때마다 −1.5점", "10년물 4%·WTI $80이면 30점, 금리 0.1%p↑ −1 · 유가 $1↑ −0.3"],
    kospi=[f"60일 평균선과 같으면 20점, 1%마다 ±1.5점 (지금 {dev(ks):+.0f}%)", "15 이하면 30점, 1 오를 때마다 −0.6점", f"5일 외국인 순매수 0이면 15점, 1조마다 ±1.2점 · 당일 순매수면 +3 (5일 {won(fr5)}원 · 당일 {won(fr1)}원)", "과열·침체 지표(RSI) 25 미만 극단적 세일 → +8"],
    kosdaq=["60일 평균선과 같으면 20점, 1%마다 ±1.5점", "실제 변동성 15% 이하면 30점, 1%p마다 −0.6점", f"5일 외국인+기관 0이면 15점, 1천억마다 ±2점 (지금 {won(kq5)}원)"],
    cr=["BTC가 60일 평균선과 같으면 20점, 1%마다 ±5", "공포·탐욕 50(중립)이면 30점, 1 벗어날 때마다 −0.4", "롱/숏 계좌비 1.3배면 15점, 0.1↑마다 −1 · 펀딩비 정상 +3"])

# ---------------- 점수 1년 이력 ----------------
def series(sym): return {_utc(r[0]).strftime("%Y-%m-%d"): r[4] for r in rows(sym)}
def devser(sym):
    rr = rows(sym); C = [r[4] for r in rr]; D = [_utc(r[0]).strftime("%Y-%m-%d") for r in rr]
    return {D[i]: (C[i] / (sum(C[i - 59:i + 1]) / 60) - 1) * 100 for i in range(59, len(C))}
def asof(s, dates):
    out, lastv, keys, j = {}, None, sorted(s), 0
    for d_ in dates:
        while j < len(keys) and keys[j] <= d_: lastv = s[keys[j]]; j += 1
        out[d_] = lastv
    return out
def pctl(h, v): v_ = sorted(h); return round(sum(1 for x in v_ if x < v) / len(v_) * 100)
def hinfo(h, now, label): return dict(avg=round(statistics.mean(h)), lo=round(min(h)), hi=round(max(h)), pct=pctl(h, now), n=len(h), label=label)
ds = sorted(devser("^GSPC"))[-252:]
sp, nd = devser("^GSPC"), asof(devser("^NDX"), ds)
vx, tn, wt, dx = [asof(series(s), ds) for s in ("^VIX", "^TNX", "CL=F", "DX-Y.NYB")]
us_h = [round(20 + clamp((sp[d] + nd[d]) / 2 * 5, -20, 20)) + round(clamp(30 - (vx[d] - 12) * 1.5, 0, 30)) + round(clamp(30 - (tn[d] - 4) * 10 - (wt[d] - 80) * 0.3, 0, 30)) for d in ds]
mac_h = [(round(clamp(25 - (tn[d] - 4) * 12, 0, 25)) + round(clamp(25 - (wt[d] - 75) * 0.6, 0, 25)) + round(clamp(25 - (dx[d] - 98) * 2, 0, 25))) * 100 / 75 for d in ds]
mac_now = (mac_parts[1][2] + mac_parts[2][2] + mac_parts[3][2]) * 100 / 75
bd = devser("BTC-USD")
fngd = {_utc(int(x["timestamp"])).strftime("%Y-%m-%d"): int(x["value"]) for x in fng_d}
lsrd = {_utc(int(t) / 1000).strftime("%Y-%m-%d"): float(v) for t, v in lsr_d}
cds = [x for x in sorted(fngd) if x in bd and (x in lsrd or not lsrd)][-365:]
cr_h = [round(clamp(20 + bd[x] * 5, 0, 40)) + round(clamp(30 - abs(fngd[x] - 50) * 0.4, 0, 30)) + round(clamp(15 - (lsrd.get(x, 1.3) - 1.3) * 10 + 3, 0, 30)) for x in cds]
kdv = devser("^KS11"); ktr = [clamp(20 + kdv[x] * 1.5, 0, 40) for x in sorted(kdv)[-252:]]

# ---------------- 유니버스 구성 ----------------
NM = CFG["names"]; SEC = CFG["sectors"]
def sec_of(m, code): return next((s for s, v in m.items() if code in v.split()), None)
SKIP_US = {"SKHY", "HSBC", "TM", "SAP", "NVO", "AZN", "SHEL", "BABA", "SONY", "RY", "TD", "HDB", "UL", "BHP", "TTE", "SAN"}
ETF_KR={"QQQ":"나스닥100 ETF","SPY":"S&P500 ETF","VOO":"S&P500 ETF(뱅가드)","IVV":"S&P500 ETF(블랙록)","VTI":"미국 전체시장 ETF","SCHD":"미국 배당주 ETF","SOXX":"미국 반도체 ETF","SMH":"반도체 ETF(VanEck)","ARKK":"혁신기술 ETF(ARK)","TQQQ":"나스닥 3배 레버리지","SQQQ":"나스닥 3배 인버스","GLD":"금 ETF","SLV":"은 ETF","USO":"원유 ETF","IWM":"러셀2000 ETF","DIA":"다우 ETF","TLT":"미국 장기국채 ETF","HYG":"미국 하이일드 채권 ETF","EEM":"신흥국 ETF","VNQ":"미국 리츠 ETF","IBIT":"비트코인 현물 ETF(블랙록)","FBTC":"비트코인 현물 ETF(피델리티)","EWY":"한국 ETF(미국 상장)","EWJ":"일본 ETF","FXI":"중국 대형주 ETF","KWEB":"중국 인터넷 ETF","MAGS":"빅테크7 ETF","SOXL":"반도체 3배 레버리지","JEPI":"커버드콜 ETF","VIG":"배당성장 ETF","VYM":"고배당 ETF","RSP":"S&P500 동일가중 ETF","IJH":"미국 중형주 ETF","IWF":"러셀1000 성장 ETF","XLK":"기술 섹터 ETF","XLV":"헬스케어 섹터 ETF","XLF":"금융 섹터 ETF","XLE":"에너지 섹터 ETF","XLP":"필수소비 섹터 ETF","XLI":"산업재 섹터 ETF","XLY":"경기소비 섹터 ETF","XLU":"유틸리티 섹터 ETF","XLC":"커뮤니케이션 섹터 ETF","XLB":"소재 섹터 ETF","XLRE":"부동산 섹터 ETF"}
us_u = []
for q in R["us"]:
    s_ = q["sym"]; rr = (R["hus"].get(s_) or {}).get("rows")
    if not rr or len(rr) < 90: continue
    etf = q.get("kind") == "etf"; x = ind(rr); g = None
    if q.get("epsf") and q.get("epst") and q["epst"] > 0: g = (q["epsf"] / q["epst"] - 1) * 100
    ed = None
    if q.get("earn"):
        ed = (_utc(q["earn"]) + dt.timedelta(hours=9)).date(); ed = (ed - TODAY).days
    sec = "ETF·레버리지" if etf else (sec_of(SEC["us"], s_) or "기타")
    us_u.append(dict(code=s_, name=NM["us"].get(s_, ETF_KR.get(s_) or (q["name"] or s_).split(" ")[0]), sec=sec, cap=q["cap"], x=x,
                     fpe=None if etf else q.get("fpe"), g=g, rating=None if etf else q.get("rating"), earn_days=ed, mk="US",
                     kind="E" if etf else "S"))
kr_u = []
for k in R["kr"]:
    c = k["code"]; rr = (R["hkr"].get(c) or {}).get("rows")
    if not rr or len(rr) < 90: continue
    etf_k = k.get("kind", "stock") != "stock"
    if not etf_k and k["name"].endswith(("우", "우B", "우C", "우C2")): continue
    det = KDET.get(c, {}); x = ind(rr)
    fl = sum(f["f"] + f["i"] for f in (det.get("flows") or [])[:20]) if det.get("flows") else None
    g = (det["per"] / det["cper"] - 1) * 100 if det.get("per") and det.get("cper") and det["cper"] > 0 else None
    kr_u.append(dict(code=c, name=NM["kr_short"].get(k["name"], k["name"]), sec="ETF·ETN" if etf_k else (sec_of(SEC["kr"], c) or "기타"), cap=k["cap"], x=x,
                     per=None if etf_k else det.get("per"), cper=None if etf_k else det.get("cper"), g=None if etf_k else g,
                     flow_won=None if etf_k else fl, flow_pct=None if (etf_k or fl is None) else fl / max(k["cap"], 1) * 100, mk="KR", mkt=k.get("mkt", "KOSPI"), kind="E" if etf_k else "S"))
cr_u = []
for c_ in R["cg"]:
    rr = R["hcr"].get(c_["sym"])
    if not rr or len(rr) < 90 or (c_["vol"] or 0) <= 0: continue
    cr_u.append(dict(code=c_["sym"], name=NM["cr"].get(c_["sym"], c_["name"]), sec=sec_of(SEC["cr"], c_["sym"]) or "기타", cap=c_["cap"], x=ind(rr), id=c_["id"],
                     turn=c_["vol"] / c_["cap"] * 100 if c_["cap"] else None, fund=HL.get(c_["sym"], {}).get("f"), mk="CR", kind="S"))
BEN = dict(US=spx, KR=ks, CR=btcI)
FLOOR = {"KR": 1e12, "US": 3e10, "CR": 1e9}
picks, ALL = {}, {}
for mk, U in (("US", us_u), ("KR", kr_u), ("CR", cr_u)):
    ranked = score_universe(U, BEN[mk], mk)
    ALL[mk] = ranked
    pool = [u for u in ranked if u["cap"] >= FLOOR[mk] and u.get("kind") != "E"]
    if len(pool) < 12: pool = ranked
    picks[mk] = [build_pick(u, mk, BEN[mk], len(ranked), i + 1) for i, u in enumerate(pick_top(pool, 5, 2))]
    print(mk, "universe", len(ranked), "pool", len(pool), [(p["name"], p["score"]) for p in picks[mk]])
# ---------------- 종목 퀀트 점수 조회기 (부모님·가족용) ----------------
ALIAS = CFG.get("alias", {})
EN_NAME = {q["sym"]: (q.get("name") or "") for q in R["us"]}
CG_NAME = {c_["sym"]: c_["name"] for c_ in R["cg"]}
SECS = sorted({u["sec"] for mk in ALL for u in ALL[mk]}); SI = {x: i for i, x in enumerate(SECS)}
MKC = {"KR": "K", "US": "U", "CR": "C"}
SEARCH = []
for mk in ("KR", "US", "CR"):
    U = ALL[mk]
    for i_, u in enumerate(U):
        x = u["x"]; pl = plan(x, mk, depth_for(x)); etf = u.get("kind") == "E"
        if mk == "CR": v1 = round(u.get("turn") or 0, 2); v2 = 0; fv = round(u["fund"], 4) if u.get("fund") is not None else 0
        elif mk == "US": v1 = round(u.get("fpe") or 0, 1); v2 = round(u.get("g") or 0); fv = round(rating_num(u.get("rating")) or 0, 1)
        else: v1 = round(u.get("cper") or u.get("per") or 0, 1); v2 = round(u.get("g") or 0); fv = round(u.get("flow_pct") or 0, 2)
        al = " ".join(z for z in (ALIAS.get(u["code"], ""), (EN_NAME.get(u["code"], "") if mk == "US" else CG_NAME.get(u["code"], "") if mk == "CR" else "")) if z).strip()
        SEARCH.append([u["name"], u["code"], MKC[mk], u.get("kind", "S"), SI[u["sec"]], u["score"], i_ + 1, len(U),
                       round(x["p"], 4), round(x["d1"], 2), round(x["m1"], 1), round(x["rsi"]),
                       pl["entry"], pl["sl"], pl["tp1"], pl["tp2"], pl["rr"],
                       [u["f"][k] for k in ("trend", "mom", "val", "flow", "vol")],
                       [round((x["p"] / x["ma200"] - 1) * 100, 1), round(x["m6x"], 1), round(x["m3"] - BEN[mk]["m3"], 1), v1, v2, fv,
                        round(x["atr"] / x["p"] * 100, 1), round(x["vol20"], 1)], al])
print("search rows", len(SEARCH))


# ---------------- 트리맵 (시총 Top20 + 산업군) ----------------
def tm_items(U, mk):
    out = []
    for u in U:
        x = u["x"]; o = dict(code=u["code"], name=u["name"], cap=u["cap"], d1=round(x["d1"], 2), m1=round(x["m1"], 2), p=x["p"], sec=u["sec"], mk=mk)
        if u.get("id"): o["id"] = u["id"]
        out.append(o)
    return out
def secsum(items):
    o = {}
    for x in items:
        if not x.get("cap"): continue
        a = o.setdefault(x["sec"], dict(sec=x["sec"], cap=0, w1=0, wd=0, n=0)); a["cap"] += x["cap"]; a["w1"] += x["cap"] * x["m1"]; a["wd"] += x["cap"] * x["d1"]; a["n"] += 1
    return sorted([dict(sec=a["sec"], cap=a["cap"], m1=round(a["w1"] / a["cap"], 2), d1=round(a["wd"] / a["cap"], 2), n=a["n"]) for a in o.values()], key=lambda z: -z["m1"])
TM = {}
for key, U, mk in (("us", us_u, "US"), ("kr", kr_u, "KR"), ("cr", cr_u, "CR")):
    items = tm_items([u for u in U if u["sec"] != "기타" or mk != "CR"], mk)
    TM[key] = dict(items=items, top20=[x["code"] for x in sorted(items, key=lambda z: -z["cap"])][:20], sectors=secsum(items))

# ---------------- 자동 해설 ----------------
def secline(key, n=2):
    s = TM[key]["sectors"]; return s[:n], s[-n:]
def band_action(s, mk):
    if s >= 70: return "추세 추종 가능 구간 · 그래도 지정가로 눌림에서만, 현금 30% 유지"
    if s >= 55: return "선별 매수 · 추천 점수 상위 종목만 얕은 지정가, 비중은 평소의 70%"
    if s >= 40: return "경계 · 추격 금지, 깊은 지정가 그물만 · 현금 35% 이상"
    return "방어 우선 · 신규는 최소 단위만, 손절선 엄수 · 현금 40% 이상"
wr = [("S&P 500", "^GSPC"), ("나스닥", "^IXIC"), ("코스피", "^KS11"), ("닛케이", "^N225"), ("대만", "^TWII"), ("상해", "000001.SS"), ("유로스톡스", "^STOXX50E")]
wm = sorted([(n, I(s)["m1"]) for n, s in wr], key=lambda z: -z[1])
press = sorted(mac_parts, key=lambda p: p[2] / p[1])
auto = dict(
    mac=[("WHY", f"가장 큰 부담은 {press[0][0]}({press[0][2]}/25)와 {press[1][0]}({press[1][2]}/25) → 돈의 가격(금리)이 내려가기 어려운 환경"),
         ("WHAT", f"한 달 기준 {wm[0][0]} {f1(wm[0][1])}·{wm[1][0]} {f1(wm[1][1])} 강세, {wm[-1][0]} {f1(wm[-1][1])} 최약세"),
         ("ACTION", band_action(S["mac"], "mac"))],
    us=[("WHY", f"S&P500 {pct(spx['d1'])}, 나스닥100 {pct(ndx['d1'])} · VIX {vix:.1f} · 10년물 {tnx:.2f}%"),
        ("WHAT", "한 달 강한 산업: " + ", ".join(f"{s['sec']} {f1(s['m1'])}" for s in secline('us')[0]) + " / 약한 산업: " + ", ".join(f"{s['sec']} {f1(s['m1'])}" for s in secline('us')[1])),
        ("ACTION", f"S&P 50일 평균선 {spx['ma50']:,.0f} {'위' if spx['p'] > spx['ma50'] else '아래'} · " + band_action(S["us"], "us"))],
    kr=[("WHY", f"코스피 {pct(ks['d1'])}, 코스닥 {pct(kq['d1'])} · 외국인(상위 종목) 당일 {won(fr1)}원, 5일 {won(fr5)}원"),
        ("WHAT", "한 달 강한 산업: " + ", ".join(f"{s['sec']} {f1(s['m1'])}" for s in secline('kr')[0]) + " / 약한 산업: " + ", ".join(f"{s['sec']} {f1(s['m1'])}" for s in secline('kr')[1])),
        ("ACTION", ("외국인 5일 순매수 전환 · " if fr5 > 0 else "외국인 5일 순매도 지속 · ") + band_action(S["kospi"], "kr"))],
    cr=[("WHY", f"비트코인 24시간 {pct(btcI['d1'])}, 한 달 {f1(btcI['m1'])} · 공포·탐욕 {fng}(전일 {fng_prev})"),
        ("WHAT", f"BTC 펀딩비 {fundB:+.4f}% · 롱 계좌 비율 {lsr:.2f}배(1주 전 {lsr_w:.2f}) → " + ("롱 쏠림, 흔들기 주의" if lsr > 1.6 else "숏 쏠림, 반등 연료" if lsr < 1.0 else "균형")),
        ("ACTION", f"최근 20일 범위 ${btcI['lo20']:,.0f}~${btcI['hi20']:,.0f} · 하단 지정가만, 상단 돌파 추격 금지")])
def nv(k, f, default): return (NOTE.get(k) or {}).get(f, default)
TITLE = dict(mac=nv("mac", "title", f"오늘 매크로는 <em>{grade(S['mac'])}</em>"), us=nv("us", "title", f"미국 증시 · <em>{grade(S['us'])} 구간</em>"),
             kr=nv("kr", "title", f"한국 증시 · <em>{grade(S['kospi'])} 구간</em>"), cr=nv("cr", "title", f"크립토 · <em>{grade(S['cr'])} 구간</em>"))

# ---------------- 눈금자 ----------------
def ruler(v, lo, hi, z): return dict(v=v, lo=lo, hi=hi, z=z)
Gz, Nz, Wz, Bz = "g", "n", "w", "b"
RUL = dict(wti=ruler(wti, 50, 130, [(80, "편안", Gz), (95, "보통", Nz), (130, "부담", Bz)]), cpi=ruler(CPI, 0, 6, [(2.5, "목표권", Gz), (3.0, "보통", Nz), (6, "부담", Bz)]),
           tnx=ruler(tnx, 3, 6, [(4.0, "편안", Gz), (4.75, "보통", Nz), (6, "부담", Bz)]), krw=ruler(FX, 1200, 1550, [(1300, "원화 강세", Gz), (1400, "보통", Nz), (1550, "원화 약세", Bz)]),
           vix=ruler(vix, 10, 40, [(15, "평온", Gz), (20, "보통", Nz), (30, "불안", Wz), (40, "공포", Bz)]), vkospi=ruler(VK, 10, 70, [(20, "평온", Gz), (30, "보통", Nz), (45, "불안", Wz), (70, "공포", Bz)]),
           spxdev=ruler(dev(spx), -10, 10, [(-5, "약세", Bz), (-1, "주의", Wz), (1, "보합", Nz), (10, "강세", Gz)]), ndxdev=ruler(dev(ndx), -10, 10, [(-5, "약세", Bz), (-1, "주의", Wz), (1, "보합", Nz), (10, "강세", Gz)]),
           ksdev=ruler(dev(ks), -25, 15, [(-10, "급락", Bz), (-3, "약세", Wz), (3, "보합", Nz), (15, "강세", Gz)]), kqdev=ruler(dev(kq), -25, 15, [(-10, "급락", Bz), (-3, "약세", Wz), (3, "보합", Nz), (15, "강세", Gz)]),
           fng=ruler(fng, 0, 100, [(25, "극공포", Bz), (45, "공포", Wz), (55, "중립", Nz), (75, "탐욕", Wz), (100, "극탐욕", Bz)]),
           fund=ruler(fundB, -0.03, 0.05, [(0, "하락베팅", Wz), (0.015, "정상", Gz), (0.05, "과열", Bz)]), lsr=ruler(lsr, 0.5, 2.5, [(0.9, "숏 쏠림", Wz), (1.3, "균형", Gz), (2.5, "롱 쏠림", Bz)]))
for r_ in RUL.values(): r_["v"] = clamp(r_["v"], r_["lo"], r_["hi"])

# ---------------- 글로벌 보드 ----------------
def gq(s):
    x = I(s); return dict(p=x["p"], d1=round(x["d1"], 2), m1=round(x["m1"], 2))
world = [("미주", [("S&P 500", "^GSPC"), ("나스닥", "^IXIC"), ("다우", "^DJI"), ("러셀2000(소형주)", "^RUT"), ("필라델피아 반도체", "^SOX")]),
         ("아시아", [("코스피", "^KS11"), ("일본 닛케이", "^N225"), ("대만 가권", "^TWII"), ("중국 상해", "000001.SS"), ("홍콩 항셍", "^HSI"), ("인도 센섹스", "^BSESN")]),
         ("유럽", [("유로스톡스50", "^STOXX50E"), ("독일 DAX", "^GDAXI"), ("영국 FTSE", "^FTSE")])]
world = [(r, [(n, gq(s)) for n, s in L]) for r, L in world]
reg_m = {r: statistics.mean(q["m1"] for _, q in L) for r, L in world}
best_r = max(reg_m, key=reg_m.get); worst_r = min(reg_m, key=reg_m.get)
worldmsg = nv("mac", "worldmsg", f"한 달 평균 {best_r} {f1(reg_m[best_r])}, {worst_r} {f1(reg_m[worst_r])} · 미국 반도체지수 한 달 {f1(I('^SOX')['m1'])}. "
              + ("지역 간 격차가 커서 '전 세계 동반 침체'보다는 특정 업종 쏠림의 되돌림에 가깝습니다." if reg_m[best_r] > 0 > reg_m[worst_r] else
                 "모든 지역이 같은 방향 — 개별 이슈보다 금리·달러 같은 공통 변수가 시장을 움직이는 중입니다."))
cur = [("3개월", "^IRX"), ("5년", "^FVX"), ("10년", "^TNX"), ("30년", "^TYX")]
curve = dict(now=[(n, last(s)) for n, s in cur], prev=[(n, rows(s)[-22][4]) for n, s in cur])
dm = statistics.mean(a[1] - b[1] for a, b in zip(curve["now"], curve["prev"])); spread = curve["now"][2][1] - curve["now"][0][1]
curvemsg = (f"한 달 새 금리가 평균 {dm*100:+.0f}bp(0.01%p) 움직였어요. 10년({curve['now'][2][1]:.2f}%) − 3개월({curve['now'][0][1]:.2f}%) = {spread:+.2f}%p → "
            + ("정상 곡선이라 '침체 신호'보다는 '물가·재정 부담' 신호에 가깝습니다." if spread > 0.3 else "역전·평탄 곡선 → 경기 둔화 경계 신호입니다."))
cb = []; seen = set()
for b, rate, lastd, nxt, lbl in CFG["central_banks"]:
    if b in seen or dt.date.fromisoformat(nxt) < TODAY: continue
    seen.add(b); dd = (dt.date.fromisoformat(nxt) - TODAY).days
    cb.append((b, rate, lastd, lbl, f"D-{dd}" if dd else "오늘"))
cmd = [(n, gq(s), u, dg) for n, s, u, dg in [("브렌트유", "BZ=F", "$", 2), ("WTI", "CL=F", "$", 2), ("금", "GC=F", "$", 0), ("은", "SI=F", "$", 2), ("구리", "HG=F", "$", 3), ("천연가스", "NG=F", "$", 3)]]
fxl = [(n, gq(s), "", dg, h) for n, s, dg, h in [("달러지수", "DX-Y.NYB", 2, "오르면 달러 강세"), ("원/달러", "KRW=X", 1, "내리면 원화 강세"), ("엔/달러", "JPY=X", 2, "오르면 엔화 약세"), ("달러/유로", "EURUSD=X", 4, "오르면 유로 강세"), ("위안/달러", "CNY=X", 3, "내리면 위안 강세")]]
cu, au, ag = gq("HG=F")["m1"], gq("GC=F")["m1"], gq("SI=F")["m1"]
cmdmsg = (f"구리(경기 체온계) 한 달 {f1(cu)} → " + ("실물 경기는 아직 버티는 중." if cu > -3 else "실물 경기 둔화 신호.")
          + f" 금 {f1(au)}·은 {f1(ag)} → " + ("고금리에 이자 안 주는 자산이 불리하다는 신호." if au < 0 else "불안할 때 사는 안전자산으로 돈이 피신 중."))
cal = []
for d_, t, e, w in CFG["events"]:
    d0 = dt.date.fromisoformat(d_)
    if d0 >= TODAY: cal.append((f"{d0.month}/{d0.day} {WD[d0.weekday()]}", t, e, w))
cal = cal[:6]
U_sec, K_sec = TM["us"]["sectors"], TM["kr"]["sectors"]
sectors_auto = dict(us=dict(good=" · ".join(f"{s['sec']}({f1(s['m1'])})" for s in U_sec[:3]), bad=" · ".join(f"{s['sec']}({f1(s['m1'])})" for s in U_sec[-3:][::-1])),
                    kr=dict(good=" · ".join(f"{s['sec']}({f1(s['m1'])})" for s in K_sec[:3]), bad=" · ".join(f"{s['sec']}({f1(s['m1'])})" for s in K_sec[-3:][::-1])))

# ---------------- Argon 가상계좌: 체결·청산 자동 판정 ----------------
def day_rows(o):
    if o["mk"] == "KR": rr = (R["hkr"].get(o["code"]) or {}).get("rows"); off = 9
    elif o["mk"] == "US": rr = (R["hus"].get(o["code"]) or {}).get("rows") or rows(o["code"]); off = -4
    else: rr = R["hcr"].get(o["code"]); off = 0
    return [(_utc(r[0] + off * 3600).date(), r[2], r[3], r[4]) for r in (rr or [])]
def cur_px(o):
    r = day_rows(o); return r[-1][3] if r else None
def krw(o, v): return v if o["mk"] == "KR" else v * FX
EXPIRE_DAYS = 10
for o in ST["orders"]:
    if o["status"] in ("closed", "cancelled"): continue
    created = dt.date.fromisoformat(o["created"])
    for d_, hi, lo, cl in day_rows(o):
        if d_ <= created or (o.get("last_eval") and d_ <= dt.date.fromisoformat(o["last_eval"])): continue
        if o["status"] == "pending":
            if lo <= o["entry"]:
                o.update(status="open", fill_date=d_.isoformat(), filled_qty=o["qty"], open_qty=o["qty"], stop=o["sl"], fx_fill=FX)
                ST["log"].append(dict(d=d_.isoformat(), t=f"{o['name']} {fmt(o['entry'], o['mk'])} 체결"))
                if lo <= o["sl"]:  # 같은 날 손절가까지 내려가면 보수적으로 손절 처리
                    o["realized_krw"] += krw(o, (o["sl"] - o["entry"]) * o["open_qty"]); o.update(status="closed", open_qty=0, exit="손절(당일)")
                    ST["log"].append(dict(d=d_.isoformat(), t=f"{o['name']} 당일 손절"))
            elif (d_ - created).days > EXPIRE_DAYS:
                o.update(status="cancelled"); ST["log"].append(dict(d=d_.isoformat(), t=f"{o['name']} 지정가 {EXPIRE_DAYS}일 미체결 → 취소"))
        elif o["status"] == "open":
            if lo <= o["stop"]:
                o["realized_krw"] += krw(o, (o["stop"] - o["entry"]) * o["open_qty"]); o.update(status="closed", open_qty=0, exit="본절" if o["stop"] >= o["entry"] else "손절")
                ST["log"].append(dict(d=d_.isoformat(), t=f"{o['name']} {o['exit']} 청산"))
            elif not o.get("tp1_hit") and hi >= o["tp1"]:
                half = o["open_qty"] / 2 if o["mk"] == "CR" else math.floor(o["open_qty"] / 2) or o["open_qty"]
                o["realized_krw"] += krw(o, (o["tp1"] - o["entry"]) * half); o["open_qty"] -= half; o.update(tp1_hit=True, stop=o["entry"])
                ST["log"].append(dict(d=d_.isoformat(), t=f"{o['name']} 1차 목표 도달 → 절반 익절, 손절선 매수가로"))
                if o["open_qty"] <= 0: o.update(status="closed", exit="1차 익절")
            elif o.get("tp1_hit") and hi >= o["tp2"]:
                o["realized_krw"] += krw(o, (o["tp2"] - o["entry"]) * o["open_qty"]); o.update(status="closed", open_qty=0, exit="2차 익절")
                ST["log"].append(dict(d=d_.isoformat(), t=f"{o['name']} 2차 목표 도달 → 전량 익절"))
        o["last_eval"] = d_.isoformat()
# 새 주문: 활성 주문이 6개 미만이고 예비 현금(30%)을 지키고도 50만 원 이상 남으면 추천 1~2위에서 보충
def equity():
    eq = ST["start_cash"] + sum(o["realized_krw"] for o in ST["orders"])
    for o in ST["orders"]:
        if o["status"] == "open":
            p = cur_px(o) or o["entry"]; eq += krw(o, (p - o["entry"]) * o["open_qty"])
    return eq
def committed():
    return sum(krw(o, o["entry"] * (o["qty"] if o["status"] == "pending" else o["open_qty"])) for o in ST["orders"] if o["status"] in ("pending", "open"))
active_codes = {o["code"] for o in ST["orders"] if o["status"] in ("pending", "open")}
for mk in ("KR", "US", "CR"):
    for p in picks[mk][:2]:
        if len(active_codes) >= 6: break
        free = equity() * 0.70 - committed()
        if free < 500_000 or p["code"] in active_codes: continue
        bud = min(1_500_000, free); px = krw(dict(mk=mk), p["entry"])
        qty = math.floor(bud / px) if mk != "CR" else round(bud / px, 5)
        if qty <= 0: continue
        ST["orders"].append(dict(id=f"{p['code']}-{TODAY_S}", name=p["name"], code=p["code"], mk=mk, created=TODAY_S, status="pending", entry=p["entry"], qty=qty,
                                 tp1=p["tp1"], tp2=p["tp2"], sl=p["sl"], rr=p["rr"], why=f"추천 {p['rank']}위 · 점수 {p['score']} · {p['head']}", budget_krw=round(qty * px),
                                 filled_qty=0, fill_date=None, realized_krw=0, last_eval=None))
        active_codes.add(p["code"]); ST["log"].append(dict(d=TODAY_S, t=f"{p['name']} 신규 지정가 {fmt(p['entry'], mk)}"))
EQ = equity(); COM = committed()
day_n = (TODAY - dt.date.fromisoformat(ST["start_date"])).days
ledger = []
for o in ST["orders"]:
    if o["status"] == "cancelled" and o["id"].split("-")[-1] != TODAY_S.replace("-", "") and (TODAY - dt.date.fromisoformat(o["created"])).days > 20: continue
    p = cur_px(o); q = o["qty"] if o["status"] == "pending" else o.get("open_qty", 0)
    pnl = o["realized_krw"] + (krw(o, (p - o["entry"]) * q) if o["status"] == "open" and p else 0)
    lbl = {"pending": "지정가 대기", "open": "보유 중" + (" · 본절" if o.get("tp1_hit") else ""), "closed": o.get("exit", "청산"), "cancelled": "취소"}[o["status"]]
    ledger.append(dict(name=o["name"], code=o["code"], mk=o["mk"], status=lbl, st=o["status"], entry=o["entry"], qty=q if o["status"] != "closed" else o["filled_qty"],
                       amt=round(krw(o, o["entry"] * (q or o["qty"]))), tp1=o["tp1"], tp2=o["tp2"], sl=o.get("stop", o["sl"]), rr=o["rr"], why=o["why"],
                       px=p, gap=None if not p else round((p / o["entry"] - 1) * 100, 1), pnl=round(pnl), id=next((c["id"] for c in R["cg"] if c["sym"] == o["code"]), None)))
for x in ledger: x["w"] = round(x["amt"] / max(EQ, 1) * 100, 1)
cash_free = EQ - COM
PAL_N = [x for x in ledger if x["st"] in ("pending", "open")]
alloc = [dict(name="현금 (예비 탄약)", w=round(cash_free / EQ * 100, 1))] + [dict(name=x["name"], w=x["w"]) for x in PAL_N]
ST["last_run"] = NOW.isoformat(timespec="minutes")
json.dump(ST, open(LP, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# ---------------- DATA ----------------
weekend = TODAY.weekday() >= 5
edition = "아침 브리핑 07:00" if NOW.hour < 12 else "저녁 브리핑 19:00"
cg_map = {c["sym"]: c for c in R["cg"]}
def cgq(s): c = cg_map.get(s) or {}; return c.get("px"), round(c.get("d1") or 0, 2)
heat = [dict(code=s, price=cgq(s)[0], chg=cgq(s)[1]) for s in ("BTC", "ETH", "SOL")]
tot = sum(c["cap"] for c in R["cg"]); dom = cg_map["BTC"]["cap"] / tot * 100
idmap = {x["code"]: x["id"] for x in TM["cr"]["items"]}
for p in picks["CR"]: idmap[p["code"]] = p["id"]
for x in ledger:
    if x["mk"] == "CR" and x["id"]: idmap[x["code"]] = x["id"]
ATS = f"미국 {kd(US_D)} 종가 · 한국 {kd(KR_D)} 종가 · 크립토 {NOW.strftime('%m/%d %H:%M')} KST"
DATA = dict(
    meta=dict(date=f"{TODAY.year}.{TODAY.month:02d}.{TODAY.day:02d} ({WD[TODAY.weekday()]})", edition=edition,
              mode="주말 모드 · 크립토 & 매크로 집중" if weekend else "평일 모드", fx=FX, asof=ATS, idmap=idmap, day=day_n, built=NOW.isoformat(timespec="minutes"),
              usd=kd(US_D), krd=kd(KR_D), auto=not bool(NOTE)),
    mac=dict(score=S["mac"], title=TITLE["mac"], parts=[list(p) + [RULES["mac"][i]] for i, p in enumerate(mac_parts)],
             hist=dict(hinfo(mac_h, mac_now, "물가 제외 3개 항목 환산 · 최근 1년"), now=round(mac_now)),
             kpis=[("WTI 국제유가", f"${wti:.2f}", f"한 달 {f1(I('CL=F')['m1'])} · 브렌트 ${brent:.1f}", "wti"), (f"미국 물가(CPI, {CPI_M}월)", f"{CPI}%", f"전월 {CPI_PREV}% · 목표 2%", "cpi"),
                   ("미 10년물 국채금리", f"{tnx:.2f}%", f"한 달 {(tnx-rows('^TNX')[-22][4])*100:+.0f}bp", "tnx"), ("원/달러 환율", f"{FX:,.1f}원", f"달러지수 {dxy:.1f}", "krw")],
             diag=nv("mac", "diag", auto["mac"]), vars=nv("mac", "vars", None), trends=nv("mac", "trends", None), sectors=nv("mac", "sectors", sectors_auto),
             world=world, worldmsg=worldmsg, curve=curve, curvemsg=curvemsg, cb=cb, cmd=cmd, fx=fxl, cmdmsg=cmdmsg, cal=cal),
    us=dict(score=S["us"], title=TITLE["us"], sub=f"{kd(US_D)} 본장 마감", parts=[list(p) + [RULES["us"][i]] for i, p in enumerate(us_parts)], hist=hinfo(us_h, S["us"], "같은 산식 · 최근 1년(252거래일)"),
            kpis=[("S&P 500", f"{spx['p']:,.2f}", spx["d1"], "spxdev", f"60일 평균 대비 {dev(spx):+.1f}%"), ("나스닥 100", f"{ndx['p']:,.2f}", ndx["d1"], "ndxdev", f"60일 평균 대비 {dev(ndx):+.1f}%"),
                  ("VIX 공포지수", f"{vix:.2f}", I("^VIX")["d1"], "vix", "20 넘으면 불안 구간"), ("미 10년물", f"{tnx:.3f}%", None, "tnx", "5% 넘으면 주식 부담"),
                  ("WTI", f"${wti:.2f}", I("CL=F")["d1"], "wti", "$95 넘으면 물가 부담"), ("나스닥100 선물", f"{last('NQ=F'):,.2f}", I("NQ=F")["d1"], None, "본장 전후 분위기 참고")],
            diag=nv("us", "diag", auto["us"]), tm=TM["us"], top=picks["US"], n=len(us_u)),
    kr=dict(score=S["kospi"], score2=S["kosdaq"], title=TITLE["kr"], sub=f"{kd(KR_D)} 마감", parts=[list(p) + [RULES["kospi"][i]] for i, p in enumerate(kospi_parts)],
            parts2=[list(p) + [RULES["kosdaq"][i]] for i, p in enumerate(kosdaq_parts)], hist=dict(pct=pctl(ktr, kospi_parts[0][2]), label="코스피 추세 항목 · 최근 1년"),
            kpis=[("코스피", f"{ks['p']:,.2f}", ks["d1"], "ksdev", f"60일 평균 대비 {dev(ks):+.1f}%"), ("코스닥", f"{kq['p']:,.2f}", kq["d1"], "kqdev", f"60일 평균 대비 {dev(kq):+.1f}%"),
                  ("원/달러", f"{FX:,.1f}원", I("KRW=X")["d1"], "krw", "낮을수록 원화 강세"), (VK_LBL, f"{VK:.2f}", None, "vkospi", "30 넘으면 불안 · 45 넘으면 공포")],
            diag=nv("kr", "diag", auto["kr"]), tm=TM["kr"], top=picks["KR"], n=len(kr_u), flow=dict(f1=fr1, f5=fr5, i5=in5)),
    cr=dict(score=S["cr"], title=TITLE["cr"], parts=[list(p) + [RULES["cr"][i]] for i, p in enumerate(cr_parts)], hist=hinfo(cr_h, S["cr"], f"같은 산식 · 최근 {len(cr_h)}일"),
            kpis=[("비트코인 BTC", heat[0]["price"], "BTC"), ("이더리움 ETH", heat[1]["price"], "ETH"), ("솔라나 SOL", heat[2]["price"], "SOL"), ("주요 코인 시총", f"${tot/1e12:.2f}조", f"BTC 점유율 {dom:.1f}%")],
            gauges=[("공포·탐욕 지수", str(fng), "fng", f"전일 {fng_prev} · 50이 중립"), ("BTC 펀딩비(8시간)", f"{fundB:+.4f}%", "fund", "0.01%가 기본값"), ("롱/숏 계좌 비율", f"{lsr:.2f}배", "lsr", f"1주 전 {lsr_w:.2f}배 · 1.0이 균형")],
            onchain=nv("cr", "onchain", [("BTC 미결제약정(Hyperliquid)", f"${HL.get('BTC', {}).get('oi', 0)/1e9:.2f}B", "선물에 걸린 돈의 크기"), ("ETH · SOL 펀딩비", f"{fundE:+.4f}% · {fundS:+.4f}%", "마이너스 = 하락 베팅 우세")]),
            chainmsg=nv("cr", "chainmsg", "펀딩비와 롱/숏 비율은 '빚내서 한쪽에 몰린 정도'예요. 한쪽으로 쏠릴수록 반대 방향 급변동(청산 연쇄)이 나오기 쉬워요."),
            diag=nv("cr", "diag", auto["cr"]), tm=TM["cr"], top=picks["CR"], heat=heat, n=len(cr_u)),
    ar=dict(start=ST["start_cash"], start_date=ST["start_date"], eq=round(EQ), reserved=round(COM), cash=round(cash_free), ledger=ledger, alloc=alloc,
            log=ST["log"][-6:][::-1], n_fill=sum(1 for o in ST["orders"] if o.get("fill_date")),
            rules=[("추격 매수 금지", "사전에 계산한 지정가에 그물만 친다. 시장가 버튼은 없다."), ("현금 30% 이상 상시 유지", "급락장은 바겐세일. 예비 탄약이 있어야 줍는다."),
                   ("손익비 1:2.5 미만 진입 금지", "잃을 수 있는 돈의 2.5배 이상 벌 수 있을 때만 들어간다."), ("기계적 분할 익절 & 본절 스탑", "1차 목표 도달 시 50% 익절, 손절선을 매수가로 올려 '못 잃는 게임'으로.")]),
    rul=RUL, sources=CFG["sources"])

# ---------------- 카톡 요약 ----------------
def b5(lst): return "\n".join(f"{p['rank']}) {p['name']} [{p['score']}점·{p['head']}] {fmt(p['entry'], p['mk'])}→{fmt(p['tp1'], p['mk'])} / 손절 {fmt(p['sl'], p['mk'])} (1:{p['rr']:.1f})" for p in lst)
KAKAO = f"""[Heeyun's Argon] {DATA['meta']['date']} {edition}

📊 시장 점수 (100점 · 40↓방어 / 55↑선별매수 / 70↑강세)
매크로 {S['mac']} · 미국 {S['us']} · 코스피 {S['kospi']} · 코스닥 {S['kosdaq']} · 크립토 {S['cr']}

🔗 한 줄 진단
{DATA['mac']['diag'][0][1]}

🇺🇸 미국 추천 Top 5 (지정가)
{b5(picks['US'])}

🇰🇷 한국 추천 Top 5 (지정가)
{b5(picks['KR'])}

🪙 크립토 추천 Top 5 (지정가)
{b5(picks['CR'])}

💼 Argon 계좌 (Day {day_n})
평가자산 {EQ:,.0f}원 ({(EQ/ST['start_cash']-1)*100:+.2f}%) · 예약·보유 {COM/1e4:,.0f}만 원 · 현금 {cash_free/1e4:,.0f}만 원
원칙: 추격 금지 · 현금 30%↑ · 손익비 1:2.5↑

※ {ATS} · 투자 권유 아님"""

# ---------------- 렌더 ----------------
W = os.path.join(HERE, "web")
tpl = open(os.path.join(W, "base.html"), encoding="utf-8").read()
css = "".join(open(os.path.join(W, f), encoding="utf-8").read() + "\n" for f in ("v2.css", "v3.css"))
js = "".join(open(os.path.join(W, f), encoding="utf-8").read() + "\n" for f in ("v2.js", "v3.js"))
tpl = tpl.replace("</style>", css + "</style>", 1).replace("const builders=[card1", js + "\nconst builders=[card1", 1).replace("/*__KAKAO__*/", KAKAO)
J = json.dumps(DATA, ensure_ascii=False, default=float)
OUT = os.path.join(ROOT, "site"); os.makedirs(OUT, exist_ok=True)
open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(tpl.replace("/*__DATA__*/null", J).replace("/*__ONLY__*/0", "0").replace("/*__LIVE__*/true", "true"))
for n in range(1, 6):
    open(os.path.join(OUT, f"card{n}.html"), "w", encoding="utf-8").write(tpl.replace("/*__DATA__*/null", J).replace("/*__ONLY__*/0", str(n)).replace("/*__LIVE__*/true", "false"))
open(os.path.join(OUT, "kakao.txt"), "w", encoding="utf-8").write(KAKAO)
open(os.path.join(OUT, "check.html"), "w", encoding="utf-8").write(open(os.path.join(W, "check_template.html"), encoding="utf-8").read())
json.dump(dict(u=ATS, d=DATA["meta"]["date"], sec=SECS, n=dict(KR=len(ALL["KR"]), US=len(ALL["US"]), CR=len(ALL["CR"])), rows=SEARCH),
          open(os.path.join(OUT, "search.json"), "w", encoding="utf-8"), ensure_ascii=False, default=float, separators=(",", ":"))
print("search.json", round(os.path.getsize(os.path.join(OUT, "search.json")) / 1024), "KB")
json.dump(DATA, open(os.path.join(OUT, "data.json"), "w", encoding="utf-8"), ensure_ascii=False, default=float)
open(os.path.join(OUT, ".nojekyll"), "w").write("")
print("built", S, "equity", round(EQ), "committed", round(COM), "auto" if not NOTE else "notes")
