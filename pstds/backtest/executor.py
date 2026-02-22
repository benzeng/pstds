# pstds/backtest/executor.py
# 信号执行器 - Phase 5 Task 3 (P5-T3)

from typing import Dict, List, Optional
from datetime import date

from pstds.backtest.portfolio import VirtualPortfolio, Trade
from pstds.agents.output_schemas import TradeDecision


class SignalExecutor:
    """
    信号执行器

    根据交易决策（TradeDecision）执行买卖操作。
    默认仓位规则：
    - STRONG_BUY: 满仓 (100%)
    - BUY: 半仓 (50%)
    - HOLD: 不动 (0%)
    - SELL: 半仓卖出 (-50%)
    - STRONG_SELL: 清仓 (-100%)
    """

    def __init__(
        self,
        portfolio: VirtualPortfolio,
        position_sizes: Dict[str, float] = None,
    ):
        """
        初始化信号执行器

        Args:
            portfolio: 虚拟投资组合
            position_sizes: 仓位比例配置
                {
                    "STRONG_BUY": 1.0,  # 满仓
                    "BUY": 0.5,  # 半仓
                    "HOLD": 0.0,  # 不动
                    "SELL": -0.5,  # 卖出一半
                    "STRONG_SELL": -1.0,  # 清仓
                }
        """
        self.portfolio = portfolio

        # 默认仓位配置
        self.position_sizes = position_sizes or {
            "STRONG_BUY": 1.0,
            "BUY": 0.5,
            "HOLD": 0.0,
            "SELL": -0.5,
            "STRONG_SELL": -1.0,
            "INSUFFICIENT_DATA": 0.0,
        }

    def set_position_size(self, action: str, size: float):
        """
        设置特定操作的仓位比例

        Args:
            action: 操作类型
            size: 仓位比例（-1.0 到 1.0）
        """
        self.position_sizes[action] = size

    def execute(
        self,
        decision: TradeDecision,
        current_price: float,
        trade_date: date,
    ) -> Optional[Trade]:
        """
        执行交易决策

        Args:
            decision: 交易决策
            current_price: 当前价格
            trade_date: 交易日期

        Returns:
            执行的交易记录，如果没有交易则返回 None
        """
        action = decision.action

        # 获取仓位比例
        position_size = self.position_sizes.get(action, 0.0)

        # HOLD 或 INSUFFICIENT_DATA 不执行交易
        if position_size == 0.0:
            # 更新持仓当前价格
            if action == "HOLD":
                self.portfolio.update_price(decision.symbol, current_price)
            return None

        symbol = decision.symbol

        # 计算目标仓位金额
        total_value = self.portfolio.get_total_value()
        target_amount = total_value * abs(position_size)

        # 计算目标股数
        shares = target_amount / current_price

        # 检查现有持仓
        existing_position = self.portfolio.get_position(symbol)

        if existing_position is None:
            # 没有持仓，只能买入
            if position_size > 0:
                # 买入
                return self.portfolio.buy(symbol, shares, current_price, trade_date)
            else:
                # 没有持仓却要卖出，忽略
                return None
        else:
            # 有持仓
            current_shares = existing_position.shares

            if position_size > 0:
                # 买入
                shares_to_buy = shares - current_shares
                if shares_to_buy > 0:
                    return self.portfolio.buy(symbol, shares_to_buy, current_price, trade_date)
                # 如果目标股数 <= 当前持仓，不操作
                return None
            else:
                # 卖出
                # 计算需要卖出的股数
                shares_to_sell = min(shares, current_shares)

                # 如果目标股数 >= 当前持仓，全部卖出
                if shares >= current_shares:
                    return self.portfolio.sell(symbol, current_shares, current_price, trade_date)
                else:
                    # 部分卖出
                    return self.portfolio.sell(symbol, shares_to_sell, current_price, trade_date)

    def execute_with_confidence(
        self,
        decision: TradeDecision,
        current_price: float,
        trade_date: date,
    ) -> Optional[Trade]:
        """
        根据置信度调整执行交易决策

        低置信度时降低仓位比例。

        Args:
            decision: 交易决策
            current_price: 当前价格
            trade_date: 交易日期

        Returns:
            执行的交易记录
        """
        action = decision.action
        confidence = decision.confidence

        # 根据置信度调整仓位
        # 高置信度 (>= 0.8): 保持原仓位
        # 中等置信度 (0.5 - 0.8): 仓位 × 0.8
        # 低置信度 (< 0.5): 仓位 × 0.5
        if confidence >= 0.8:
            confidence_factor = 1.0
        elif confidence >= 0.5:
            confidence_factor = 0.8
        else:
            confidence_factor = 0.5

        # 应用置信度调整
        base_size = self.position_sizes.get(action, 0.0)
        adjusted_size = base_size * confidence_factor

        # 更新临时仓位配置
        original_size = self.position_sizes[action]
        self.position_sizes[action] = adjusted_size

        # 执行交易
        trade = self.execute(decision, current_price, trade_date)

        # 恢复原始仓位配置
        self.position_sizes[action] = original_size

        return trade

    def execute_with_volatility(
        self,
        decision: TradeDecision,
        current_price: float,
        trade_date: date,
    ) -> Optional[Trade]:
        """
        根据波动率调整执行交易决策

        高波动时降低仓位，低波动时保持原仓位。

        Args:
            decision: 交易决策
            current_price: 当前价格
            trade_date: 交易日期

        Returns:
            执行的交易记录
        """
        action = decision.action
        volatility_adjustment = decision.volatility_adjustment

        # 根据波动率调整仓位
        # 低波动 (volatility_adjustment < 1.0): 仓位 × 1.2
        # 正常波动 (volatility_adjustment == 1.0): 保持原仓位
        # 高波动 (volatility_adjustment > 1.0): 仓位 × 0.7
        if volatility_adjustment < 1.0:
            volatility_factor = 1.2
        elif volatility_adjustment > 1.0:
            volatility_factor = 0.7
        else:
            volatility_factor = 1.0

        # 应用波动率调整
        base_size = self.position_sizes.get(action, 0.0)
        adjusted_size = base_size * volatility_factor

        # 确保仓位在合理范围内
        adjusted_size = max(-1.0, min(1.0, adjusted_size))

        # 更新临时仓位配置
        original_size = self.position_sizes[action]
        self.position_sizes[action] = adjusted_size

        # 执行交易
        trade = self.execute(decision, current_price, trade_date)

        # 恢复原始仓位配置
        self.position_sizes[action] = original_size

        return trade

    def close_all_positions(self, current_prices: Dict[str, float], trade_date: date) -> List[Trade]:
        """
        清空所有持仓

        Args:
            current_prices: 当前价格字典 {symbol: price}
            trade_date: 交易日期

        Returns:
            执行的交易记录列表
        """
        trades = []

        for symbol in list(self.portfolio.positions.keys()):
            price = current_prices.get(symbol, self.portfolio.get_position(symbol).current_price)
            trade = self.portfolio.sell(
                symbol,
                self.portfolio.get_position(symbol).shares,
                price,
                trade_date
            )
            trades.append(trade)

        return trades

    def get_position_config(self) -> Dict[str, float]:
        """
        获取当前仓位配置

        Returns:
            仓位配置字典
        """
        return self.position_sizes.copy()
