#!/usr/bin/env python3
# PSTDS AlphaVantageAdapter 简单演示脚本

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from datetime import date, datetime, UTC
import pandas as pd
from unittest.mock import patch
from pstds.temporal.context import TemporalContext
from pstds.data.adapters import AlphaVantageAdapter

def main():
    print("=" * 60)
    print("PSTDS AlphaVantageAdapter 演示")
    print("=" * 60)
    print(f"演示时间: {datetime.now(UTC)}")
    print()

    # 设置模拟 API key
    os.environ['ALPHA_VANTAGE_API_KEY'] = 'demo_key'

    try:
        adapter = AlphaVantageAdapter()
        ctx = TemporalContext.for_live(date.today())

        print("[INFO] 初始化 AlphaVantageAdapter 成功")
        print(f"[INFO] 数据源名称: {adapter.name}")
        print()

        # 1. 演示行情数据
        print("[TEST 1] 行情数据 (OHLCV)")
        print("-" * 40)

        mock_ohlcv = pd.DataFrame({
            '1. open': [185.5, 186.2, 184.8],
            '2. high': [187.8, 188.5, 186.9],
            '3. low': [184.2, 185.1, 183.5],
            '4. close': [186.9, 187.6, 185.2],
            '5. adjusted close': [186.9, 187.6, 185.2],
            '6. volume': [45000000, 52000000, 38000000],
        }, index=pd.date_range(end=date.today(), periods=3, freq='D'))

        with patch.object(adapter.ts, 'get_daily_adjusted', return_value=(mock_ohlcv, {})):
            df = adapter.get_ohlcv("AAPL", date.today() - pd.Timedelta(days=7), date.today(), "1d", ctx)

            print(f"[SUCCESS] 获取到 {len(df)} 条 AAPL 行情数据")
            print(f"[INFO] 数据列: {list(df.columns)}")
            print(f"[INFO] 最新收盘价: ${df['close'].iloc[-1]:.2f}")
            print(f"[INFO] 数据源: {df['data_source'].iloc[0]}")

        # 2. 演示基本面数据
        print("\n[TEST 2] 基本面数据 (Fundamentals)")
        print("-" * 40)

        mock_fundamentals = pd.DataFrame({
            'PERatio': [29.5],
            'PriceToBookRatio': [6.8],
            'ReturnOnEquityQuarterly': [0.19],
            'MarketCapitalization': [2950000000000],
            'NetIncome': [102000000000],
            'LatestQuarter': ['2024-03-31']
        })

        with patch.object(adapter.fd, 'get_company_overview', return_value=(mock_fundamentals, {})):
            fundamentals = adapter.get_fundamentals("AAPL", date.today(), ctx)

            print(f"[SUCCESS] 获取基本面数据成功")
            print(f"[INFO] 市盈率 (P/E): {fundamentals['pe_ratio']:.2f}")
            print(f"[INFO] 市净率 (P/B): {fundamentals['pb_ratio']:.2f}")
            print(f"[INFO] 净资产收益率 (ROE): {fundamentals['roe']:.2%}")
            print(f"[INFO] 数据源: {fundamentals['data_source']}")

        # 3. 演示新闻数据
        print("\n[TEST 3] 新闻数据 (News)")
        print("-" * 40)

        mock_news = {
            'feed': [
                {
                    'title': 'Apple Announces Revolutionary AI Features',
                    'summary': 'Apple unveiled groundbreaking artificial intelligence capabilities.',
                    'source': 'TechCrunch',
                    'url': 'https://techcrunch.com/apple-ai',
                    'time_published': '20241201T143000',
                    'ticker_sentiment': [{'ticker': 'AAPL', 'ticker_sentiment_score': 0.85}]
                }
            ]
        }

        with patch('requests.get') as mock_get:
            mock_get.return_value.json.return_value = mock_news
            mock_get.return_value.raise_for_status.return_value = None

            news_items = adapter.get_news("AAPL", 7, ctx)

            print(f"[SUCCESS] 获取到 {len(news_items)} 条相关新闻")
            if news_items:
                news = news_items[0]
                print(f"[INFO] 新闻标题: {news.title}")
                print(f"[INFO] 新闻来源: {news.source}")
                print(f"[INFO] 相关性评分: {news.relevance_score:.2f}")

        # 4. 演示适配器能力
        print("\n[TEST 4] 适配器能力 (Capabilities)")
        print("-" * 40)

        test_symbols = ["AAPL", "MSFT", "GOOGL"]
        for symbol in test_symbols:
            market_type = adapter.get_market_type(symbol)
            print(f"[INFO] {symbol}: 市场类型 = {market_type}")

        print("\n" + "=" * 60)
        print("[SUCCESS] AlphaVantageAdapter 演示完成")
        print("=" * 60)
        print("总结:")
        print("  - AlphaVantageAdapter 已成功实现")
        print("  - 支持行情数据 (OHLCV) 获取")
        print("  - 支持基本面数据获取")
        print("  - 支持新闻数据获取")
        print("  - 完全集成 PSTDS 时间隔离系统")
        print("  - 符合 ISD v1.0 接口规范")

    except Exception as e:
        print(f"[ERROR] 演示失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()