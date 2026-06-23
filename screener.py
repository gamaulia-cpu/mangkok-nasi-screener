"""
Mangkuk Nasi (Wyckoff Accumulation) Screener — IDX Stocks
=========================================================
Mendeteksi 4 komponen akumulasi Wyckoff fase A/B/C:
  - Bowl Formation (25pt)
  - Trend Efficiency (10pt)
  - Vol Contraction (15pt)
  - Spring / Volume Climax (15pt)
Skor maksimal 65 — sinyal hanya jika 65/65.
"""

import argparse
import csv
import os
import sys
import time
from datetime import datetime, timedelta

import yfinance as yf

# ── Konfigurasi ────────────────────────────────────────────────
DEFAULT_LOOKBACK = 60   # minimal 60 hari untuk data harga
DEFAULT_VOL_MA = 20
DEFAULT_RECENT_VOL = 10
DEFAULT_SC_MULT = 2.5
DEFAULT_ST_CONTRACT = 0.7
REQ_DELAY = 1.5        # delay antar request (detik) untuk hindari rate limit
MAX_RETRIES = 3

# ── Komponen Scoring ───────────────────────────────────────────
SCORE_BOWL = 25
SCORE_TREND = 10
SCORE_VOL_CONTRACT = 15
SCORE_SPRING = 15
SCORE_MAX = SCORE_BOWL + SCORE_TREND + SCORE_VOL_CONTRACT + SCORE_SPRING  # 65


def fetch_data(symbol: str, period: str = "6mo") -> tuple | None:
    """Ambil data harga & volume dari Yahoo Finance.

    Returns:
        (close_prices, high_prices, low_prices, volumes) sebagai list.
    """
    for attempt in range(MAX_RETRIES):
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period)

            if df.empty or len(df) < DEFAULT_LOOKBACK:
                return None

            closes = df["Close"].tolist()
            highs = df["High"].tolist()
            lows = df["Low"].tolist()
            volumes = df["Volume"].tolist()

            return closes, highs, lows, volumes
        except yf.exceptions.YFRateLimitError:
            wait = REQ_DELAY * (attempt + 1) * 3
            print(f"rate limited, menunggu {wait:.0f}s...", end=" ", flush=True)
            time.sleep(wait)
        except Exception:
            return None
    return None


def calc_components(closes, highs, lows, volumes):
    """Hitung 4 komponen dan score untuk satu saham.

    Returns:
        dict { bowl, trend_ok, vol_contract, spring, score, fase }
    """
    # ── Bowl Formation ──────────────────────────────────────────
    lookback = 40
    lookback60 = 60

    highest_40 = max(highs[-lookback:])
    lowest_60 = min(lows[-lookback60:])
    range_60 = highest_40 - lowest_60
    range_pct = (range_60 / lowest_60) * 100 if lowest_60 > 0 else 0

    current_close = closes[-1]
    price_pos = ((current_close - lowest_60) / range_60) * 100 if range_60 > 0 else 50

    swg_high = max(highs[-5:])
    swg_low = min(lows[-5:])
    swg_rng = ((swg_high - swg_low) / swg_low) * 100 if swg_low > 0 else 0

    bowl = (15 < range_pct < 60) and (swg_rng < 15) and (30 < price_pos < 80)

    # ── Trend Efficiency ────────────────────────────────────────
    eff_len = 20
    price_eff = ((closes[-1] / closes[-(eff_len + 1)]) - 1) * 100 if closes[-(eff_len + 1)] > 0 else 0
    trend_ok = -30 < price_eff < 15

    # ── Vol Contraction ─────────────────────────────────────────
    vol_ma = sum(volumes[-DEFAULT_VOL_MA:]) / DEFAULT_VOL_MA if DEFAULT_VOL_MA > 0 else 1
    recent_vol_avg = sum(volumes[-DEFAULT_RECENT_VOL:]) / DEFAULT_RECENT_VOL
    vol_contract = (vol_ma > 0) and (recent_vol_avg < vol_ma * DEFAULT_ST_CONTRACT)

    # ── Spring / Vol Climax ─────────────────────────────────────
    sc_high = False
    for i in range(-20, 0):
        window = volumes[i - DEFAULT_VOL_MA:i]
        if len(window) == DEFAULT_VOL_MA:
            vol_ma_i = sum(window) / DEFAULT_VOL_MA
            if volumes[i] > vol_ma_i * DEFAULT_SC_MULT:
                sc_high = True
                break

    # ── Scoring ─────────────────────────────────────────────────
    score = 0
    score += SCORE_BOWL if bowl else 0
    score += SCORE_TREND if trend_ok else 0
    score += SCORE_VOL_CONTRACT if vol_contract else 0
    score += SCORE_SPRING if sc_high else 0

    # ── Fase ────────────────────────────────────────────────────
    phase_a = sc_high and price_eff < 0
    phase_b = bowl and trend_ok and not phase_a
    phase_c = vol_contract and bowl and trend_ok

    if phase_a:
        fase = "A — Spring / Vol Climax"
    elif phase_b:
        fase = "B — Otomatis Rally / Bowl"
    elif phase_c:
        fase = "C — Kontraksi / Test"
    else:
        fase = "—"

    return {
        "bowl": bowl,
        "trend_ok": trend_ok,
        "vol_contract": vol_contract,
        "spring": sc_high,
        "score": score,
        "price_eff": round(price_eff, 1),
        "range_pct": round(range_pct, 1),
        "price_pos": round(price_pos, 1),
        "swg_rng": round(swg_rng, 1),
        "fase": fase,
    }


def screen_stock(symbol: str) -> dict | None:
    """Screen satu saham, return dict hasil atau None jika gagal."""
    data = fetch_data(symbol)
    if data is None:
        return None

    closes, highs, lows, volumes = data
    comp = calc_components(closes, highs, lows, volumes)
    comp["symbol"] = symbol
    comp["close"] = round(closes[-1], 2)
    comp["volume"] = int(volumes[-1])
    return comp


def load_stock_list(path: str) -> list[str]:
    """Load daftar saham dari file (1 symbol per baris, # untuk komentar)."""
    symbols = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                symbols.append(line)
    return symbols


def print_report(results: list[dict], perfect_only: bool = True, csv_output: str = None):
    """Cetak hasil screener ke terminal dan/atau CSV."""
    if perfect_only:
        filtered = [r for r in results if r and r["score"] == SCORE_MAX]
    else:
        filtered = [r for r in results if r]

    filtered.sort(key=lambda x: x["score"], reverse=True)

    # ── Console ─────────────────────────────────────────────────
    if not filtered:
        print("Tidak ada sinyal 65/65 ditemukan.\n")
        return

    print(f"{'Symbol':<10} {'Close':>8} {'Vol':>10} {'Score':>6} {'Fase':<30} {'Bowl':>6} {'Trend':>6} {'V.Contr':>8} {'Spring':>8}")
    print("-" * 100)
    for r in filtered:
        print(
            f"{r['symbol']:<10} {r['close']:>8.0f} {r['volume']:>10,} {r['score']:>6} "
            f"{r['fase']:<30} {str(r['bowl']):>6} {str(r['trend_ok']):>6} "
            f"{str(r['vol_contract']):>8} {str(r['spring']):>8}"
        )
    print()

    # ── Detail komponen ─────────────────────────────────────────
    print("Detail Komponen (65/65):")
    print("-" * 60)
    for r in filtered:
        print(f"  {r['symbol']} — Score {r['score']}/65 | {r['fase']}")
        print(f"    Bowl:        {r['bowl']}  (range={r['range_pct']}%, pos={r['price_pos']}%, swg={r['swg_rng']}%)")
        print(f"    Trend Eff:   {r['trend_ok']}  (return 20b={r['price_eff']}%)")
        print(f"    Vol Contract:{r['vol_contract']}")
        print(f"    Spring:      {r['spring']}")
        print()

    # ── CSV ─────────────────────────────────────────────────────
    if csv_output:
        fields = [
            "symbol", "close", "volume", "score", "fase",
            "bowl", "trend_ok", "vol_contract", "spring",
            "range_pct", "price_pos", "swg_rng", "price_eff",
        ]
        with open(csv_output, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(filtered)
        print(f"CSV disimpan: {csv_output}")


def main():
    parser = argparse.ArgumentParser(
        description="Mangkuk Nasi Wyckoff Screener — IDX Stocks"
    )
    parser.add_argument(
        "stocks_file",
        nargs="?",
        default="stocks.txt",
        help="Path ke file daftar saham (default: stocks.txt)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Tampilkan semua skor, bukan hanya 65/65",
    )
    parser.add_argument(
        "--csv",
        type=str,
        default=None,
        help="Simpan hasil ke file CSV",
    )
    parser.add_argument(
        "--single",
        type=str,
        default=None,
        help="Screen satu saham saja (contoh: AGII.JK)",
    )
    args = parser.parse_args()

    if args.single:
        symbols = [args.single]
    else:
        if not os.path.exists(args.stocks_file):
            print(f"File tidak ditemukan: {args.stocks_file}")
            sys.exit(1)
        symbols = load_stock_list(args.stocks_file)

    print(f"\nMangkuk Nasi Screener — Wyckoff Accumulation (max score: {SCORE_MAX}/65)")
    print(f"Memindai {len(symbols)} saham...\n")

    results = []
    for i, sym in enumerate(symbols, 1):
        print(f"  [{i}/{len(symbols)}] {sym}...", end=" ", flush=True)
        result = screen_stock(sym)
        if result:
            results.append(result)
            print(f"score={result['score']}/65")
        else:
            print("gagal/data tidak cukup")
        time.sleep(REQ_DELAY)

    print()
    print_report(results, perfect_only=not args.all, csv_output=args.csv)


if __name__ == "__main__":
    main()
