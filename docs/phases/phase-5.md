# Phase 5：回测引擎（第 11-12 周）

**目标**：完整回测流程可运行，输出标准绩效指标。

---

## 任务列表

**P5-T1：实现 TradingCalendar**
`pstds/backtest/calendar.py`：使用 `pandas_market_calendars` 处理美股（NYSE）和港股（HKEX）节假日；A 股使用 AKShare 的 `tool_trade_date_hist_sina` 接口获取交易日历（缓存本地）。

**P5-T2：实现 VirtualPortfolio**
`pstds/backtest/portfolio.py`：管理 `cash`、`positions`、`trade_history`，buy/sell 含手续费和滑点计算（按 DDD v2.0 第 7.2 节公式）。

**P5-T3：实现 SignalExecutor**
`pstds/backtest/executor.py`：`STRONG_BUY` 满仓、`BUY` 半仓、`HOLD` 不动、`SELL` 半仓卖出、`STRONG_SELL` 清仓，仓位比例可配置。

**P5-T4：实现 PerformanceCalculator**
`pstds/backtest/performance.py`：计算 DDD v2.0 第 7.3 节的 7 项绩效指标（累计收益、年化收益、最大回撤、夏普比率、卡尔马比率、胜率、预测准确率）。

**P5-T5：实现 BacktestRunner**
`pstds/backtest/runner.py`：主控类，核心循环中每个交易日创建 `TemporalContext.for_backtest(current_date)`，确保零前视偏差。每日快照写入 MongoDB。

**P5-T6：实现 Streamlit 回测页**
`web/pages/04_backtest.py`：日期区间选择（禁止选择未来日期）、净值曲线图（与 Buy&Hold 对比）、绩效指标卡片。

---

## Phase 5 完成门槛

```bash
echo "=== Phase 5 验证开始 ==="

# 回测引擎单元测试
python -c "
from pstds.backtest.portfolio import VirtualPortfolio
portfolio = VirtualPortfolio(initial_capital=100000, commission_rate=0.001, slippage_bps=5)
trade = portfolio.buy('AAPL', 10, 185.0)
assert portfolio.cash < 100000
assert portfolio.positions.get('AAPL', 0) == 10
print(f'✓ VirtualPortfolio 买入测试通过，剩余现金: {portfolio.cash:.2f}')
trade2 = portfolio.sell('AAPL', 10, 190.0)
print(f'✓ VirtualPortfolio 卖出测试通过，实现盈利')
"

python -c "
from pstds.backtest.calendar import TradingCalendar
cal = TradingCalendar()
from datetime import date
days = cal.get_trading_days(date(2024, 1, 1), date(2024, 1, 31), 'US')
assert len(days) > 0
assert date(2024, 1, 1) not in days  # 元旦不是交易日
print(f'✓ TradingCalendar: 2024年1月美股交易日共 {len(days)} 天')
"

python -c "
from pstds.backtest.performance import PerformanceCalculator
import pandas as pd
nav = pd.Series([100000, 101000, 99000, 102000, 103000])
metrics = PerformanceCalculator.calculate(nav, benchmark=None)
assert 'sharpe_ratio' in metrics
assert 'max_drawdown' in metrics
print(f'✓ PerformanceCalculator: 夏普比率={metrics[\"sharpe_ratio\"]:.2f}')
"

# 回测零前视偏差验证（核心）
pytest tests/integration/test_backtest_no_lookahead.py -v

echo "=== Phase 5 验证完成 ==="
```
