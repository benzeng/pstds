# pstds/backtest/runner.py
# 回测运行器 - Phase 5 Task 5 (P5-T5)
# DDD v2.0 相关章节：主控类，核心循环，零前视偏差

from typing import Dict, List, Optional, Callable, Any
from datetime import date, datetime, UTC
import pandas as pd

from pstds.temporal.context import TemporalContext
from pstds.backtest.calendar import TradingCalendar
from pstds.backtest.portfolio import VirtualPortfolio
from pstds.backtest.executor import SignalExecutor
from pstds.backtest.performance import PerformanceCalculator
from pstds.storage.mongo_store import MongoStore
from pstds.agents.output_schemas import TradeDecision
from pstds.agents.extended_graph import ExtendedTradingAgentsGraph


class BacktestRunner:
    """
    回测运行器

    主控类，核心循环中每个交易日创建 TemporalContext.for_backtest(current_date)，
    确保零前视偏差。每日快照写入 MongoDB。
    """

    def __init__(
        self,
        initial_capital: float = 100000.0,
        commission_rate: float = 0.001,
        min_commission: float = 5.0,
        slippage_bps: int = 5,
        mongo_store: Optional[MongoStore] = None,
        save_snapshots: bool = True,
    ):
        """
        初始化回测运行器

        Args:
            initial_capital: 初始资金
            commission_rate: 手续费率
            min_commission: 最低手续费
            slippage_bps: 滑点（bps）
            mongo_store: MongoDB 存储实例（可选）
            save_snapshots: 是否保存每日快照到 MongoDB
        """
        self.initial_capital = initial_capital
        self.mongo_store = mongo_store
        self.save_snapshots = save_snapshots

        # 初始化组件
        self.calendar = TradingCalendar()
        self.portfolio = VirtualPortfolio(
            initial_capital=initial_capital,
            commission_rate=commission_rate,
            min_commission=min_commission,
            slippage_bps=slippage_bps,
        )
        self.executor = SignalExecutor(self.portfolio)
        self.performance_calculator = PerformanceCalculator()

        # 回测状态
        self.is_running = False
        self.current_date: Optional[date] = None

        # 每日快照
        self.daily_snapshots: List[Dict] = []

    def run(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        market_type: str = "US",
        decision_callback: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """
        运行回测

        Args:
            symbol: 股票代码
            start_date: 回测开始日期
            end_date: 回测结束日期
            market_type: 市场类型
            decision_callback: 决策回调函数（用于获取每日决策）
                signature: callback(ctx, symbol, date) -> TradeDecision
                如果未提供，使用 ExtendedTradingAgentsGraph

        Returns:
            回测结果字典
        """
        self.is_running = True

        # 获取交易日历
        trading_days = self.calendar.get_trading_days(start_date, end_date, market_type)

        if not trading_days:
            return {
                "symbol": symbol,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "error": "No trading days in the specified range",
                "status": "failed",
            }

        # 初始化扩展图（如果没有提供决策回调）
        graph = None
        if decision_callback is None:
            graph = ExtendedTradingAgentsGraph()

        # 重置组合
        self.portfolio.reset()
        self.daily_snapshots = []

        # 每日价格数据（需要从数据源获取）
        # 这里简化处理，实际实现需要从数据源获取
        prices = self._get_mock_prices(symbol, trading_days)

        # 核心回测循环
        for i, trade_date in enumerate(trading_days):
            print(f"回测进度: {i+1}/{len(trading_days)} - {trade_date}")

            # 创建 TemporalContext（确保零前视偏差）
            ctx = TemporalContext.for_backtest(trade_date)
            self.current_date = trade_date

            # 获取决策
            if decision_callback:
                decision = decision_callback(ctx, symbol, trade_date)
            elif graph:
                try:
                    result = graph.propagate(symbol, trade_date, ctx, depth="L2")
                    decision = result.get("final_trade_decision")
                except Exception as e:
                    print(f"获取决策失败: {e}")
                    # 创建数据不足的决策
                    from pstds.agents.output_schemas import DataSource
                    decision = TradeDecision(
                        action="INSUFFICIENT_DATA",
                        confidence=0.0,
                        conviction="LOW",
                        primary_reason=f"Analysis failed: {str(e)}",
                        insufficient_data=True,
                        target_price_low=None,
                        target_price_high=None,
                        time_horizon="",
                        risk_factors=["Analysis error"],
                        data_sources=[DataSource(
                            name="error",
                            url=None,
                            data_timestamp=datetime.now(UTC),
                            market_type=market_type,
                            fetched_at=datetime.now(UTC),
                        )],
                        analysis_date=trade_date,
                        analysis_timestamp=datetime.now(UTC),
                        volatility_adjustment=1.0,
                        debate_quality_score=0.0,
                        symbol=symbol,
                        market_type=market_type,
                    )
            else:
                continue

            # 获取当前价格
            current_price = prices.get(trade_date, 0.0)
            if current_price <= 0:
                print(f"警告: {trade_date} 没有价格数据，跳过")
                continue

            # 更新持仓价格
            self.portfolio.update_price(symbol, current_price)

            # 执行交易决策
            trade = self.executor.execute(decision, current_price, trade_date)

            # 记录每日快照
            snapshot = {
                "date": trade_date.isoformat(),
                "symbol": symbol,
                "market_type": market_type,
                "price": current_price,
                "nav": self.portfolio.get_nav(trade_date),
                "cash": self.portfolio.get_cash(),
                "positions_count": len(self.portfolio.positions),
                "decision": {
                    "action": decision.action,
                    "confidence": decision.confidence,
                } if decision else None,
            }

            if trade:
                snapshot["trade"] = {
                    "action": trade.action,
                    "shares": trade.shares,
                    "price": trade.price,
                    "net_amount": trade.net_amount,
                }

            self.daily_snapshots.append(snapshot)

            # 保存到 MongoDB（如果启用）
            if self.save_snapshots and self.mongo_store:
                try:
                    self.mongo_store.save_analysis({
                        "symbol": symbol,
                        "analysis_date": trade_date,
                        "decision": {
                            "action": decision.action,
                            "confidence": decision.confidence,
                        } if decision else None,
                        "nav": self.portfolio.get_nav(trade_date),
                        "cash": self.portfolio.get_cash(),
                    })
                except Exception as e:
                    print(f"保存快照到 MongoDB 失败: {e}")

        self.is_running = False

        # 计算绩效指标
        nav_series = pd.Series(
            [s["nav"] for s in self.daily_snapshots],
            index=[pd.to_datetime(s["date"]) for s in self.daily_snapshots]
        )

        metrics = self.performance_calculator.calculate(nav_series)

        # 构建返回结果
        result = {
            "symbol": symbol,
            "market_type": market_type,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "trading_days_count": len(trading_days),
            "initial_capital": self.initial_capital,
            "final_nav": self.portfolio.get_total_value(),
            "total_return": metrics["total_return"],
            "annualized_return": metrics["annualized_return"],
            "max_drawdown": metrics["max_drawdown"],
            "sharpe_ratio": metrics["sharpe_ratio"],
            "calmar_ratio": metrics["calmar_ratio"],
            "win_rate": metrics["win_rate"],
            "prediction_accuracy": metrics["prediction_accuracy"],
            "trade_count": len(self.portfolio.trade_history),
            "daily_snapshots": self.daily_snapshots,
            "nav_series": nav_series,
            "status": "completed",
        }

        return result

    def _get_mock_prices(self, symbol: str, dates: List[date]) -> Dict[date, float]:
        """
        获取模拟价格数据（简化实现）

        实际实现应该从数据源获取历史价格数据。

        Args:
            symbol: 股票代码
            dates: 日期列表

        Returns:
            {日期: 价格} 字典
        """
        import random
        prices = {}
        base_price = 150.0

        for i, d in enumerate(dates):
            # 简单随机漫步
            change = random.uniform(-0.02, 0.02)
            base_price = base_price * (1 + change)
            prices[d] = base_price

        return prices

    def get_progress(self) -> float:
        """
        获取回测进度

        Returns:
            进度百分比（0-100）
        """
        if not self.current_date:
            return 0.0
        return 0.0  # 实际实现中应该计算真实进度

    def stop(self):
        """
        停止回测
        """
        self.is_running = False

    def get_daily_snapshots(self) -> List[Dict]:
        """
        获取每日快照

        Returns:
            每日快照列表
        """
        return self.daily_snapshots

    def get_portfolio(self) -> VirtualPortfolio:
        """
        获取当前投资组合

        Returns:
            VirtualPortfolio 实例
        """
        return self.portfolio

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典

        Returns:
            回测运行器状态字典
        """
        return {
            "initial_capital": self.initial_capital,
            "is_running": self.is_running,
            "current_date": self.current_date.isoformat() if self.current_date else None,
            "portfolio": self.portfolio.to_dict(),
            "daily_snapshots": self.daily_snapshots,
        }
