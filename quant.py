# -*- coding: utf-8 -*-
"""Argon 퀀트 엔진 — 5팩터 추천 모델 + 지정가 타점(손익비 1:2.5 이상)

추천 점수(0~100) = 유니버스 안에서의 '등수'를 백분위로 바꾼 뒤 가중 평균
  추세 20%  : 200일 평균선 위에 있는가, 50일선이 200일선 위인가 (큰 흐름)
  모멘텀 25%: 최근 6개월(마지막 1달 제외) 상승률 + 최근 3개월 시장 대비 초과 수익
  가치 20%  : 미국·한국 = 예상 이익 대비 주가(PER 역수) + 이익 증가율 / 크립토 = 거래 활력(거래대금÷시총)
  수급 20%  : 한국 = 외국인+기관 20일 순매수÷시총 / 미국 = 애널리스트 평균 평가 / 크립토 = 펀딩비(낮을수록 +)
  안정성 15%: 20일 변동성이 낮을수록 + (같은 수익이면 덜 흔들리는 쪽)
"""
import math, statistics

W = dict(trend=.20, mom=.25, val=.20, flow=.20, vol=.15)
FNAME = dict(trend="추세", mom="모멘텀", val="가치·실적", flow="수급", vol="안정성")
FNAME_CR = dict(val="거래 활력", flow="파생 쏠림")
FNAME_US = dict(flow="전문가 평가")


def ind(rows):
    C = [r[4] for r in rows]; H = [r[2] for r in rows]; L = [r[3] for r in rows]; n = len(C)
    tr = [max(H[i] - L[i], abs(H[i] - C[i - 1]), abs(L[i] - C[i - 1])) for i in range(1, n)]
    atr = sum(tr[-14:]) / 14
    g = [max(C[i] - C[i - 1], 0) for i in range(n - 14, n)]; l = [max(C[i - 1] - C[i], 0) for i in range(n - 14, n)]
    rsi = 100 - 100 / (1 + (sum(g) / (sum(l) + 1e-12)))
    ma = lambda k: sum(C[-k:]) / len(C[-k:])
    ret = lambda a, b=0: (C[-1 - b] / C[max(0, n - 1 - a)] - 1) * 100
    lr = [math.log(C[i] / C[i - 1]) for i in range(max(1, n - 20), n)]
    return dict(p=C[-1], prev=C[-2], d1=(C[-1] / C[-2] - 1) * 100, m1=ret(21), m3=ret(63), m6x=ret(126, 21) if n > 130 else ret(n - 1, 21),
                ma20=ma(20), m20=ma(20), m60=ma(60), ma50=ma(50), ma200=ma(200), atr=atr, rsi=rsi,
                lo20=min(L[-20:]), hi20=max(H[-20:]), hi52=max(H[-250:]), vol20=statistics.pstdev(lr) * math.sqrt(252) * 100, n=n)


def krtick(x):
    t = 1 if x < 2000 else 5 if x < 5000 else 10 if x < 20000 else 50 if x < 50000 else 100 if x < 200000 else 500 if x < 500000 else 1000
    return round(x / t) * t


def rnd(x, mk):
    if mk == "KR": return krtick(x)
    if mk == "US": return round(x, 2)
    s = max(2, 3 - int(math.floor(math.log10(abs(x)))))
    return round(x, s)


def plan(x, mk, depth=0.6):
    p, a = x["p"], x["atr"]
    entry = p - depth * a
    sl = max(min(x["lo20"] * 0.985, entry - 1.0 * a), entry - 1.6 * a)
    if sl >= entry - 0.8 * a: sl = entry - 0.8 * a
    risk = entry - sl
    tp1 = entry + max(2.5 * risk, min(x["m20"] - entry, 3.5 * risk))
    tp2 = entry + max(4.2 * risk, (tp1 - entry) * 1.6)
    e, s, t1, t2 = [rnd(v, mk) for v in (entry, sl, tp1, tp2)]
    risk = e - s
    if risk <= 0:  # 호가 단위 반올림으로 진입가와 손절가가 붙는 경우(초저가·ETN 등) 보정
        s = rnd(e - max(x["atr"] * 0.5, e * 0.01), mk); risk = e - s
    if risk <= 0:
        risk = max(e * 0.01, 1e-9); s = rnd(e - risk, mk); risk = e - s
    if t1 <= e: t1 = rnd(e + 2.5 * risk, mk)
    if t2 <= t1: t2 = rnd(e + 4.2 * risk, mk)
    rr = (t1 - e) / risk
    if rr < 2.5:
        t1 = rnd(e + 2.5 * risk * 1.01, mk); rr = (t1 - e) / risk
    rr2 = (t2 - e) / risk
    return dict(entry=e, sl=s, tp1=t1, tp2=t2, rr=min(round(rr, 1), 12.0), rr2=min(round(rr2, 1), 20.0))


def depth_for(x):
    return 1.0 if x["rsi"] > 65 else (0.85 if x["p"] < x["m60"] else 0.6)


def pctrank(vals):
    """None은 중간(50) 처리"""
    real = sorted(v for v in vals if v is not None)
    out = []
    for v in vals:
        if v is None or not real: out.append(50.0); continue
        below = sum(1 for r in real if r < v); eq = sum(1 for r in real if r == v)
        out.append((below + 0.5 * eq) / len(real) * 100)
    return out


def rating_num(s):
    try: return float(str(s).split(" ")[0])
    except Exception: return None


def score_universe(U, bench, mk):
    """U: list of dict(code,name,sec,x(ind), ...extra raw). returns sorted list with factors"""
    raw = dict(trend=[], mom=[], val=[], flow=[], vol=[])
    for u in U:
        x = u["x"]
        raw["trend"].append(0.6 * (x["p"] / x["ma200"] - 1) * 100 + 0.4 * (x["ma50"] / x["ma200"] - 1) * 100)
        raw["mom"].append(0.6 * x["m6x"] + 0.4 * (x["m3"] - bench["m3"]))
        if mk == "CR":
            raw["val"].append(u.get("turn"))
            raw["flow"].append(None if u.get("fund") is None else -u["fund"])
        elif mk == "US":
            fpe, g = u.get("fpe"), u.get("g")
            raw["val"].append(None if not fpe or fpe <= 0 else (100 / fpe) + 0.15 * max(-30, min(60, g or 0)))
            r = rating_num(u.get("rating")); raw["flow"].append(None if r is None else -r)
        else:
            pe, g = u.get("cper") or u.get("per"), u.get("g")
            raw["val"].append(None if not pe or pe <= 0 else (100 / pe) + 0.15 * max(-30, min(60, g or 0)))
            raw["flow"].append(u.get("flow_pct"))
        raw["vol"].append(-x["vol20"])
    R = {k: pctrank(v) for k, v in raw.items()}
    for i, u in enumerate(U):
        u["f"] = {k: round(R[k][i]) for k in W}
        u["score"] = round(sum(W[k] * R[k][i] for k in W))
    return sorted(U, key=lambda z: -z["score"])


def pick_top(U, n=5, max_per_sec=2, cap_min=0.0, no_etf=True):
    out, cnt = [], {}
    for u in U:
        x = u["x"]
        if x["m1"] < -30 or x["n"] < 90:  # 한 달 -30% 이상 폭락주는 '떨어지는 칼날'로 제외
            continue
        if cap_min and u.get("cap", 0) < cap_min: continue
        if no_etf and u.get("kind") == "E": continue
        if cnt.get(u["sec"], 0) >= max_per_sec: continue
        cnt[u["sec"]] = cnt.get(u["sec"], 0) + 1
        out.append(u)
        if len(out) == n: break
    return out


# ---------------- 쉬운 설명 생성 ----------------
def lvl(p):
    return "최상위권" if p >= 85 else "상위권" if p >= 65 else "중간" if p >= 40 else "하위권"


def fmt(v, mk):
    if mk == "KR": return f"{v:,.0f}원"
    if mk == "US": return f"${v:,.2f}"
    if v >= 1000: return f"${v:,.0f}"
    if v >= 1: return f"${v:,.2f}"
    if v >= 0.01: return f"${v:.4f}"
    return "$" + f"{v:.10f}".rstrip("0")


def won(v):
    a = abs(v)
    s = f"{a/1e12:,.1f}조" if a >= 1e12 else f"{a/1e8:,.0f}억"
    return ("+" if v >= 0 else "−") + s


def explain(u, mk, bench, nuni):
    x, f = u["x"], u["f"]
    names = {**FNAME, **(FNAME_CR if mk == "CR" else FNAME_US if mk == "US" else {})}
    up200 = (x["p"] / x["ma200"] - 1) * 100
    S = {}
    S["trend"] = (f"1년 평균 가격(200일선)보다 {up200:+.0f}% {'위' if up200 >= 0 else '아래'}에 있어요. "
                  + ("큰 흐름이 위를 향하고 있다는 뜻이에요." if up200 >= 0 and x["ma50"] > x["ma200"] else
                     "큰 흐름은 아직 회복 중이라 확인이 필요해요." if up200 < 0 else "최근 주춤하지만 큰 흐름은 살아 있어요."))
    rel = x["m3"] - bench["m3"]
    S["mom"] = (f"최근 6개월(마지막 한 달 제외) {x['m6x']:+.0f}%, 최근 3개월은 {'시장' if mk!='CR' else '비트코인'}보다 {rel:+.0f}%p. "
                "'오르던 종목이 한동안 더 오르는' 경향(모멘텀)을 노려요.")
    if mk == "CR":
        S["val"] = f"하루 거래대금이 시가총액의 {u.get('turn', 0):.1f}%. 거래가 활발할수록 원하는 가격에 사고팔기 쉬워요."
        fd = u.get("fund")
        S["flow"] = ("선물 펀딩비 정보 없음 → 중간 점수 처리." if fd is None else
                     f"선물 펀딩비 {fd:+.4f}%(8시간). " + ("'내린다'에 건 사람이 많아요 → 반등하면 이들이 급히 되사며 상승 연료가 돼요." if fd < 0 else
                                                     "과열 아님(기본값 0.01% 이하) → 빚내서 산 사람이 적어 급락 위험이 낮아요." if fd <= 0.01 else
                                                     "'오른다'에 빚내서 건 사람이 많아요 → 흔들기 급락 주의."))
    else:
        pe = u.get("fpe") if mk == "US" else (u.get("cper") or u.get("per"))
        g = u.get("g")
        S["val"] = ("이익 추정치가 없어 중간 점수 처리." if not pe else
                    f"내년 예상 이익 기준 PER {pe:.1f}배" + (f", 이익 증가 예상 {g:+.0f}%" if g is not None else "") +
                    ". PER은 '번 돈 1원에 몇 원을 내고 사는가' — 낮을수록 싸요.")
        if mk == "US":
            r = u.get("rating")
            S["flow"] = ("애널리스트 평가 없음." if not r else
                         f"월가 애널리스트 평균 평가 {r.split(' - ')[0]}점(1=적극 매수, 5=매도) → '{r.split(' - ')[-1].replace('Strong Buy','적극 매수').replace('Buy','매수').replace('Hold','보유')}'.")
        else:
            fl = u.get("flow_won")
            S["flow"] = ("수급 데이터 없음." if fl is None else
                         f"최근 20거래일 외국인+기관 {won(fl)}원 {'순매수' if fl >= 0 else '순매도'}(시총 대비 {u.get('flow_pct', 0):+.2f}%). "
                         + ("큰손이 사 모으는 중이에요." if fl >= 0 else "큰손은 아직 파는 중이라 분할 접근."))
    S["vol"] = f"하루 평균 흔들림 {x['atr']/x['p']*100:.1f}%, 연 변동성 {x['vol20']:.0f}%. " + ("덜 흔들려서 손절선을 가깝게 둘 수 있어요." if f["vol"] >= 55 else "많이 흔들리니 비중은 작게.")
    order = sorted(W, key=lambda k: -f[k])
    why = [dict(k=names[k], p=f[k], t=S[k]) for k in order[:3]]
    weak = order[-1]
    risks = [f"약한 고리 · {names[weak]} {lvl(f[weak])}({f[weak]}점): {S[weak]}"] if f[weak] < 50 else [f"가장 낮은 항목({names[weak]})도 {f[weak]}점 — 뚜렷한 약점은 없어요. 그래도 손절선은 반드시 지정."]
    if x["rsi"] > 70: risks.append(f"단기 과열(RSI {x['rsi']:.0f}) — 추격 금지, 지정가까지 기다리기.")
    if x["p"] < x["m60"]: risks.append("60일 평균선 아래 — 반등 확인 전 비중 절반만.")
    if u.get("earn_days") is not None and 0 <= u["earn_days"] <= 14:
        risks.append(f"{u['earn_days']}일 뒤 실적 발표 — 발표 전후 하루 5~10% 흔들림 가능.")
    tag = {"trend": "큰 흐름 상승", "mom": "오르는 힘", "val": "싸다" if mk != "CR" else "거래 활발", "flow": "큰손 매수" if mk == "KR" else "전문가 강추" if mk == "US" else "숏 쏠림 역이용", "vol": "덜 흔들림"}
    head = " · ".join(tag[k] for k in order[:2])
    return why, risks, head


def build_pick(u, mk, bench, nuni, rank):
    x = u["x"]; pl = plan(x, mk, depth_for(x))
    why, risks, head = explain(u, mk, bench, nuni)
    gap = (pl["entry"] / x["p"] - 1) * 100
    act = (f"현재가 {fmt(x['p'],mk)}보다 {abs(gap):.1f}% 아래 <b>{fmt(pl['entry'],mk)}</b>에 지정가. "
           f"1차 목표 {fmt(pl['tp1'],mk)}({(pl['tp1']/pl['entry']-1)*100:+.1f}%)에서 절반 익절, "
           f"손절 {fmt(pl['sl'],mk)}({(pl['sl']/pl['entry']-1)*100:+.1f}%) — 잃을 돈의 {pl['rr']}배를 노리는 자리.")
    return dict(rank=rank, code=u["code"], name=u["name"], sec=u["sec"], mk=mk, id=u.get("id"), price=x["p"], chg=round(x["d1"], 2),
                score=u["score"], f=u["f"], head=head, why=why, risks=risks[:3], act=act, **pl, reason=head, rsi=round(x["rsi"]))
