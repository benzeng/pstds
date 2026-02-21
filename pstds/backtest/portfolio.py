# pstds/backtest/portfolio.py
# 虚拟组合 - Phase 5 Task 2 (P5-T2)
# DDD v2.0 第 7.2 节：买卖含手续费和滑点计算

from typing import Dict, List, Optional, Any
from datetime import date, datetime
from dataclasses import dataclass, field
import json


@dataclass
class Position:
    """
    持仓信息
    """
    symbol: str
    shares: float  # 持有股数
    avg_cost: float  # 平均成本
    market_type: str
    entry_date: date
    current_price: float = 0.0


@dataclass
class Trade:
    """
    交易记录
    """
    symbol: str
    action: str  # "buy" or "sell"
    shares: float
    price: float
    amount: float  # 成交金额
    commission: float  # 手续费
    slippage: float  # 滑点损失
    trade_date: date
    market_type: str
    net_amount: float = 0.0  # 净成交金额（扣除手续费和滑点）


class VirtualPortfolio:
    """
    虚拟投资组合

    管理现金、持仓、交易历史，计算手续费和滑点。
    按 DDD v2.0 第 7.2 节公式：
    - 手续费 = max(成交金额 × 手续费率, 最低手续费)
    - 滑点 = 股数 × (滑点 bps / 10000)
    """

    def __init__(
        self,
        initial_capital: float = 100000.0,
        commission_rate: float = 0.001,
        min_commission: float = 5.0,
        slippage_bps: int = 5,
        market_type: str = "US",
    ):
        """
        初始化虚拟投资组合

        Args:
            initial_capital: 初始资金
            commission_rate: 手续费率（默认 0.1%）
            min_commission: 最低手续费（默认 $5）
            slippage_bps: 滑点（bps，基点，默认 5bps = 0.05%）
            market_type: 市场类型（US, CN_A, HK）
        """
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.commission_rate = commission_rate
        self.min_commission = min_commission
        self.slippage_bps = slippage_bps
        self.market_type = market_type

        # 持仓 {symbol: Position}
        self.positions: Dict[str, Position] = {}

        # 交易历史
        self.trade_history: List[Trade] = []

        # 净值历史 {date: total_value}
        self.nav_history: Dict[date, float] = {}

    def _calculate_commission(self, amount: float) -> float:
        """
        计算手续费

        公式：max(成交金额 × 手续费率, 最低手续费)

        Args:
            amount: 成交金额

        Returns:
            手续费金额
        """
        return max(amount * self.commission_rate, self.min_commission)

    def _calculate_slippage(self, shares: float, price: float) -> float:
        """
        计算滑点损失

        公式：股数 × (滑点 bps / 10000)

        Args:
            shares: 股数
            price: 价格

        Returns:
            滑点损失金额
        """
        return shares * price * (self.slippage_bps / 10000.0)

    def buy(
        self,
        symbol: str,
        shares: float,
        price: float,
        trade_date: date,
    ) -> Trade:
        """
        买入股票

        Args:
            symbol: 股票代码
            shares: 股数
            price: 买入价格
            trade_date: 交易日期

        Returns:
            交易记录
        """
        # 计算成交金额
        amount = shares * price

        # 计算手续费
        commission = self._calculate_commission(amount)

        # 计算滑点
        slippage = self._calculate_slippage(shares, price)

        # 净成交金额
        net_amount = amount - commission - slippage

        # 检查资金是否足够
        if net_amount > self.cash:
            raise ValueError(
                f"资金不足：需要 {net_amount:.2f}，可用 {self.cash:.2f}"
            )

        # 更新现金
        self.cash -= net_amount

        # 更新或创建持仓
        if symbol in self.positions:
            # 已有持仓，计算新的平均成本
            existing_position = self.positions[symbol]
            total_shares = existing_position.shares + shares
            total_cost = (existing_position.shares * existing_position.avg_cost +
                         shares * price)
            avg_cost = total_cost / total_shares

            self.positions[symbol] = Position(
                symbol=symbol,
                shares=total_shares,
                avg_cost=avg_cost,
                market_type=self.market_type,
                entry_date=existing_position.entry_date,
                current_price=price,
            )
        else:
            # 新建持仓
            self.positions[symbol] = Position(
                symbol=symbol,
                shares=shares,
                avg_cost=price,
                market_type=self.market_type,
                entry_date=trade_date,
                current_price=price,
            )

        # 记录交易
        trade = Trade(
            symbol=symbol,
            action="buy",
            shares=shares,
            price=price,
            amount=amount,
            commission=commission,
            slippage=slippage,
            trade_date=trade_date,
            market_type=self.market_type,
            net_amount=net_amount,
        )
        self.trade_history.append(trade)

        return trade

    def sell(
        self,
        symbol: str,
        shares: float,
        price: float,
        trade_date: date,
    ) -> Trade:
        """
        卖出股票

        Args:
            symbol: 股票代码
            shares: 股数
            price: 卖出价格
            trade_date: 交易日期

        Returns:
            交易记录
        """
        # 检查是否有足够持仓
        if symbol not in self.positions:
            raise ValueError(f"没有 {symbol} 的持仓")

        position = self.positions[symbol]
        if position.shares < shares:
            raise ValueError(
                f"持仓不足：持有 {position.shares:.2f}，卖出 {shares:.2f}"
            )

        # 计算成交金额
        amount = shares * price

        # 计算手续费
        commission = self._calculate_commission(amount)

        # 计算滑点
        slippage = self._calculate_slippage(shares, price)

        # 净成交金额
        net_amount = amount - commission - slippage

        # 更新现金
        self.cash += net_amount

        # 更新持仓
        if position.shares == shares:
            # 全部卖出，删除持仓
            del self.positions[symbol]
        else:
            # 部分卖出，计算新的平均成本
            remaining_shares = position.shares - shares
            self.positions[symbol] = Position(
                symbol=symbol,
                shares=remaining_shares,
                avg_cost=position.avg_cost,
                market_type=self.market_type,
                entry_date=position.entry_date,
                current_price=price,
            )

        # 记录交易
        trade = Trade(
            symbol=symbol,
            action="sell",
            shares=shares,
            price=price,
            amount=amount,
            commission=commission,
            slippage=slippage,
            trade_date=trade_date,
            market_type=self.market_type,
            net_amount=net_amount,
        )
        self.trade_history.append(trade)

        return trade

    def update_price(self, symbol: str, price: float):
        """
        更新持仓的当前价格

        Args:
            symbol: 股票代码
            price: 当前价格
        """
        if symbol in self.positions:
            self.positions[symbol].current_price = price

    def get_position(self, symbol: str) -> Optional[Position]:
        """
        获取持仓信息

        Args:
            symbol: 股票代码

        Returns:
            持仓信息，不存在则返回 None
        """
        return self.positions.get(symbol)

    def get_total_value(self) -> float:
        """
        获取组合总价值

        Returns:
            总价值（现金 + 持仓市值）
        """
        total = self.cash

        for position in self.positions.values():
            total += position.shares * position.current_price

        return total

    def get_nav(self, as_of_date: date) -> float:
        """
        获取指定日期的净值

        Args:
            as_of_date: 日期

        Returns:
            净值
        """
        return self.nav_history.get(as_of_date, self.get_total_value())

    def record_nav(self, as_of_date: date):
        """
        记录净值

        Args:
            as_of_date: 日期
        """
        self.nav_history[as_of_date] = self.get_total_value()

    def get_positions_summary(self) -> List[Dict[str, Any]]:
        """
        获取持仓摘要

        Returns:
            持仓摘要列表
        """
        summary = []
        for symbol, position in self.positions.items():
            market_value = position.shares * position.current_price
            unrealized_pnl = (position.current_price - position.avg_cost) * position.shares
            unrealized_pnl_pct = ((position.current_price - position.avg_cost) /
                                 position.avg_cost * 100)

            summary.append({
                "symbol": symbol,
                "shares": position.shares,
                "avg_cost": position.avg_cost,
                "current_price": position.current_price,
                "market_value": market_value,
                "unrealized_pnl": unrealized_pnl,
                "unrealized_pnl_pct": unrealized_pnl_pct,
                "entry_date": position.entry_date,
            })

        return summary

    def get_cash(self) -> float:
        """
        获取现金余额

        Returns:
            现金余额
        """
        return self.cash

    def get_trade_history(self) -> List[Trade]:
        """
        获取交易历史

        Returns:
            交易记录列表
        """
        return self.trade_history

    def get_nav_history(self) -> Dict[date, float]:
        """
        获取净值历史

        Returns:
            {日期: 净值} 字典
        """
        return self.nav_history

    def get_total_return(self) -> float:
        """
        获取总收益率

        Returns:
            总收益率（百分比）
        """
        total_value = self.get_total_value()
        return (total_value - self.initial_capital) / self.initial_capital * 100

    def reset(self):
        """
        重置组合到初始状态
        """
        self.cash = self.initial_capital
        self.positions = {}
        self.trade_history = []
        self.nav_history = {}

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典

        Returns:
            组合信息字典
        """
        return {
            "initial_capital": self.initial_capital,
            "cash": self.cash,
            "commission_rate": self.commission_rate,
            "min_commission": self.min_commission,
            "slippage_bps": self.slippage_bps,
            "market_type": self.market_type,
            "positions": {symbol: {
                "shares": pos.shares,
                "avg_cost": pos.avg_cost,
                "current_price": pos.current_price,
                "entry_date": pos.entry_date.isoformat(),
            } for symbol, pos in self.positions.items()},
            "trade_history": [
                {
                    "symbol": t.symbol,
                    "action": t.action,
                    "shares": t.shares,
                    "price": t.price,
                    "amount": t.amount,
                    "commission": t.commission,
                    "slippage": t.slippage,
                    "trade_date": t.trade_date.isoformat(),
                    "market_type": t.market_type,
                    "net_amount": t.net_amount,
                }
                for t in self.trade_history
            ],
            "nav_history": {
                date.isoformat(): nav for date, nav in self.nav_history.items()
            },
            "total_value": self.get_total_value(),
            "total_return": self.get_total_return(),
        }
