# pstds/backtest/calendar.py
# 交易日历 - Phase 5 Task 1 (P5-T1)

from typing import List, Optional, Set
from datetime import date, datetime, timedelta
import pandas as pd
from pathlib import Path

try:
    import pandas_market_calendars as mcal
    MCAL_AVAILABLE = True
except ImportError:
    MCAL_AVAILABLE = False
    mcal = None

try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False
    ak = None


class TradingCalendar:
    """
    交易日历管理器

    支持美股（NYSE）、港股（HKEX）和 A 股（沪深）交易日历。
    缓存交易日历到本地以提高性能。
    """

    def __init__(self, cache_dir: str = "./data/cache"):
        """
        初始化交易日历管理器

        Args:
            cache_dir: 缓存目录路径
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # 日历实例缓存
        self._calendars = {}

        # A 股交易日历缓存（本地）
        self._cn_a_trading_days_cache = None

    def _get_calendar(self, market_type: str):
        """
        获取市场日历实例

        Args:
            market_type: 市场类型 (US, CN_A, HK)

        Returns:
            pandas_market_calendars 日历实例
        """
        if market_type in self._calendars:
            return self._calendars[market_type]

        if not MCAL_AVAILABLE:
            print("pandas_market_calendars 未安装，仅支持 A 股（使用 AKShare）")
            return None

        # 创建日历实例
        if market_type == "US":
            cal = mcal.get_calendar('NYSE')
        elif market_type == "HK":
            cal = mcal.get_calendar('HKEX')
        else:
            # A 股不使用 pandas_market_calendars
            return None

        self._calendars[market_type] = cal
        return cal

    def _load_cn_a_trading_days(self, year: int) -> List[date]:
        """
        加载 A 股交易日历（从缓存或 AKShare）

        Args:
            year: 年份

        Returns:
            该年份的交易日列表
        """
        cache_file = self.cache_dir / f"cn_a_trading_days_{year}.json"

        # 尝试从缓存加载
        if cache_file.exists():
            try:
                import json
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return [date.fromisoformat(d) for d in data]
            except Exception as e:
                print(f"加载 A 股交易日历缓存失败: {e}")

        # 从 AKShare 获取
        if not AKSHARE_AVAILABLE:
            print("AKShare 未安装，无法获取 A 股交易日历")
            return []

        try:
            # 获取交易日历
            df = ak.tool_trade_date_hist_sina(f"{year}")
            if df is not None and not df.empty:
                # 解析交易日
                trading_days = []
                for trade_date in df['trade_date']:
                    try:
                        # AKShare 返回的日期格式可能是字符串
                        if isinstance(trade_date, str):
                            trading_day = datetime.strptime(trade_date, "%Y-%m-%d").date()
                        else:
                            trading_day = pd.to_datetime(trade_date).date()
                        trading_days.append(trading_day)
                    except Exception as e:
                        print(f"解析日期失败: {e}")

                # 按日期排序
                trading_days = sorted(trading_days)

                # 缓存到本地
                try:
                    with open(cache_file, 'w', encoding='utf-8') as f:
                        json.dump([d.isoformat() for d in trading_days], f)
                except Exception as e:
                    print(f"保存 A 股交易日历缓存失败: {e}")

                return trading_days

        except Exception as e:
            print(f"从 AKShare 获取 A 股交易日历失败: {e}")

        return []

    def get_trading_days(
        self,
        start_date: date,
        end_date: date,
        market_type: str = "US",
    ) -> List[date]:
        """
        获取指定日期范围内的交易日

        Args:
            start_date: 开始日期
            end_date: 结束日期
            market_type: 市场类型 (US, CN_A, HK)

        Returns:
            交易日列表（已排序）
        """
        if start_date > end_date:
            return []

        trading_days = []

        if market_type == "CN_A":
            # A 股：按年份加载
            years = list(range(start_date.year, end_date.year + 1))
            for year in years:
                year_days = self._load_cn_a_trading_days(year)
                trading_days.extend(year_days)

            # 过滤日期范围
            trading_days = [d for d in trading_days if start_date <= d <= end_date]

        else:
            # 美股和港股：使用 pandas_market_calendars
            cal = self._get_calendar(market_type)
            if cal is None:
                return []

            try:
                # 获取有效交易日
                # 新版 pandas_market_calendars 返回 DataFrame
                schedule_df = cal.schedule(start_date, end_date)

                # DataFrame 的 market_open 列包含交易日期
                if 'market_open' in schedule_df.columns and not schedule_df.empty:
                    # 提取日期（去重）
                    trading_days = schedule_df['market_open'].dt.date.unique().tolist()
                else:
                    trading_days = []

            except Exception as e:
                print(f"获取交易日历失败: {e}")
                return []

        return sorted(trading_days)

    def is_trading_day(self, check_date: date, market_type: str = "US") -> bool:
        """
        检查指定日期是否为交易日

        Args:
            check_date: 要检查的日期
            market_type: 市场类型

        Returns:
            是否为交易日
        """
        trading_days = self.get_trading_days(check_date, check_date, market_type)
        return check_date in trading_days

    def get_next_trading_day(
        self,
        check_date: date,
        market_type: str = "US",
        max_days_ahead: int = 10,
    ) -> Optional[date]:
        """
        获取指定日期之后的下一个交易日

        Args:
            check_date: 检查日期
            market_type: 市场类型
            max_days_ahead: 最多向前查找的天数

        Returns:
            下一个交易日，None 表示未找到
        """
        end_date = check_date + timedelta(days=max_days_ahead)
        trading_days = self.get_trading_days(check_date, end_date, market_type)

        # 找到第一个大于 check_date 的交易日
        for trading_day in trading_days:
            if trading_day > check_date:
                return trading_day

        return None

    def get_previous_trading_day(
        self,
        check_date: date,
        market_type: str = "US",
        max_days_back: int = 10,
    ) -> Optional[date]:
        """
        获取指定日期之前的上一个交易日

        Args:
            check_date: 检查日期
            market_type: 市场类型
            max_days_back: 最多向后查找的天数

        Returns:
            上一个交易日，None 表示未找到
        """
        start_date = check_date - timedelta(days=max_days_back)
        trading_days = self.get_trading_days(start_date, check_date, market_type)

        # 找到第一个小于 check_date 的交易日
        for trading_day in reversed(trading_days):
            if trading_day < check_date:
                return trading_day

        return None

    def get_market_days_in_range(
        self,
        start_date: date,
        end_date: date,
        market_type: str = "US",
    ) -> int:
        """
        计算指定日期范围内的市场开市天数

        Args:
            start_date: 开始日期
            end_date: 结束日期
            market_type: 市场类型

        Returns:
            市场开市天数
        """
        trading_days = self.get_trading_days(start_date, end_date, market_type)
        return len(trading_days)

    def clear_cache(self):
        """
        清除本地缓存
        """
        import glob
        cache_files = glob.glob(str(self.cache_dir / "cn_a_trading_days_*.json"))
        for cache_file in cache_files:
            try:
                Path(cache_file).unlink()
                print(f"已删除缓存: {cache_file}")
            except Exception as e:
                print(f"删除缓存失败: {e}")


# 全局交易日历实例
_global_calendar: Optional[TradingCalendar] = None


def get_calendar() -> TradingCalendar:
    """
    获取全局交易日历实例（单例）

    Returns:
        TradingCalendar 实例
    """
    global _global_calendar
    if _global_calendar is None:
        _global_calendar = TradingCalendar()
    return _global_calendar
