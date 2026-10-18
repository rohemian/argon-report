# -*- coding: utf-8 -*-
"""Argon 데이터 수집기 — 표준 라이브러리만 사용 (GitHub Actions에서 pip 설치 불필요)

출처
  한국 목록·수급·일봉 : 네이버증권 (m.stock.naver.com, api.stock.naver.com)
  미국 주식·ETF·지수 : Yahoo Finance
  크립토 시총         : CoinGecko / 크립토 일봉: Binance, Yahoo
  파생(펀딩비·미결제): Hyperliquid
  심리·수급           : alternative.me(공포탐욕), OKX(롱숏비율)
  미국 물가           : 미국 노동통계국(BLS)
"""
import json, os, re, time, datetime as dt, urllib.request, concurrent.futures as cf

UA = {"User-Agent": "Mozilla/5.0"}
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "cache")
os.makedirs(CACHE, exist_ok=True)
TR = 24          # 동시 요청 수(야후·바이낸스)
NV_TR = 10       # 네이버 동시 요청 수(높이면 차단됨)
N_KR_FLOW = 900  # 외국인·기관 수급을 받아올 한국 종목 수(시총 상위)


def req(url, data=None, raw=False, tries=3, timeout=25):
    for i in range(tries):
        try:
            h = dict(UA)
            if data is not None:
                h["Content-Type"] = "application/json"
            b = urllib.request.urlopen(urllib.request.Request(url, headers=h, data=data), timeout=timeout).read()
            s = b.decode("utf-8", "replace")
            return s if raw else json.loads(s)
        except Exception:
            time.sleep(0.6 * (i + 1))
    return "" if raw else None


def num(x):
    try:
        return float(re.sub(r"[^0-9.\-]", "", str(x)) or 0)
    except Exception:
        return 0.0


# ---------------- 한국 (네이버) ----------------
def naver_list():
    out = []
    for mk in ("KOSPI", "KOSDAQ"):
        for pg in range(1, 45):
            d = req(f"https://m.stock.naver.com/api/stocks/marketValue/{mk}?page={pg}&pageSize=100", tries=2)
            s = (d or {}).get("stocks") if isinstance(d, dict) else None
            if not s:
                break
            for x in s:
                out.append(dict(code=x["itemCode"], name=x["stockName"], kind=x.get("stockEndType", "stock"), mkt=mk,
                                cap=num(x.get("marketValueRaw")) or num(x.get("marketValue")) * 1e8,
                                px=num(x.get("closePriceRaw")) or num(x.get("closePrice")), d1=num(x.get("fluctuationsRatio"))))
            if len(s) < 100:
                break
    return out


def naver_hist(code):
    """한국 일봉 1년 (ETF·ETN 포함). 실패 시 None"""
    d = req(f"https://api.stock.naver.com/chart/domestic/item/{code}?periodType=dayCandle&period=1y", tries=2)
    try:
        rows = []
        for p in d["priceInfos"]:
            c = num(p.get("closePrice") or p.get("closePriceRaw"))
            if not c:
                continue
            ld = str(p.get("localDate") or "")
            m = re.match(r"(\d{4})[.\-/]?(\d{2})[.\-/]?(\d{2})", ld)
            ts = int(dt.datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), tzinfo=dt.timezone.utc).timestamp()) if m else 0
            rows.append([ts, num(p.get("openPrice")) or c, num(p.get("highPrice")) or c, num(p.get("lowPrice")) or c, c,
                         num(p.get("accumulatedTradingVolume"))])
        rows = [r for r in rows if r[0]]
        rows.sort(key=lambda r: r[0])
        return code, (rows if len(rows) >= 90 else None)
    except Exception:
        return code, None


def naver_flows(code):
    code, det = code, {}
    d = req(f"https://m.stock.naver.com/api/stock/{code}/integration", tries=2) or {}
    info = {x.get("code"): x.get("value") for x in d.get("totalInfos", []) or []}
    tr = req(f"https://m.stock.naver.com/api/stock/{code}/trend?pageSize=20", tries=2) or []
    flows = []
    for t in (tr if isinstance(tr, list) else []):
        c = num(t.get("closePrice")) or 0
        flows.append(dict(d=t.get("bizdate"), f=num(t.get("foreignerPureBuyQuant")) * c, i=num(t.get("organPureBuyQuant")) * c))
    return code, dict(per=num(info.get("per")), cper=num(info.get("cnsPer")), pbr=num(info.get("pbr")), flows=flows)


# ---------------- Yahoo ----------------
def yahoo_chart(sym, rng="1y"):
    for host in ("query1", "query2"):
        d = req(f"https://{host}.finance.yahoo.com/v8/finance/chart/{urllib.request.quote(sym)}?range={rng}&interval=1d", tries=2)
        try:
            r = d["chart"]["result"][0]; q = r["indicators"]["quote"][0]
            rows = [[t, o, h, l, c, v or 0] for t, o, h, l, c, v in
                    zip(r["timestamp"], q["open"], q["high"], q["low"], q["close"], q["volume"]) if c is not None and h is not None]
            if len(rows) >= 60:
                return dict(sym=sym, price=r["meta"].get("regularMarketPrice") or rows[-1][4], time=r["meta"].get("regularMarketTime"), rows=rows)
        except Exception:
            continue
    return None


def yahoo_screener(n=250):
    for host in ("query2", "query1"):
        d = req(f"https://{host}.finance.yahoo.com/v1/finance/screener/predefined/saved?scrIds=largest_market_cap&count={n}", tries=2)
        try:
            return d["finance"]["result"][0]["quotes"]
        except Exception:
            continue
    return []


US_ETF = ["QQQ", "SPY", "VOO", "IVV", "VTI", "SCHD", "SOXX", "SMH", "ARKK", "TQQQ", "SQQQ", "GLD", "SLV", "USO", "IWM", "DIA",
          "TLT", "HYG", "EEM", "VNQ", "IBIT", "FBTC", "XLK", "XLV", "XLF", "XLE", "XLP", "XLI", "XLY", "XLU", "XLC", "XLB", "XLRE",
          "EWY", "EWJ", "FXI", "KWEB", "MAGS", "SOXL", "JEPI", "VIG", "VYM", "RSP", "IJH", "IWF"]

STABLE = set("USDT USDC USDE DAI FDUSD USDS PYUSD USD1 TUSD BUSD USDD RLUSD USDTB BUIDL USYC USDF FRAX USDG USDX EURC XAUT PAXG BSC-USD USD0 GHO CRVUSD SUSDE SUSDS USDB USR".split())


def crypto_universe(n=250):
    d = req(f"https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page={n}&page=1&price_change_percentage=24h,7d,30d") or []
    out = []
    for x in d:
        sym, nm, idd = x["symbol"].upper(), x["name"], x["id"]
        low = (nm + " " + idd).lower()
        if sym in STABLE or sym == "USDY" or any(w in low for w in ("wrapped", "staked", "bridged", "restaked", "liquid staking")):
            continue
        if x.get("current_price") and 0.97 < x["current_price"] < 1.03 and "usd" in low:
            continue
        out.append(dict(id=idd, sym=sym, name=nm, cap=x["market_cap"] or 0, px=x["current_price"],
                        d1=x.get("price_change_percentage_24h") or 0, m1=x.get("price_change_percentage_30d_in_currency") or 0,
                        vol=x.get("total_volume") or 0))
    return out


def crypto_hist(sym):
    d = req(f"https://data-api.binance.vision/api/v3/klines?symbol={sym}USDT&interval=1d&limit=400", tries=2)
    if isinstance(d, list) and len(d) >= 90:
        return sym, [[int(k[0] / 1000), float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[7])] for k in d]
    y = yahoo_chart(f"{sym}-USD", "2y")
    return sym, (y["rows"] if y else None)


def bls_cpi():
    d = req("https://api.bls.gov/publicAPI/v2/timeseries/data/CUUR0000SA0")
    try:
        s = [x for x in d["Results"]["series"][0]["data"] if x["period"].startswith("M") and x["period"] != "M13" and re.match(r"^[0-9.]+$", x["value"])]
        v = {(int(x["year"]), int(x["period"][1:])): float(x["value"]) for x in s}
        y, m = max(k for k in v if (k[0] - 1, k[1]) in v)
        pm = max(k for k in v if k < (y, m) and (k[0] - 1, k[1]) in v)
        return dict(yoy=round((v[(y, m)] / v[(y - 1, m)] - 1) * 100, 1), prev=round((v[pm] / v[(pm[0] - 1, pm[1])] - 1) * 100, 1), month=m, year=y)
    except Exception:
        return None


def hyperliquid():
    d = req("https://api.hyperliquid.xyz/info", data=json.dumps({"type": "metaAndAssetCtxs"}).encode())
    out = {}
    try:
        for a, b in zip(d[0]["universe"], d[1]):
            out[a["name"]] = dict(f=float(b["funding"]) * 100 * 8, oi=float(b["openInterest"]) * float(b["markPx"]))
    except Exception:
        pass
    return out


GLOBAL = ["^GSPC", "^NDX", "^IXIC", "^DJI", "^RUT", "^SOX", "^VIX", "NQ=F", "ES=F", "^KS11", "^KQ11", "^N225", "^TWII",
          "000001.SS", "^HSI", "^BSESN", "^STOXX50E", "^GDAXI", "^FTSE", "^IRX", "^FVX", "^TNX", "^TYX",
          "CL=F", "BZ=F", "GC=F", "SI=F", "HG=F", "NG=F", "DX-Y.NYB", "KRW=X", "JPY=X", "EURUSD=X", "CNY=X", "BTC-USD"]


def main():
    t0 = time.time()
    out = {"fetched_at": int(time.time())}
    with cf.ThreadPoolExecutor(TR) as ex:
        f_glob = {s: ex.submit(yahoo_chart, s, "2y") for s in GLOBAL}
        f_scr = ex.submit(yahoo_screener, 250)
        f_kr = ex.submit(naver_list)
        f_cg = ex.submit(crypto_universe, 250)
        f_hl = ex.submit(hyperliquid)
        f_cpi = ex.submit(bls_cpi)
        f_fng = ex.submit(req, "https://api.alternative.me/fng/?limit=400")
        f_lsr = ex.submit(req, "https://www.okx.com/api/v5/rubik/stat/contracts/long-short-account-ratio?ccy=BTC&period=1D")
        out["glob"] = {s: f.result() for s, f in f_glob.items()}
        scr, kr, cg = f_scr.result(), f_kr.result(), f_cg.result()
        out.update(hl=f_hl.result(), cpi=f_cpi.result(), fng=f_fng.result(), lsr=f_lsr.result())
    print(f"[list] kr={len(kr)} us_screener={len(scr)} cg={len(cg)} glob_ok={sum(1 for v in out['glob'].values() if v)}")

    # 미국: 시총 상위 주식 + 대표 ETF
    seen, us = set(), []
    for q in scr:
        s = q.get("symbol", "")
        if q.get("quoteType") != "EQUITY" or q.get("exchange") in ("PNK", "OQX", "OEM") or "." in s or s in ("GOOG", "BRK-A", "FOXA", "NWSA"):
            continue
        if q.get("market") and q["market"] != "us_market":
            continue
        seen.add(s)
        us.append(dict(sym=s, name=q.get("shortName") or s, cap=q.get("marketCap") or 0, kind="stock", fpe=q.get("forwardPE"),
                       epsf=q.get("epsForward"), epst=q.get("epsTrailingTwelveMonths"), rating=q.get("averageAnalystRating"),
                       earn=q.get("earningsTimestampStart") or q.get("earningsTimestamp")))
    for s in US_ETF:
        if s in seen:
            continue
        seen.add(s)
        us.append(dict(sym=s, name=s, cap=0, kind="etf", fpe=None, epsf=None, epst=None, rating=None, earn=None))
    out["us"] = us
    out["kr"] = kr
    out["cg"] = cg
    print(f"[universe] us={len(us)}")

    # 이력: 한국은 네이버(ETF 포함), 미국·크립토는 야후/바이낸스
    with cf.ThreadPoolExecutor(24) as ex:   # 야후·바이낸스: 스레드 많이
        hu = {x["sym"]: ex.submit(yahoo_chart, x["sym"], "1y") for x in us}
        hc = {x["sym"]: ex.submit(crypto_hist, x["sym"]) for x in cg[:240]}
        out["hus"] = {k: f.result() for k, f in hu.items()}
        out["hcr"] = dict(f.result() for f in hc.values())
    top_flow = [x["code"] for x in sorted([k for k in kr if k["kind"] == "stock"], key=lambda z: -z["cap"])[:N_KR_FLOW]]
    with cf.ThreadPoolExecutor(NV_TR) as ex:  # 네이버: 과하면 차단되므로 스레드 적게
        hk = {c: ex.submit(naver_hist, c) for c in [x["code"] for x in kr]}
        HR = {}
        for c, f in hk.items():
            cc, rows = f.result()
            if rows: HR[cc] = rows
    with cf.ThreadPoolExecutor(NV_TR) as ex:
        kf = {c: ex.submit(naver_flows, c) for c in top_flow}
        out["kdet"] = dict(f.result() for f in kf.values())
    out["hkr"] = {c: dict(rows=r) for c, r in HR.items()}

    if out["glob"] is None or sum(1 for v in out["glob"].values() if v) < 30 or not cg or not kr or not us:
        raise SystemExit("핵심 데이터 수집 실패 → 이번 회차는 건너뛰고 기존 페이지 유지")
    json.dump(out, open(os.path.join(CACHE, "raw.json"), "w"), ensure_ascii=False)
    kd = [x for x in kr if x["kind"] == "stock"]
    print(f"[hist] kr {len(HR)}/{len(kr)} (주식 {len([x for x in kd if x['code'] in HR])}/{len(kd)}) "
          f"us {sum(1 for v in out['hus'].values() if v)}/{len(us)} cr {sum(1 for v in out['hcr'].values() if v)}/{len(out['hcr'])} "
          f"flows {len(out['kdet'])} | cpi={out['cpi']} | {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
