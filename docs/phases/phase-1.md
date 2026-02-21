# Phase 1：时间隔离层（最高优先级）

**目标**：实现 TemporalGuard，通过所有 TG-001~TG-012 测试，完成前视偏差消除验证。

> 🔴 **在此阶段完成前，不得开始任何其他模块的编码。**

---

## 任务列表

**P1-T1：实现 pstds/temporal/context.py**

严格按照 ISD v1.0 第 2.2 节实现：
- `frozen=True` 的 dataclass（确保不可变）
- 字段：`analysis_date: date`、`mode: Literal['LIVE','BACKTEST']`、`created_at: datetime`、`session_id: str`
- 类方法：`for_live(analysis_date)`、`for_backtest(sim_date)`
- 实例方法：`get_prompt_prefix()` — 返回完整中文时间锚定声明，必须包含 `{analysis_date}` 的实际值

**P1-T2：实现 pstds/temporal/audit.py**

- `AuditRecord` dataclass：`timestamp`、`session_id`、`analysis_date`、`data_source`、`data_timestamp`、`is_compliant: bool`、`violation_detail: str`、`caller_module: str`
- `AuditLogger` 类：`log(record: AuditRecord)` 方法，以 JSONL 格式追加写入 `data/logs/temporal_audit.jsonl`
- `get_violation_count(session_id)` 方法：返回指定会话的违规记录数量

**P1-T3：实现 pstds/temporal/guard.py**

严格按照 ISD v1.0 第 5 节实现：

```
TemporalViolationError(Exception)
  - __init__(data_timestamp, analysis_date, caller_info)
  - 错误信息格式：f"时间违规: 数据时间戳 {data_timestamp} > analysis_date {analysis_date} (调用方: {caller_info})"

RealtimeAPIBlockedError(Exception)
  - 在 BACKTEST 模式调用实时 API 时抛出

TemporalGuard（纯静态方法类）:
  validate_timestamp(data_timestamp, ctx, caller_info='') -> None
    - 将 data_timestamp 标准化为 date 类型再比较
    - 违规时：调用 AuditLogger 记录 is_compliant=False，然后抛出异常

  filter_news(news_list, ctx) -> List[NewsItem]
    - 过滤 published_at.date() > ctx.analysis_date 的项目
    - 调用 AuditLogger 记录过滤数量（filtered_count 写入 violation_detail）
    - 返回合规子列表

  assert_backtest_safe(ctx, api_name) -> None
    - ctx.mode == 'BACKTEST' 时抛出 RealtimeAPIBlockedError
    - 错误信息：f"BACKTEST 模式禁止调用实时 API: {api_name}"

  inject_temporal_prompt(base_prompt, ctx) -> str
    - 返回 ctx.get_prompt_prefix() + "\n\n" + base_prompt
```

**P1-T4：实现 pstds/agents/output_schemas.py**

严格按照 ISD v1.0 第 3 节实现 `TradeDecision` Pydantic 模型，包含所有字段约束和跨字段验证器。同时实现 `DataSource` 模型。

**P1-T5：实现 pstds/data/models.py**

实现 `NewsItem`、`OHLCVRecord` Pydantic 模型，以及 `MarketType`、`ActionType` 等类型别名。

**P1-T6：实现 pstds/data/router.py**

`MarketRouter` 类，`route(symbol: str) -> MarketType` 方法：
- `r'^[0-9]{6}$'` 且首2位在 `{'60','00','30','68','83','43'}` → `CN_A`
- `r'^\d{4,5}\.HK$'` → `HK`
- `r'^[A-Za-z]{1,5}$'` → `US`
- 其他：抛出 `MarketNotSupportedError`（继承自 `ValueError`，错误码 E009）

**P1-T7：编写测试套件**

创建以下测试文件，严格按照 TSD v1.0 第 2.1、2.2、2.3 节的用例表：

- `tests/unit/test_temporal_guard.py`：TG-001 至 TG-012（12 个用例）
- `tests/unit/test_output_schemas.py`：PM-001 至 PM-008（8 个用例）
- `tests/unit/test_market_router.py`：RT-001 至 RT-008（8 个用例）

每个测试函数的 docstring 中注明对应的用例 ID（如 `"""TG-003: 未来时间戳必须被拒绝"""`）。

---

## Phase 1 完成门槛

```bash
echo "=== Phase 1 验证开始 ==="

# 步骤 1：单元测试（必须全部通过）
pytest tests/unit/test_temporal_guard.py -v --tb=short
# 预期：12 passed

pytest tests/unit/test_output_schemas.py -v --tb=short
# 预期：8 passed

pytest tests/unit/test_market_router.py -v --tb=short
# 预期：8 passed

# 步骤 2：覆盖率检查（temporal/ 模块必须 > 95%）
pytest tests/unit/ --cov=pstds/temporal --cov-report=term-missing --cov-fail-under=95

# 步骤 3：阻塞性回归测试
pytest tests/unit/test_temporal_guard.py::test_future_timestamp_raises -v
# 预期：PASSED（TG-003 — 最关键用例）

pytest tests/unit/test_temporal_guard.py::test_backtest_blocks_realtime -v
# 预期：PASSED（TG-008）

# 步骤 4：不可变性验证
python -c "
from datetime import date
from pstds.temporal.context import TemporalContext
ctx = TemporalContext.for_live(date(2024, 1, 2))
try:
    ctx.analysis_date = date(2024, 1, 3)
    raise AssertionError('ERROR: TemporalContext 必须是不可变的！')
except Exception as e:
    if 'AssertionError' in type(e).__name__:
        raise
    print('✓ TemporalContext 不可变性验证通过')
"

# 步骤 5：提示词注入验证
python -c "
from datetime import date
from pstds.temporal.context import TemporalContext
from pstds.temporal.guard import TemporalGuard
ctx = TemporalContext.for_live(date(2024, 1, 2))
result = TemporalGuard.inject_temporal_prompt('原始提示词', ctx)
assert '2024-01-02' in result, '时间锚定声明必须包含分析日期'
assert result.startswith(ctx.get_prompt_prefix()), '时间声明必须在提示词最前面'
print('✓ 提示词注入验证通过')
"

echo "=== Phase 1 全部验证通过，可以进入 Phase 2 ==="
```

**Phase 1 阻塞条件**：若 TG-003 或 TG-008 失败，立即停止，不得进行任何后续工作。
