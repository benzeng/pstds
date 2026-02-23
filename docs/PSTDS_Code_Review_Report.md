# PSTDS v1.0 Code Review 报告

**审查日期**：2026年2月22日  
**代码规模**：8,490 行（pstds/ 核心模块）+ 2,215 行（web/）  
**审查范围**：全模块静态分析 + 关键路径逻辑追踪

---

## 总体评价

代码质量**明显高于同类 AI 辅助项目的平均水平**。架构分层清晰，铁律约束基本落地，`tradingagents/` 目录完全未被修改（✅ 遵守 C-01）。主要问题集中在两个区域：**时间隔离的覆盖盲区**和**回测引擎的 Mock 占位**。

---

## 🔴 严重问题（影响核心可信度，必须优先修复）

### BUG-001：`get_ohlcv` 时间隔离校验不完整

**位置**：`pstds/data/adapters/yfinance_adapter.py` L39、L45

**问题描述**：当前只对 `end_date` 调用了一次 `validate_timestamp`，校验的是「请求范围是否合规」，但**没有逐行校验 DataFrame 中每条数据的实际日期**。

yfinance 在以下情况会静默返回超出 `end_date` 的数据：
- 美股盘后数据（after-hours）时间戳可能晚于收盘日
- `end + Timedelta(days=1)` 这行代码（L45）本身就在向 yfinance 多请求一天

```python
# 当前代码（有漏洞）
TemporalGuard.validate_timestamp(end_date, ctx, ...)   # 只校验 end_date 本身
df = ticker.history(end=end_date + pd.Timedelta(days=1))  # 实际请求多一天！

# 修复方案：对 DataFrame 每行做过滤
df = df[df['date'].dt.date <= ctx.analysis_date]
# 或更严格：
for ts in df['date']:
    TemporalGuard.validate_timestamp(ts, ctx, 'yfinance.get_ohlcv.row')
```

**影响**：在回测中可能混入当日收盘后的数据，造成前视偏差，REG-001 测试无法真正验证此漏洞。

---

### BUG-002：`TemporalContext` 未传入原版 `TradingAgentsGraph`

**位置**：`pstds/agents/extended_graph.py` L108-L110

**问题描述**：`propagate()` 接受了 `ctx` 参数，但调用父类时完全丢弃了它：

```python
# 当前代码
final_state, signal = super().propagate(
    company_name=symbol,
    trade_date=trade_date    # ← ctx 没有传入原版图！
)
```

原版 `TradingAgentsGraph.propagate(company_name, trade_date)` 不接受 `ctx`，意味着**原版的所有 Agent（技术/基本面/新闻/情绪分析师）在运行时完全绕过了 TemporalGuard**。时间隔离只存在于 PSTDS 的包装层，原版 Agent 获取数据时不受任何时间约束。

**这是当前系统最严重的架构缺陷。**

**修复方案**（选择其一）：

方案A（推荐）：修改原版 Agent 的数据获取调用，通过 `self.ctx` 注入上下文：
```python
def propagate(self, symbol, trade_date, ctx, depth='L2'):
    self.ctx = ctx  # 存储到实例
    # 通过 monkey-patch 或 config 将 ctx 传给原版数据获取层
    self._inject_ctx_to_agents(ctx)
    final_state, signal = super().propagate(company_name=symbol, trade_date=trade_date)
```

方案B：绕过原版 propagate，直接接管数据获取层，将 `ctx` 注入到每个数据源调用。

---

### BUG-003：回测引擎使用随机价格，不可用于真实验证

**位置**：`pstds/backtest/runner.py` L252-L273

**问题描述**：`_get_mock_prices()` 使用随机漫步生成价格，注释里写「实际实现需要从数据源获取」，但这个实际实现从未完成：

```python
def _get_mock_prices(self, symbol, dates):
    import random
    base_price = 150.0
    for d in dates:
        change = random.uniform(-0.02, 0.02)  # ← 纯随机！
        base_price = base_price * (1 + change)
```

这意味着回测引擎目前：
1. 绩效指标完全基于随机数，没有参考价值
2. `SignalExecutor` 和 `VirtualPortfolio` 虽然逻辑正确，但输入无效
3. 每次运行结果都不同，无法复现

**修复方案**：

```python
def _get_real_prices(self, symbol, dates, market_type):
    """使用真实历史数据替代随机价格"""
    from pstds.data.router import MarketRouter
    router = MarketRouter()
    
    ctx = TemporalContext.for_backtest(dates[-1])  # 使用最后一天作为边界
    adapter = router.get_adapter(symbol)
    
    df = adapter.get_ohlcv(
        symbol=symbol,
        start_date=dates[0],
        end_date=dates[-1],
        interval='1d',
        ctx=ctx,
    )
    
    return {row['date'].date(): row['close'] for _, row in df.iterrows()}
```

---

### BUG-004：新闻时间戳时区不一致，可能导致过滤失效

**位置**：`pstds/data/adapters/yfinance_adapter.py` L182

**问题描述**：

```python
published_at=datetime.fromtimestamp(
    item.get("providerPublishTime", 0),
    tz=None    # ← 产生 naive datetime（无时区信息）
)
```

`TemporalContext.analysis_date` 是 `date` 类型（无时区），而 `filter_news` 在比较时使用 `news.published_at.date()`。当 `published_at` 是 naive datetime 时，时区转换可能将 UTC 时间误判为本地时间，导致：
- 北京时间用户：UTC 时间戳比本地时间晚 8 小时，当天下午发布的新闻可能被误判为「次日新闻」而被过滤
- 相反情况：次日的新闻可能漏过滤

**修复方案**：

```python
published_at=datetime.fromtimestamp(
    item.get("providerPublishTime", 0),
    tz=UTC    # ← 统一使用 UTC
)
```

同时在 `filter_news` 中确保比较时统一转换为 UTC date。

---

## 🟠 中等问题（影响测试可信度或功能完整性）

### BUG-005：REG-002 决策多样性测试是硬编码假数据

**位置**：`tests/integration/test_backtest_no_lookahead.py` L57

```python
# 这不是真正的回归测试，是一个永远通过的假测试
decisions = ["BUY", "BUY", "HOLD", "SELL", "BUY"]  # ← 手写的固定数组
unique_actions = set(decisions)
assert len(unique_actions) >= 2   # 显然永远成立
```

**影响**：REG-002 作为「回归测试」没有实际意义，无法检测系统是否真的输出多样化决策。

**修复方案**：使用 Mock LLM 驱动真实的 5 次分析调用，验证输出多样性。

---

### BUG-006：`get_ohlcv` 缺少 `assert_backtest_safe` 保护

**位置**：`pstds/data/adapters/yfinance_adapter.py`

`get_fundamentals`（L116）和 `get_news`（L165）都有 `assert_backtest_safe` 保护，但 `get_ohlcv` 没有。在 BACKTEST 模式下，`get_ohlcv` 仍然会调用 yfinance 的实时接口获取实时数据。

虽然有 `validate_timestamp(end_date)` 校验，但这是「事后校验」而不是「事前阻断」——网络请求已经发出，只是对返回结果进行校验。

**修复**：在 `get_ohlcv` 开头同样添加 `assert_backtest_safe`（BACKTEST 模式应走缓存/本地数据，不应发网络请求）。

---

### BUG-007：`data_sources` 时间戳使用当前时间而非数据时间

**位置**：`pstds/agents/extended_graph.py` L250

```python
data_timestamp = datetime.now(UTC)   # ← 应该是数据实际对应的时间，不是获取时间
```

`DataSource.data_timestamp` 的语义是「该数据项所对应的市场时间」（如「2024-01-02 收盘数据」），而不是「何时获取的」（那是 `fetched_at`）。当前写法导致数据溯源信息完全失真，无法用于审计。

---

## 🟡 改进建议（不影响当前功能，但影响长期可维护性）

### SUG-001：`extended_graph._build_graph()` 注释与实现不符

注释说「在正确位置插入 data_quality_guard_node 和 debate_referee_node」，但实际实现只是调用 `super()._build_graph()` 并加了一行注释：

```python
# 注意：在原版架构中，节点是通过 LangGraph 构建的
# 这里我们只是记录扩展功能的接口，实际的图集成需要更深入的修改
```

说明 `debate_referee` 实际上是在 `propagate()` 中手动调用的（L124），而不是真正作为图节点运行。这是合理的变通，但应该更新注释，避免误导。

---

### SUG-002：`AuditLogger` 每次调用都创建新实例，并发安全性待确认

```python
# guard.py 中多处这样写：
logger = AuditLogger()
logger.log(record)
```

每次 `validate_timestamp` 调用都创建新的 `AuditLogger` 实例，写 JSONL 文件时如果没有文件锁，在并发回测场景下（`propagate_batch`）可能出现日志乱序或丢失。建议使用单例模式或 `logging` 模块。

---

### SUG-003：`BacktestRunner.get_progress()` 未实现

```python
def get_progress(self) -> float:
    if not self.current_date:
        return 0.0
    return 0.0  # 实际实现中应该计算真实进度
```

Web 页面的进度条因此始终显示 0%。

---

## ✅ 做得好的地方

- **时间隔离核心逻辑正确**：`TemporalContext`（frozen=True）、`TemporalGuard` 的四个静态方法、审计日志写入，都按设计正确实现
- **temperature=0.0 强制执行彻底**：所有 5 个 LLM 适配器（OpenAI/Anthropic/Gemini/DeepSeek/DashScope）都有 `assert` 断言保护，不可被覆盖
- **Pydantic 模型约束完整**：`TradeDecision` 所有跨字段验证器都实现了（insufficient_data↔action、target_price_high≥low），Primary_reason 长度限制也在
- **tradingagents/ 目录完全未修改**：严格遵守了 C-01 约束
- **Web UI 规模完整**：7 个页面共 2,215 行，结构完整
- **错误处理一致**：数据适配器全部遵守「失败返回空而非抛异常」的设计原则

---

## 修复优先级与工作量估计

| 优先级 | 问题 | 预计修复时间 | 影响范围 |
|--------|------|-------------|---------|
| 🔴 P0 | BUG-002：ctx 未传入原版 Agent | 2-4小时 | 整个分析流程 |
| 🔴 P0 | BUG-003：回测使用随机价格 | 3-5小时 | 回测引擎 |
| 🔴 P1 | BUG-001：get_ohlcv 逐行时间校验 | 1小时 | 数据层 |
| 🟠 P1 | BUG-004：新闻时区问题 | 30分钟 | 新闻过滤 |
| 🟠 P2 | BUG-005：REG-002 假测试 | 2小时 | 测试可信度 |
| 🟠 P2 | BUG-006：get_ohlcv 缺少 backtest 保护 | 15分钟 | 数据层 |
| 🟡 P3 | BUG-007：data_sources 时间戳语义 | 30分钟 | 数据溯源 |
| 🟡 P3 | SUG-001~003 | 各30分钟 | 代码质量 |

---

## 建议的下一步

**第一步（本周）**：先修 BUG-002。这是最根本的问题——只要 ctx 没有真正进入原版 Agent 的数据获取层，时间隔离就只是「门面工程」。修复方式需要深入理解 TradingAgents 原版的数据流。

**第二步（本周）**：修 BUG-003，用真实历史数据替换随机价格。这样才能跑出第一次有意义的回测结果。

**第三步（下周）**：修 BUG-001 和 BUG-004，把数据层的时间隔离做严实，然后重跑 REG-001 回归测试，看审计日志是否真的干净。

完成这三步后，系统才真正达到「可信赖」的状态，可以开始用真实数据验证分析质量。

---

*本报告基于静态代码分析生成，无网络环境，未运行测试。建议配合实际运行 pytest 验证。*
