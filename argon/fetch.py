# -*- coding: utf-8 -*-
"""Argon 데이터 수집기 — 표준 라이브러리만 사용 (GitHub Actions에서 pip 설치 불필요)
출처: Yahoo Finance(차트·시총 스크리너), 네이버증권(한국 시총·PER·외국인/기관 수급),
      CoinGecko(크립토 시총), Binance 공개 시세(크립토 일봉), Hyperliquid(펀딩비),
      OKX(롱숏 비율), alternative.me(공포·탐욕), BLS(미국 CPI), FRED(연준 금리)
"""
import json, os, re, time, urllib.request, concurrent.futures as cf

UA = {"User-Agent": "Mozilla/5.0"}
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "cache")
os.makedirs(CACHE, exist_ok=True)


def req(url, data=None, raw=False, tries=3, timeout=25):
    last = None
    for i in range(tries):
        try:
            h = dict(UA)
            if data is not None:
                h["Content-Type"] = "application/json"
            r = urllib.request.urlopen(urllib.request.Request(url, headers=h, data=data), timeout=timeout).read()
            s = r.decode("utf-8", "replace")
            return s if raw else json.loads(s)
        except Exception as e:  # noqa
            last = e
            time.sleep(1.5 * (i + 1))
    return None if not raw else ""


# ---------------- Yahoo ----------------
def yahoo_chart(sym, rng="1y"):
    for host in ("query1", "query2"):
        d = req(f"https://{host}.finance.yahoo.com/v8/finance/chart/{urllib.request.quote(sym)}?range={rng}&interval=1d")
        try:
            r = d["chart"]["result"][0]
            q = r["indicators"]["quote"][0]
            rows = [[t, o, h, l, c, v or 0] for t, o, h, l, c, v in
                    zip(r["timestamp"], q["open"], q["high"], q["low"], q["close"], q["volume"]) if c is not None and h is not None]
            if len(rows) >= 5:
                return dict(sym=sym, price=r["meta"].get("regularMarketPrice") or rows[-1][4],
                            time=r["meta"].get("regularMarketTime"), rows=rows)
        except Exception:
            continue
    return None


def yahoo_screener(n=150):
    for host in ("query2", "query1"):
        d = req(f"https://{host}.finance.yahoo.com/v1/finance/screener/predefined/saved?scrIds=largest_market_cap&count={n}")
        try:
            return d["finance"]["result"][0]["quotes"]
        except Exception:
            continue
    return []


# ---------------- Naver (한국) ----------------
def naver_caps():
    out = []
    for mk, size in (("KOSPI", 100), ("KOSDAQ", 35)):
        d = req(f"https://m.stock.naver.com/api/stocks/marketValue/{mk}?page=1&pageSize={size}") or {}
        for x in d.get("stocks", []):
            if x.get("stockEndType") != "stock":
                continue
            out.append(dict(code=x["itemCode"], name=x["stockName"], mk=mk,
                            cap=int(x["marketValue"].replace(",", "")) * 1e8))
    return out


def _num(s):
    try:
        return float(re.sub(r"[^0-9.\-]", "", s))
    except Exception:
        return None


def naver_detail(code):
    d = req(f"https://m.stock.naver.com/api/stock/{code}/integration") or {}
    info = {x.get("code"): x.get("value") for x in d.get("totalInfos", []) or []}
    tr = req(f"https://m.stock.naver.com/api/stock/{code}/trend?pageSize=20") or []
    flows = []
    for t in tr if isinstance(tr, list) else []:
        c = _num(t.get("closePrice", "0")) or 0
        flows.append(dict(d=t.get("bizdate"), f=(_num(t.get("foreignerPureBuyQuant", "0")) or 0) * c,
                          i=(_num(t.get("organPureBuyQuant", "0")) or 0) * c))
    return code, dict(per=_num(info.get("per") or ""), cper=_num(info.get("cnsPer") or ""),
                      pbr=_num(info.get("pbr") or ""), flows=flows)


# ---------------- Crypto ----------------
STABLE = set("USDT USDC USDE DAI FDUSD USDS PYUSD USD1 TUSD BUSD USDD RLUSD USDTB BUIDL USYC USDF FRAX USDG USDX EURC XAUT PAXG BSC-USD USD0 GHO CRVUSD SUSDE SUSDS USDB USR".split())


def crypto_universe():
    d = req("https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=120&page=1&price_change_percentage=24h,7d,30d") or []
    out = []
    for x in d:
        sym, nm, idd = x["symbol"].upper(), x["name"], x["id"]
        low = (nm + " " + idd).lower()
        if sym in STABLE or any(w in low for w in ("wrapped", "staked", "bridged", "restaked", "liquid staking", "usd")) and sym not in ("BTC",):
            continue
        if x.get("current_price") and 0.97 < x["current_price"] < 1.03 and "usd" in low:
            continue
        out.append(dict(id=idd, sym=sym, name=nm, cap=x["market_cap"] or 0, px=x["current_price"],
                        d1=x.get("price_change_percentage_24h") or 0, m1=x.get("price_change_percentage_30d_in_currency") or 0,
                        vol=x.get("total_volume") or 0))
    return out


def binance_daily(sym):
    d = req(f"https://data-api.binance.vision/api/v3/klines?symbol={sym}USDT&interval=1d&limit=400", tries=2)
    if isinstance(d, list) and len(d) >= 30:
        return [[int(k[0] / 1000), float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[7])] for k in d]
    return None


def crypto_hist(sym):
    rows = binance_daily(sym)
    if rows is None:
        y = yahoo_chart(f"{sym}-USD", "2y")
        rows = y["rows"] if y else None
    return sym, rows


def hyperliquid():
    d = req("https://api.hyperliquid.xyz/info", data=json.dumps({"type": "metaAndAssetCtxs"}).encode())
    out = {}
    try:
        for a, b in zip(d[0]["universe"], d[1]):
            out[a["name"]] = dict(f=float(b["funding"]) * 100 * 8, oi=float(b["openInterest"]) * float(b["markPx"]))
    except Exception:
        pass
    return out  # f = 8시간 환산 펀딩비(%)


# ---------------- Macro ----------------
def bls_cpi():
    d = req("https://api.bls.gov/publicAPI/v2/timeseries/data/CUUR0000SA0")
    try:
        s = d["Results"]["series"][0]["data"]
        s = [x for x in s if x["period"].startswith("M") and x["period"] != "M13" and re.match(r"^[0-9.]+$", x["value"])]
        v = {(int(x["year"]), int(x["period"][1:])): float(x["value"]) for x in s}
        (y, m) = max(k for k in v if (k[0] - 1, k[1]) in v)
        def yoy(y, m):
            return (v[(y, m)] / v[(y - 1, m)] - 1) * 100
        pm = max(k for k in v if k < (y, m) and (k[0] - 1, k[1]) in v)
        return dict(yoy=round(yoy(y, m), 1), prev=round(yoy(*pm), 1), month=m, year=y)
    except Exception:
        return None


def fred_last(series):
    s = req(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}", raw=True, tries=2, timeout=20)
    try:
        last = [l for l in s.strip().splitlines()[1:] if not l.endswith(",.")][-1]
        return float(last.split(",")[1])
    except Exception:
        return None


GLOBAL = ["^GSPC", "^NDX", "^IXIC", "^DJI", "^RUT", "^SOX", "^VIX", "NQ=F", "ES=F", "^KS11", "^KQ11", "^N225", "^TWII",
          "000001.SS", "^HSI", "^BSESN", "^STOXX50E", "^GDAXI", "^FTSE", "^IRX", "^FVX", "^TNX", "^TYX",
          "CL=F", "BZ=F", "GC=F", "SI=F", "HG=F", "NG=F", "DX-Y.NYB", "KRW=X", "JPY=X", "EURUSD=X", "CNY=X", "BTC-USD"]


def main():
    t0 = time.time()
    out = {"fetched_at": int(time.time())}
    with cf.ThreadPoolExecutor(10) as ex:
        f_glob = {s: ex.submit(yahoo_chart, s, "2y") for s in GLOBAL}
        f_scr = ex.submit(yahoo_screener, 150)
        f_kr = ex.submit(naver_caps)
        f_cg = ex.submit(crypto_universe)
        f_hl = ex.submit(hyperliquid)
        f_cpi = ex.submit(bls_cpi)
        f_fng = ex.submit(req, "https://api.alternative.me/fng/?limit=400")
        f_lsr = ex.submit(req, "https://www.okx.com/api/v5/rubik/stat/contracts/long-short-account-ratio?ccy=BTC&period=1D")
        f_fed = ex.submit(fred_last, "DFEDTARU")
        out["glob"] = {s: f.result() for s, f in f_glob.items()}
        scr = f_scr.result(); kr = f_kr.result(); cg = f_cg.result()
        out.update(hl=f_hl.result(), cpi=f_cpi.result(), fng=f_fng.result(), lsr=f_lsr.result(), fed_upper=f_fed.result())

    # 미국 유니버스: 미국 상장 보통주 시총 상위 (중복 클래스·장외 제외)
    seen, us = set(), []
    for q in scr:
        s = q.get("symbol", "")
        if q.get("quoteType") != "EQUITY" or q.get("exchange") in ("PNK", "OQX", "OEM") or "." in s or s in ("GOOG", "BRK-A", "FOXA", "NWSA"):
            continue
        if q.get("market") and q["market"] != "us_market":
            continue
        us.append(dict(sym=s, name=q.get("shortName") or s, cap=q.get("marketCap") or 0, fpe=q.get("forwardPE"),
                       epsf=q.get("epsForward"), epst=q.get("epsTrailingTwelveMonths"),
                       rating=q.get("averageAnalystRating"), earn=q.get("earningsTimestampStart") or q.get("earningsTimestamp"),
                       ex=q.get("fullExchangeName")))
        if len(us) >= 70:
            break
    out["us"] = us
    out["kr"] = kr
    out["cg"] = cg
    with cf.ThreadPoolExecutor(12) as ex:
        hu = {x["sym"]: ex.submit(yahoo_chart, x["sym"], "1y") for x in us}
        hk = {x["code"]: ex.submit(yahoo_chart, x["code"] + (".KS" if x["mk"] == "KOSPI" else ".KQ"), "1y") for x in kr}
        dk = [ex.submit(naver_detail, x["code"]) for x in kr]
        hc = [ex.submit(crypto_hist, x["sym"]) for x in cg[:45]]
        out["hus"] = {k: f.result() for k, f in hu.items()}
        out["hkr"] = {k: f.result() for k, f in hk.items()}
        out["kdet"] = dict(f.result() for f in dk)
        out["hcr"] = dict(f.result() for f in hc)
    if sum(1 for v in out["glob"].values() if v) < 30 or not out["cg"] or not out["kr"] or not us:
        raise SystemExit("핵심 데이터 수집 실패 → 이번 회차는 건너뛰고 기존 페이지 유지")
    json.dump(out, open(os.path.join(CACHE, "raw.json"), "w"), ensure_ascii=False)
    ok = lambda dct: sum(1 for v in dct.values() if v)
    print(f"fetch done {time.time()-t0:.0f}s | glob {ok(out['glob'])}/{len(GLOBAL)} us {ok(out['hus'])}/{len(us)} "
          f"kr {ok(out['hkr'])}/{len(kr)} cr {ok(out['hcr'])}/{len(out['hcr'])} cpi={out['cpi']} fed={out['fed_upper']} hl={len(out['hl'])}")


if __name__ == "__main__":
    main()
