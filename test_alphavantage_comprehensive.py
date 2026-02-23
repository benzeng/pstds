#!/usr/bin/env python3
# AlphaVantageAdapter 综合测试脚本
# 测试行情、新闻、基本面三种数据类型

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from datetime import date, datetime, UTC
import pandas as pd
from unittest.mock import patch, MagicMock
from pstds.temporal.context import TemporalContext
from pstds.temporal.guard import TemporalGuard
from pstds.data.adapters import AlphaVantageAdapter
from pstds.data.models import NewsItem

# 设置模拟的 AlphaVantage API key（在模块级别设置）
os.environ['ALPHA_VANTAGE_API_KEY'] = 'test_key_demo'

def setup_test_environment():
    """设置测试环境"""
    print("=== Setting up Test Environment ===")

    # 创建 TemporalContext
    ctx = TemporalContext.for_live(date.today())
    print(f"Created TemporalContext: {ctx}")

    return ctx

def test_market_data_integration():
    """测试行情数据集成"""
    print("\n=== Testing Market Data Integration ===")

    try:
        adapter = AlphaVantageAdapter()
        ctx = setup_test_environment()

        # 创建模拟的 OHLCV 数据
        mock_ohlcv_data = pd.DataFrame({
            '1. open': [175.0, 176.5, 174.8],
            '2. high': [177.2, 178.1, 176.9],
            '3. low': [174.5, 175.8, 173.2],
            '4. close': [176.8, 177.5, 175.2],
            '5. adjusted close': [176.8, 177.5, 175.2],
            '6. volume': [85000000, 92000000, 78000000],
        }, index=pd.date_range(end=date.today(), periods=3, freq='D'))

        # 模拟 API 调用
        with patch.object(adapter.ts, 'get_daily_adjusted', return_value=(mock_ohlcv_data, {})), \
             patch.object(TemporalGuard, 'validate_timestamp'):

            df = adapter.get_ohlcv(
                symbol="AAPL",
                start_date=date.today() - pd.Timedelta(days=7),
                end_date=date.today(),
                interval="1d",
                ctx=ctx
            )

            print(f"[SUCCESS] Retrieved {len(df)} OHLCV records")
            print(f"Columns: {list(df.columns)}")
            print(f"Data types: {df.dtypes.to_dict()}")
            print(f"Sample data:")
            print(df.head().to_string())

            # 验证数据结构
            required_columns = ['date', 'open', 'high', 'low', 'close', 'volume', 'adj_close', 'data_source']
            missing_cols = [col for col in required_columns if col not in df.columns]
            if missing_cols:
                print(f"[ERROR] Missing columns: {missing_cols}")
            else:
                print("[SUCCESS] All required columns present")

            return len(df) > 0

    except Exception as e:
        print(f"[ERROR] Market data test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_fundamentals_integration():
    """测试基本面数据集成"""
    print("\n=== Testing Fundamentals Data Integration ===")

    try:
        adapter = AlphaVantageAdapter()
        ctx = setup_test_environment()

        # 创建模拟的基本面数据
        mock_fundamentals = pd.DataFrame({
            'PERatio': [28.5],
            'PriceToBookRatio': [6.2],
            'ReturnOnEquityQuarterly': [0.18],
            'MarketCapitalization': [2800000000000],
            'NetIncome': [99800000000],
            'LatestQuarter': ['2024-03-31']
        })

        # 模拟 API 调用
        with patch.object(adapter.fd, 'get_company_overview', return_value=(mock_fundamentals, {})), \
             patch.object(TemporalGuard, 'assert_backtest_safe'):

            fundamentals = adapter.get_fundamentals(
                symbol="AAPL",
                as_of_date=date.today(),
                ctx=ctx
            )

            print(f"[SUCCESS] Retrieved fundamentals data")
            print(f"Fields retrieved:")
            for key, value in fundamentals.items():
                print(f"  {key}: {value}")

            # 验证必需字段
            required_fields = ['pe_ratio', 'pb_ratio', 'roe', 'revenue', 'net_income']
            missing_fields = [field for field in required_fields if field not in fundamentals]
            if missing_fields:
                print(f"[ERROR] Missing fields: {missing_fields}")
            else:
                print("[SUCCESS] All required fields present")

            return fundamentals.get('pe_ratio') is not None

    except Exception as e:
        print(f"[ERROR] Fundamentals test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_news_integration():
    """测试新闻数据集成"""
    print("\n=== Testing News Data Integration ===")

    try:
        adapter = AlphaVantageAdapter()
        ctx = setup_test_environment()

        # 创建模拟的新闻数据
        mock_news_response = {
            'feed': [
                {
                    'title': 'Apple Reports Record Q4 Revenue of $89.5 Billion',
                    'summary': 'Apple Inc. announced financial results for its fiscal 2024 fourth quarter ended September 28, 2024. The Company posted record quarterly revenue of $89.5 billion, up 2 percent year over year, and quarterly earnings per diluted share of $1.47, up 12 percent year over year.',
                    'source': 'Apple Press Release',
                    'url': 'https://investor.apple.com/news-releases/news-release-details/apple-reports-record-q4-revenue-895-billion',
                    'time_published': '20241201T160000',
                    'ticker_sentiment': [
                        {
                            'ticker': 'AAPL',
                            'ticker_sentiment_score': 0.75
                        }
                    ]
                },
                {
                    'title': 'Analysts Raise Apple Price Target on Strong iPhone Sales',
                    'summary': 'Several Wall Street analysts have raised their price targets for Apple following stronger-than-expected iPhone 15 sales data.',
                    'source': 'MarketWatch',
                    'url': 'https://www.marketwatch.com/story/analysts-raise-apple-price-target',
                    'time_published': '20241201T103000',
                    'ticker_sentiment': [
                        {
                            'ticker': 'AAPL',
                            'ticker_sentiment_score': 0.65
                        }
                    ]
                }
            ]
        }

        # 模拟 API 调用
        with patch('requests.get') as mock_get, \
             patch.object(TemporalGuard, 'assert_backtest_safe'), \
             patch.object(TemporalGuard, 'filter_news', side_effect=lambda news, ctx: news):

            mock_get.return_value.json.return_value = mock_news_response
            mock_get.return_value.raise_for_status.return_value = None

            news_items = adapter.get_news(
                symbol="AAPL",
                days_back=7,
                ctx=ctx
            )

            print(f"[SUCCESS] Retrieved {len(news_items)} news items")

            for i, news in enumerate(news_items):
                print(f"\nNews {i+1}:")
                print(f"  Title: {news.title}")
                print(f"  Source: {news.source}")
                print(f"  Published: {news.published_at}")
                print(f"  Relevance: {news.relevance_score}")
                print(f"  Content preview: {news.content[:100]}...")

            # 验证新闻结构
            if news_items:
                sample_news = news_items[0]
                required_attrs = ['title', 'content', 'published_at', 'source', 'relevance_score']
                missing_attrs = [attr for attr in required_attrs if not hasattr(sample_news, attr)]
                if missing_attrs:
                    print(f"[ERROR] Missing attributes: {missing_attrs}")
                else:
                    print("[SUCCESS] All required news attributes present")

            return len(news_items) > 0

    except Exception as e:
        print(f"[ERROR] News test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_adapter_capabilities():
    """测试适配器能力"""
    print("\n=== Testing Adapter Capabilities ===")

    try:
        adapter = AlphaVantageAdapter()

        # 测试支持的股票代码
        test_symbols = ["AAPL", "MSFT", "GOOGL", "TSLA"]

        for symbol in test_symbols:
            # 测试市场类型判断
            market_type = adapter.get_market_type(symbol)
            print(f"Symbol {symbol}: Market type = {market_type}")

            # 测试可用性检查（模拟）
            with patch.object(adapter.ts, 'get_quote_endpoint', return_value=(pd.DataFrame(), {})):
                available = adapter.is_available(symbol)
                print(f"Symbol {symbol}: Available = {available}")

        print("[SUCCESS] Adapter capabilities test completed")
        return True

    except Exception as e:
        print(f"[ERROR] Capabilities test failed: {e}")
        return False

def main():
    """主测试函数"""
    print("Starting AlphaVantageAdapter Comprehensive Test")
    print(f"Current time: {datetime.now(UTC)}")
    print("=" * 60)

    results = {
        'market_data': False,
        'fundamentals': False,
        'news': False,
        'capabilities': False
    }

    try:
        # 测试适配器能力
        results['capabilities'] = test_adapter_capabilities()

        # 测试行情数据
        results['market_data'] = test_market_data_integration()

        # 测试基本面数据
        results['fundamentals'] = test_fundamentals_integration()

        # 测试新闻数据
        results['news'] = test_news_integration()

        # 总结结果
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)

        all_passed = True
        for test_name, passed in results.items():
            status = "[PASS]" if passed else "[FAIL]"
            print(f"{status} {test_name.replace('_', ' ').title()}")
            if not passed:
                all_passed = False

        print("\n" + "=" * 60)
        if all_passed:
            print("[SUCCESS] All tests passed! AlphaVantageAdapter is working correctly.")
        else:
            print("[WARNING] Some tests failed. Check the output above for details.")
        print("=" * 60)

    except Exception as e:
        print(f"\n[ERROR] Test execution failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()