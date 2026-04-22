import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import requests
import yfinance as yf

THEMES = {
    "defense": {
        "label": "防衛・安全保障",
        "tickers": ["ITA", "XAR", "DFEN"],
        "triggers": ["NDAA", "国防予算", "NATO", "武器輸出"],
    },
    "energy_fossil": {
        "label": "化石燃料エネルギー",
        "tickers": ["XLE", "XOP", "OIH"],
        "triggers": ["LNG輸出許可", "EPA規制緩和", "掘削権"],
    },
    "energy_clean": {
        "label": "クリーンエネルギー",
        "tickers": ["ICLN", "TAN", "QCLN"],
        "triggers": ["IRA予算", "太陽光補助金", "EV税控除"],
    },
    "ai_semicon": {
        "label": "AI・半導体",
        "tickers": ["SOXX", "SMH", "AIQ", "ROBT"],
        "triggers": ["CHIPS法", "輸出規制(BIS)", "中国デカップリング"],
    },
    "healthcare": {
        "label": "医療・薬価",
        "tickers": ["XLV", "IBB", "IHF", "XBI"],
        "triggers": ["Medicare交渉薬", "FDA人員", "RFK発言"],
    },
    "finance": {
        "label": "金融・規制",
        "tickers": ["XLF", "KBE", "KBWB", "BITB"],
        "triggers": ["SEC方針", "CFPB", "暗号資産規制", "銀行M&A"],
    },
    "infrastructure": {
        "label": "インフラ・建設",
        "tickers": ["PAVE", "IGF", "IFRA"],
        "triggers": ["IIJA執行", "政府契約(USAspending)", "予算継続決議"],
    },
    "trade_china": {
        "label": "貿易・関税・中国",
        "tickers": ["KWEB", "FXI", "CQQQ", "EWJ"],
        "triggers": ["追加関税", "台湾情勢", "デリスキング"],
    },
    "agri": {
        "label": "農業・食料安全保障",
        "tickers": ["MOO", "DBA", "SOIL"],
        "triggers": ["Farm Bill", "穀物輸出規制", "肥料関税"],
    },
    "space": {
        "label": "宇宙・次世代通信",
        "tickers": ["UFO", "ARKX", "WCLD"],
        "triggers": ["NASA予算", "Space Force", "FCC周波数"],
    },
}

def fetch_price_data(tickers, period="1mo"):
    return yf.download(tickers, period=period, auto_adjust=True, progress=False, group_by="ticker")

def _pct(series, i, j):
    try:
        return round((float(series.iloc[i]) / float(series.iloc[j]) - 1) * 100, 2)
    except Exception:
        return None

def _signal(chg_1d, chg_5d, vol_ratio):
    if chg_1d is None:
        return "🟡 中立"
    score = 0
    if chg_1d > 1.0: score += 1
    elif chg_1d < -1.0: score -= 1
    if chg_5d is not None:
        if chg_5d > 3.0: score += 1
        elif chg_5d < -3.0: score -= 1
    if vol_ratio is not None and vol_ratio > 1.5:
        score += 1 if chg_1d > 0 else -1
    if score >= 2: return "🟢 強気"
    elif score <= -2: return "🔴 弱気"
    return "🟡 中立"

def calc_momentum(df, ticker, multi):
    try:
        close = df[ticker]["Close"].dropna() if multi else df["Close"].dropna()
        volume = df[ticker]["Volume"].dropna() if multi else df["Volume"].dropna()
        if len(close) < 2:
            return {"ticker": ticker, "price": None, "chg_1d": None, "chg_5d": None, "chg_20d": None, "vol_ratio": None, "signal": "⚠️ データ不足"}
        price = round(float(close.iloc[-1]), 2)
        chg_1d = _pct(close, -1, -2)
        chg_5d = _pct(close, -1, -6) if len(close) >= 6 else None
        chg_20d = _pct(close, -1, -21) if len(close) >= 21 else None
        vol_ratio = None
        if len(volume) >= 2:
            avg_vol = volume.iloc[-21:-1].mean() if len(volume) >= 21 else volume.iloc[:-1].mean()
            vol_ratio = round(float(volume.iloc[-1] / avg_vol), 2) if avg_vol > 0 else None
        return {"ticker": ticker, "price": price, "chg_1d": chg_1d, "chg_5d": chg_5d, "chg_20d": chg_20d, "vol_ratio": vol_ratio, "signal": _signal(chg_1d, chg_5d, vol_ratio)}
    except Exception as e:
        return {"ticker": ticker, "price": None, "chg_1d": None, "chg_5d": None, "chg_20d": None, "vol_ratio": None, "signal": f"⚠️ {e}"}

def _aggregate_signal(etfs):
    green = sum(1 for e in etfs if "🟢" in (e.get("signal") or ""))
    red   = sum(1 for e in etfs if "🔴" in (e.get("signal") or ""))
    if green > red and green >= len(etfs) / 2: return "🟢 強気"
    if red > green and red   >= len(etfs) / 2: return "🔴 弱気"
    return "🟡 中立"

def build_snapshot(period="1mo"):
    snapshot = {"generated_at": datetime.now().strftime("%Y-%m-%d %H:%M JST"), "themes": {}}
    all_tickers = [t for v in THEMES.values() for t in v["tickers"]]
    print("📡 価格データ取得中...", file=sys.stderr)
    df = fetch_price_data(all_tickers, period=period)
    multi = hasattr(df.columns, "levels") and len(df.columns.levels) > 1
    for key, meta in THEMES.items():
        print(f"  {meta['label']}", file=sys.stderr)
        etfs = [calc_momentum(df, t, multi) for t in meta["tickers"]]
        snapshot["themes"][key] = {
            "label": meta["label"],
            "triggers": meta["triggers"],
            "theme_signal": _aggregate_signal(etfs),
            "etfs": etfs,
        }
    return snapshot

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--days", type=int, default=30)
    args = parser.parse_args()
    period = {5: "5d", 30: "1mo", 90: "3mo"}.get(args.days, "1mo")
    snap = build_snapshot(period=period)
    if args.json:
        print(json.dumps(snap, ensure_ascii=False, indent=2))
    else:
        for k, t in snap["themes"].items():
            print(f"\n{t['label']}  {t['theme_signal']}")
            for e in t["etfs"]:
                print(f"  {e['ticker']:<6} ${e['price']}  1d:{e['chg_1d']}%  5d:{e['chg_5d']}%  sig:{e['signal']}")
