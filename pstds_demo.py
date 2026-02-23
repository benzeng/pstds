#!/usr/bin/env python3
# PSTDS - Personal Stock Trading Decision System Demo

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from datetime import date, datetime, UTC
import pandas as pd
from pstds.temporal.context import TemporalContext

def create_demo_data():
    """Create demo data"""
    import os
    os.makedirs('./data/raw/prices', exist_ok=True)

    # Create AAPL demo data
    dates = pd.date_range(start='2026-01-01', end='2026-02-21', freq='D')
    aapl_data = {
        'date': dates,
        'open': [150.0 + i * 0.5 for i in range(len(dates))],
        'high': [152.0 + i * 0.5 for i in range(len(dates))],
        'low': [148.0 + i * 0.5 for i in range(len(dates))],
        'close': [151.0 + i * 0.5 for i in range(len(dates))],
        'volume': [1000000 + i * 10000 for i in range(len(dates))],
        'adj_close': [151.0 + i * 0.5 for i in range(len(dates))]
    }
    pd.DataFrame(aapl_data).to_csv('./data/raw/prices/AAPL.csv', index=False)
    print(f"Created AAPL demo data: {len(dates)} days")

def demo_temporal_isolation():
    """Demonstrate temporal isolation"""
    print("\n" + "="*60)
    print("TEMPORAL ISOLATION DEMO")
    print("="*60)

    # Create backtest context for Feb 15, 2026
    ctx = TemporalContext.for_backtest(date(2026, 2, 15))

    print(f"Analysis Date: {ctx.analysis_date}")
    print(f"Mode: {ctx.mode}")
    print(f"\nTime Isolation Prompt:")
    print(ctx.get_prompt_prefix())

    # Demonstrate time guard
    from pstds.temporal.guard import TemporalGuard

    print(f"\nTesting time validation:")
    try:
        TemporalGuard.validate_timestamp(date(2026, 2, 10), ctx, "demo")
        print("Feb 10, 2026: VALID (before analysis date)")
    except Exception as e:
        print(f"Feb 10, 2026: {e}")

    try:
        TemporalGuard.validate_timestamp(date(2026, 2, 20), ctx, "demo")
        print("Feb 20, 2026: Should have failed!")
    except Exception as e:
        print(f"Feb 20, 2026: BLOCKED (after analysis date)")

def demo_data_sources():
    """Demonstrate data sources"""
    print("\n" + "="*60)
    print("DATA SOURCES DEMO")
    print("="*60)

    ctx = TemporalContext.for_backtest(date(2026, 2, 15))

    # Local CSV Adapter
    print("\n1. LOCAL CSV ADAPTER (for backtesting)")
    print("-" * 40)

    from pstds.data.adapters.local_csv_adapter import LocalCSVAdapter
    adapter = LocalCSVAdapter()

    df = adapter.get_ohlcv("AAPL", date(2026, 2, 1), date(2026, 2, 15), "1d", ctx)
    print(f"AAPL OHLCV Data: {len(df)} records")
    print(f"Latest close: ${df['close'].iloc[-1]:.2f}")
    print(f"Volume: {df['volume'].iloc[-1]:,}")
    print(f"Data source: {df['data_source'].iloc[0]}")

    # Market routing
    print("\n2. MARKET ROUTING")
    print("-" * 40)

    from pstds.data.router import MarketRouter

    symbols = ["AAPL", "000001", "0700.HK", "TSLA"]
    for symbol in symbols:
        market = MarketRouter.route(symbol)
        print(f"{symbol:>8} -> {market} market")

def demo_data_quality():
    """Demonstrate data quality system"""
    print("\n" + "="*60)
    print("DATA QUALITY SYSTEM DEMO")
    print("="*60)

    from pstds.data.fallback import DataQualityReport

    # Create quality report
    report = DataQualityReport(score=100.0)
    print(f"Initial Quality Score: {report.score}/100")

    # Simulate some issues
    report.add_fallback("yfinance")
    print(f"After API fallback: {report.score}/100")

    report.add_missing_field("pe_ratio")
    print(f"After missing field: {report.score}/100")

    report.add_anomaly("Unusual price spike detected")
    print(f"After anomaly alert: {report.score}/100")

    print(f"\nFinal Report:")
    for key, value in report.to_dict().items():
        if key != "generated_at":
            print(f"  {key}: {value}")

def demo_adapter_comparison():
    """Compare different adapters"""
    print("\n" + "="*60)
    print("ADAPTER COMPARISON DEMO")
    print("="*60)

    symbols = ["AAPL", "000001", "0700.HK"]

    for symbol in symbols:
        print(f"\n{symbol}:")
        print("-" * 20)

        # Test YFinance adapter
        try:
            from pstds.data.adapters.yfinance_adapter import YFinanceAdapter
            yf_adapter = YFinanceAdapter()
            yf_market = yf_adapter.get_market_type(symbol)
            print(f"  YFinance: {yf_market} market")
        except Exception as e:
            print(f"  YFinance: Error - {e}")

        # Test AKShare adapter
        try:
            from pstds.data.adapters.akshare_adapter import AKShareAdapter
            ak_adapter = AKShareAdapter()
            ak_market = ak_adapter.get_market_type(symbol)
            print(f"  AKShare: {ak_market} market")
        except Exception as e:
            print(f"  AKShare: Error - {e}")

        # Test Local CSV adapter
        try:
            from pstds.data.adapters.local_csv_adapter import LocalCSVAdapter
            local_adapter = LocalCSVAdapter()
            available = local_adapter.is_available(symbol)
            local_market = local_adapter.get_market_type(symbol)
            print(f"  Local CSV: Available={available}, {local_market} market")
        except Exception as e:
            print(f"  Local CSV: Error - {e}")

def main():
    """Main demo function"""
    print("PSTDS - Personal Stock Trading Decision System")
    print("Data System Demonstration")
    print("="*60)
    print(f"Demo Time: {datetime.now(UTC)}")

    # Create demo data
    create_demo_data()

    # Run demos
    demo_temporal_isolation()
    demo_data_sources()
    demo_adapter_comparison()
    demo_data_quality()

    print("\n" + "="*60)
    print("DEMO SUMMARY")
    print("="*60)
    print("Temporal isolation prevents future data leakage")
    print("Multiple data adapters support different markets")
    print("Local CSV adapter perfect for backtesting")
    print("Market routing automatically detects stock types")
    print("Data quality system tracks reliability")
    print("YFinance: US stocks (rate limited in live demo)")
    print("AKShare: CN_A and HK stocks")
    print("Fallback system ensures data availability")
    print("\nThe PSTDS data system is ready for production use!")

if __name__ == "__main__":
    main()