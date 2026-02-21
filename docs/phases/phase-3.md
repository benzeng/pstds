# Phase 3：智能体引擎层（第 5-7 周）

**目标**：扩展 TradingAgentsGraph，增加 TemporalContext 支持、辩论裁判员、Pydantic 输出校验。

---

## 任务列表

**P3-T1：实现扩展 LLM 工厂**
`pstds/llm/factory.py`：继承原版 LLMFactory，新增 DeepSeek 和 DashScope 适配器。**所有适配器的 temperature 参数必须硬编码为 0.0，通过断言保护：`assert kwargs.get('temperature', 0.0) == 0.0`。**

`pstds/llm/cost_estimator.py`：
- `estimate(prompt: str, model: str) -> dict`：预估阶段（按每 4 字符 ≈ 1 token 估算）
- `record_actual(usage: dict, model: str) -> dict`：核算阶段（从 API 响应 usage 字段提取）
- 价格表硬编码主流模型（可定期更新）

**P3-T2：实现 DebateRefereeNode**
`pstds/agents/debate_referee.py`：
- 输入：完整辩论历史（`investment_debate_state`）
- 输出：`DebateQualityReport` Pydantic 模型
- 4 维度评分，加权计算（30%/30%/20%/20%）
- `overall_score < 5.0` 时 `is_low_quality = True`，强制将后续 TradeDecision 的 `conviction` 降为 `LOW`

**P3-T3：实现 ExtendedTradingAgentsGraph**
`pstds/agents/extended_graph.py`：
- 继承 `TradingAgentsGraph`，重写 `_build_graph()`
- 节点插入顺序：`data_quality_guard_node`（最前）→ 原版节点 → `debate_referee_node` → `portfolio_manager_node` → `result_persistence_node`（最后）
- 重写 `propagate(symbol, date, ctx: TemporalContext, depth: str = 'L2')` 方法
- 新增 `propagate_batch(tasks: list)` 和 `propagate_stream(symbol, date, ctx)` 方法

**P3-T4：实现 Pydantic 输出校验层**
在 `portfolio_manager_node` 输出后插入校验逻辑：
- 尝试将 LLM 输出 JSON 字符串解析为 `TradeDecision`
- 失败时将错误信息追加到下一次 LLM 调用的 prompt
- 最多重试 3 次，第 3 次失败时创建 `action=INSUFFICIENT_DATA` 的 TradeDecision

**P3-T5：实现多层次记忆系统**（可简化版）
`pstds/memory/episodic.py`：使用 ChromaDB 存储近 90 天分析决策的向量表示，提供 `add_decision(trade_decision)` 和 `search_similar(symbol, context_desc)` 接口。

**P3-T6：编写集成测试**
`tests/integration/test_full_analysis_flow.py`（INT-001~007）：使用 Mock LLM（返回 `valid_trade_decision.json`），不进行真实 LLM 调用。

`tests/integration/test_backtest_no_lookahead.py`（REG-001~005）：核心回归测试，确保零前视偏差。

---

## Phase 3 完成门槛

```bash
echo "=== Phase 3 验证开始 ==="

# 集成测试（含 Mock LLM）
pytest tests/integration/test_full_analysis_flow.py -v --tb=short
# 预期：7 passed

# 🔴 最关键回归测试
pytest tests/integration/test_backtest_no_lookahead.py -v --tb=short
# 预期：5 passed（REG-001~005 全部通过）

# temperature 参数验证（不得为非零值）
python -c "
from pstds.llm.factory import LLMFactory
import inspect
factory = LLMFactory()
# 检查工厂创建的 LLM 实例 temperature 是否为 0.0
llm = factory.create_mock()
assert getattr(llm, 'temperature', 0.0) == 0.0, 'temperature 必须为 0.0！'
print('✓ temperature=0.0 验证通过')
"

# 辩论裁判员输出结构验证
python -c "
from pstds.agents.debate_referee import DebateRefereeNode, DebateQualityReport
print('✓ DebateRefereeNode 可导入')
"

# 总体覆盖率报告
pytest tests/ --cov=pstds --cov-report=term-missing --cov-report=html:htmlcov

echo "=== Phase 3 验证完成 ==="
```

**Phase 3 阻塞条件**：若 REG-001（前视偏差）或 REG-003（BACKTEST API 锁定）失败，立即停止。
