#!/usr/bin/env python3
# Local CSV Data Test

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from datetime import date, datetime, UTC
import pandas as pd
from pstds.temporal.context import TemporalContext
from pstds.data.adapters.local_csv_adapter import LocalCSVAdapter

def create_sample_data():
    """Create sample CSV data for testing"""
    import os
    import numpy as np
    os.makedirs('./data/raw/prices', exist_ok=True)

    # Create sample AAPL data
    dates = pd.date_range(start='2025-01-01', end='2026-02-21', freq='D')
    np.random.seed(42)

    aapl_data = {
        'date': dates,
        'open': 150 + np.random.normal(0, 2, len(dates)).cumsum(),
        'high': None,
        'low': None,
        'close': None,
        'volume': np.random.randint(1000000, 5000000, len(dates)),
        'adj_close': None
    }

    # Calculate high, low, close
    for i in range(len(dates)):
        open_price = aapl_data['open'][i]
        daily_change = np.random.normal(0, 1)
        close_price = open_price + daily_change
        high_price = max(open_price, close_price) + abs(np.random.normal(0, 0.5))
        low_price = min(open_price, close_price) - abs(np.random.normal(0, 0.5))

        aapl_data['high'][i] = high_price
        aapl_data['low'][i] = low_price
        aapl_data['close'][i] = close_price
        aapl_data['adj_close'][i] = close_price

    df = pd.DataFrame(aapl_data)
    df.to_csv('./data/raw/prices/AAPL.csv', index=False)
    print(f"Created sample AAPL data: {len(df)} records")
    return df

def test_local_csv_adapter():
    """Test Local CSV Adapter"""
    print("\n=== Testing Local CSV Adapter ===")

    # Create sample data first
    try:
        import numpy as np
        sample_df = create_sample_data()
    except ImportError:
        print("NumPy not available, creating simple data")
        # Create simple data without NumPy
        dates = pd.date_range(start='2025-01-01', end='2026-02-21', freq='D')
        simple_data = {
            'date': dates,
            'open': [150.0 + i * 0.1 for i in range(len(dates))],
            'high': [151.0 + i * 0.1 for i in range(len(dates))],
            'low': [149.0 + i * 0.1 for i in range(len(dates))],
            'close': [150.5 + i * 0.1 for i in range(len(dates))],
            'volume': [1000000 + i * 1000 for i in range(len(dates))],
            'adj_close': [150.5 + i * 0.1 for i in range(len(dates))]
        }
        sample_df = pd.DataFrame(simple_data)
        sample_df.to_csv('./data/raw/prices/AAPL.csv', index=False)
        print(f"Created simple AAPL data: {len(sample_df)} records")

    # Initialize adapter
    adapter = LocalCSVAdapter()

    # Create TemporalContext for backtest
    ctx = TemporalContext.for_backtest(date(2026, 2, 15))

    print(f"\nTesting with analysis_date: {ctx.analysis_date}")

    # Test OHLCV data retrieval
    try:
        df = adapter.get_ohlcv(
            symbol="AAPL",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 2, 21),
            interval="1d",
            ctx=ctx
        )

        if not df.empty:
            print(f"SUCCESS: Got {len(df)} OHLCV records")
            print(f"Date range: {df['date'].min()} to {df['date'].max()}")
            print(f"Columns: {list(df.columns)}")
            print(f"\nLatest 5 records:")
            print(df.tail().to_string(index=False))
        else:
            print("No data retrieved")

    except Exception as e:
        print(f"ERROR: {e}")

    # Test fundamentals (should return empty data)
    try:
        fundamentals = adapter.get_fundamentals(
            symbol="AAPL",
            as_of_date=date(2026, 2, 15),
            ctx=ctx
        )
        print(f"\nFundamentals data:")
        for key, value in fundamentals.items():
            print(f"  {key}: {value}")

    except Exception as e:
        print(f"ERROR getting fundamentals: {e}")

    # Test news (should return empty)
    try:
        news_items = adapter.get_news(
            symbol="AAPL",
            days_back=7,
            ctx=ctx
        )
        print(f"\nNews items: {len(news_items)}")

    except Exception as e:
        print(f"ERROR getting news: {e}")

    # Test adapter capabilities
    try:
        available = adapter.is_available("AAPL")
        print(f"\nAAPL available: {available}")

        market_type = adapter.get_market_type("AAPL")
        print(f"AAPL market type: {market_type}")

    except Exception as e:
        print(f"ERROR testing capabilities: {e}")

if __name__ == "__main__":
    print("Testing Local CSV Data Adapter")
    print(f"Current time: {datetime.now(UTC)}")

    test_local_csv_adapter()
    print("\nLocal CSV test completed!")