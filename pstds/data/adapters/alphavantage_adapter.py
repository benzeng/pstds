# pstds/data/adapters/alphavantage_adapter.py
# AlphaVantage 数据适配器 - ISD v1.0 Section 4.1

from alpha_vantage.timeseries import TimeSeries
from alpha_vantage.fundamentaldata import FundamentalData
from typing import List, Literal, Optional
from datetime import date, datetime, UTC, timedelta
import pandas as pd
import os
import requests

from pstds.temporal.context import TemporalContext
from pstds.temporal.guard import TemporalGuard
from pstds.data.adapters.base import MarketDataAdapter
from pstds.data.models import NewsItem, MarketType


class AlphaVantageAdapter:
    """
    AlphaVantage 数据适配器

    主要用于美股数据获取，作为 YFinance 的备用数据源。
    需要 ALPHA_VANTAGE_API_KEY 环境变量。
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        初始化 AlphaVantage 适配器

        Args:
            api_key: AlphaVantage API key，如果为 None 则从环境变量读取
        """
        self.api_key = api_key or os.getenv("ALPHA_VANTAGE_API_KEY")
        if not self.api_key:
            raise ValueError("AlphaVantage API key not found. Set ALPHA_VANTAGE_API_KEY environment variable.")

        self.name = "alphavantage"
        self.ts = TimeSeries(key=self.api_key, output_format='pandas')
        self.fd = FundamentalData(key=self.api_key, output_format='pandas')
        self.base_url = "https://www.alphavantage.co/query"

    def get_ohlcv(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        interval: Literal["1d", "1wk", "1mo"],
        ctx: TemporalContext,
    ) -> pd.DataFrame:
        """
        获取 OHLCV 行情数据

        内部调用 TemporalGuard.validate_timestamp(end_date, ctx)
        """
        # 时间隔离校验
        TemporalGuard.validate_timestamp(end_date, ctx, f"{self.name}.get_ohlcv")

        try:
            # 映射间隔参数
            interval_map = {
                "1d": "daily",
                "1wk": "weekly",
                "1mo": "monthly"
            }
            av_interval = interval_map.get(interval, "daily")

            # 获取数据
            if av_interval == "daily":
                data, meta_data = self.ts.get_daily_adjusted(symbol=symbol, outputsize='full')
            elif av_interval == "weekly":
                data, meta_data = self.ts.get_weekly_adjusted(symbol=symbol)
            else:  # monthly
                data, meta_data = self.ts.get_monthly_adjusted(symbol=symbol)

            if data is None or data.empty:
                return pd.DataFrame(columns=[
                    "date", "open", "high", "low", "close",
                    "volume", "adj_close", "data_source"
                ])

            # 标准化列名和数据格式
            data = data.reset_index()
            # 确保 date 列存在且正确命名
            if 'date' not in data.columns and 'index' in data.columns:
                data = data.rename(columns={'index': 'date'})
            data['date'] = pd.to_datetime(data['date'], utc=True)

            # 重命名列以匹配标准格式
            column_mapping = {
                '1. open': 'open',
                '2. high': 'high',
                '3. low': 'low',
                '4. close': 'close',
                '5. adjusted close': 'adj_close',
                '6. volume': 'volume'
            }

            # 只保留需要的列并重命名
            required_cols = ['1. open', '2. high', '3. low', '4. close', '5. adjusted close', '6. volume']
            available_cols = [col for col in required_cols if col in data.columns]

            data = data[['date'] + available_cols].rename(columns=column_mapping)

            # 确保所有必需列都存在
            for col in ['open', 'high', 'low', 'close', 'adj_close', 'volume']:
                if col not in data.columns:
                    data[col] = None

            # 添加元数据列
            data['data_source'] = self.name
            data['fetched_at'] = datetime.now(UTC)

            # 日期范围过滤
            start_dt = pd.to_datetime(start_date, utc=True)
            end_dt = pd.to_datetime(end_date, utc=True)
            data = data[(data['date'] >= start_dt) & (data['date'] <= end_dt)]

            # 确保列顺序
            final_cols = ['date', 'open', 'high', 'low', 'close', 'volume', 'adj_close', 'data_source']
            data = data[final_cols]

            return data

        except Exception as e:
            print(f"AlphaVantageAdapter.get_ohlcv error: {e}")
            return pd.DataFrame(columns=[
                "date", "open", "high", "low", "close",
                "volume", "adj_close", "data_source"
            ])

    def get_fundamentals(
        self,
        symbol: str,
        as_of_date: date,
        ctx: TemporalContext,
    ) -> dict:
        """
        获取基本面数据

        缺失字段用 None 填充，网络失败返回含 None 值的字典
        """
        try:
            # BACKTEST 模式禁止调用实时 API
            TemporalGuard.assert_backtest_safe(ctx, f"{self.name}.get_fundamentals")

            # 获取公司概览数据
            data, meta_data = self.fd.get_company_overview(symbol)

            if data is None or data.empty:
                # 返回含 None 值的字典
                return {
                    "pe_ratio": None,
                    "pb_ratio": None,
                    "roe": None,
                    "revenue": None,
                    "net_income": None,
                    "earnings_date": None,
                    "report_period": None,
                    "data_source": self.name,
                    "fetched_at": datetime.now(UTC),
                }

            # 转换为字典格式
            overview = data.iloc[0].to_dict()

            # 标准化字段映射
            result = {
                "pe_ratio": self._safe_float(overview.get('PERatio')),
                "pb_ratio": self._safe_float(overview.get('PriceToBookRatio')),
                "roe": self._safe_float(overview.get('ReturnOnEquityQuarterly')),
                "revenue": self._safe_float(overview.get('MarketCapitalization')),  # 使用市值作为替代
                "net_income": self._safe_float(overview.get('NetIncome')),
                "earnings_date": overview.get('LatestQuarter'),
                "report_period": overview.get('LatestQuarter'),
                "data_source": self.name,
                "fetched_at": datetime.now(UTC),
            }

            return result

        except Exception as e:
            print(f"AlphaVantageAdapter.get_fundamentals error: {e}")
            # 返回含 None 值的字典
            return {
                "pe_ratio": None,
                "pb_ratio": None,
                "roe": None,
                "revenue": None,
                "net_income": None,
                "earnings_date": None,
                "report_period": None,
                "data_source": self.name,
                "fetched_at": datetime.now(UTC),
            }

    def get_news(
        self,
        symbol: str,
        days_back: int,
        ctx: TemporalContext,
    ) -> List[NewsItem]:
        """
        获取新闻数据

        内部调用 TemporalGuard.filter_news() 过滤未来新闻
        relevance_score < 0.6 的项目在内部过滤
        """
        try:
            # BACKTEST 模式禁止调用实时 API
            TemporalGuard.assert_backtest_safe(ctx, f"{self.name}.get_news")

            # 计算日期范围
            end_date = datetime.now(UTC)
            start_date = end_date - timedelta(days=days_back)

            # 使用 AlphaVantage News & Sentiment API
            params = {
                'function': 'NEWS_SENTIMENT',
                'tickers': symbol,
                'time_from': start_date.strftime('%Y%m%dT%H%M'),
                'time_to': end_date.strftime('%Y%m%dT%H%M'),
                'sort': 'LATEST',
                'limit': '100',
                'apikey': self.api_key
            }

            response = requests.get(self.base_url, params=params)
            response.raise_for_status()

            data = response.json()

            if 'feed' not in data or not data['feed']:
                return []

            # 转换为 NewsItem 格式
            news_items = []
            for item in data['feed']:
                # 计算相关性评分
                relevance = 0.6  # 默认相关

                # 尝试从 sentiment 获取相关性评分
                ticker_sentiment = item.get('ticker_sentiment', [])
                for sentiment in ticker_sentiment:
                    if sentiment.get('ticker') == symbol:
                        relevance = min(abs(float(sentiment.get('ticker_sentiment_score', 0.1))) + 0.5, 1.0)
                        break

                # 只保留相关性较高的新闻
                if relevance < 0.6:
                    continue

                # 处理发布时间
                published_at = None
                if 'time_published' in item and item['time_published']:
                    try:
                        # AlphaVantage 返回格式: "20240101T120000"
                        time_str = item['time_published']
                        if len(time_str) >= 15:
                            dt_part = time_str[:8]  # YYYYMMDD
                            time_part = time_str[9:15]  # HHMMSS
                            iso_str = f"{dt_part[:4]}-{dt_part[4:6]}-{dt_part[6:8]}T{time_part[:2]}:{time_part[2:4]}:{time_part[4:6]}Z"
                            published_at = datetime.fromisoformat(iso_str.replace('Z', '+00:00'))
                    except (ValueError, TypeError):
                        published_at = datetime.now(UTC)
                else:
                    published_at = datetime.now(UTC)

                news_items.append(NewsItem(
                    title=item.get('title', ''),
                    content=item.get('summary', '')[:500],  # 截断至 500 tokens
                    published_at=published_at,
                    source=item.get('source', ''),
                    url=item.get('url', ''),
                    relevance_score=relevance,
                    market_type="US",  # AlphaVantage 主要支持美股
                    symbol=symbol,
                ))

            # 时间隔离：过滤未来新闻
            filtered = TemporalGuard.filter_news(news_items, ctx)

            return filtered

        except Exception as e:
            print(f"AlphaVantageAdapter.get_news error: {e}")
            return []

    def is_available(self, symbol: str) -> bool:
        """检查数据源是否支持该股票代码"""
        try:
            # 尝试获取基本信息
            data, meta_data = self.ts.get_quote_endpoint(symbol)
            return data is not None and not data.empty
        except:
            return False

    def get_market_type(self, symbol: str) -> Literal["US", "CN_A", "HK"]:
        """获取股票对应的市场类型"""
        # AlphaVantage 主要支持美股
        if symbol.endswith(".HK"):
            return "HK"
        else:
            return "US"

    def _safe_float(self, value) -> Optional[float]:
        """安全转换为浮点数"""
        try:
            if value is None or value == 'None' or value == '':
                return None
            return float(value)
        except (ValueError, TypeError):
            return None