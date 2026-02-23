**个人专用股票交易决策系统**

PSTDS — Personal Stock Trading Decision System

**系统架构文档（SAD）v3.0**

工程质量基线 + 功能补全 + 组合分析扩展 \| 2026年3月 \| 版本 v3.0

# 1. 架构总览

## 1.1 架构设计哲学

v3.0 保持 v2.0 的六层架构和「时间优先」第一设计原则不变。主要变化：新增 portfolio/ 横向扩展模块，补全记忆系统三层架构，完整实现 v2.0 规划的 news_filter、backtest/report、llm 适配器。monkey-patch 技术债（BUG-002）在 v3.x 专项重构，v3.0 维持现状并通过文档明确标注。

## 1.2 架构设计原则更新

| **设计原则**               | **v2.0 状态**                             | **v3.0 落地方式**                                            |
|----------------------------|-------------------------------------------|--------------------------------------------------------------|
| 时间隔离优先（最高优先级） | ✅ 已实现，TemporalGuard 横切所有数据访问 | ✅ 维持，组合分析新增路径同样强制经过 TemporalGuard          |
| 核心引擎不改，扩展在外围   | ✅ 保留 tradingagents/ 不修改             | ✅ 维持，portfolio/ 模块作为独立扩展，不依赖 tradingagents/  |
| 数据流单向                 | ✅ 保留                                   | ✅ 维持                                                      |
| 层间通过接口隔离           | ✅ 保留                                   | ✅ 维持，portfolio/ 通过 MarketDataAdapter Protocol 访问数据 |
| 本地优先                   | ✅ 保留                                   | ✅ 维持，组合分析纯量化本地计算，不调用 LLM                  |
| 成本可控                   | ✅ 分级推理 + Token 预算                  | v3.0 补全：组合分析零 LLM 成本，news_filter 本地计算         |
| 确定性输出                 | ✅ temperature=0 + Pydantic               | ✅ 维持                                                      |

## 1.3 系统分层架构（六层，维持 v2.0）

> Layer 6 — 时间隔离横切层（TemporalGuard）：跨层强制中间件（✅ 维持）  
> Layer 5 — 展示层（Presentation Layer）：Streamlit Web App（♻️ 新增组合分析页、UI 升级）  
> Layer 4 — 业务协调层（Orchestration Layer）：调度器、批量队列、Token 预算管理（✅ 维持）  
> Layer 3 — 智能体引擎层（Agent Engine Layer）：TradingAgents LangGraph 图（✅ 维持）  
> + 组合分析引擎（🆕 PortfolioAnalyzer/PositionAdvisor，独立于 LangGraph）  
> Layer 2 — 数据服务层（Data Service Layer）：数据适配器、新闻聚合器（♻️ news_filter 补全）  
> + 记忆系统（♻️ 三层架构补全）  
> Layer 1 — 基础设施层（Infrastructure Layer）：SQLite、MongoDB、Parquet、ChromaDB（♻️ 新增集合）

## 1.4 关键架构决策（ADR）——v3.0 新增/变更

ADR-06（v3.0 新增）：portfolio/ 作为独立量化模块，不通过 LangGraph

- 决定：多股票组合分析（PortfolioAnalyzer/PositionAdvisor）作为独立量化模块，不进入 LangGraph 工作流，通过直接调用 DataRouter 获取数据。

- 理由：组合分析是纯量化计算（矩阵运算、统计），无需 LLM 推理，强行纳入 LangGraph 会增加复杂性并引入不必要的 LLM 成本。

- 取舍：组合分析结果无法直接注入 Agent 辩论流程（后续版本可考虑将组合风险报告作为 risk_management_node 的额外输入）。

ADR-07（v3.0 新增）：NewsFilter 作为 data_quality_guard_node 的上游预处理器

- 决定：NewsFilter 不作为独立 LangGraph 节点，而是在 data_quality_guard_node 内部调用，输出写入 data_quality_report。

- 理由：减少 LangGraph 节点数量，过滤是数据准备阶段的工作，属于数据质量守卫的职责范围。

ADR-08（v3.0 确认）：monkey-patch 技术债推迟到 v3.x 重构

- 决定：extended_graph.py 中的 \_inject_ctx_to_agents() monkey-patch 在 v3.0 中维持现状，v3.x 专项重构为依赖注入。

- 理由：重构需要修改 tradingagents/ 核心或大幅重写 extended_graph.py，风险高，优先交付新功能。已在代码中明确标注 BUG-002，加入测试保护防止并发场景下的竞态条件恶化。

ADR-01 至 ADR-05 维持 v2.0 决策不变。

# 2. 各层详细架构（v3.0 变更部分）

## 2.1 Layer 6：TemporalGuard——维持 v2.0

与 v2.0 SAD 第 2.1 节完全一致，不作变更。组合分析新增的数据访问路径（PortfolioAnalyzer.fetch_ohlcv_batch）同样强制经过 TemporalGuard.validate_timestamp。

## 2.2 Layer 1：基础设施层——v3.0 新增存储

| **存储组件**       | **类型**     | **存储内容**                                 | **v3.0 状态**                  |
|--------------------|--------------|----------------------------------------------|--------------------------------|
| market_cache.db    | SQLite       | OHLCV、技术指标（TTL 24h）、新闻（TTL 6h）   | ✅ 维持（已修复 TTL 单位 bug） |
| analysis_store     | MongoDB      | Agent 分析全文、辩论记录、结构化决策         | ✅ 维持                        |
| portfolio_analyses | MongoDB      | 🆕 组合分析结果（相关性矩阵、VaR、仓位建议） | 🆕 新增                        |
| reflection_records | MongoDB      | 🆕 预测 vs 实际价格对比记录                  | 🆕 新增                        |
| memory_patterns    | MongoDB      | 长期模式记忆条目                             | ♻️ 从占位补全实现              |
| cost_records       | MongoDB      | Token 消耗、费用明细                         | ✅ 维持                        |
| data/raw/prices/   | Parquet 文件 | 原始 OHLCV（只追加，已修复去重 bug）         | ✅ 维持（bug 已修）            |
| vector_memory/     | ChromaDB     | 近 90 天决策向量嵌入                         | ♻️ episodic 骨架补全           |
| config/            | YAML 文件    | 用户配置（已移除明文 API Key）               | ✅ 维持（S1 bug 已修）         |
| OS Keychain        | 系统密钥链   | 所有 API Key，AES-256 加密                   | ✅ 维持                        |

## 2.3 Layer 2：数据服务层——v3.0 补全 news_filter

MarketDataAdapter Protocol 和四个适配器与 v2.0 SAD 第 2.3 节一致，不变。

NewsFilter 架构（v3.0 补全）：

```python
# pstds/data/news_filter.py  
NewsFilter  
├── _score_relevance(news: NewsItem, symbol: str, keywords: List[str]) -> float  
│ # TF-IDF 余弦相似度；若 ChromaDB 可用则用句向量；返回 0.0-1.0  
├── _deduplicate(news_list: List[NewsItem]) -> List[NewsItem]  
│ # 计算通过相关性过滤的新闻两两相似度，阈值 0.85 去重  
└── filter(news_list, symbol, ctx: TemporalContext) -> NewsFilterResult  
# 调用顺序：TemporalGuard.filter_news → _score_relevance → _deduplicate
```

在 data_quality_guard_node 内的调用位置：

```python
# extended_graph.py / data_quality_guard_node  
raw_news = adapter.get_news(symbol, days_back, ctx) # 已经过时间隔离  
filter_result = NewsFilter().filter(raw_news, symbol, ctx) # 三级过滤  
state["news_items"] = filter_result.passed  
state["data_quality_report"]["news_filter"] = {  
"dropped_future": filter_result.dropped_future,  
"dropped_irrelevant": filter_result.dropped_irrelevant,  
"dropped_duplicate": filter_result.dropped_duplicate,  
}
```

## 2.4 Layer 3：智能体引擎层——v3.0 新增组合分析引擎

LangGraph 工作流图与 v2.0 SAD 第 2.4 节一致，不变。v3.0 新增独立的组合分析引擎，不在 LangGraph 中：

```python
# pstds/portfolio/analyzer.py  
class PortfolioAnalyzer:  
def analyze(symbols: List[str], ctx: TemporalContext,  
positions: Optional[Dict[str, float]] = None) -> PortfolioAnalysisResult  
# 内部调用链：  
# 1. DataRouter.get_ohlcv_batch(symbols, lookback=60, ctx) # TemporalGuard 校验  
# 2. 计算收益率矩阵 → 皮尔逊相关性矩阵  
# 3. 计算行业集中度（需 sector 信息，来自 fundamentals）  
# 4. 历史模拟 VaR（95% 置信度）  
# 5. 返回 PortfolioAnalysisResult  
  
# pstds/portfolio/advisor.py  
class PositionAdvisor:  
def advise(decisions: List[TradeDecision],  
analysis: PortfolioAnalysisResult,  
risk_profile: str) -> PositionAdvice  
# 最大夏普比率优化（等权 or confidence 加权）  
# 约束：单只 ≤ 30%，高相关对总仓位 ≤ 50%
```

## 2.5 Layer 2：记忆系统——v3.0 补全三层架构

<table>
<colgroup>
<col style="width: 25%" />
<col style="width: 25%" />
<col style="width: 25%" />
<col style="width: 25%" />
</colgroup>
<thead>
<tr class="header">
<th><strong>记忆层次</strong></th>
<th><strong>实现文件</strong></th>
<th><strong>v3.0 补全内容</strong></th>
<th><strong>关键接口</strong></th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td>短期工作记忆</td>
<td>memory/short_term.py（新增）</td>
<td>GraphState 快照序列化/反序列化<br />
支持会话恢复</td>
<td>save_snapshot(state) → str<br />
restore_snapshot(id) → GraphState</td>
</tr>
<tr class="even">
<td>中期情景记忆</td>
<td>memory/episodic.py（骨架补全）</td>
<td>search_similar() 返回实际结果<br />
滚动窗口清理</td>
<td>add_decision(decision)<br />
search_similar(symbol, context) -&gt; List[SimilarCase]</td>
</tr>
<tr class="odd">
<td>长期模式记忆</td>
<td>memory/pattern.py（新增）</td>
<td>每周批量提炼任务<br />
MongoDB 持久化</td>
<td>add_pattern(pattern)<br />
get_patterns(symbol) -&gt; List[Pattern]</td>
</tr>
<tr class="even">
<td>反事实记忆</td>
<td>memory/reflection.py（新增）</td>
<td>T+1 自动对比<br />
模式提炼触发器</td>
<td>record_outcome(analysis_id, actual_return)<br />
run_weekly_refinement()</td>
</tr>
</tbody>
</table>

## 2.6 Layer 3：LLM 适配器扩展——v3.0 补全

<table>
<colgroup>
<col style="width: 25%" />
<col style="width: 25%" />
<col style="width: 25%" />
<col style="width: 25%" />
</colgroup>
<thead>
<tr class="header">
<th><strong>提供商</strong></th>
<th><strong>实现类</strong></th>
<th><strong>v3.0 状态</strong></th>
<th><strong>关键说明</strong></th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td>OpenAI</td>
<td>OpenAIAdapter</td>
<td>✅ 已实现</td>
<td>原版</td>
</tr>
<tr class="even">
<td>Anthropic Claude</td>
<td>AnthropicAdapter</td>
<td>✅ 已实现</td>
<td>原版</td>
</tr>
<tr class="odd">
<td>Google Gemini</td>
<td>GeminiAdapter</td>
<td>✅ 已实现</td>
<td>原版</td>
</tr>
<tr class="even">
<td>DeepSeek</td>
<td>DeepSeekAdapter（llm/deepseek.py）</td>
<td>🆕 v3.0 补全</td>
<td>支持 deepseek-reasoner 推理模式<br />
流式输出；usage 字段 token 计费</td>
</tr>
<tr class="odd">
<td>阿里 DashScope</td>
<td>DashScopeAdapter（llm/dashscope.py）</td>
<td>🆕 v3.0 补全</td>
<td>qwen-max/turbo；中文优化提示词<br />
aliyun token 格式换算</td>
</tr>
<tr class="even">
<td>Ollama 本地</td>
<td>OllamaAdapter</td>
<td>✅ 已实现</td>
<td>原版+扩展</td>
</tr>
<tr class="odd">
<td>OpenRouter</td>
<td>OpenRouterAdapter</td>
<td>✅ 已实现</td>
<td>原版</td>
</tr>
<tr class="even">
<td>Trading-R1（预留）</td>
<td>TradingR1Adapter（占位）</td>
<td>⏳ v3.x</td>
<td>模型权重尚未开源</td>
</tr>
</tbody>
</table>

## 2.7 Layer 5：展示层——v3.0 新增/升级

| **页面/模块**                  | **v2.0 状态**    | **v3.0 变更**                                    |
|--------------------------------|------------------|--------------------------------------------------|
| pages/01_analysis.py           | ✅ 已实现        | ✅ 维持                                          |
| pages/02_watchlist.py          | ✅ 已实现        | ✅ 维持                                          |
| pages/03_history.py            | 基础实现         | ♻️ 新增决策准确率趋势折线图（月度）              |
| pages/04_backtest.py           | 基础实现         | ♻️ 归因分析可视化、净值曲线导出、历史报告检索    |
| pages/05_cost.py               | ✅ 已实现        | ✅ 维持                                          |
| pages/06_portfolio.py          | 持仓录入（基础） | ♻️ 与 PortfolioAnalyzer 联动，展示组合风险仪表盘 |
| pages/07_settings.py           | ✅ 已实现        | ♻️ 新增 DeepSeek/Qwen 配置项                     |
| pages/08_portfolio_analysis.py | 不存在           | 🆕 新增：相关性热力图 + 风险仪表盘 + 仓位建议    |
| components/chart.py            | 基础 K 线图      | ♻️ 全屏模式、时间周期切换、深色主题              |
| components/report_card.py      | ✅ 已实现        | ✅ 维持                                          |
| utils/exporter.py              | ✅ 已实现        | ♻️ 新增组合分析报告和回测报告导出                |

# 3. 部署架构（v3.0 更新）

## 3.1 标准部署组件清单

| **组件**             | **端口** | **角色**                               | **v3.0 状态**                                       |
|----------------------|----------|----------------------------------------|-----------------------------------------------------|
| Streamlit Web Server | 8501     | Web UI 主进程                          | ✅ 维持                                             |
| APScheduler 后台进程 | 内进程   | 定时任务（含 ReflectionEngine 周任务） | ♻️ 新增反事实记忆提炼任务                           |
| MongoDB              | 27017    | 分析结果持久库                         | ♻️ 新增 portfolio_analyses、reflection_records 集合 |
| SQLite 文件          | 无       | 行情缓存                               | ✅ 维持（bug 已修）                                 |
| ChromaDB 向量库      | 内进程   | 语义记忆检索（三层记忆补全）           | ♻️ 从骨架到完整实现                                 |
| Ollama 服务          | 11434    | 本地 LLM 推理（可选）                  | ✅ 维持                                             |

## 3.2 docker-compose.yml 变更

v3.0 docker-compose.yml 在 v2.0 基础上变更：

- 新增 APScheduler 的反事实记忆周任务调度（REFLECTION_SCHEDULE 环境变量，默认「每周一 02:00」）。

- DeepSeek 和 DashScope API Key 通过环境变量注入（DEEPSEEK_API_KEY、DASHSCOPE_API_KEY）。

- 其余配置与 v2.0 一致。

# 4. 关键接口规范（v3.0 新增部分）

## 4.1 MarketDataAdapter Protocol——维持 v2.0

与 v2.0 SAD 第 4.1 节完全一致，不作变更。

## 4.2 PortfolioAnalyzer 接口

```python
# pstds/portfolio/analyzer.py  
  
@dataclass  
class PortfolioAnalysisResult:  
symbols: List[str]  
analysis_date: date  
correlation_matrix: pd.DataFrame # shape: n x n  
high_correlation_pairs: List[Tuple[str, str, float]] # (sym1, sym2, corr) where corr > 0.7  
sector_weights: Dict[str, float] # 行业权重  
sector_concentration_warning: bool # 任一行业 > 40%  
portfolio_var_95: Optional[float] # 历史模拟 VaR（仅有持仓时计算）  
homogeneity_warning: bool # 均值相关性 > 0.6  
data_quality_score: float # 数据质量分（0-100）  
  
class PortfolioAnalyzer:  
def __init__(self, data_router: DataRouter): ...  
  
def analyze(  
self,  
symbols: List[str], # 最多 20 只  
ctx: TemporalContext, # 必填，时间隔离上下文  
positions: Optional[Dict[str, float]] = None, # {symbol: weight}  
lookback_days: int = 60,  
) -> PortfolioAnalysisResult: ...
```

## 4.3 PositionAdvisor 接口

```python
# pstds/portfolio/advisor.py  
  
@dataclass  
class PositionAdvice:  
weights: Dict[str, float] # {symbol: recommended_weight}  
rationale: Dict[str, str] # {symbol: reason}  
risk_warnings: List[str] # 组合级风险警告  
optimization_method: str # 'equal_weight' | 'confidence_weighted' | 'max_sharpe'  
  
class PositionAdvisor:  
def advise(  
self,  
decisions: List[TradeDecision], # 各股决策  
analysis: PortfolioAnalysisResult, # 组合分析结果  
risk_profile: Literal['conservative', 'balanced', 'aggressive'],  
current_positions: Optional[Dict[str, float]] = None,  
) -> PositionAdvice: ...
```

## 4.4 NewsFilter 接口

```python
# pstds/data/news_filter.py  
  
@dataclass  
class NewsFilterResult:  
passed: List[NewsItem]  
dropped_future: int  
dropped_irrelevant: int  
dropped_duplicate: int  
filter_duration_ms: float  
  
class NewsFilter:  
def __init__(self, relevance_threshold: float = 0.6,  
dedup_threshold: float = 0.85): ...  
  
def filter(  
self,  
news_list: List[NewsItem],  
symbol: str,  
ctx: TemporalContext, # 用于时间隔离校验  
keywords: Optional[List[str]] = None,  
) -> NewsFilterResult: ...
```

## 4.5 LLM 适配器接口（新增适配器签名）

```python
# pstds/llm/deepseek.py  
class DeepSeekAdapter(BaseLLMClient):  
def __init__(self, model: str, # 'deepseek-reasoner' | 'deepseek-chat'  
api_key: str, # 从 OS Keychain 获取  
temperature: float = 0.0,  
budget_tokens: Optional[int] = None): ...  
  
def complete(self, messages: List[dict],  
stream: bool = False) -> LLMResponse: ...  
# LLMResponse 包含 content, usage(input_tokens, output_tokens, cost_usd)  
  
# pstds/llm/dashscope.py  
class DashScopeAdapter(BaseLLMClient):  
def __init__(self, model: str, # 'qwen-max' | 'qwen-turbo'  
api_key: str,  
temperature: float = 0.0,  
budget_tokens: Optional[int] = None): ...
```

# 5. 记忆与学习系统架构（v3.0 补全实现）

v2.0 SAD 第 5 节描述了三层记忆架构设计，v3.0 将其完整实现。以下为各层补全的关键设计决策：

## 5.1 短期工作记忆（short_term.py，新增）

实现方式：Python dict 存储当前会话的 GraphState 快照，会话结束后自动清空。

v3.0 新增：快照序列化为 JSON 并写入临时文件（data/snapshots/），支持因异常中断后的会话恢复。最多保留最近 5 个快照，超过后自动删除最旧的。

## 5.2 中期情景记忆（episodic.py，骨架补全）

search_similar() 在 v3.0 中增强：除返回相似历史场景外，同时查询 reflection_records 集合获取该场景的实际结果，形成「相似情境 + 历史结果」完整反馈。

向量嵌入策略：优先使用 OpenAI text-embedding-3-small（若 API 可用），回退到 sentence-transformers 本地模型。

## 5.3 长期模式记忆（pattern.py，新增）

每周一次的模式提炼由 APScheduler 触发，执行 ReflectionEngine.run_weekly_refinement()：

- 从 reflection_records 中筛选：置信度 \> 0.7 且预测方向正确的记录。

- 按 symbol + 市场状态（趋势/震荡/高波动）聚合，计算各类别的胜率和样本量。

- 胜率 \> 65% 且样本量 ≥ 10 的规律，写入 memory_patterns 集合。

## 5.4 反事实记忆（reflection.py，新增）

> \# ReflectionEngine 主要方法  
>   
> record_outcome(analysis_id: str, actual_return: float) -\> None  
> \# T+1 获取价格，计算实际涨跌方向 vs 预测方向，写入 reflection_records  
>   
> run_weekly_refinement() -\> RefinementReport  
> \# 批量提炼：reflection_records → memory_patterns  
> \# 返回：新增 patterns 数量、更新 patterns 数量、样本数  
>   
> get_accuracy_trend(symbol: Optional\[str\] = None,  
> months: int = 6) -\> List\[MonthlyAccuracy\]  
> \# 返回月度预测准确率，供 UI 折线图展示

# 6. 回测引擎架构（v3.0 补全 BacktestReportGenerator）

回测引擎其他组件（BacktestRunner、TradingCalendar、VirtualPortfolio、SignalExecutor、PerformanceCalculator）与 v2.0 SAD 第 6 节一致，不变。

## 6.1 BacktestReportGenerator（v3.0 新增实现）

```python
# pstds/backtest/report.py  
  
@dataclass  
class BacktestReport:  
backtest_id: str  
symbol: str  
date_range: Tuple[date, date]  
config: dict  
performance: PerformanceMetrics # 夏普、最大回撤、年化收益等  
nav_curve: pd.DataFrame # columns: [date, portfolio_value, benchmark_value]  
daily_records: List[DailyRecord] # 逐日：date, action, confidence, actual_return, pnl  
attribution: AttributionReport # 归因分析  
  
@dataclass  
class AttributionReport:  
signal_contribution: float # 多空信号贡献（%）  
volatility_adj_contribution: float # 波动率调整贡献（%）  
data_quality_impact: float # 数据质量影响（%）  
unexplained: float # 残差  
  
class BacktestReportGenerator:  
def generate(self, runner_result: dict,  
portfolio: VirtualPortfolio,  
perf_calc: PerformanceCalculator) -> BacktestReport: ...  
  
def export_pdf(self, report: BacktestReport, output_path: str) -> None: ...  
def export_docx(self, report: BacktestReport, output_path: str) -> None: ...  
def export_markdown(self, report: BacktestReport, output_path: str) -> None: ...
```
