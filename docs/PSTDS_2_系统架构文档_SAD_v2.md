**个人专用股票交易决策系统**

*PSTDS --- Personal Stock Trading Decision System*

**系统架构文档（SAD）v2.0**

综合改进方案 + PSTDS 用户方案 \| 2026年2月 \| 版本 v2.0

**1. 架构总览**

**1.1 架构设计哲学**

PSTDS v2.0 在
v1.0「分层松耦合」基础上，引入「时间优先」作为第一设计原则，从根本上解决了原
TradingAgents 框架的前视偏差问题。五层架构保持不变，但在 Layer
2（数据服务层）之上增加了一个横切关注点------TemporalGuard
时间隔离层，它作为所有数据访问的强制中间件存在，而非可选组件。

  ----------------------------------------------------------------------------------
  **设计原则**                     **v1.0 状态** **v2.0 落地方式**
  -------------------------------- ------------- -----------------------------------
  时间隔离优先（新增最高优先级）   无            TemporalGuard
                                                 横切所有数据访问，analysis_date
                                                 强制参数

  核心引擎不改，扩展在外围         是            保留，ExtendedTradingAgentsGraph
                                                 通过继承扩展

  数据流单向                       是            保留，增加 TemporalGuard 拦截点

  层间通过接口隔离                 是            保留，新增 TemporalContext Protocol

  本地优先                         是            保留，Ollama 为零成本默认后备

  成本可控（新增）                 部分          Token 预算硬性上限 + 4
                                                 级分析深度自动路由

  确定性输出（新增）               无            temperature=0 锁定 + Pydantic
                                                 校验 + 决策哈希缓存
  ----------------------------------------------------------------------------------

**1.2 系统分层架构（六层）**

  -----------------------------------------------------------------------------------
  *Layer 6 ---
  时间隔离横切层（TemporalGuard）：跨层中间件，拦截所有数据请求并注入时间约束（v2.0
  新增） Layer 5 --- 展示层（Presentation Layer）：Streamlit Web
  App、报告导出、通知推送、成本仪表盘 Layer 4 --- 业务协调层（Orchestration
  Layer）：调度器、批量任务队列、并行协调器、Token 预算管理器 Layer 3 ---
  智能体引擎层（Agent Engine Layer）：TradingAgents LangGraph 图、Agent 团队、LLM
  适配器、Pydantic 输出校验 Layer 2 --- 数据服务层（Data Service
  Layer）：市场数据适配器、新闻聚合器、缓存管理器、数据质量校验器 Layer 1 ---
  基础设施层（Infrastructure Layer）：SQLite 缓存库、MongoDB 结果库、Parquet
  原始数据仓库、配置管理、ChromaDB 向量记忆库*

  -----------------------------------------------------------------------------------

**1.3 关键架构决策（ADR）**

**ADR-01：TemporalGuard 作为强制横切层而非可选组件**

决定：TemporalGuard
不是可配置开关，而是所有数据访问路径上的强制拦截器。理由：前视偏差是致命缺陷，可选设计给了绕过的可能，导致用户在不知情的情况下得到失效的回测结果。取舍：增加了数据访问的复杂性，但这是为可信度付出的必要代价。

**ADR-02：保留 Streamlit 作为 Web 前端**

决定：沿用 Streamlit，不升级为 FastAPI +
React。理由：个人项目优先开发效率，Streamlit 与 Python
生态无缝集成，维护成本低，TradingAgents
社区已有成熟实现可参考。取舍：牺牲细粒度 UI
定制能力，个人场景无高并发需求。

**ADR-03：MongoDB 用于分析结果，SQLite 用于行情缓存，Parquet
用于回测原始数据**

决定：三种存储按用途分离。理由：MongoDB 文档模型直接映射嵌套 JSON
报告；SQLite 零依赖适合 TTL 缓存；Parquet
列存格式适合时序行情数据的高效读写。取舍：三种存储引入了额外复杂性，但各自是该场景的最优选择。

**ADR-04：ChromaDB 作为向量记忆库（v2.0 新增）**

决定：引入 ChromaDB 本地向量数据库替代原版 BM25
文本检索作为中期记忆系统。理由：语义检索能力更强，能识别相似但措辞不同的历史决策场景；完全本地部署，无隐私风险。取舍：引入新依赖，增加了启动复杂性。

**ADR-05：Trading-R1 预留接口**

决定：v2.0 不集成 Trading-R1 微调模型，LLMFactory
中保留提供商槽位。理由：模型权重尚未开源，微调训练数据未发布。预留方案：待开源后通过配置文件启用，无需修改核心代码。

**2. 各层详细架构**

**2.1 Layer 6：TemporalGuard 时间隔离层（v2.0 核心新增）**

  -----------------------------------------------------------------------------------------------------------------------------------
  *TemporalGuard 是 v2.0
  最重要的架构创新，解决了原框架的致命前视偏差问题。它不属于任何单一层，而是横切所有层的强制中间件，类似于安全框架中的认证拦截器。*

  -----------------------------------------------------------------------------------------------------------------------------------

**TemporalGuard 工作机制**

- 每次分析任务启动时，创建一个 TemporalContext 对象，绑定
  analysis_date（分析基准日期）和 mode（LIVE / BACKTEST）。

- TemporalContext
  通过依赖注入传入数据服务层和智能体引擎层的所有数据访问组件。

- 数据适配器在执行任何查询前，调用
  TemporalGuard.validate(data_timestamp,
  analysis_date)，校验失败则拒绝返回数据。

- 新闻数据的 published_at 字段由 TemporalGuard 强制校验，published_at \>
  analysis_date 的文章被丢弃并记录审计日志。

- BACKTEST 模式下，TemporalGuard 额外锁定所有外部实时 API
  调用，强制使用本地历史缓存。

**LLM 知识隔离机制**

TemporalGuard 还负责为所有智能体注入标准时间锚定声明，成为 Agent
系统提示词的强制前缀：

+-------------------------------------------------------------------+
| 【时间隔离声明（TemporalGuard 强制注入）】                        |
|                                                                   |
| 你当前正在分析 {analysis_date} 这一天的市场情况。                 |
|                                                                   |
| 不得引用该日期之后发生的任何事件、数据或新闻。                    |
|                                                                   |
| 你的所有分析必须基于以下明确提供的数据，                          |
|                                                                   |
| 不得使用训练记忆中的具体财务数字或新闻内容。                      |
|                                                                   |
| 若提供数据不足以支撑结论，输出 INSUFFICIENT_DATA 标志。           |
+-------------------------------------------------------------------+

**2.2 Layer 1：基础设施层**

**存储架构**

  -------------------------------------------------------------------------------------------------------
  **存储组件**       **类型**     **存储内容**                               **保留策略**
  ------------------ ------------ ------------------------------------------ ----------------------------
  market_cache.db    SQLite       OHLCV 行情、技术指标（TTL 24h）、新闻（TTL 行情数据永久保留（回测用）
                                  6h）                                       

  analysis_store     MongoDB      Agent                                      永久，≥ 2 年
                                  分析全文、辩论记录、结构化决策摘要、Cost   
                                  Records                                    

  data/raw/prices/   Parquet 文件 原始 OHLCV 数据，按股票代码分文件，只追加  永久，回测基础数据

  data/raw/news/     JSON 文件    新闻文章（含 published_at），只追加        永久，回测基础数据

  vector_memory/     ChromaDB     近 90 天决策历史的向量嵌入，支持语义检索   滚动窗口 90 天

  config/            YAML 文件    用户配置、LLM                              版本控制
                                  设置、数据源偏好、分析深度模板             

  OS Keychain        系统密钥链   所有 API Key，AES-256 加密                 用户管理
  -------------------------------------------------------------------------------------------------------

**配置管理三级覆盖**

- 第一优先级：环境变量（.env）------部署时覆盖，适合 Docker 场景。

- 第二优先级：用户配置（config/user.yaml）------个人偏好，持久保存，不进版本控制。

- 第三优先级：系统默认（config/default.yaml）------TradingAgents
  DEFAULT_CONFIG 扩展版，含 v2.0 新增配置项。

**2.3 Layer 2：数据服务层**

**市场数据适配器架构**

所有适配器实现统一的 MarketDataAdapter
Protocol，新增市场或数据源无需修改上层代码。v2.0 中每个适配器都必须接受
TemporalContext 参数。

  -----------------------------------------------------------------------------------------------
  **适配器**            **覆盖市场**           **数据类型**                   **时间隔离支持**
  --------------------- ---------------------- ------------------------------ -------------------
  YFinanceAdapter       美股、港股、ETF        OHLCV、基本面、财务报表        ✓ date 参数过滤

  AlphaVantageAdapter   美股（主/备）          行情、新闻、基本面             ✓ 历史端点支持

  AKShareAdapter        A股（沪深）、港股      行情、财务、资金流、东财情绪   ✓ 历史区间参数

  LocalCSVAdapter       任意市场（用户自备）   用户提供的本地历史数据         ✓ 天然隔离
  -----------------------------------------------------------------------------------------------

**数据流与缓存策略**

- DataRouter
  根据股票代码格式判断市场类型（6位数字60/000/002/300→A股；.HK→港股；英文字母→美股）。

- CacheManager 检查 SQLite 是否存在有效缓存（TTL
  内）且通过时间隔离校验。

- 缓存未命中时调用适配器获取数据，数据写入 SQLite 缓存同时追加写入
  Parquet/JSON 原始存储。

- 主源失败时 FallbackManager
  自动切换备用源，记录降级事件到数据质量报告。

**数据质量守卫（Data Quality Guardian）**

分析流程启动前执行独立的数据质量检查节点，输出数据质量报告：

  --------------------------------------------------------------------------------------
  **检查项目**       **检查方式**                           **失败处理**
  ------------------ -------------------------------------- ----------------------------
  价格数据完整性     时序连续性检查、价格非负、成交量非零   标记缺口，警告用户

  财报数据完整性     必需字段（PE/PB/ROE）存在性检查        标记缺失字段，降级分析

  新闻时间戳合规     published_at ≤ analysis_date 校验      强制丢弃违规新闻

  股票异常事件检测   停牌检测、分拆/合并调整检测            提醒用户数据可能不可靠
  --------------------------------------------------------------------------------------

**2.4 Layer 3：智能体引擎层**

**LangGraph 工作流图结构**

ExtendedTradingAgentsGraph 继承原版
TradingAgentsGraph，通过子类扩展实现功能增强。v2.0
在原版节点基础上增加了 3 个关键节点：

  -----------------------------------------------------------------------------------------------------
  **节点名称**                **来源**      **v2.0 变更说明**
  --------------------------- ------------- -----------------------------------------------------------
  data_quality_guard_node     v2.0 新增     流程最前端，运行数据质量守卫，输出 data_quality_report

  technical_analyst_node      原版+扩展     新增A股技术指标适配；引入价格异常检测；接受 TemporalContext

  fundamentals_analyst_node   原版+扩展     A股财务字段映射；强制 API 数据；禁止引用训练记忆

  news_analyst_node           原版+扩展     三级相关性过滤；时间戳严格校验；东财新闻源集成

  sentiment_analyst_node      原版+扩展     东方财富股吧集成；24h/7d 双窗口；来源引用记录

  bull_researcher_node        原版+改进     立场随机化；论据引用要求；低质量辩论标记

  bear_researcher_node        原版+改进     同上，防连续BUY机制触发时加强权重

  debate_referee_node         v2.0 新增     4维度辩论质量评分，低于阈值标记 LOW_CONFIDENCE

  trader_node                 原版+扩展     5档决策输出；波动率调整；结构化仓位建议（Trading-R1方法）

  risk_management_node        原版+扩展     组合级相关性风险检查；持仓集中度评估

  portfolio_manager_node      原版          结构化 JSON 最终决策输出（v2.0 Pydantic 校验）

  result_persistence_node     v1.0+扩展     写入 MongoDB；cost_records 记录；向量记忆更新
  -----------------------------------------------------------------------------------------------------

**GraphState 扩展字段（v2.0 新增）**

  ------------------------------------------------------------------------------------------
  **新增字段名**          **类型**          **说明**
  ----------------------- ----------------- ------------------------------------------------
  temporal_context        TemporalContext   时间上下文，含 analysis_date 和 mode

  data_quality_report     dict              数据获取质量报告（质量分、降级记录、缺失字段）

  analysis_id             str (UUID)        本次分析唯一标识，用于 MongoDB 存储和审计追踪

  llm_cost_actual         dict              实际 Token 消耗统计（从 API 响应 usage
                                            字段提取）

  confidence_scores       dict              各 Agent 节点的置信度评分（0.0-1.0）

  debate_quality_score    float             辩论裁判员给出的综合质量评分（0-10）

  volatility_adjustment   float             20日历史波动率调整系数（参考 Trading-R1 方法）

  decision_hash           str               输入数据+模型配置哈希，用于缓存命中判断
  ------------------------------------------------------------------------------------------

**Pydantic 结构化输出校验**

v2.0 在 portfolio_manager_node 输出处强制执行 Pydantic
校验，确保决策结构完整性：

+---------------------------------------------------------------------+
| TradeDecision 模型必填字段：                                        |
|                                                                     |
| action:                                                             |
| Literal\[\'STRONG_BUY\',\'BUY\',\'HOLD\',\'SELL\',\'STRONG_SELL\'\] |
|                                                                     |
| confidence: float \# 0.0-1.0                                        |
|                                                                     |
| conviction: Literal\[\'HIGH\',\'MEDIUM\',\'LOW\'\]                  |
|                                                                     |
| primary_reason: str \# max_length=100                               |
|                                                                     |
| target_price_low: Optional\[float\]                                 |
|                                                                     |
| target_price_high: Optional\[float\]                                |
|                                                                     |
| time_horizon: str                                                   |
|                                                                     |
| risk_factors: List\[str\] \# 至少 1 条                              |
|                                                                     |
| data_sources: List\[DataSource\] \# 含 url 和 timestamp             |
|                                                                     |
| analysis_date: date                                                 |
|                                                                     |
| analysis_timestamp: datetime                                        |
|                                                                     |
| volatility_adjustment: float                                        |
|                                                                     |
| debate_quality_score: float                                         |
+---------------------------------------------------------------------+

**2.5 Layer 4：业务协调层**

**Token 预算管理器（v2.0 新增）**

- 每次分析任务启动前，根据分析深度级别（L0-L3）和历史平均消耗，预估本次
  Token 用量。

- 设置硬性上限：超出预算自动降级分析深度或截断输入，不允许无限制消耗。

- 输入侧截断规则：新闻摘要 ≤ 500 tokens/条，财报摘要 ≤ 2000
  tokens，强制执行。

- 调用完成后从 API 响应 usage 字段提取实际消耗，写入 MongoDB
  cost_records 集合。

**并行分析协调器（v2.0 增强）**

- 使用 asyncio 实现多股票并行分析，I/O
  等待时间重叠，最大并发数由配置控制（默认 3，可调至 10）。

- LLM 调用层实现令牌桶限流，避免触发 API Rate Limit。

- 并行分析完成后，Portfolio Coordinator
  汇总各股信号，检查组合相关性约束（防止过度集中于同一风险因子）。

**任务调度器**

- 使用 APScheduler 实现定时任务，支持 Cron 表达式（如「工作日 08:30
  分析自选股」）。

- 任务状态机：PENDING → RUNNING → COMPLETED / FAILED，自动重试最多 3
  次。

- 调度配置持久化存储于 MongoDB scheduled_tasks 集合。

**2.6 Layer 5：展示层**

  ---------------------------------------------------------------------------------------------------------------------------
  **页面/模块**               **功能描述**
  --------------------------- -----------------------------------------------------------------------------------------------
  pages/01_analysis.py        主分析界面：股票输入、参数配置（深度级别/LLM/风险偏好）、实时进度（节点权重进度条）、结果展示

  pages/02_watchlist.py       自选股管理：分组标签、批量并行分析、Cron 定时配置

  pages/03_history.py         历史记录：检索过滤、决策趋势图、与当前分析对比

  pages/04_backtest.py        回测界面：日期区间、参数配置、净值曲线、绩效指标（v2.0 新增）

  pages/05_cost.py            成本仪表盘：本次消耗、月度趋势、上限告警配置（v2.0 新增）

  pages/06_portfolio.py       持仓管理：当前仓位录入、风险敞口仪表盘（可选）

  pages/07_settings.py        系统设置：LLM 配置、API Key 管理、数据源偏好、通知设置

  components/chart.py         K线图（蜡烛+布林带+均线）+ 成交量 + MACD + RSI，Plotly 交互

  components/report_card.py   分析师报告卡片、辩论时间线、决策徽章（5档颜色标识）

  utils/exporter.py           报告导出：PDF（WeasyPrint）、DOCX（python-docx）、Markdown
  ---------------------------------------------------------------------------------------------------------------------------

**3. 部署架构**

**3.1 标准部署组件清单**

  --------------------------------------------------------------------------------
  **组件**            **端口**   **角色**                             **必需性**
  ------------------- ---------- ------------------------------------ ------------
  Streamlit Web       8501       Web UI 主进程，含实时进度推送        必需
  Server                                                              

  APScheduler         内进程     定时任务执行器，随主进程或独立运行   必需
  后台进程                                                            

  MongoDB             27017      分析结果持久库（Docker               必需
                                 容器或直接安装）                     

  SQLite 文件         无         行情缓存，无需额外服务               必需
  (./data/cache.db)                                                   

  ChromaDB 向量库     内进程     语义记忆检索（本地文件模式）         推荐

  Ollama 服务         11434      本地 LLM                             可选
                                 推理（Qwen3-4B），可完全离线         
  --------------------------------------------------------------------------------

**3.2 Docker Compose 部署（推荐）**

通过 docker-compose.yml
一键启动所有服务，服务编排包括：pstds-app（主应用+调度器）、mongodb、ollama（可选）。推荐配置：健康检查、卷挂载持久化数据、环境变量注入
API Key。

**3.3 硬件配置建议**

  ----------------------------------------------------------------------------------------
  **配置档位**   **硬件规格**                   **适用场景**
  -------------- ------------------------------ ------------------------------------------
  最低配置       8 GB RAM、无独显、SSD 30 GB    仅使用云端 LLM API（OpenAI / DeepSeek）

  推荐配置       16 GB RAM、RTX 3060 12GB       云端 API + 本地 Qwen3-4B
                 VRAM、SSD 100 GB               混合，支持回测数据存储

  高性能配置     32 GB RAM、RTX 4080 16GB       全本地运行，支持更大参数模型，大规模回测
                 VRAM、NVMe 200 GB              
  ----------------------------------------------------------------------------------------

**4. 关键接口规范**

**4.1 MarketDataAdapter Protocol（含 v2.0 时间隔离扩展）**

+-------------------------------------------------------------------+
| MarketDataAdapter Protocol 方法定义：                             |
|                                                                   |
| get_ohlcv(symbol, start_date, end_date, interval, ctx:            |
| TemporalContext) → DataFrame                                      |
|                                                                   |
| 返回：标准化 OHLCV，列名 \[date, open, high, low, close, volume\] |
|                                                                   |
| 约束：end_date 必须 ≤ ctx.analysis_date（TemporalGuard 强制）     |
|                                                                   |
| get_fundamentals(symbol, as_of_date, ctx: TemporalContext) → dict |
|                                                                   |
| 返回：基本面数据，必含 pe_ratio, pb_ratio, roe, revenue,          |
| net_income                                                        |
|                                                                   |
| 约束：返回 as_of_date 时可用的最新财报数据（非未来数据）          |
|                                                                   |
| get_news(symbol, days, end_date, ctx: TemporalContext) →          |
| List\[NewsItem\]                                                  |
|                                                                   |
| 返回：NewsItem 含 title, content, published_at, source, url       |
|                                                                   |
| 约束：published_at ≤ ctx.analysis_date（TemporalGuard 强制过滤）  |
|                                                                   |
| is_available(symbol) → bool                                       |
|                                                                   |
| get_market_type(symbol) → Literal\[\'US\', \'CN_A\', \'HK\'\]     |
+-------------------------------------------------------------------+

**4.2 TemporalContext 接口**

+-------------------------------------------------------------------+
| TemporalContext 数据类：                                          |
|                                                                   |
| analysis_date: date \# 分析基准日期（必须）                       |
|                                                                   |
| mode: Literal\[\'LIVE\', \'BACKTEST\'\] \# 实时模式或回测模式     |
|                                                                   |
| audit_log: AuditLogger \# 数据访问审计记录器                      |
|                                                                   |
| TemporalGuard 核心方法：                                          |
|                                                                   |
| validate(data_timestamp: datetime, ctx: TemporalContext) → bool   |
|                                                                   |
| \# 校验 data_timestamp ≤ ctx.analysis_date                        |
|                                                                   |
| \# 失败时记录审计日志并抛出 TemporalViolationError                |
|                                                                   |
| lock_realtime_apis(ctx: TemporalContext) → None                   |
|                                                                   |
| \# BACKTEST 模式下锁定所有外部实时 API 调用                       |
|                                                                   |
| inject_system_prompt(base_prompt: str, ctx: TemporalContext) →    |
| str                                                               |
|                                                                   |
| \# 在系统提示词前注入标准时间锚定声明                             |
+-------------------------------------------------------------------+

**4.3 LLM 适配器工厂（扩展版）**

  ------------------------------------------------------------------------
  **提供商**           **实现类**                 **来源**
  -------------------- -------------------------- ------------------------
  OpenAI               OpenAIAdapter              原版

  Anthropic Claude     AnthropicAdapter           原版

  Google Gemini        GeminiAdapter              原版

  DeepSeek             DeepSeekAdapter            v2.0 新增

  阿里 DashScope       DashScopeAdapter           v2.0 新增
  (Qwen)                                          

  Ollama 本地          OllamaAdapter（扩展）      原版+扩展

  OpenRouter           OpenRouterAdapter          原版

  Trading-R1（预留）   TradingR1Adapter（占位）   v2.0 预留
  ------------------------------------------------------------------------

所有适配器统一接受 budget_tokens（Token 预算上限）参数，超出时抛出
BudgetExceededError，由 Token 预算管理器处理降级逻辑。

**5. 记忆与学习系统架构（v2.0 新增）**

v2.0 引入三层记忆架构，替代原版简单的 BM25
关键词检索，提供更强的时序感知和语义理解能力。

  -------------------------------------------------------------------------------------------------------------
  **记忆层次**   **存储引擎**      **时间跨度**   **功能**
  -------------- ----------------- -------------- -------------------------------------------------------------
  短期工作记忆   Python            单次分析会话   当前分析的 GraphState 上下文，会话结束后清空
                 内存（dict）                     

  中期情景记忆   ChromaDB 向量库   近 90 天       历史决策的语义向量，支持「查找类似市场环境下的决策」

  长期模式记忆   MongoDB           永久积累       从历史决策提炼的规律，如「该股财报前3天情绪信号预测价值高」
                 memory_patterns                  
                 集合                             
  -------------------------------------------------------------------------------------------------------------

反事实记忆：每次分析后，系统将「实际结果 vs 系统预测」记录到 MongoDB
reflection_records
集合，定期触发模式提炼任务，将有效规律写入长期模式记忆。

**6. 回测引擎架构（v2.0 核心功能）**

回测引擎是独立的可选模块，通过依赖注入与主分析流程共享数据适配器和
TemporalGuard，确保回测与实盘分析使用完全相同的数据访问路径，消除回测与实盘的行为差异。

  ------------------------------------------------------------------------------------------------
  **组件**                    **实现说明**
  --------------------------- --------------------------------------------------------------------
  BacktestRunner              主控类，接受 symbol、date_range、analysis_config，驱动整个回测流程

  TradingCalendar             交易日历，按市场类型提供有效交易日列表（A股/美股/港股各异）

  TemporalContext（BACKTEST   每个回测日创建独立上下文，analysis_date 逐日推进，API 实时调用被锁定
  mode）                      

  VirtualPortfolio            虚拟账户，管理持仓、可用资金、交易记录，支持配置手续费率和滑点模型

  SignalExecutor              将 TradeDecision 的 action 字段按资金管理规则转换为具体仓位变化

  PerformanceCalculator       逐日计算并累积绩效指标（夏普、最大回撤、年化收益等）

  BacktestReportGenerator     生成完整回测报告（含净值曲线数据、逐日决策记录、绩效汇总）
  ------------------------------------------------------------------------------------------------

  -------------------------------------------------------------------
  *回测可复现性保障：回测过程中每个交易日的输入数据快照和 LLM
  配置（含随机种子）都被记录到 MongoDB backtest_snapshots
  集合，支持在任意日期重新运行验证。temperature=0
  确保相同输入产生相同决策。*

  -------------------------------------------------------------------
