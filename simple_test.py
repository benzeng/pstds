#!/usr/bin/env python3
# Simple PSTDS Test

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from datetime import date, datetime, UTC
import pandas as pd
from pstds.temporal.context import TemporalContext

def create_simple_csv():
    """Create simple CSV data for testing"""
    import os
    os.makedirs('./data/raw/prices', exist_ok=True)

    # Create simple data
    data = {
        'date': [
            '2026-01-01', '2026-01-02', '2026-01-03', '2026-01-04', '2026-01-05',
            '2026-01-06', '2026-01-07', '2026-01-08', '2026-01-09', '2026-01-10'
        ],
        'open': [150.0, 151.0, 152.0, 151.5, 153.0, 152.5, 154.0, 153.5, 155.0, 154.5],
        'high': [152.0, 153.0, 154.0, 153.5, 155.0, 154.5, 156.0, 155.5, 157.0, 156.5],
        'low': [149.0, 150.0, 151.0, 150.5, 152.0, 151.5, 153.0, 152.5, 154.0, 153.5],
        'close': [151.0, 152.0, 151.5, 153.0, 152.5, 154.0, 153.5, 155.0, 154.5, 156.0],
        'volume': [1000000, 1100000, 950000, 1200000, 1050000, 1150000, 980000, 1250000, 1100000, 1300000],
        'adj_close': [151.0, 152.0, 151.5, 153.0, 152.5, 154.0, 153.5, 155.0, 154.5, 156.0]
    }

    df = pd.DataFrame(data)
    df.to_csv('./data/raw/prices/AAPL.csv', index=False)
    print(f"Created AAPL.csv with {len(df)} records")
    return df

def test_temporal_context():
    """Test TemporalContext"""
    print("\n=== Testing TemporalContext ===")

    # Test LIVE mode
    ctx_live = TemporalContext.for_live(date(2026, 2, 21))
    print(f"LIVE context: analysis_date={ctx_live.analysis_date}, mode={ctx_live.mode}")
    print(f"Prompt prefix: {ctx_live.get_prompt_prefix()[:100]}...")

    # Test BACKTEST mode
    ctx_backtest = TemporalContext.for_backtest(date(2026, 2, 15))
    print(f"BACKTEST context: analysis_date={ctx_backtest.analysis_date}, mode={ctx_backtest.mode}")

    return ctx_backtest

def test_local_adapter(ctx):
    """Test Local CSV Adapter"""
    print("\n=== Testing Local CSV Adapter ===")

    try:
        from pstds.data.adapters.local_csv_adapter import LocalCSVAdapter
        adapter = LocalCSVAdapter()

        # Test OHLCV
        print("\nTesting OHLCV retrieval...")
        df = adapter.get_ohlcv(
            symbol="AAPL",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 10),
            interval="1d",
            ctx=ctx
        )

        if not df.empty:
            print(f"SUCCESS: Got {len(df)} records")
            print(f"Columns: {list(df.columns)}")
            print(f"\nData preview:")
            print(df.to_string(index=False))
        else:
            print("No data retrieved")

        # Test fundamentals
        print("\nTesting fundamentals...")
        fundamentals = adapter.get_fundamentals(
            symbol="AAPL",
            as_of_date=date(2026, 2, 15),
            ctx=ctx
        )
        print(f"Fundamentals: {fundamentals}")

        # Test news
        print("\nTesting news...")
        news_items = adapter.get_news(
            symbol="AAPL",
            days_back=7,
            ctx=ctx
        )
        print(f"News items: {len(news_items)}")

        # Test capabilities
        print("\nTesting adapter capabilities...")
        available = adapter.is_available("AAPL")
        print(f"AAPL available: {available}")

        market_type = adapter.get_market_type("AAPL")
        print(f"AAPL market type: {market_type}")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

def test_data_router():
    """Test Data Router"""
    print("\n=== Testing Data Router ===")

    try:
        from pstds.data.router import DataRouter, MarketRouter

        # Test market routing
        test_symbols = ["AAPL", "000001", "0700.HK"]

        for symbol in test_symbols:
            try:
                market_type = MarketRouter.route(symbol)
                print(f"{symbol} -> {market_type}")
            except Exception as e:
                print(f"{symbol} -> ERROR: {e}")

        # Test data router
        router = DataRouter()
        for symbol in test_symbols:
            try:
                market_type = router.get_market_type(symbol)
                adapter = router.get_adapter(symbol)
                print(f"{symbol}: {market_type} -> {adapter.name}")
            except Exception as e:
                print(f"{symbol} -> ERROR: {e}")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Simple PSTDS Test")
    print(f"Current time: {datetime.now(UTC)}")

    # Create test data
    create_simple_csv()

    # Test TemporalContext
    ctx = test_temporal_context()

    # Test Local CSV Adapter
    test_local_adapter(ctx)

    # Test Data Router
    test_data_router()

    print("\nAll tests completed!")