# pstds/backtest/performance.py
# 绩效计算器 - Phase 5 Task 4 (P5-T4)
# DDD v2.0 第 7.3 节：7 项绩效指标

from typing import Dict, List, Optional
from datetime import date, timedelta
from collections import defaultdict, deque
import pandas as pd
import numpy as np


class PerformanceCalculator:
    """
    绩效计算器

    计算回测的 7 项绩效指标：
    1. 累计收益
    2. 年化收益
    3. 最大回撤
    4. 夏普比率
    5. 卡尔马比率
    6. 胜率
    7. 预测准确率
    """

    def __init__(self, risk_free_rate: float = 0.02):
        """
        初始化绩效计算器

        Args:
            risk_free_rate: 无风险利率（默认 2%）
        """
        self.risk_free_rate = risk_free_rate

    @staticmethod
    def calculate(
        nav_series: pd.Series,
        benchmark: Optional[pd.Series] = None,
        risk_free_rate: float = 0.02,
    ) -> Dict[str, float]:
        """
        计算绩效指标（静态方法）

        Args:
            nav_series: 净值序列（pd.Series，索引为日期）
            benchmark: 基准指数序列（可选）
            risk_free_rate: 无风险利率（默认 2%）

        Returns:
            包含 7 项绩效指标的字典
        """
        if nav_series.empty:
            return {
                "total_return": 0.0,
                "annualized_return": 0.0,
                "max_drawdown": 0.0,
                "sharpe_ratio": 0.0,
                "calmar_ratio": 0.0,
                "win_rate": 0.0,
                "prediction_accuracy": 0.0,
            }

        # 转换为 numpy 数组
        nav_values = nav_series.values

        # 1. 累计收益
        total_return = (nav_values[-1] / nav_values[0] - 1) * 100

        # 2. 年化收益
        days = len(nav_series)
        years = days / 252  # 假设一年 252 个交易日
        annualized_return = ((nav_values[-1] / nav_values[0]) ** (1 / years) - 1) * 100

        # 3. 最大回撤
        cummax = np.maximum.accumulate(nav_values)
        drawdown = (nav_values - cummax) / cummax * 100
        max_drawdown = np.min(drawdown)

        # 计算日收益率
        returns = pd.Series(nav_values).pct_change().dropna()

        # 4. 夏普比率
        if len(returns) > 1 and returns.std() > 0:
            excess_returns = returns - (risk_free_rate / 252)
            sharpe_ratio = excess_returns.mean() / returns.std() * np.sqrt(252)
        else:
            sharpe_ratio = 0.0

        # 5. 卡尔马比率
        if max_drawdown < 0:
            calmar_ratio = annualized_return / abs(max_drawdown)
        else:
            calmar_ratio = 0.0

        # 6. 胜率（需要交易历史，通过 calculate_with_trades() 获取）
        win_rate = None

        # 7. 预测准确率（需要决策历史，通过 calculate_with_decisions() 获取）
        prediction_accuracy = None

        # 如果有基准，计算相对指标
        alpha = 0.0
        beta = 0.0
        if benchmark is not None and len(benchmark) == len(nav_series):
            benchmark_returns = benchmark.pct_change().dropna()
            if len(benchmark_returns) > 1 and benchmark_returns.std() > 0:
                # Alpha (超额收益)
                alpha = (annualized_return - benchmark_returns.mean() * 252 * 100)
                # Beta (市场敏感度)
                beta = returns.cov(benchmark_returns) / benchmark_returns.var()

        return {
            "total_return": total_return,
            "annualized_return": annualized_return,
            "max_drawdown": max_drawdown,
            "sharpe_ratio": sharpe_ratio,
            "calmar_ratio": calmar_ratio,
            "alpha": alpha,
            "beta": beta,
            "win_rate": win_rate,
            "prediction_accuracy": prediction_accuracy,
        }

    def calculate_with_trades(
        self,
        nav_series: pd.Series,
        trades: List[Dict],
        benchmark: Optional[pd.Series] = None,
    ) -> Dict[str, float]:
        """
        计算包含交易的绩效指标

        Args:
            nav_series: 净值序列
            trades: 交易记录列表
            benchmark: 基准指数序列（可选）

        Returns:
            包含 7 项绩效指标的字典
        """
        # 首先计算基本指标
        metrics = self.calculate(nav_series, benchmark, self.risk_free_rate)

        # 6. 胜率（使用 FIFO 队列按时间顺序匹配买卖对，避免 O(n²) 的首次买入搜索）
        if trades:
            winning_trades = 0
            losing_trades = 0
            # FIFO 队列：按时间顺序匹配买卖对
            buy_queues = defaultdict(deque)
            # 先按时间排序确保顺序正确
            sorted_trades = sorted(trades, key=lambda t: t.get("date", ""))
            for trade in sorted_trades:
                symbol = trade.get("symbol", "")
                action = trade.get("action", "").lower()
                price = trade.get("price", 0.0)
                if action in ("buy", "strong_buy"):
                    buy_queues[symbol].append(price)
                elif action in ("sell", "strong_sell"):
                    if buy_queues[symbol]:
                        buy_price = buy_queues[symbol].popleft()
                        if price > buy_price:
                            winning_trades += 1
                        else:
                            losing_trades += 1

            total_trades = winning_trades + losing_trades
            if total_trades > 0:
                metrics["win_rate"] = winning_trades / total_trades * 100

        return metrics

    def calculate_with_decisions(
        self,
        nav_series: pd.Series,
        decisions: List[Dict],
        price_changes: pd.Series,
        benchmark: Optional[pd.Series] = None,
    ) -> Dict[str, float]:
        """
        计算包含决策准确率的绩效指标

        Args:
            nav_series: 净值序列
            decisions: 决策记录列表
            price_changes: 价格变化序列
            benchmark: 基准指数序列（可选）

        Returns:
            包含 7 项绩效指标的字典
        """
        # 首先计算基本指标
        metrics = self.calculate(nav_series, benchmark, self.risk_free_rate)

        # 7. 预测准确率
        correct_predictions = 0
        total_predictions = 0

        # 对齐决策和价格变化
        for decision in decisions:
            decision_date = decision.get("analysis_date")
            action = decision.get("action")

            if decision_date and decision_date in price_changes.index:
                actual_change = price_changes.loc[decision_date]

                # 预测验证
                is_correct = False
                if action in ["BUY", "STRONG_BUY"] and actual_change > 0:
                    is_correct = True
                elif action in ["SELL", "STRONG_SELL"] and actual_change < 0:
                    is_correct = True

                if is_correct:
                    correct_predictions += 1
                total_predictions += 1

        if total_predictions > 0:
            metrics["prediction_accuracy"] = correct_predictions / total_predictions * 100

        return metrics

    def format_metrics(self, metrics: Dict[str, float]) -> str:
        """
        格式化绩效指标为可读字符串

        Args:
            metrics: 绩效指标字典

        Returns:
            格式化的字符串
        """
        win_rate_str = (
            f"胜率: {metrics['win_rate']:.2f}%"
            if metrics.get('win_rate') is not None
            else "胜率: N/A (需要交易数据)"
        )
        prediction_accuracy_str = (
            f"预测准确率: {metrics['prediction_accuracy']:.2f}%"
            if metrics.get('prediction_accuracy') is not None
            else "预测准确率: N/A (需要决策数据)"
        )
        lines = [
            "=== 绩效指标 ===",
            f"累计收益: {metrics['total_return']:.2f}%",
            f"年化收益: {metrics['annualized_return']:.2f}%",
            f"最大回撤: {metrics['max_drawdown']:.2f}%",
            f"夏普比率: {metrics['sharpe_ratio']:.2f}",
            f"卡尔马比率: {metrics['calmar_ratio']:.2f}",
            win_rate_str,
            prediction_accuracy_str,
        ]

        return "\n".join(lines)
