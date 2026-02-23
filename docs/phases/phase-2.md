# Phase 2：记忆系统完整实现（第 3-4 周）

**目标**：完整实现三层记忆系统（短期/情景/模式）和反事实反思引擎，并集成到分析流程。

> 参考文档：DDD v3.0 第 2.3 节，TSD v2.0 MS 节

---

## 任务列表

### P2-T1：实现 ShortTermMemory

**文件**：`pstds/memory/short_term.py`

```python
# 接口规范（ISD v2.0）
class ShortTermMemory:
    def __init__(self, symbol: str, ctx: TemporalContext): ...
    def set(self, key: str, value: Any) -> None: ...
    def get(self, key: str, default: Any = None) -> Any: ...
    def clear(self) -> None: ...
```

要求：
- 线程安全：不使用全局状态，每个实例独立
- 无持久化，内存存储（dict）即可
- `clear()` 供 `result_persistence_node` 在会话结束时调用

```bash
# 验证
python -c "
from pstds.memory.short_term import ShortTermMemory
from pstds.temporal.context import TemporalContext
from datetime import date
ctx = TemporalContext.for_live(date(2024, 1, 2))
mem = ShortTermMemory('AAPL', ctx)
mem.set('last_action', 'BUY')
assert mem.get('last_action') == 'BUY'
assert mem.get('missing', 'default') == 'default'
mem.clear()
assert mem.get('last_action') is None
print('✓ ShortTermMemory 验证通过')
"
```

---

### P2-T2：完整实现 EpisodicMemory

**文件**：`pstds/memory/episodic.py`（补全已有骨架）

必须实现（参考 DDD v3.0 第 2.3 节）：

① `add_decision(trade_decision, ctx)`：
- 将 `symbol + action + confidence + analysis_date + 市场状态摘要` 编码为文本
- 使用 `all-MiniLM-L6-v2` 向量化（或 TF-IDF 降级）存入 ChromaDB
- metadata 包含 `analysis_date` 字符串（用于过期清理和时间隔离过滤）

② `search_similar(symbol, ctx, top_k=5) → List[dict]`：
- 检索最相似的历史决策
- **时间隔离过滤**：过滤 `metadata.analysis_date >= ctx.analysis_date` 的记录（防止未来决策泄露，对应 REG-007）
- ChromaDB 不可用时返回 `[]`（静默降级，不抛出异常）

③ `cleanup_expired()`：删除超过 90 天的向量记录（由 APScheduler 每日触发）

```bash
# 验证
pytest tests/integration/test_memory_system.py::test_episodic_no_future_leak -v  # REG-007
python -c "
from pstds.memory.episodic import EpisodicMemory
# ChromaDB 不可用时应静默降级
mem = EpisodicMemory(db_path='/tmp/test_chroma_nonexistent_12345')
result = mem.search_similar('AAPL', None)
assert result == [], f'期望返回空列表，实际返回: {result}'
print('✓ EpisodicMemory 静默降级验证通过')
"
```

---

### P2-T3：实现 PatternMemory 和 ReflectionEngine

**文件**：`pstds/memory/pattern.py`、`pstds/memory/reflection.py`

① `PatternMemory`（DDD v3.0 第 2.3 节）：
- `get_patterns(symbol, min_evidence=5) → List[dict]`：从 MongoDB `memory_patterns` 集合查询高置信度模式，`accuracy_rate < 0.5` 的条目以 `is_positive=False` 返回
- `update_accuracy(pattern_key, correct: bool)`：原子更新（MongoDB `$inc` 操作）
- `refine_patterns(lookback_days=30)`：从 `reflection_records` 聚合挖掘新模式，幂等（upsert，相同 `pattern_key` 不产生重复条目）

② `ReflectionRecord` dataclass + `ReflectionEngine`（DDD v3.0 第 2.3 节）：
- `schedule(analysis_id, analysis_date)`：注册 APScheduler 一次性任务，触发时间 = `analysis_date + 1 交易日收盘后`（A 股 15:30，美股 16:00 ET，港股 16:00 HKT）
- `execute_reflection(analysis_id)`：完整反事实逻辑——获取实际收盘价 → 判断预测是否正确 → 写入 `reflection_records` → 调用 `PatternMemory.update_accuracy()`
- 市场数据获取复用 `DataRouter`，使用 LIVE 模式 ctx（获取实际收盘价）

```bash
# 验证
python -c "
from pstds.memory.pattern import PatternMemory
from pstds.memory.reflection import ReflectionEngine, ReflectionRecord
print('✓ PatternMemory、ReflectionEngine 可导入')
"
```

---

### P2-T4：集成记忆系统到 result_saver.py

**文件**：`pstds/agents/result_saver.py`（更新 `result_persistence_node`）

在现有 MongoDB 写入逻辑之后，追加（参考 DDD v3.0 第 3.2 节代码示例）：
```python
# 1. 情景记忆
try:
    episodic_memory.add_decision(trade_decision, ctx)
except Exception as e:
    logger.warning(f"EpisodicMemory.add_decision 失败（不影响主流程）: {e}")

# 2. 反思调度
try:
    reflection_engine.schedule(analysis_id, ctx.analysis_date)
except Exception as e:
    logger.warning(f"ReflectionEngine.schedule 失败: {e}")

# 3. 短期记忆清理
if "short_term_memory" in state and state["short_term_memory"]:
    state["short_term_memory"].clear()
```

同步更新 `pstds/scheduler/scheduler.py`，新增定时任务：
- 每日 02:00：`EpisodicMemory.cleanup_expired()`
- 每周日 02:00：`PatternMemory.refine_patterns()`

---

## Phase 2 完成门槛

```bash
echo "=== Phase 2 验证开始 ==="

# 记忆系统集成测试
pytest tests/integration/test_memory_system.py -v --tb=short
# 期望：MS-INT-001~004，4 passed

# 🔴 REG-007：情景记忆不引入未来决策（阻塞性）
pytest tests/integration/test_backtest_no_lookahead.py::test_episodic_no_future_leak -v
# 期望：PASSED

# 静默降级验证
python -c "
from pstds.memory.episodic import EpisodicMemory
mem = EpisodicMemory(db_path='/nonexistent/path')
r = mem.search_similar('AAPL', None)
assert isinstance(r, list)
print('✓ ChromaDB 不可用时静默降级正常')
"

# 全量回归（确保前序 Phase 不被破坏）
pytest tests/integration/test_backtest_no_lookahead.py -v --tb=short
# 期望：REG-001~007，7 passed

echo "=== Phase 2 全部验证通过，可进入 Phase 3 ==="
```

**Phase 2 阻塞条件**：REG-007（情景记忆未来决策泄露）失败，立即停止。这是 v3.0 新增的可信度红线。
