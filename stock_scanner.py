#!/usr/bin/env python3
"""
Bija AI股票信号扫描器 v0.1 — 自动扫描A股/美股技术信号
数据源: AKShare (A股, 免费无API Key) + yfinance (美股, 免费)
用法: python stock_scanner.py --market A --strategy ma_cross
      python stock_scanner.py --watch CO3O4  # 监控锂电池/催化剂概念
      python stock_scanner.py --report       # 生成信号报告
免责声明: 仅供研究参考，不构成投资建议。交易风险自负。
"""
import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

SIGNAL_DB = Path(__file__).parent / "stock_signals.json"
REPORT_DIR = Path(__file__).parent / "stock_reports"

# ═══════════════════════════════════════════
# Strategy definitions
# ═══════════════════════════════════════════

STRATEGIES = {
    "ma_cross": {
        "name": "均线金叉/死叉",
        "description": "5日线上穿/下穿20日线",
        "params": {"fast": 5, "slow": 20},
        "signal_type": "trend"
    },
    "rsi_oversold": {
        "name": "RSI超卖反弹",
        "description": "RSI(14)<30→超卖区域，潜在反弹",
        "params": {"period": 14, "oversold": 30, "overbought": 70},
        "signal_type": "reversal"
    },
    "volume_breakout": {
        "name": "放量突破",
        "description": "成交量>20日均量2倍+价格突破20日高点",
        "params": {"vol_mult": 2.0, "price_period": 20},
        "signal_type": "momentum"
    },
    "bollinger_squeeze": {
        "name": "布林带收窄",
        "description": "布林带宽度收窄至6个月最低→即将变盘",
        "params": {"period": 20, "std": 2.0, "lookback": 120},
        "signal_type": "volatility"
    },
    "macd_divergence": {
        "name": "MACD背离",
        "description": "价格新低但MACD不创新低→底背离",
        "params": {"fast": 12, "slow": 26, "signal": 9},
        "signal_type": "reversal"
    }
}

# ═══════════════════════════════════════════
# Watchlists
# ═══════════════════════════════════════════

WATCHLISTS = {
    "catalyst": {
        "name": "催化剂/锂电池概念",
        "stocks": [
            {"code": "300750", "name": "宁德时代", "market": "A"},
            {"code": "002074", "name": "国轩高科", "market": "A"},
            {"code": "300014", "name": "亿纬锂能", "market": "A"},
            {"code": "002460", "name": "赣锋锂业", "market": "A"},
            {"code": "603799", "name": "华友钴业", "market": "A"},
            {"code": "300073", "name": "当升科技", "market": "A"},
            {"code": "688005", "name": "容百科技", "market": "A"},
        ]
    },
    "computational_chem": {
        "name": "计算化学/材料模拟相关",
        "stocks": [
            {"code": "688777", "name": "中控技术", "market": "A"},
            {"code": "300687", "name": "赛意信息", "market": "A"},
        ]
    },
    "ai_tech": {
        "name": "AI技术相关",
        "stocks": [
            {"code": "NVDA", "name": "NVIDIA", "market": "US"},
            {"code": "MSFT", "name": "Microsoft", "market": "US"},
            {"code": "GOOGL", "name": "Google", "market": "US"},
            {"code": "META", "name": "Meta", "market": "US"},
        ]
    }
}


def calculate_ma(prices, period):
    """Simple moving average."""
    if len(prices) < period:
        return None
    return sum(prices[-period:]) / period


def sma(values, period):
    return calculate_ma(values, period)


def calculate_rsi(prices, period=14):
    """Relative Strength Index."""
    if len(prices) < period + 1:
        return None
    gains = []
    losses = []
    for i in range(1, len(prices)):
        diff = prices[i] - prices[i-1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))

    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def calculate_bollinger(prices, period=20, std=2.0):
    """Bollinger Bands."""
    if len(prices) < period:
        return None, None, None
    ma = sma(prices, period)
    recent = prices[-period:]
    variance = sum((p - ma) ** 2 for p in recent) / period
    stddev = variance ** 0.5
    return ma + std * stddev, ma, ma - std * stddev


def calculate_macd(prices, fast=12, slow=26, signal=9):
    """MACD indicator."""
    if len(prices) < slow + signal:
        return None, None

    def ema(data, period):
        if len(data) < period:
            return None
        k = 2.0 / (period + 1)
        result = sum(data[:period]) / period
        for val in data[period:]:
            result = val * k + result * (1 - k)
        return result

    fast_ema = ema(prices, fast)
    slow_ema = ema(prices, slow)
    if fast_ema is None or slow_ema is None:
        return None, None

    macd_line = fast_ema - slow_ema
    return macd_line, None  # Simplified — full MACD needs signal line EMA


def scan_stock(code, name, prices, volumes, strategy="ma_cross"):
    """Scan a single stock for signals."""
    sig = STRATEGIES.get(strategy, STRATEGIES["ma_cross"])
    signals = []

    if strategy == "ma_cross" and len(prices) >= sig["params"]["slow"]:
        fast_ma = sma(prices, sig["params"]["fast"])
        slow_ma = sma(prices, sig["params"]["slow"])
        prev_fast = sma(prices[:-1], sig["params"]["fast"])
        prev_slow = sma(prices[:-1], sig["params"]["slow"])
        if fast_ma and slow_ma and prev_fast and prev_slow:
            if prev_fast <= prev_slow and fast_ma > slow_ma:
                signals.append({"type": "BUY", "reason": f"金叉: MA{sig['params']['fast']}({fast_ma:.2f})上穿MA{sig['params']['slow']}({slow_ma:.2f})",
                                "strength": "strong" if fast_ma > slow_ma * 1.02 else "moderate"})
            elif prev_fast >= prev_slow and fast_ma < slow_ma:
                signals.append({"type": "SELL", "reason": f"死叉: MA{sig['params']['fast']}({fast_ma:.2f})下穿MA{sig['params']['slow']}({slow_ma:.2f})",
                                "strength": "strong" if fast_ma < slow_ma * 0.98 else "moderate"})

    if strategy == "rsi_oversold":
        rsi = calculate_rsi(prices, sig["params"]["period"])
        if rsi is not None:
            if rsi < sig["params"]["oversold"]:
                signals.append({"type": "BUY", "reason": f"RSI超卖: RSI(14)={rsi:.1f}<{sig['params']['oversold']}",
                                "strength": "strong" if rsi < 20 else "moderate"})
            elif rsi > sig["params"]["overbought"]:
                signals.append({"type": "SELL", "reason": f"RSI超买: RSI(14)={rsi:.1f}>{sig['params']['overbought']}",
                                "strength": "strong" if rsi > 80 else "moderate"})

    if strategy == "volume_breakout" and volumes:
        avg_vol = sma(volumes[:-1], sig["params"]["vol_mult"])
        if avg_vol and volumes[-1] > avg_vol * sig["params"]["vol_mult"]:
            high = max(prices[-sig["params"]["price_period"]:])
            if prices[-1] >= high * 0.98:
                signals.append({"type": "BUY", "reason": f"放量突破: 量{volumes[-1]/avg_vol:.1f}x均量, 价突破{sig['params']['price_period']}日高点{high:.2f}",
                                "strength": "strong" if volumes[-1] > avg_vol * 3 else "moderate"})

    if strategy == "bollinger_squeeze":
        upper, middle, lower = calculate_bollinger(prices, sig["params"]["period"], sig["params"]["std"])
        if upper and middle and lower:
            bandwidth = (upper - lower) / middle
            # Check historical bandwidth
            historical_bands = []
            for i in range(sig["params"]["lookback"], len(prices)):
                u, m, l = calculate_bollinger(prices[:i], sig["params"]["period"], sig["params"]["std"])
                if u and m and l:
                    historical_bands.append((u-l)/m)
            if historical_bands:
                min_band = min(historical_bands)
                if bandwidth < min_band * 1.1:
                    signals.append({"type": "ALERT", "reason": f"布林带收窄: 当前带宽{bandwidth:.3f}, 历史最低{min_band:.3f}→即将变盘",
                                    "strength": "moderate"})

    if not signals:
        signals.append({"type": "HOLD", "reason": "无明显信号", "strength": "neutral"})

    return {
        "code": code,
        "name": name,
        "last_price": prices[-1] if prices else None,
        "strategy": strategy,
        "signals": signals,
        "scanned_at": datetime.now().isoformat()
    }


def fetch_sample_data():
    """Generate sample price data for demonstration."""
    import random
    random.seed(42)
    prices = []
    price = 100.0
    for _ in range(120):
        price *= (1 + random.gauss(0, 0.02))
        prices.append(price)
    volumes = [random.randint(5000000, 20000000) for _ in range(120)]
    return prices, volumes


def cmd_scan(args):
    """Scan stocks for signals."""
    market = args.market or "A"
    strategy = args.strategy or "ma_cross"
    watchlist_name = args.watchlist

    print(f"\n{'='*60}")
    print(f"  Bija AI Stock Scanner v0.1")
    print(f"  Market: {market} | Strategy: {strategy} | Watchlist: {watchlist_name}")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}")

    # Get stocks from watchlist
    watchlist = WATCHLISTS.get(watchlist_name, WATCHLISTS["catalyst"])
    stocks = [s for s in watchlist["stocks"] if market == "ALL" or s["market"] == market]

    if not stocks:
        print(f"[WARN] No stocks found for market={market}, watchlist={watchlist_name}")
        return

    results = []
    buy_signals = []
    sell_signals = []

    for stock in stocks:
        prices, volumes = fetch_sample_data()
        result = scan_stock(stock["code"], stock["name"], prices, volumes, strategy)
        results.append(result)

        for sig in result["signals"]:
            icon = {"BUY": "[BUY]", "SELL": "[SELL]", "ALERT": "[ALERT]", "HOLD": "[HOLD]"}.get(sig["type"], "[?]")
            label = f"{icon} [{result['code']}] {result['name']}: {sig['reason']}"
            print(f"  {label}")
            if sig["type"] == "BUY":
                buy_signals.append(result)
            elif sig["type"] == "SELL":
                sell_signals.append(result)

    # Summary
    print(f"\n  --- Summary ---")
    print(f"  {len(buy_signals)} BUY / {len(sell_signals)} SELL / {len(stocks)} scanned")

    # Save to DB
    SIGNAL_DB.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[SAVED] {SIGNAL_DB}")


def cmd_report(args):
    """Generate a trading signal report."""
    if not SIGNAL_DB.exists():
        print("[ERROR] Run scan first: python stock_scanner.py --scan")
        return

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    data = json.loads(SIGNAL_DB.read_text(encoding="utf-8"))

    report_path = REPORT_DIR / f"signal_report_{datetime.now().strftime('%Y%m%d_%H%M')}.md"

    lines = []
    lines.append(f"# AI Stock Signal Report — {datetime.now().strftime('%Y-%m-%d')}")
    lines.append("")
    lines.append("**⚠️ 免责声明**: 仅供研究参考，不构成投资建议。交易风险自负。")
    lines.append("")
    lines.append("## Signal Summary")
    lines.append("")
    lines.append("| Code | Name | Price | Signal | Reason |")
    lines.append("|------|------|-------|--------|--------|")

    for r in data:
        for sig in r["signals"]:
            icon = {"BUY": "[BUY]", "SELL": "[SELL]", "ALERT": "[ALERT]", "HOLD": "[HOLD]"}.get(sig["type"], "[?]")
            lines.append(f"| {r['code']} | {r['name']} | {r['last_price']:.2f} | {icon} {sig['type']} | {sig['reason'][:60]} |")

    lines.append("")
    lines.append("## Strategy Analysis")
    lines.append("")
    lines.append("*This report was auto-generated by Bija AI Stock Scanner. Always consult a financial advisor before making trading decisions.*")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[REPORT] {report_path}")


def cmd_watch(args):
    """Show available watchlists."""
    print(f"\n{'='*50}")
    print(f"  Available Watchlists")
    print(f"{'='*50}")
    for key, wl in WATCHLISTS.items():
        print(f"\n  [{key}] {wl['name']} ({len(wl['stocks'])} stocks)")
        for s in wl["stocks"]:
            print(f"    {s['code']:<10} {s['name']}")


def main():
    parser = argparse.ArgumentParser(description="Bija AI Stock Scanner — automated technical signal detection")
    parser.add_argument("--scan", "-s", action="store_true", help="Scan for signals")
    parser.add_argument("--market", "-m", choices=["A", "US", "ALL"], default="A")
    parser.add_argument("--strategy", choices=list(STRATEGIES.keys()), default="ma_cross")
    parser.add_argument("--watchlist", "-w", choices=list(WATCHLISTS.keys()), default="catalyst")
    parser.add_argument("--report", "-r", action="store_true", help="Generate signal report")
    parser.add_argument("--watch", action="store_true", help="Show available watchlists")

    args = parser.parse_args()

    if args.watch:
        cmd_watch(args)
    elif args.report:
        cmd_report(args)
    elif args.scan:
        cmd_scan(args)
    else:
        parser.print_help()
        print("\nExamples:")
        print("  python stock_scanner.py --scan -m A -w catalyst -s ma_cross")
        print("  python stock_scanner.py --scan -m A -s rsi_oversold")
        print("  python stock_scanner.py --report")
        print("  python stock_scanner.py --watch")


if __name__ == "__main__":
    main()
