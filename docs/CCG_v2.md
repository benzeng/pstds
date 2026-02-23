**个人专用股票交易决策系统**

PSTDS — Personal Stock Trading Decision System

**Claude Code 操作指南（CCG）v2.0**

Claude Code Developer Guide \| 2026年3月 \| 版本 v2.0

# 0. 使用前必读

## 0.1 文档体系（编码前必须全部阅读）

| **文档编号**  | **文档名称**         | **版本** | **编码中的用途**                             |
|---------------|----------------------|----------|----------------------------------------------|
| FRD           | 功能需求文档         | v3.0     | 理解每个功能"做什么"，验收标准参考           |
| SAD           | 系统架构文档         | v3.0     | 理解模块划分、依赖关系、新增组件的设计决策   |
| DDD           | 详细设计文档         | v3.0     | 目录结构、接口签名、数据库 Schema 的直接参考 |
| ISD           | 接口与数据契约规范   | v2.0     | 编写每个函数时的接口签名来源，不得偏离       |
| TSD           | 测试规范文档         | v2.0     | 编写测试用例的直接依据，覆盖率要求           |
| CCG（本文档） | Claude Code 操作指南 | v2.0     | 分阶段操作步骤和 Prompt 模板                 |

## 0.2 v3.0 编码起点说明

```bash
重要：v3.0 的起点代码已包含 Code Review 修复（9项Bug已由人工提交Claude Code完成）。编码前请先运行 pytest tests/ 确认所有现有测试通过，再开始新功能开发。不要在现有测试失败的情况下添加新代码。

# 编码前验证起点状态  
cd /path/to/pstds  
source .venv/bin/activate  
pytest tests/ -v --tb=short  
# 期望：所有现有测试通过（至少 TG-001~TG-012，PM-001~PM-008，RT-001~RT-008）  
# 如有失败，先修复再继续
```

## 0.3 Claude Code 会话管理原则（与 CCG v1.0 相同）

> 📌 每个 Phase 建议独立 Claude Code 会话；新会话开始时必须先执行会话初始化 Prompt；生成代码与文档不符时以文档为准；所有 Prompt 引用对应文档章节号。

## 0.4 会话初始化 Prompt（v2.0 更新）

**【会话初始化 Prompt — 每次新会话必须首先发送】**

```python
我正在开发 PSTDS（个人专用股票交易决策系统）v3.0 版本，基于 TradingAgents 框架。  
  
本项目有严格的设计文档体系，所有编码必须严格遵守：  
  
核心约束（必须始终遵守）：  
1. 目录结构严格按照 DDD v3.0 第1节，不得新建文档外未定义的目录  
2. 所有接口签名严格按照 ISD v2.0，不得随意修改参数名或类型  
3. TemporalContext 必须是所有数据访问方法的必填参数  
4. LLM temperature 参数必须固定为 0.0，不可配置化  
5. 不修改 tradingagents/ 目录下的任何文件  
6. 所有新增代码放在 pstds/ 目录下  
7. API Key 只从环境变量读取，禁止写入任何配置文件  
8. NewsFilter 必须是纯函数（不修改输入列表，无内部状态）  
9. PortfolioAnalyzer 使用的历史数据 end_date 必须 <= ctx.analysis_date  
  
当前阶段：[在此填写当前 Phase 编号和模块名]  
当前工作目录：/path/to/pstds  
  
请确认理解上述约束，然后我们开始本阶段的工作。
```

# 1. Phase 1：功能补全核心（第 1-2 周）

> Phase 1 包含 v3.0 最重要的三个补全任务：NewsFilter、国产LLM适配器、BacktestReportGenerator。

## 1.1 步骤 1：实现 NewsFilter 三级过滤器

**【Prompt 1.1】**

```bash
请根据 DDD v3.0 第 2.1 节和 ISD v2.0 第 4.1 节，创建 pstds/data/news_filter.py。  
  
实现要点：  
1. NewsFilterStats dataclass（ISD v2.0 第 2.3 节定义的四个字段和两个 property）  
2. NewsFilter 类的 filter() 方法：三级串联，纯函数设计（不修改输入列表）  
3. L1：直接调用 TemporalGuard.filter_news()，不重复实现  
4. L2：默认使用 sklearn TF-IDF（查询词 = symbol + company_name），  
embedding 方式通过 method 参数切换，两种方式均需处理 corpus 为空的情况  
5. L3：余弦相似度去重，相似度 > dedup_threshold 的对保留 published_at 最早的  
6. 任何内部错误静默降级（不传播异常），记录 logger.warning  
  
完成后同步创建 tests/fixtures/news/aapl_news_low_relevance.json 和  
aapl_news_duplicates.json 两个测试 Fixture（格式参考已有的 aapl_news_mixed_dates.json）

# 完成后验证  
pytest tests/unit/test_news_filter.py -v  
# NF-001 到 NF-010 全部通过  
pytest tests/unit/test_news_filter.py --cov=pstds/data/news_filter --cov-report=term-missing  
# 覆盖率 > 80%
```

## 1.2 步骤 2：更新 data_quality_guard_node 调用 NewsFilter

**【Prompt 1.2】**

```python
请更新 pstds/agents/extended_graph.py 中的 data_quality_guard_node 节点。  
  
变更要点（参考 SAD v3.0 第 2.4 节）：  
1. 在节点内部实例化 NewsFilter（从配置读取 method/threshold 参数）  
2. 对 state["news_list"] 执行 news_filter.filter() 三级过滤  
3. 将过滤后列表写回 state["news_list"]（后续节点直接使用，无需再过滤）  
4. 将 NewsFilterStats 对象写入 state["news_filter_stats"]  
5. 同步更新 GraphState TypedDict 新增 news_filter_stats 字段  
  
注意：news_analyst_node 不需要修改，它将直接接收已过滤的 news_list。
```

## 1.3 步骤 3：实现 DeepSeek 和 DashScope 适配器

**【Prompt 1.3】**

```bash
请根据 DDD v3.0 第 2.5 节和 ISD v2.0 第 4.4 节，创建以下两个文件：  
  
① pstds/llm/deepseek.py：实现 DeepSeekClient  
- 使用 openai Python 包，base_url="https://api.deepseek.com"  
- 从 DEEPSEEK_API_KEY 环境变量读取 Key（未设置→ ConfigurationError E010）  
- temperature 硬编码为 0.0  
- 429响应：指数退避重试（sleep 1/2/4秒，最多3次）→ LLMRateLimitError（E006）  
  
② pstds/llm/dashscope.py：实现 DashScopeClient  
- base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"  
- 从 DASHSCOPE_API_KEY 环境变量读取 Key  
- 其余与 DeepSeekClient 相同  
  
③ 更新 pstds/llm/factory.py：注册两个新适配器，  
LLMFactory.create(market_type="CN_A") 时优先返回 DashScopeClient("qwen-max")

# 完成后验证  
pytest tests/adapters/test_deepseek.py tests/adapters/test_dashscope.py -v  
# DS-001~DS-005 和 QW-001~QW-003 全部通过  
  
# 手动验证（需设置真实Key）  
python -c "  
import os; os.environ["DEEPSEEK_API_KEY"] = "your-key"  
from pstds.llm.deepseek import DeepSeekClient  
client = DeepSeekClient("deepseek-chat")  
print(client.invoke([{"role": "user", "content": "say hi"}]))  
"
```

## 1.4 步骤 4：实现 BacktestReportGenerator

**【Prompt 1.4】**

```python
请根据 DDD v3.0 第 2.4 节，创建 pstds/backtest/report.py，实现 BacktestReportGenerator 类。  
  
必须实现的方法：  
1. nav_series() → Dict[str, float]：日度净值序列 {日期字符串: NAV值}  
2. attribution_analysis() → dict：按 action 类型统计准确率  
{BUY: {count, correct, accuracy_pct}, SELL: {...}}（HOLD不计入）  
3. to_markdown() → str：生成 Markdown 报告文本  
包含：回测概况/绩效指标表格/净值走势描述/归因分析/逐日决策摘要（最近10条）  
4. to_docx(output_path: str)：调用 pstds/export/docx_exporter.py  
5. save_to_mongo(store) → str：序列化写入 backtest_results.report_text 字段  
  
注意：BacktestReportGenerator 不负责回测计算，它是纯数据格式化和导出层。  
输入数据来自 BacktestRunner 已完成的 backtest_result dict 和 daily_records 列表。
```

## 1.5 Phase 1 完成门槛

```bash
# Phase 1 完成验证  
pytest tests/unit/test_news_filter.py -v # NF-001~NF-010  
pytest tests/adapters/test_deepseek.py tests/adapters/test_dashscope.py -v # DS+QW  
pytest tests/integration/test_full_analysis_flow.py::test_news_filter_integration -v # INT-008/009  
pytest tests/integration/test_backtest_no_lookahead.py -v # REG-001~007（含新增006/007）
```

# 2. Phase 2：记忆系统完整实现（第 3-4 周）

## 2.1 步骤 1：实现 ShortTermMemory

**【Prompt 2.1】**

```python
请根据 DDD v3.0 第 2.3 节，创建 pstds/memory/short_term.py，实现 ShortTermMemory 类。  
  
要求：  
1. 接收 symbol 和 TemporalContext 初始化  
2. 提供 set(key, value) / get(key, default) / clear() 三个方法  
3. 线程安全：不使用全局状态，每个实例独立  
4. 无持久化，内存存储即可（dict）  
5. clear() 方法供 result_persistence_node 在会话结束时调用
```

## 2.2 步骤 2：完整实现 EpisodicMemory（补全已有骨架）

**【Prompt 2.2】**

```python
请基于现有的 pstds/memory/episodic.py 骨架，完整实现 EpisodicMemory 类。  
  
参考 DDD v3.0 第 2.3 节，必须实现：  
1. add_decision(trade_decision, ctx)：  
- 将 symbol + action + confidence + analysis_date + 市场状态摘要（PE区间/RSI/趋势）  
编码为文本，使用 all-MiniLM-L6-v2 向量化（或 TF-IDF 降级）存入 ChromaDB  
- metadata 包含 analysis_date 字符串（用于过期清理和时间隔离过滤）  
2. search_similar(symbol, ctx, top_k=5)：  
- 检索最相似的历史决策，过滤 analysis_date >= ctx.analysis_date 的记录  
（防止未来决策泄露，对应 REG-007）  
- ChromaDB 不可用时返回 []（静默降级）  
3. cleanup_expired()：删除超过90天的向量记录（由 APScheduler 每日触发）  
  
请为 search_similar 的时间隔离过滤写单元测试（MS-INT-004 对应）。
```

## 2.3 步骤 3：实现 PatternMemory 和 ReflectionEngine

**【Prompt 2.3】**

```python
请根据 DDD v3.0 第 2.3 节，创建以下两个文件：  
  
① pstds/memory/pattern.py：实现 PatternMemory  
- get_patterns(symbol, min_evidence=5)：从 MongoDB memory_patterns 集合查询  
返回高置信度（evidence_count >= min_evidence）的模式列表  
accuracy_rate < 0.5 的条目以负向参考形式返回（is_positive=False）  
- update_accuracy(pattern_key, correct)：原子更新（使用 MongoDB \$inc 操作）  
- refine_patterns(lookback_days=30)：从 reflection_records 聚合挖掘新模式  
幂等：upsert 操作，相同 pattern_key 不产生重复条目  
  
② pstds/memory/reflection.py：实现 ReflectionEngine 和 ReflectionRecord dataclass  
- schedule(analysis_id, analysis_date)：注册 APScheduler 一次性任务  
触发时间 = analysis_date + 1交易日收盘后（A股15:30，美股/港股各自时区）  
- execute_reflection(analysis_id)：实现完整反事实逻辑（见 DDD v3.0 第 2.3 节）  
- 市场数据获取复用 DataRouter，使用 LIVE 模式 ctx（获取实际收盘价）
```

## 2.4 步骤 4：集成记忆系统到 result_saver.py

**【Prompt 2.4】**

```python
请按照 DDD v3.0 第 3.2 节，更新 pstds/agents/result_saver.py 中的 result_persistence_node 函数。  
  
在现有 MongoDB 写入逻辑之后，追加以下操作（参考 DDD v3.0 中的代码示例）：  
1. try/except 包裹 EpisodicMemory.add_decision() 调用，失败时 logger.warning  
2. try/except 包裹 ReflectionEngine.schedule() 调用，失败时 logger.warning  
3. ShortTermMemory.clear()（如果 GraphState 中有 short_term_memory 实例）  
  
同步更新 APScheduler 配置（pstds/scheduler/scheduler.py），新增：  
- 每日02:00：EpisodicMemory.cleanup_expired()  
- 每周日02:00：PatternMemory.refine_patterns()
```

## 2.5 Phase 2 完成门槛

```bash
pytest tests/integration/test_memory_system.py -v # MS-INT-001~004  
# 特别验证 REG-007（情景记忆不引入未来决策）  
pytest tests/integration/test_backtest_no_lookahead.py::test_episodic_no_future_leak -v
```

# 3. Phase 3：组合分析模块（第 5-6 周）

## 3.1 步骤 1：实现 PortfolioAnalyzer

**【Prompt 3.1】**

```bash
请根据 DDD v3.0 第 2.2 节和 ISD v2.0 第 4.2 节，创建 pstds/portfolio/analyzer.py。  
  
实现要点：  
1. correlation_matrix()：  
- 从 DataRouter 获取各股 OHLCV，end_date 强制为 ctx.analysis_date（TemporalGuard）  
- 计算日收益率（pct_change），然后 DataFrame.corr()（Pearson）  
- 共同交易日 < min_common_days（默认30）时返回 None，记录 E011 警告  
2. hhi(weights)：sum(w^2)，纯计算函数，无需 ctx  
3. volatility_contribution()：边际风险贡献法（marginal contribution × weight / portfolio_vol）  
4. stress_test()：各股历史最大单日跌幅（min(pct_change)）加权求和  
  
时间隔离是重点：所有 get_ohlcv 调用必须传入 ctx，end_date 不得超过 ctx.analysis_date。

# 完成后验证  
pytest tests/unit/test_portfolio_analyzer.py -v # PA-001~PA-007  
# 特别验证时间隔离  
pytest tests/unit/test_portfolio_analyzer.py::test_correlation_time_isolation -v # PA-002
```

## 3.2 步骤 2：实现 PositionAdvisor

**【Prompt 3.2】**

```python
请根据 DDD v3.0 第 2.2 节和 ISD v2.0 第 4.3 节，创建 pstds/portfolio/advisor.py。  
  
实现 PositionAdvisor.advise() 的完整算法（ISD v2.0 中有详细步骤注释）：  
1. ACTION_TO_WEIGHT 映射（代码中的字典常量）  
2. 调用 PortfolioAnalyzer.correlation_matrix() 和 hhi()  
3. HHI 超限时的缩减算法：识别高相关对 → 按比例缩减 → 循环直到 HHI ≤ max_hhi  
4. current_positions 差值计算 → operation 字段（BUY/SELL/HOLD）  
5. 保证最终 sum(adjusted_weights) <= 1.0  
  
同时实现 PositionAdvice 和 PortfolioImpact dataclass（ISD v2.0 第 2.4/2.5 节）。
```

## 3.3 步骤 3：实现 PortfolioCoordinator

**【Prompt 3.3】**

```python
请根据 DDD v3.0 第 2.2 节，创建 pstds/portfolio/coordinator.py，实现 PortfolioCoordinator。  
  
PortfolioCoordinator 是批量分析的后处理协调器，在所有股票分析完成后调用：  
1. 接收 List[TradeDecision] 和 ctx  
2. 调用 PortfolioAnalyzer 计算相关性矩阵  
3. 调用 PositionAdvisor 获取调整后仓位建议  
4. 将 PortfolioImpact 回填到每个 TradeDecision 的 portfolio_impact 字段  
5. 构造 portfolio_snapshot dict 写入 MongoDB portfolio_snapshots 集合  
  
注意：单股分析不经过 PortfolioCoordinator，portfolio_impact 保持 None。  
批量分析入口在 ExtendedTradingAgentsGraph.propagate_batch() 中调用 Coordinator。
```

## 3.4 步骤 4：实现 08_portfolio_analysis.py 页面

**【Prompt 3.4】**

```python
请根据 FRD v3.0 第 9.2 节，创建 web/pages/08_portfolio_analysis.py。  
  
UI 组件（按从上到下顺序）：  
1. 多股票代码输入框（st.text_area，逗号分隔，说明最多20只）  
2. 时间窗口选择器（st.selectbox：30/60/90/180天）  
3. 分析按钮，点击后调用 PortfolioAnalyzer  
4. 相关性热力图（Plotly go.Heatmap）：  
- colorscale="RdBu_r"（红=高相关，蓝=低/负相关）  
- 相关系数>0.7的格子添加矩形注释标记  
- 悬停显示精确系数值（小数点后2位）  
5. 仓位建议面板：展示 PositionAdvice 列表，用 st.progress 可视化仓位比例  
6. 压力测试结果（明确标注"历史情景假设，非预测"）  
  
图表使用 Plotly，不使用 st.pyplot（避免静态图）。
```

## 3.5 Phase 3 完成门槛

```bash
pytest tests/unit/test_portfolio_analyzer.py -v # PA-001~PA-007  
pytest tests/integration/test_portfolio_flow.py -v # PA-INT-001~PA-INT-004  
# 组合时间隔离回归  
pytest tests/integration/test_portfolio_flow.py::test_portfolio_temporal_isolation -v
```

# 4. Phase 4：Web UI 升级（第 7-8 周）

## 4.1 步骤 1：升级 06_portfolio.py

**【Prompt 4.1】**

```python
请大幅升级 web/pages/06_portfolio.py，将其从基础框架升级为完整的持仓管理页面。  
  
参考 FRD v3.0 第 9.1 节和 SAD v3.0 第 2.6 节：  
1. 持仓录入区：表格形式，columns = [股票代码, 持仓数量, 成本价, 当前价（自动获取）]  
2. 相关性热力图（复用 08_portfolio_analysis.py 的热力图组件）  
3. 波动率贡献饼图（Plotly go.Pie）  
4. 仓位建议面板（基于当前持仓调用 PositionAdvisor）  
5. 压力测试区块  
  
提取热力图和仓位面板为 web/components/ 中的可复用函数，供06和08两个页面共用。
```

## 4.2 步骤 2：升级 chart.py（K线图增强）

**【Prompt 4.2】**

```python
请根据 FRD v3.0 第 9.3 节，升级 web/components/chart.py。  
  
变更要点：  
1. 全屏模式：chart 容器外层包裹 Plotly config={"displayModeBar": True}，  
并添加 fullscreen 按钮（config={"modeBarButtonsToAdd": ["toggleFullscreen"]}）  
2. 多均线开关：在图表旁添加 st.multiselect 让用户选择显示 MA5/MA10/MA20/MA60  
3. 成交量配色：从配置/symbol 判断市场类型，A股用红涨绿跌（红=#F63538，绿=#30CC5A），  
美股/港股用绿涨红跌（颜色相反）  
4. 所有子图时间轴联动：xaxis_rangeslider_visible=False，使用 shared_xaxes=True  
  
保持四层布局结构（主图K线/成交量/MACD/RSI）不变，仅在此基础上增强。
```

## 4.3 步骤 3：升级 03_history.py 添加准确率趋势图

**【Prompt 4.3】**

```python
请在 web/pages/03_history.py 中新增"决策准确率趋势"模块。  
  
功能要求（参考 FRD v3.0 第 9.1 节 US-13）：  
1. 从 MongoDB reflection_records 聚合查询月度准确率  
Pipeline: 按月分组 → 统计 prediction_correct=True 的比例  
2. 展示为 Plotly 折线图，X轴=月份，Y轴=准确率（0-100%），添加 50% 基准线  
3. 过滤器：市场类型（全部/A股/美股/港股）和分析深度（L0/L1/L2/L3）  
4. 数据不足时（< 5 条 reflection 记录）显示提示：  
"暂无足够历史数据，需累积约30次分析后趋势图才有统计意义"  
  
如果 reflection_records 集合不存在或为空，页面正常显示（不抛出异常）。
```

## 4.4 步骤 4：升级 01_analysis.py 新增展示组件

**【Prompt 4.4】**

```python
请在 web/pages/01_analysis.py 中，在分析完成后的结果展示区新增两个组件：  
  
① 新闻过滤统计（在新闻标签页顶部）：  
使用 st.columns(4) 展示四个 st.metric：  
- "原始新闻"：stats.raw_count  
- "时间过滤后"：stats.after_temporal（delta=temporal_filtered，红色）  
- "相关性过滤后"：stats.after_relevance（delta=relevance_filtered，红色）  
- "最终使用"：stats.after_dedup（加粗显示）  
数据来源：GraphState.news_filter_stats  
  
② 情景记忆侧边栏（st.sidebar 底部）：  
标题"相似历史决策"，展示 similar_past_decisions 列表（最多5条）  
每条显示：日期、action徽章、confidence值  
如果列表为空，显示"（首次分析，暂无历史参考）"
```

## 4.5 Phase 4 完成门槛

```bash
# 手动端到端检查清单  
streamlit run web/app.py  
# □ 08_portfolio_analysis 页面可打开，热力图正常渲染  
# □ 06_portfolio 页面热力图和波动率图正常  
# □ 01_analysis 分析完成后显示新闻过滤四格指标  
# □ 03_history 准确率趋势图（无数据时显示提示文字，不崩溃）  
# □ K线图有全屏按钮，均线可单独开关  
# □ 深色主题下无白色背景块  
  
# 自动化测试  
pytest tests/ -v --tb=short  
# 所有测试（包括Phase 1-3新增的）继续通过
```

# 5. 常见问题与处理规范（v2.0 更新）

## 5.1 代码与设计文档不符（继承自 CCG v1.0）

> 📌 与 CCG v1.0 第 8.1 节相同的5条规则继续有效。v2.0 新增以下场景。

| **场景**                                    | **处理方式**                                                                         |
|---------------------------------------------|--------------------------------------------------------------------------------------|
| NewsFilter 实现为有状态类（保存了处理历史） | 立即要求修改为纯函数设计（不修改输入列表，每次调用返回新对象）                       |
| PortfolioAnalyzer 的 OHLCV 获取未传入 ctx   | 立即要求修正，这会导致 TemporalGuard 无法校验，是阻塞性问题                          |
| 记忆系统写入使用同步调用影响分析延迟        | 要求改为 try/except 包裹并用异步或线程调用，不影响主流程返回时间                     |
| API Key 出现在代码或日志中                  | 立即要求清除，改为环境变量读取，检查日志级别确保Key不被打印                          |
| 组合分析使用了 analysis_date 之后的价格     | 这是严重错误，立即停止，修复 PortfolioAnalyzer.correlation_matrix() 的 end_date 约束 |

## 5.2 Phase 2 记忆系统相关问题

| **问题**                                    | **处理步骤**                                                                                                       |
|---------------------------------------------|--------------------------------------------------------------------------------------------------------------------|
| ChromaDB 初始化失败（首次运行或依赖未安装） | pip install chromadb；若环境不支持，确认 EpisodicMemory 的静默降级逻辑正常（返回空列表不抛出异常）                 |
| 情景记忆检索返回了未来的决策                | 立即检查 search_similar() 的过滤条件，确认 metadata.analysis_date \< ctx.analysis_date 过滤生效，运行 REG-007 测试 |
| 反事实任务在测试中干扰其他测试              | 测试环境中 Mock APScheduler，不真正注册任务；或使用 @pytest.mark.timeout 防止等待                                  |

## 5.3 Phase 3 组合分析相关问题

| **问题**                      | **处理步骤**                                                                         |
|-------------------------------|--------------------------------------------------------------------------------------|
| 相关性矩阵为 None（数据不足） | 检查 Fixture 数据是否有至少30个共同交易日；测试中使用完整季度数据                    |
| HHI 调整后仍然超过 max_hhi    | 检查循环终止条件；若所有股票都高相关，按比例均等缩减直到满足约束                     |
| 组合分析不符合时间隔离要求    | 运行 PA-002（test_correlation_time_isolation）；确认 DataRouter.get_ohlcv() 传入 ctx |

# 6. 最终验证（全部 Phase 完成）

```bash
# 完整测试套件  
pytest tests/ -v --tb=short  
  
# 覆盖率报告  
pytest tests/ --cov=pstds --cov-report=html --cov-report=term-missing  
# 要求: pstds/temporal/ > 95%，总体 > 80%  
  
# 全部回归测试（必须100%通过）  
pytest tests/integration/test_backtest_no_lookahead.py -v # REG-001~REG-007  
  
# 端到端冒烟测试  
python -c "  
from pstds.agents.extended_graph import ExtendedTradingAgentsGraph  
from pstds.temporal.context import TemporalContext  
from datetime import date  
ctx = TemporalContext.for_live(date(2024, 1, 2))  
graph = ExtendedTradingAgentsGraph(config={"analysis_depth": "L1"})  
result = graph.propagate("AAPL", "2024-01-02", ctx=ctx)  
assert result["decision"]["action"] in ["STRONG_BUY","BUY","HOLD","SELL","STRONG_SELL","INSUFFICIENT_DATA"]  
assert result.get("news_filter_stats") is not None  
print("v3.0 端到端冒烟测试通过")  
"  
  
# 组合分析冒烟测试  
python -c "  
from pstds.portfolio.analyzer import PortfolioAnalyzer  
from pstds.temporal.context import TemporalContext  
from datetime import date  
ctx = TemporalContext.for_live(date(2024, 3, 29))  
# 使用 Mock DataRouter  
analyzer = PortfolioAnalyzer(mock_router, config={})  
matrix = analyzer.correlation_matrix(["AAPL", "NVDA"], ctx)  
print(f"相关性矩阵形状: {matrix.shape}")  
print("组合分析冒烟测试通过")  
"

记住：Phase 3 的组合分析时间隔离（PA-002 测试）和 Phase 2 的情景记忆未来决策隔离（REG-007）是 v3.0 新增的两条可信度红线，与 v2.0 的前视偏差回归测试（REG-001）同等重要，必须在生产使用前全部通过。
```
