# Phase 1：功能补全核心（第 1-2 周）

**目标**：实现 v3.0 最重要的三个补全任务：NewsFilter 三级过滤器、国产 LLM 适配器、BacktestReportGenerator。

> 参考文档：DDD v3.0 第 2.1/2.4/2.5 节，ISD v2.0 第 4.1/4.4 节，TSD v2.0 NF/DS/QW 节

---

## 任务列表

### P1-T1：实现 NewsFilter 三级过滤器

**文件**：`pstds/data/news_filter.py`

实现要点（严格按照 ISD v2.0 第 4.1 节）：
- `NewsFilterStats` dataclass：4 个字段（`raw_count`、`after_temporal`、`after_relevance`、`after_dedup`）+ 2 个 property（`temporal_filtered`、`relevance_filtered`）
- `NewsFilter.filter(news_list, symbol, ctx, company_name='')` → `(List[NewsItem], NewsFilterStats)`
  - **纯函数设计**：不修改输入列表，每次调用返回新对象（C-08 约束）
  - L1 时间过滤：直接调用 `TemporalGuard.filter_news()`，不重复实现
  - L2 相关性过滤：默认使用 sklearn TF-IDF（查询词 = `symbol + " " + company_name`），`method` 参数支持切换为 embedding；corpus 为空时静默返回原列表
  - L3 余弦去重：相似度 > `dedup_threshold` 的对中保留 `published_at` 最早的
  - 任何内部错误静默降级（不传播异常），记录 `logger.warning`

同步创建 Fixture 文件：
- `tests/fixtures/news/aapl_news_low_relevance.json`（含低相关性新闻）
- `tests/fixtures/news/aapl_news_duplicates.json`（含重复内容新闻）

```bash
# 验证
pytest tests/unit/test_news_filter.py -v
# 期望：NF-001~NF-010 全部通过

pytest tests/unit/test_news_filter.py --cov=pstds/data/news_filter --cov-report=term-missing
# 期望：覆盖率 > 80%

# 纯函数验证（用含内容的列表，空列表无法检测修改行为）
python -c "
from pstds.data.news_filter import NewsFilter
from pstds.data.models import NewsItem
from pstds.temporal.context import TemporalContext
from datetime import date, datetime, timezone

ctx = TemporalContext.for_live(date(2024, 1, 2))
nf = NewsFilter()

# 构造一条合规新闻
item = NewsItem(
    title='AAPL Q4 earnings beat expectations',
    content='Apple reported strong earnings...',
    published_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    source='Reuters',
    url='https://example.com/1',
    relevance_score=0.0,
)
original_list = [item]
original_len = len(original_list)

result, stats = nf.filter(original_list, 'AAPL', ctx)

assert result is not original_list, '❌ NewsFilter 返回了输入列表本身（非纯函数）'
assert len(original_list) == original_len, '❌ NewsFilter 修改了输入列表的长度'
assert stats.raw_count == original_len
print('✓ NewsFilter 纯函数验证通过')
"
```

---

### P1-T2：集成 NewsFilter 到 data_quality_guard_node

**文件**：`pstds/agents/extended_graph.py`（更新 data_quality_guard_node）

变更要点（参考 SAD v3.0 第 2.4 节）：
- 在节点内部实例化 `NewsFilter`（从配置读取 `method`/`threshold` 参数）
- 对 `state["news_list"]` 执行 `news_filter.filter()` 三级过滤
- 将过滤后列表写回 `state["news_list"]`（后续节点直接使用）
- 将 `NewsFilterStats` 写入 `state["news_filter_stats"]`
- 同步更新 `GraphState TypedDict` 新增 `news_filter_stats` 字段

> `news_analyst_node` 不需要修改，直接接收已过滤的 `news_list`。

```bash
# 验证
pytest tests/integration/test_full_analysis_flow.py::test_news_filter_integration -v  # INT-008/009
```

---

### P1-T3：实现 DeepSeek 和 DashScope 适配器

**文件**：`pstds/llm/deepseek.py`、`pstds/llm/dashscope.py`、更新 `pstds/llm/factory.py`

① `pstds/llm/deepseek.py`：`DeepSeekClient`
- 使用 `openai` 包，`base_url="https://api.deepseek.com"`
- 从 `DEEPSEEK_API_KEY` 环境变量读取 Key（未设置 → `ConfigurationError` E010）
- `temperature` 硬编码为 `0.0`，断言保护：`assert temperature == 0.0`
- 429 响应：指数退避重试（sleep 1/2/4 秒，最多 3 次）→ `LLMRateLimitError`（E006）

② `pstds/llm/dashscope.py`：`DashScopeClient`
- `base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"`
- 从 `DASHSCOPE_API_KEY` 环境变量读取 Key
- 其余与 DeepSeekClient 相同

③ 更新 `pstds/llm/factory.py`：
- 注册两个新适配器
- `LLMFactory.create(market_type="CN_A")` 时优先返回 `DashScopeClient("qwen-max")`

```bash
# 验证
pytest tests/adapters/test_deepseek.py tests/adapters/test_dashscope.py -v
# 期望：DS-001~DS-005 和 QW-001~QW-003 全部通过

# API Key 安全验证（不得出现在任何输出中）
python -c "
import os, logging
os.environ['DEEPSEEK_API_KEY'] = 'sk-test-secret-key-12345'
logging.basicConfig(level=logging.DEBUG)
# 触发一次调用，检查日志中不出现 Key
from pstds.llm.deepseek import DeepSeekClient
try:
    c = DeepSeekClient('deepseek-chat')
except Exception:
    pass
print('✓ 请手动检查上方日志：不得出现 sk-test-secret-key-12345')
"
```

---

### P1-T4：实现 BacktestReportGenerator

**文件**：`pstds/backtest/report.py`

实现 `BacktestReportGenerator` 类（参考 DDD v3.0 第 2.4 节）：

- `__init__(backtest_result: dict, daily_records: list)`：接收 BacktestRunner 已完成的结果，不负责回测计算
- `nav_series() → Dict[str, float]`：日度净值序列 `{日期字符串: NAV值}`
- `attribution_analysis() → dict`：按 action 类型统计准确率 `{BUY: {count, correct, accuracy_pct}, SELL: {...}}`（HOLD 不计入）
- `to_markdown() → str`：生成 Markdown 报告，包含：回测概况/绩效指标表格/净值走势描述/归因分析/逐日决策摘要（最近 10 条）
- `to_docx(output_path: str)`：调用 `pstds/export/docx_exporter.py`
- `save_to_mongo(store) → str`：序列化写入 `backtest_results.report_text` 字段

```bash
# 验证
python -c "
from pstds.backtest.report import BacktestReportGenerator
# 用最小化 mock 数据测试
mock_result = {
    'symbol': 'AAPL', 'start_date': '2024-01-02', 'end_date': '2024-03-29',
    'initial_capital': 100000.0, 'final_nav': 108500.0,
    'total_return': 0.085, 'annualized_return': 0.34, 'max_drawdown': -0.032,
    'sharpe_ratio': 1.85, 'calmar_ratio': 2.1, 'win_rate': 0.62,
    'prediction_accuracy': 0.58, 'trade_count': 23, 'trading_days_count': 62,
}
mock_records = []
gen = BacktestReportGenerator(mock_result, mock_records)
md = gen.to_markdown()
assert '回测概况' in md or 'AAPL' in md
print('✓ BacktestReportGenerator.to_markdown() 正常')
nav = gen.nav_series()
print(f'✓ nav_series() 返回 {len(nav)} 条记录')
"
```

---

## Phase 1 完成门槛

```bash
echo "=== Phase 1 验证开始 ==="

# NewsFilter
pytest tests/unit/test_news_filter.py -v --tb=short
# 期望：NF-001~NF-010，10 passed

# 国产 LLM 适配器
pytest tests/adapters/test_deepseek.py tests/adapters/test_dashscope.py -v --tb=short
# 期望：DS-001~005 + QW-001~003，8 passed

# NewsFilter 集成
pytest tests/integration/test_full_analysis_flow.py::test_news_filter_integration -v --tb=short
# 期望：INT-008/009，2 passed

# 🔴 前视偏差回归（Phase 1 范围：REG-001~006，REG-007 在 Phase 2 实现后验证）
pytest tests/integration/test_backtest_no_lookahead.py::test_reg001_aapl_lookahead_elimination -v
pytest tests/integration/test_backtest_no_lookahead.py::test_reg002_five_day_decision_diversity -v
pytest tests/integration/test_backtest_no_lookahead.py::test_reg003_backtest_blocks_realtime_api -v
pytest tests/integration/test_backtest_no_lookahead.py::test_reg004_decision_reproducibility -v
pytest tests/integration/test_backtest_no_lookahead.py::test_reg005_temperature_locked -v
pytest tests/integration/test_backtest_no_lookahead.py::test_reg006_news_no_future_data -v
# 期望：REG-001~006，6 passed
# ⚠️  REG-007（情景记忆隔离）在 Phase 2 实现 EpisodicMemory 后才能运行

# 回归：确保 Phase 0 的所有测试仍然通过
pytest tests/unit/ tests/adapters/ -q --tb=short
# 期望：0 failed

echo "=== Phase 1 全部验证通过，可进入 Phase 2 ==="
```

**Phase 1 阻塞条件**：REG-001、REG-003、REG-006 任一失败，立即停止。REG-007 在 Phase 2 实现 EpisodicMemory 后才纳入阻塞条件。
