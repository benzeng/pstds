# BUG-002 修复方案：TemporalContext 注入原版 Agent 数据层

## 根本原因分析

读完原版代码后，数据流如下：

```
ExtendedTradingAgentsGraph.propagate(symbol, date, ctx)
  └─ super().propagate(company_name, trade_date)         ← ctx 在此丢失
       └─ graph.invoke(init_state)
            └─ market_analyst_node(state)
                 └─ LLM.bind_tools([get_stock_data])     ← LLM 自主决定调用参数
                      └─ get_stock_data(symbol, start, end)
                           └─ route_to_vendor("get_stock_data", ...)
                                └─ get_YFin_data_online(symbol, start, end)
                                     └─ yf.Ticker().history(start, end)  ← 无任何时间约束
```

**关键发现**：`get_stock_data` 的 `end_date` 参数是 LLM 在对话中自主生成的字符串（如 `"2024-01-10"`），不是程序控制的。LLM 可能传入任何日期，原版框架对此没有任何约束。

这意味着**时间隔离必须在 `route_to_vendor` 这一层拦截**，因为这是所有数据请求的唯一汇合点，且在 LLM 决策之后、数据返回之前。

---

## 修复策略：在 route_to_vendor 注入时间拦截

**核心思路**：不修改 `tradingagents/` 任何文件，而是在 `ExtendedTradingAgentsGraph` 初始化时，用一个包装后的 `route_to_vendor` 替换原版，注入时间校验逻辑。

这利用了 Python 的模块全局变量机制：原版 `core_stock_tools.py` 从 `interface.py` 导入 `route_to_vendor`，我们在运行时替换这个引用即可。

---

## 具体实现

### 新增文件：`pstds/agents/temporal_injection.py`

```python
# pstds/agents/temporal_injection.py
"""
BUG-002 修复：将 TemporalContext 注入原版 TradingAgents 数据层。

原版 route_to_vendor 不接受时间上下文，所有工具调用的 end_date 参数
由 LLM 自主生成，无时间隔离保护。

修复方式：在 ExtendedTradingAgentsGraph 启动时，用包装函数替换
tradingagents.dataflows.interface 中的 route_to_vendor，
对所有返回数据进行时间隔离校验和过滤。

约束：不修改 tradingagents/ 目录下任何文件。
"""

import re
import tradingagents.dataflows.interface as _interface
import tradingagents.agents.utils.core_stock_tools as _stock_tools
import tradingagents.agents.utils.news_data_tools as _news_tools
import tradingagents.agents.utils.technical_indicators_tools as _indicator_tools
import tradingagents.agents.utils.fundamental_data_tools as _fundamental_tools

from datetime import date, datetime
from typing import Callable, Optional
from pstds.temporal.context import TemporalContext
from pstds.temporal.guard import TemporalGuard, TemporalViolationError
from pstds.temporal.audit import AuditLogger, AuditRecord


# 保存原版 route_to_vendor，用于恢复
_original_route_to_vendor: Optional[Callable] = None


def _make_temporal_aware_router(ctx: TemporalContext, original_router: Callable) -> Callable:
    """
    创建时间感知的路由器包装函数。

    对所有进入 route_to_vendor 的调用：
    1. 拦截 end_date / curr_date 参数，确保不超过 ctx.analysis_date
    2. 对返回的字符串数据，过滤掉日期晚于 analysis_date 的行
    3. 将所有拦截行为写入审计日志
    """
    analysis_date_str = ctx.analysis_date.strftime("%Y-%m-%d")
    logger = AuditLogger()

    def temporal_aware_route(method: str, *args, **kwargs) -> str:
        # ── 步骤1：钳制输入参数中的日期 ─────────────────────────
        args = list(args)

        # get_stock_data(symbol, start_date, end_date)
        # get_news(ticker, start_date, end_date)
        # get_indicators(symbol, indicator, curr_date, look_back_days)
        # get_global_news(curr_date, look_back_days, limit)
        # get_fundamentals / get_balance_sheet 等无日期参数

        if method in ("get_stock_data", "get_news",
                      "get_global_news", "get_indicators",
                      "get_balance_sheet", "get_cashflow",
                      "get_income_statement", "get_fundamentals",
                      "get_insider_transactions"):
            args = _clamp_date_args(method, args, analysis_date_str, ctx, logger)

        # ── 步骤2：BACKTEST 模式阻断实时接口 ────────────────────
        # 注：BACKTEST 模式下原版工具仍会发网络请求（因为工具本身不知道模式）
        # 我们在此阻断，强制使用缓存（返回空结果）
        if ctx.mode == "BACKTEST":
            _log_backtest_intercept(method, ctx, logger)
            # 返回空但格式合法的字符串，让 LLM 感知数据不足
            return (
                f"[TEMPORAL ISOLATION] Data for {method} is not available in BACKTEST mode "
                f"for analysis_date={analysis_date_str}. "
                f"No data beyond {analysis_date_str} will be provided."
            )

        # ── 步骤3：调用原版路由 ───────────────────────────────────
        result = original_router(method, *args, **kwargs)

        # ── 步骤4：过滤返回数据中的未来日期行 ───────────────────
        if isinstance(result, str) and result:
            result = _filter_future_rows(result, ctx, method, logger)

        return result

    return temporal_aware_route


def _clamp_date_args(
    method: str,
    args: list,
    analysis_date_str: str,
    ctx: TemporalContext,
    logger: AuditLogger,
) -> list:
    """
    钳制参数中的日期，确保不超过 analysis_date。

    各方法参数位置：
      get_stock_data(symbol[0], start_date[1], end_date[2])
      get_news(ticker[0], start_date[1], end_date[2])
      get_indicators(symbol[0], indicator[1], curr_date[2], look_back_days[3])
      get_global_news(curr_date[0], look_back_days[1], limit[2])
      其他无日期参数
    """
    date_positions = {
        "get_stock_data": [2],       # end_date
        "get_news": [2],             # end_date
        "get_indicators": [2],       # curr_date
        "get_global_news": [0],      # curr_date
    }

    positions = date_positions.get(method, [])

    for pos in positions:
        if pos < len(args) and isinstance(args[pos], str):
            original_date = args[pos]
            clamped = _clamp_date_str(original_date, analysis_date_str)
            if clamped != original_date:
                # 记录被钳制的日期
                logger.log(AuditRecord(
                    timestamp=datetime.utcnow(),
                    session_id=ctx.session_id,
                    analysis_date=datetime.combine(ctx.analysis_date, datetime.min.time()),
                    data_source=f"temporal_injection.{method}",
                    data_timestamp=datetime.strptime(original_date, "%Y-%m-%d") if _is_date(original_date) else datetime.utcnow(),
                    is_compliant=False,
                    violation_detail=(
                        f"LLM 请求的 end_date={original_date} 被钳制为 {clamped}，"
                        f"method={method}"
                    ),
                    caller_module="temporal_injection._clamp_date_args",
                ))
                args[pos] = clamped

    return args


def _clamp_date_str(date_str: str, max_date_str: str) -> str:
    """若 date_str 晚于 max_date_str，返回 max_date_str，否则原样返回。"""
    if not _is_date(date_str):
        return date_str
    return date_str if date_str <= max_date_str else max_date_str


def _is_date(s: str) -> bool:
    """判断字符串是否是 yyyy-mm-dd 格式。"""
    return bool(re.match(r"^\d{4}-\d{2}-\d{2}$", s))


def _filter_future_rows(
    csv_text: str,
    ctx: TemporalContext,
    method: str,
    logger: AuditLogger,
) -> str:
    """
    过滤 CSV 格式字符串中日期晚于 analysis_date 的行。

    原版返回的数据格式通常是：
      # 注释行
      Date,Open,High,...
      2024-01-01,185.2,...
      2024-01-02,186.1,...

    此函数保留注释行和表头，过滤数据行中日期 > analysis_date 的行。
    """
    analysis_date_str = ctx.analysis_date.strftime("%Y-%m-%d")
    lines = csv_text.splitlines()
    filtered_lines = []
    removed_count = 0

    for line in lines:
        # 注释行和空行原样保留
        if not line or line.startswith("#"):
            filtered_lines.append(line)
            continue

        # 尝试提取行首的日期（格式 yyyy-mm-dd 或 yyyy-mm-dd HH:MM:SS）
        date_match = re.match(r"^(\d{4}-\d{2}-\d{2})", line)
        if date_match:
            row_date = date_match.group(1)
            if row_date > analysis_date_str:
                removed_count += 1
                continue  # 过滤此行

        filtered_lines.append(line)

    if removed_count > 0:
        logger.log(AuditRecord(
            timestamp=datetime.utcnow(),
            session_id=ctx.session_id,
            analysis_date=datetime.combine(ctx.analysis_date, datetime.min.time()),
            data_source=f"temporal_injection.filter.{method}",
            data_timestamp=datetime.utcnow(),
            is_compliant=False,
            violation_detail=(
                f"从 {method} 返回数据中过滤 {removed_count} 行未来数据，"
                f"analysis_date={analysis_date_str}"
            ),
            caller_module="temporal_injection._filter_future_rows",
        ))

    return "\n".join(filtered_lines)


def _log_backtest_intercept(method: str, ctx: TemporalContext, logger: AuditLogger):
    """记录 BACKTEST 模式下被阻断的实时 API 调用。"""
    logger.log(AuditRecord(
        timestamp=datetime.utcnow(),
        session_id=ctx.session_id,
        analysis_date=datetime.combine(ctx.analysis_date, datetime.min.time()),
        data_source=f"backtest_block.{method}",
        data_timestamp=datetime.utcnow(),
        is_compliant=True,  # 阻断本身是合规行为
        violation_detail=f"BACKTEST 模式阻断实时 API 调用：{method}",
        caller_module="temporal_injection._log_backtest_intercept",
    ))


# ── 公开 API ──────────────────────────────────────────────────────────────────

def inject_temporal_context(ctx: TemporalContext) -> None:
    """
    将 TemporalContext 注入原版 TradingAgents 数据层。

    调用此函数后，所有通过 route_to_vendor 的数据请求都会经过时间隔离校验。
    必须在 super().propagate() 之前调用，在之后调用 restore_original_router() 恢复。

    用法（在 ExtendedTradingAgentsGraph.propagate 中）：
        inject_temporal_context(ctx)
        try:
            final_state, signal = super().propagate(...)
        finally:
            restore_original_router()
    """
    global _original_route_to_vendor

    # 保存原版
    _original_route_to_vendor = _interface.route_to_vendor

    # 创建时间感知包装器
    wrapped = _make_temporal_aware_router(ctx, _original_route_to_vendor)

    # 替换 interface 模块中的引用
    _interface.route_to_vendor = wrapped

    # 同时替换各工具模块中已导入的引用
    # （Python import 会在模块加载时复制引用，需逐个替换）
    for module in [_stock_tools, _news_tools, _indicator_tools, _fundamental_tools]:
        if hasattr(module, "route_to_vendor"):
            setattr(module, "route_to_vendor", wrapped)


def restore_original_router() -> None:
    """恢复原版 route_to_vendor，清除时间隔离注入。"""
    global _original_route_to_vendor

    if _original_route_to_vendor is None:
        return

    _interface.route_to_vendor = _original_route_to_vendor

    for module in [_stock_tools, _news_tools, _indicator_tools, _fundamental_tools]:
        if hasattr(module, "route_to_vendor"):
            setattr(module, "route_to_vendor", _original_route_to_vendor)

    _original_route_to_vendor = None
```

---

### 修改文件：`pstds/agents/extended_graph.py`

只需修改 `propagate` 方法，其余不变：

```python
# 在文件顶部新增导入
from pstds.agents.temporal_injection import inject_temporal_context, restore_original_router

# 替换原有的 propagate 方法
def propagate(
    self,
    symbol: str,
    trade_date: date,
    ctx: TemporalContext,
    depth: str = "L2",
) -> Dict[str, Any]:
    """
    重写 propagate，通过 temporal_injection 将 ctx 注入原版数据层。
    使用 try/finally 确保无论成功失败都能恢复原版路由器。
    """
    self.ctx = ctx

    # ── 注入时间隔离（BUG-002 修复核心）────────────────────────
    inject_temporal_context(ctx)

    try:
        final_state, signal = super().propagate(
            company_name=symbol,
            trade_date=trade_date,
        )
    except Exception as e:
        return self._create_insufficient_data_decision(
            symbol, ctx, error=str(e)
        )
    finally:
        # 无论成功失败，必须恢复原版路由器
        restore_original_router()

    # 以下逻辑不变
    trade_decision = self._convert_to_trade_decision(final_state, symbol, ctx)

    debate_quality_report = None
    if "investment_debate_state" in final_state:
        debate_state = final_state["investment_debate_state"]
        debate_quality_report = self.debate_referee.evaluate(debate_state)

    if debate_quality_report and debate_quality_report.is_low_quality:
        trade_decision.conviction = "LOW"

    prompt_text = self._build_summary_prompt(final_state)
    cost_estimate = self.cost_estimator.estimate(
        prompt=prompt_text,
        model=self.config.get("deep_think_llm", "unknown"),
    )

    return {
        "symbol": symbol,
        "trade_date": trade_date,
        "analysis_date": ctx.analysis_date,
        "final_trade_decision": trade_decision,
        "debate_quality_report": debate_quality_report,
        "cost_estimate": cost_estimate,
    }
```

---

## 给 Claude Code 的操作 Prompt

把以下内容直接发给 Claude Code：

```
请修复 BUG-002（TemporalContext 未传入原版 TradingAgents 数据层）。

修复方案如下：

第一步：创建新文件 pstds/agents/temporal_injection.py
实现三个公开函数：
- inject_temporal_context(ctx)：在 propagate 调用前注入，替换 tradingagents.dataflows.interface.route_to_vendor
  为一个包装函数，该包装函数做三件事：
  1. 钳制 end_date / curr_date 参数，不超过 ctx.analysis_date
  2. BACKTEST 模式下阻断所有请求，返回说明字符串
  3. 过滤返回的 CSV 字符串中日期晚于 analysis_date 的数据行
- restore_original_router()：在 propagate 结束后恢复原版路由器
- _make_temporal_aware_router(ctx, original)：创建包装函数的内部实现

约束：不修改 tradingagents/ 目录下任何文件。

各工具方法的日期参数位置：
  get_stock_data(symbol[0], start_date[1], end_date[2]) → 钳制 args[2]
  get_news(ticker[0], start_date[1], end_date[2]) → 钳制 args[2]
  get_indicators(symbol[0], indicator[1], curr_date[2], ...) → 钳制 args[2]
  get_global_news(curr_date[0], ...) → 钳制 args[0]

inject_temporal_context 需要同时替换以下模块中的 route_to_vendor 引用：
  tradingagents.dataflows.interface
  tradingagents.agents.utils.core_stock_tools
  tradingagents.agents.utils.news_data_tools
  tradingagents.agents.utils.technical_indicators_tools
  tradingagents.agents.utils.fundamental_data_tools

第二步：修改 pstds/agents/extended_graph.py 的 propagate 方法
在 super().propagate() 调用前后用 try/finally 包裹：
  inject_temporal_context(ctx)
  try:
      final_state, signal = super().propagate(...)
  finally:
      restore_original_router()

第三步：创建测试文件 tests/unit/test_temporal_injection.py
包含以下测试用例：
- test_end_date_clamped：LLM 传入未来 end_date 时被钳制为 analysis_date
- test_backtest_blocks_all_methods：BACKTEST 模式下所有方法返回说明字符串而非真实数据
- test_future_csv_rows_filtered：CSV 返回数据中未来日期行被过滤
- test_router_restored_after_propagate：propagate 结束后原版路由器被恢复
- test_router_restored_on_exception：propagate 抛异常时路由器仍被恢复

完成后运行：
  pytest tests/unit/test_temporal_injection.py -v
  pytest tests/integration/test_backtest_no_lookahead.py::test_reg003_backtest_blocks_realtime_api -v
```

---

## 修复后的验证方法

```bash
# 1. 新增单元测试全部通过
pytest tests/unit/test_temporal_injection.py -v

# 2. 验证注入后路由器被替换
python -c "
import tradingagents.dataflows.interface as iface
from pstds.agents.temporal_injection import inject_temporal_context, restore_original_router
from pstds.temporal.context import TemporalContext
from datetime import date

original = iface.route_to_vendor
ctx = TemporalContext.for_backtest(date(2024, 1, 2))

inject_temporal_context(ctx)
assert iface.route_to_vendor is not original, '注入失败：路由器未被替换'
print('✓ 路由器已被替换')

restore_original_router()
assert iface.route_to_vendor is original, '恢复失败：路由器未被还原'
print('✓ 路由器已恢复')
"

# 3. 验证 BACKTEST 模式下数据被阻断
python -c "
import tradingagents.dataflows.interface as iface
from pstds.agents.temporal_injection import inject_temporal_context, restore_original_router
from pstds.temporal.context import TemporalContext
from datetime import date

ctx = TemporalContext.for_backtest(date(2024, 1, 2))
inject_temporal_context(ctx)
try:
    result = iface.route_to_vendor('get_stock_data', 'AAPL', '2024-01-01', '2024-01-10')
    assert 'TEMPORAL ISOLATION' in result, f'BACKTEST 阻断失败，返回了真实数据: {result[:100]}'
    print('✓ BACKTEST 模式数据阻断正常')
finally:
    restore_original_router()
"

# 4. 验证 end_date 被钳制
python -c "
import tradingagents.dataflows.interface as iface
from pstds.agents.temporal_injection import inject_temporal_context, restore_original_router
from pstds.temporal.context import TemporalContext
from datetime import date
from unittest.mock import patch

ctx = TemporalContext.for_live(date(2024, 1, 2))
inject_temporal_context(ctx)
try:
    # 用 mock 验证传给原版路由器的参数
    calls = []
    original_impl = iface.route_to_vendor.__closure__  # 获取包装器中的 original
    # 简化验证：直接检查日期钳制逻辑
    from pstds.agents.temporal_injection import _clamp_date_str
    result = _clamp_date_str('2024-01-10', '2024-01-02')
    assert result == '2024-01-02', f'钳制失败：{result}'
    print('✓ end_date 钳制逻辑正确')
finally:
    restore_original_router()
"
```

---

## 重要注意事项

**线程安全**：当前实现用全局变量存储原版路由器，`propagate_batch`（并发调用）场景下存在竞态条件。如果需要支持并发，应改为线程本地存储（`threading.local()`）或为每次调用创建独立的注入上下文。

**BACKTEST 模式的数据来源**：当前 BACKTEST 模式下所有数据请求都返回空字符串（告知 LLM 数据不足）。真正完整的回测应当从本地缓存/Parquet 文件读取历史数据，这需要在后续实现 `LocalCSVAdapter` 与原版工具的集成。这是一个独立的改进点，不影响 BUG-002 的修复正确性。
