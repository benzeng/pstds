**个人专用股票交易决策系统**

*PSTDS --- Personal Stock Trading Decision System*

**详细设计文档（DDD）v2.0**

综合改进方案 + PSTDS 用户方案 \| 2026年2月 \| 版本 v2.0

**1. 项目目录结构**

v2.0 在 v1.0 目录结构基础上新增了
temporal/（时间隔离层）、backtest/（回测引擎）、memory/（向量记忆系统）三个核心模块目录。所有新增模块均在独立的
pstds/ 扩展包内，不修改 tradingagents/ 原版核心目录。

+-------------------------------------------------------------------+
| pstds/ ← 项目根目录                                               |
|                                                                   |
| ├── tradingagents/ ← 原版 TradingAgents 核心（尽量不改动）        |
|                                                                   |
| │ ├── agents/ ← 各类 Agent 实现                                   |
|                                                                   |
| │ ├── graph/ ← LangGraph 工作流图                                 |
|                                                                   |
| │ ├── dataflows/ ← 原版数据获取工具                               |
|                                                                   |
| │ └── default_config.py                                           |
|                                                                   |
| │                                                                 |
|                                                                   |
| ├── pstds/ ← 本项目扩展代码                                       |
|                                                                   |
| │ ├── temporal/ ← 【v2.0 新增】时间隔离层（最高优先级）           |
|                                                                   |
| │ │ ├── context.py ← TemporalContext 数据类                       |
|                                                                   |
| │ │ ├── guard.py ← TemporalGuard 拦截器                           |
|                                                                   |
| │ │ └── audit.py ← 数据访问审计日志                               |
|                                                                   |
| │ │                                                               |
|                                                                   |
| │ ├── data/ ← 数据服务层                                          |
|                                                                   |
| │ │ ├── adapters/ ← 市场数据适配器                                |
|                                                                   |
| │ │ │ ├── base.py ← MarketDataAdapter Protocol（含                |
| TemporalContext）                                                 |
|                                                                   |
| │ │ │ ├── yfinance_adapter.py                                     |
|                                                                   |
| │ │ │ ├── akshare_adapter.py                                      |
|                                                                   |
| │ │ │ ├── alphavantage_adapter.py                                 |
|                                                                   |
| │ │ │ └── local_csv_adapter.py                                    |
|                                                                   |
| │ │ ├── cache.py ← SQLite 缓存管理器（含 TTL 和时间隔离校验）     |
|                                                                   |
| │ │ ├── router.py ← 市场路由器                                    |
|                                                                   |
| │ │ ├── news_filter.py ← 三级新闻相关性过滤器                     |
|                                                                   |
| │ │ ├── quality_guard.py ← 数据质量守卫                           |
|                                                                   |
| │ │ └── fallback.py ← 降级管理器                                  |
|                                                                   |
| │ │                                                               |
|                                                                   |
| │ ├── agents/ ← Agent 扩展                                        |
|                                                                   |
| │ │ ├── extended_graph.py ←                                       |
| ExtendedTradingAgentsGraph（含新增节点）                          |
|                                                                   |
| │ │ ├── debate_referee.py ← 辩论裁判员节点                        |
|                                                                   |
| │ │ ├── result_saver.py ← 结果持久化节点（含向量记忆更新）        |
|                                                                   |
| │ │ └── output_schemas.py ← Pydantic 输出校验模型（TradeDecision  |
| 等）                                                              |
|                                                                   |
| │ │                                                               |
|                                                                   |
| │ ├── llm/ ← LLM 适配器扩展                                       |
|                                                                   |
| │ │ ├── factory.py ← 扩展版 LLMFactory（含 Token 预算参数）       |
|                                                                   |
| │ │ ├── deepseek.py ← DeepSeek 适配器                             |
|                                                                   |
| │ │ ├── dashscope.py ← 阿里 Qwen 适配器                           |
|                                                                   |
| │ │ └── cost_estimator.py ← Token 成本估算与核算                  |
|                                                                   |
| │ │                                                               |
|                                                                   |
| │ ├── backtest/ ← 【v2.0 新增】回测引擎                           |
|                                                                   |
| │ │ ├── runner.py ← BacktestRunner 主控类                         |
|                                                                   |
| │ │ ├── calendar.py ← 交易日历（A股/美股/港股）                   |
|                                                                   |
| │ │ ├── portfolio.py ← VirtualPortfolio 虚拟账户                  |
|                                                                   |
| │ │ ├── executor.py ← SignalExecutor 信号执行引擎                 |
|                                                                   |
| │ │ ├── performance.py ← PerformanceCalculator 绩效计算           |
|                                                                   |
| │ │ └── report.py ← BacktestReportGenerator                       |
|                                                                   |
| │ │                                                               |
|                                                                   |
| │ ├── memory/ ← 【v2.0 新增】记忆系统                             |
|                                                                   |
| │ │ ├── short_term.py ← 短期工作记忆（内存）                      |
|                                                                   |
| │ │ ├── episodic.py ← 中期情景记忆（ChromaDB）                    |
|                                                                   |
| │ │ ├── pattern.py ← 长期模式记忆（MongoDB）                      |
|                                                                   |
| │ │ └── reflection.py ← 反事实记忆与模式提炼                      |
|                                                                   |
| │ │                                                               |
|                                                                   |
| │ ├── scheduler/ ← 任务调度                                       |
|                                                                   |
| │ │ ├── scheduler.py ← APScheduler 封装                           |
|                                                                   |
| │ │ └── task_queue.py ← asyncio 并行任务队列（含令牌桶限流）      |
|                                                                   |
| │ │                                                               |
|                                                                   |
| │ ├── storage/ ← 持久化层                                         |
|                                                                   |
| │ │ ├── mongo_store.py ← MongoDB 操作                             |
|                                                                   |
| │ │ └── models.py ← MongoDB 文档模型定义                          |
|                                                                   |
| │ │                                                               |
|                                                                   |
| │ ├── export/ ← 报告导出                                          |
|                                                                   |
| │ │ ├── pdf_exporter.py ← WeasyPrint PDF                          |
|                                                                   |
| │ │ ├── docx_exporter.py ← python-docx Word                       |
|                                                                   |
| │ │ └── md_exporter.py ← Markdown                                 |
|                                                                   |
| │ │                                                               |
|                                                                   |
| │ └── notify/ ← 通知模块                                          |
|                                                                   |
| │ ├── desktop.py                                                  |
|                                                                   |
| │ └── email_notify.py                                             |
|                                                                   |
| │                                                                 |
|                                                                   |
| ├── web/ ← Streamlit Web App                                      |
|                                                                   |
| │ ├── app.py ← 入口                                               |
|                                                                   |
| │ ├── pages/ ← 多页面（01-07）                                    |
|                                                                   |
| │ └── components/ ← 可复用 UI 组件                                |
|                                                                   |
| │                                                                 |
|                                                                   |
| ├── tests/ ← 测试套件（v2.0 新增要求 \> 80% 覆盖率）              |
|                                                                   |
| │ ├── unit/                                                       |
|                                                                   |
| │ │ ├── test_temporal_guard.py ← 时间隔离单元测试（最高优先级）   |
|                                                                   |
| │ │ ├── test_data_adapters.py                                     |
|                                                                   |
| │ │ └── test_output_schemas.py                                    |
|                                                                   |
| │ └── integration/                                                |
|                                                                   |
| │ ├── test_backtest_no_lookahead.py ← 前视偏差回归测试            |
|                                                                   |
| │ └── test_full_analysis_flow.py                                  |
|                                                                   |
| │                                                                 |
|                                                                   |
| ├── config/                                                       |
|                                                                   |
| │ ├── default.yaml                                                |
|                                                                   |
| │ └── user.yaml ← gitignore                                       |
|                                                                   |
| │                                                                 |
|                                                                   |
| ├── data/ ← 运行时数据（gitignore）                               |
|                                                                   |
| │ ├── cache.db ← SQLite                                           |
|                                                                   |
| │ ├── raw/ ← Parquet + JSON 原始数据（只追加）                    |
|                                                                   |
| │ ├── backtest/ ← 回测结果存档                                    |
|                                                                   |
| │ ├── reports/ ← 导出报告                                         |
|                                                                   |
| │ └── logs/ ← 分析日志、审计轨迹                                  |
|                                                                   |
| │                                                                 |
|                                                                   |
| ├── docker-compose.yml                                            |
|                                                                   |
| ├── Dockerfile                                                    |
|                                                                   |
| ├── requirements.txt                                              |
|                                                                   |
| └── start.py ← 一键启动入口                                       |
+-------------------------------------------------------------------+

**2. TemporalGuard 时间隔离层详细设计**

  ---------------------------------------------------------------------------------------------------
  *TemporalGuard 是 v2.0
  最关键的新增模块，必须在其他所有模块之前完成设计和测试。它的正确性直接决定系统回测结果的可信度。*

  ---------------------------------------------------------------------------------------------------

**2.1 TemporalContext 数据类**

+-------------------------------------------------------------------+
| \# pstds/temporal/context.py                                      |
|                                                                   |
| TemporalContext 字段：                                            |
|                                                                   |
| analysis_date: date \# 分析基准日期（必填）                       |
|                                                                   |
| mode: Literal\[\'LIVE\', \'BACKTEST\'\] \# 运行模式               |
|                                                                   |
| created_at: datetime \# 上下文创建时间（UTC）                     |
|                                                                   |
| audit_logger: AuditLogger \# 数据访问审计记录器实例               |
|                                                                   |
| 类方法：                                                          |
|                                                                   |
| for_live(analysis_date) → TemporalContext \# 创建实时分析上下文   |
|                                                                   |
| for_backtest(date) → TemporalContext \#                           |
| 创建回测上下文，自动锁定实时API                                   |
|                                                                   |
| get_prompt_prefix() → str \# 返回标准时间锚定声明（注入提示词）   |
+-------------------------------------------------------------------+

**2.2 TemporalGuard 拦截器核心逻辑**

+-------------------------------------------------------------------+
| \# pstds/temporal/guard.py                                        |
|                                                                   |
| TemporalGuard 方法：                                              |
|                                                                   |
| validate_timestamp(ts: datetime, ctx: TemporalContext) → None     |
|                                                                   |
| \# 校验 ts \<= ctx.analysis_date                                  |
|                                                                   |
| \# 违规时：记录审计日志 + 抛出 TemporalViolationError             |
|                                                                   |
| \# 审计日志包含：违规时间戳、analysis_date、调用栈信息            |
|                                                                   |
| filter_news(news_list: List\[NewsItem\], ctx: TemporalContext) →  |
| List\[NewsItem\]                                                  |
|                                                                   |
| \# 过滤 published_at \> ctx.analysis_date 的新闻                  |
|                                                                   |
| \# 记录过滤数量到审计日志                                         |
|                                                                   |
| lock_realtime_apis(ctx: TemporalContext) → None                   |
|                                                                   |
| \# BACKTEST 模式：在 DataRouter 中注册实时API黑名单               |
|                                                                   |
| \# 任何绕过尝试抛出 RealtimeAPIBlockedError                       |
|                                                                   |
| inject_temporal_prompt(base_prompt: str, ctx: TemporalContext) →  |
| str                                                               |
|                                                                   |
| \# 在系统提示词最前面注入时间锚定声明                             |
|                                                                   |
| \# 声明内容不可被后续提示词覆盖（置于 system 角色）               |
+-------------------------------------------------------------------+

**2.3 数据访问审计日志格式**

+-------------------------------------------------------------------+
| \# pstds/temporal/audit.py --- 审计记录结构                       |
|                                                                   |
| AuditRecord 字段：                                                |
|                                                                   |
| timestamp: datetime \# 记录时间（UTC）                            |
|                                                                   |
| analysis_id: str \# 关联分析任务 ID                               |
|                                                                   |
| analysis_date: date \# 本次分析基准日期                           |
|                                                                   |
| data_source: str \# 数据来源（yfinance/akshare/等）               |
|                                                                   |
| data_timestamp: datetime \# 被访问数据的时间戳                    |
|                                                                   |
| is_compliant: bool \# 是否通过时间隔离校验                        |
|                                                                   |
| violation_detail: str \# 违规详情（仅 is_compliant=False 时）     |
|                                                                   |
| caller_module: str \# 调用者模块名                                |
+-------------------------------------------------------------------+

**2.4 时间隔离单元测试规范**

test_temporal_guard.py
是测试套件中优先级最高的文件，必须在任何其他模块开发前完成，覆盖率要求
100%。

  ---------------------------------------------------------------------------------------------------
  **测试用例**                        **测试内容**             **预期结果**
  ----------------------------------- ------------------------ --------------------------------------
  test_valid_timestamp                数据时间戳 ≤             通过，无审计违规记录
                                      analysis_date            

  test_future_timestamp_rejected      数据时间戳 \>            抛出
                                      analysis_date            TemporalViolationError，审计日志记录

  test_news_filtering                 包含未来新闻的列表过滤   未来新闻被过滤，合规新闻保留

  test_backtest_api_lock              BACKTEST 模式下调用实时  抛出 RealtimeAPIBlockedError
                                      API                      

  test_prompt_injection               时间锚定声明注入         输出提示词首部包含正确的 analysis_date

  test_aapl_no_lookahead_regression   复现 Issue #203（AAPL    不触发实时数据访问，决策不全为 BUY
                                      2024-01→03 回测）        
  ---------------------------------------------------------------------------------------------------

**3. 数据服务层详细设计**

**3.1 MarketDataAdapter Protocol（v2.0 更新版）**

所有适配器必须接受 TemporalContext 参数，并在执行数据查询前调用
TemporalGuard 进行时间边界校验。

+-------------------------------------------------------------------+
| \# pstds/data/adapters/base.py                                    |
|                                                                   |
| MarketDataAdapter Protocol 方法签名：                             |
|                                                                   |
| get_ohlcv(                                                        |
|                                                                   |
| symbol: str,                                                      |
|                                                                   |
| start_date: date,                                                 |
|                                                                   |
| end_date: date,                                                   |
|                                                                   |
| interval: str, \# \'1d\' \| \'1h\' \| \'1m\'                      |
|                                                                   |
| ctx: TemporalContext \# 必填，时间隔离上下文                      |
|                                                                   |
| ) → pd.DataFrame                                                  |
|                                                                   |
| 列名固定：\[date, open, high, low, close, volume, adj_close\]     |
|                                                                   |
| date 列格式：UTC datetime                                         |
|                                                                   |
| TemporalGuard.validate_timestamp(end_date, ctx) 在内部调用        |
|                                                                   |
| get_fundamentals(                                                 |
|                                                                   |
| symbol: str,                                                      |
|                                                                   |
| as_of_date: date, \# 返回该日期可用的最新财报（非未来）           |
|                                                                   |
| ctx: TemporalContext                                              |
|                                                                   |
| ) → dict                                                          |
|                                                                   |
| 必含字段：pe_ratio, pb_ratio, roe, revenue, net_income,           |
|                                                                   |
| earnings_date, report_period, data_source, fetched_at             |
|                                                                   |
| get_news(                                                         |
|                                                                   |
| symbol: str,                                                      |
|                                                                   |
| days_back: int,                                                   |
|                                                                   |
| ctx: TemporalContext                                              |
|                                                                   |
| ) → List\[NewsItem\]                                              |
|                                                                   |
| NewsItem 字段：title, content, published_at, source, url,         |
| relevance_score                                                   |
|                                                                   |
| 内部调用 TemporalGuard.filter_news() 过滤未来新闻                 |
|                                                                   |
| is_available(symbol: str) → bool                                  |
|                                                                   |
| get_market_type(symbol: str) → Literal\[\'US\', \'CN_A\',         |
| \'HK\'\]                                                          |
+-------------------------------------------------------------------+

**3.2 市场路由规则**

  --------------------------------------------------------------------------------------------------------
  **Symbol 特征**                     **市场判定**          **主数据源**      **备用数据源**
  ----------------------------------- --------------------- ----------------- ----------------------------
  6位纯数字，60/000/002/003/300开头   A股（沪深）           AKShareAdapter    无（暂无免费备源）

  4-5位数字+.HK 后缀                  港股（HKEX）          AKShareAdapter    YFinanceAdapter（.HK格式）
                                                            港股接口          

  1-5位英文字母（无后缀）             美股（NYSE/NASDAQ）   YFinanceAdapter   AlphaVantageAdapter

  路径形如 xxx.csv                    本地数据              LocalCSVAdapter   无
  --------------------------------------------------------------------------------------------------------

**3.3 SQLite 缓存表结构**

  ----------------------------------------------------------------------------------------------------
  **表名**              **字段**                **TTL**                       **时间隔离支持**
  --------------------- ----------------------- ----------------------------- ------------------------
  ohlcv_cache           symbol, date, open,     24h（行情），永久（回测用）   查询时 WHERE date \<=
                        high, low, close,                                     analysis_date
                        volume, adj_close,                                    
                        fetched_at                                            

  fundamentals_cache    symbol, as_of_date,     24h                           WHERE as_of_date \<=
                        data_json, fetched_at                                 analysis_date

  news_cache            symbol, published_at,   6h                            WHERE published_at \<=
                        title_hash, news_json,                                analysis_date
                        fetched_at                                            

  technical_cache       symbol, date,           24h                           WHERE date \<=
                        indicator, value,                                     analysis_date
                        fetched_at                                            

  decision_hash_cache   input_hash,             7天                           无需隔离（按哈希命中）
                        result_json, created_at                               
  ----------------------------------------------------------------------------------------------------

**3.4 数据质量守卫检查规范**

  -----------------------------------------------------------------------------------------------
  **检查类别**   **检查项目**                     **判定阈值**         **失败处理**
  -------------- -------------------------------- -------------------- --------------------------
  价格数据       时序连续性（交易日无缺口）       缺口 ≤ 3 个交易日    标记缺口，质量分 -10 分

  价格数据       价格合理性（非负，无极端异常）   涨跌幅 ≤             标记异常点，提醒用户
                                                  30%（A股限制）       

  财报数据       必需字段完整性                   PE/PB/ROE 全部存在   标记缺失，降级基本面分析

  新闻数据       时间戳合规                       published_at ≤       强制丢弃，记录数量
                                                  analysis_date        

  异常事件       停牌检测、分拆合并检测           参考历史成交量异常   高优先级警告
  -----------------------------------------------------------------------------------------------

数据质量报告结构：data_quality_score（0-100分）、compliant_news_count、filtered_news_count、missing_fundamentals_fields、anomaly_alerts（列表）、fallback_sources_used（列表）。

**4. 智能体引擎层详细设计**

**4.1 ExtendedTradingAgentsGraph 扩展要点**

+-------------------------------------------------------------------+
| \# pstds/agents/extended_graph.py                                 |
|                                                                   |
| class ExtendedTradingAgentsGraph(TradingAgentsGraph):             |
|                                                                   |
| 扩展要点：                                                        |
|                                                                   |
| 1\. 重写 \_build_graph()：                                        |
|                                                                   |
| \- 在原版节点之前插入 data_quality_guard_node                     |
|                                                                   |
| \- 在原版 portfolio_manager_node 之后插入 debate_referee_node     |
|                                                                   |
| \- 在最后追加 result_persistence_node                             |
|                                                                   |
| 2\. 重写 propagate()：                                            |
|                                                                   |
| \- 接受 TemporalContext 参数                                      |
|                                                                   |
| \- 调用前注入扩展 DataRouter（替换原版 yfinance 直接调用）        |
|                                                                   |
| \- 初始化 Token 预算管理器                                        |
|                                                                   |
| 3\. 新增方法：                                                    |
|                                                                   |
| \- propagate_batch(tasks: List\[AnalysisTask\]) →                 |
| 异步并行批量执行                                                  |
|                                                                   |
| \- propagate_stream(symbol, date, ctx) → 生成器，供 Streamlit     |
| 实时进度                                                          |
|                                                                   |
| \- propagate_backtest(symbol, date, ctx: BACKTEST) → 回测专用入口 |
+-------------------------------------------------------------------+

**4.2 Pydantic 输出模型规范**

+---------------------------------------------------------------------+
| \# pstds/agents/output_schemas.py                                   |
|                                                                     |
| class DataSource(BaseModel):                                        |
|                                                                     |
| name: str \# 数据源名称                                             |
|                                                                     |
| url: Optional\[str\] \# 原始 URL（新闻/研报）                       |
|                                                                     |
| timestamp: datetime \# 数据时间戳（已通过时间隔离校验）             |
|                                                                     |
| market_type: str                                                    |
|                                                                     |
| class TradeDecision(BaseModel):                                     |
|                                                                     |
| action:                                                             |
| Literal\[\'STRONG_BUY\',\'BUY\',\'HOLD\',\'SELL\',\'STRONG_SELL\'\] |
|                                                                     |
| confidence: float = Field(ge=0.0, le=1.0)                           |
|                                                                     |
| conviction: Literal\[\'HIGH\',\'MEDIUM\',\'LOW\'\]                  |
|                                                                     |
| primary_reason: str = Field(max_length=100)                         |
|                                                                     |
| target_price_low: Optional\[float\] = Field(gt=0)                   |
|                                                                     |
| target_price_high: Optional\[float\] = Field(gt=0)                  |
|                                                                     |
| time_horizon: str \# 如 \'2-4 weeks\'                               |
|                                                                     |
| risk_factors: List\[str\] = Field(min_length=1)                     |
|                                                                     |
| data_sources: List\[DataSource\] = Field(min_length=1)              |
|                                                                     |
| analysis_date: date                                                 |
|                                                                     |
| analysis_timestamp: datetime                                        |
|                                                                     |
| volatility_adjustment: float                                        |
|                                                                     |
| debate_quality_score: float = Field(ge=0.0, le=10.0)                |
|                                                                     |
| insufficient_data: bool = False \# 数据不足时置 True                |
|                                                                     |
| 校验规则：                                                          |
|                                                                     |
| \- target_price_high \>= target_price_low（若均存在）               |
|                                                                     |
| \- action == \'HOLD\' 时允许 target_price\_\* 为 None               |
|                                                                     |
| \- insufficient_data == True 时 action 强制为 None                  |
|                                                                     |
| \- 校验失败：重试最多 3 次，仍失败标记 ANALYSIS_FAILED              |
+---------------------------------------------------------------------+

**4.3 辩论裁判员节点设计**

+-------------------------------------------------------------------+
| \# pstds/agents/debate_referee.py                                 |
|                                                                   |
| 辩论裁判员评分维度（各 0-10 分，加权平均）：                      |
|                                                                   |
| logic_consistency: float \# 逻辑一致性（权重 30%）                |
|                                                                   |
| data_sufficiency: float \# 数据充分性（权重 30%）---              |
| 论点是否引用具体数据                                              |
|                                                                   |
| assumption_validity: float \# 假设合理性（权重 20%）              |
|                                                                   |
| rebuttal_effectiveness: float \# 反驳有效性（权重 20%）           |
|                                                                   |
| DebateQualityReport 字段：                                        |
|                                                                   |
| overall_score: float \# 加权综合分                                |
|                                                                   |
| is_low_quality: bool \# overall_score \< 5.0 时为 True            |
|                                                                   |
| bull_data_citation_count: int \# 多方引用数据次数                 |
|                                                                   |
| bear_data_citation_count: int \# 空方引用数据次数                 |
|                                                                   |
| unsupported_claims: List\[str\] \# 无数据支撑的断言列表           |
|                                                                   |
| recommendation: str \# 裁判员建议（ACCEPT/REVISE/REJECT）         |
|                                                                   |
| 当 is_low_quality == True：                                       |
|                                                                   |
| TradeDecision.conviction 强制降为 \'LOW\'                         |
|                                                                   |
| UI 中显示「低置信度决策」警告标签                                 |
+-------------------------------------------------------------------+

**4.4 波动率调整决策机制（Trading-R1 方法移植）**

+-------------------------------------------------------------------+
| \# trader_node 内部逻辑（参考 Trading-R1 论文方法）               |
|                                                                   |
| 步骤：                                                            |
|                                                                   |
| 1\. 计算过去 20 个交易日历史波动率（年化标准差）                  |
|                                                                   |
| 2\. 波动率分级：                                                  |
|                                                                   |
| \- 低波动（\< 15%）：标准决策阈值                                 |
|                                                                   |
| \- 中波动（15%-30%）：提高 BUY/SELL 阈值 10%                      |
|                                                                   |
| \- 高波动（\> 30%）：提高 STRONG_BUY/STRONG_SELL 阈值 20%，       |
|                                                                   |
| 要求更充分的证据支撑                                              |
|                                                                   |
| 3\. 将波动率调整系数写入 GraphState.volatility_adjustment         |
|                                                                   |
| 4\. TradeDecision 中包含 volatility_adjustment 字段               |
|                                                                   |
| 五档决策门槛（以综合置信度 0-1 为基准）：                         |
|                                                                   |
| STRONG_BUY \> 0.85（低波动）/ 0.90（高波动）                      |
|                                                                   |
| BUY \> 0.65（低波动）/ 0.72（高波动）                             |
|                                                                   |
| HOLD 0.35 - 0.65（区间）                                          |
|                                                                   |
| SELL \< 0.35（低波动）/ \< 0.28（高波动）                         |
|                                                                   |
| STRONG_SELL \< 0.15（低波动）/ \< 0.10（高波动）                  |
+-------------------------------------------------------------------+

**5. 数据模型详细设计**

**5.1 MongoDB 集合设计**

**analyses 集合（v2.0 更新）**

+-------------------------------------------------------------------+
| // MongoDB analyses 集合文档结构（v2.0）                          |
|                                                                   |
| {                                                                 |
|                                                                   |
| \_id: UUID, // 分析唯一 ID                                        |
|                                                                   |
| symbol: \'600519\',                                               |
|                                                                   |
| market_type: \'CN_A\',                                            |
|                                                                   |
| analysis_date: \'2026-02-19\', // 分析基准日期（非创建日期）      |
|                                                                   |
| created_at: ISODate,                                              |
|                                                                   |
| mode: \'LIVE\' \| \'BACKTEST\',                                   |
|                                                                   |
| config: {                                                         |
|                                                                   |
| llm_provider, deep_think_llm, quick_think_llm,                    |
|                                                                   |
| max_debate_rounds, analysis_depth_level,                          |
|                                                                   |
| temperature: 0.0 // v2.0 固定为 0.0                               |
|                                                                   |
| },                                                                |
|                                                                   |
| temporal: {                                                       |
|                                                                   |
| analysis_date: \'2026-02-19\',                                    |
|                                                                   |
| compliant_news_count: 12,                                         |
|                                                                   |
| filtered_news_count: 2, // 因时间违规被过滤的新闻数               |
|                                                                   |
| temporal_violations: \[\] // 审计违规记录（正常应为空）           |
|                                                                   |
| },                                                                |
|                                                                   |
| data_quality: {                                                   |
|                                                                   |
| score: 87, // 0-100                                               |
|                                                                   |
| missing_fields: \[\],                                             |
|                                                                   |
| anomaly_alerts: \[\],                                             |
|                                                                   |
| fallbacks_used: \[\]                                              |
|                                                                   |
| },                                                                |
|                                                                   |
| reports: { // 各 Agent 输出全文                                   |
|                                                                   |
| market_report: \'\...\',                                          |
|                                                                   |
| sentiment_report: \'\...\',                                       |
|                                                                   |
| news_report: \'\...\',                                            |
|                                                                   |
| fundamentals_report: \'\...\',                                    |
|                                                                   |
| investment_debate_state: { rounds: \[\], quality_report: {} },    |
|                                                                   |
| trader_investment_plan: \'\...\',                                 |
|                                                                   |
| risk_debate_state: { \... },                                      |
|                                                                   |
| final_trade_decision: \'\...\'                                    |
|                                                                   |
| },                                                                |
|                                                                   |
| decision: { // 结构化决策摘要（TradeDecision JSON）               |
|                                                                   |
| action: \'BUY\',                                                  |
|                                                                   |
| confidence: 0.72,                                                 |
|                                                                   |
| conviction: \'MEDIUM\',                                           |
|                                                                   |
| primary_reason: \'\...\', // max 100 字                           |
|                                                                   |
| target_price_low: 1680,                                           |
|                                                                   |
| target_price_high: 1750,                                          |
|                                                                   |
| time_horizon: \'2-4 weeks\',                                      |
|                                                                   |
| risk_factors: \[\'\...\'\],                                       |
|                                                                   |
| data_sources: \[{ name, url, timestamp }\],                       |
|                                                                   |
| volatility_adjustment: 1.08,                                      |
|                                                                   |
| debate_quality_score: 7.5,                                        |
|                                                                   |
| insufficient_data: false                                          |
|                                                                   |
| },                                                                |
|                                                                   |
| input_hash: \'sha256:\...\', //                                   |
| 输入数据+模型配置哈希（用于缓存命中）                             |
|                                                                   |
| cost: { total_tokens: 38420, estimated_usd: 0.09, actual_usd:     |
| 0.11 }                                                            |
|                                                                   |
| }                                                                 |
+-------------------------------------------------------------------+

**backtest_results 集合（v2.0 新增）**

+-------------------------------------------------------------------+
| // backtest_results 集合文档结构                                  |
|                                                                   |
| {                                                                 |
|                                                                   |
| \_id: UUID,                                                       |
|                                                                   |
| symbol: \'AAPL\',                                                 |
|                                                                   |
| date_range: { start: \'2024-01-02\', end: \'2024-03-29\' },       |
|                                                                   |
| config: { analysis_depth_level, llm_config, risk_profile },       |
|                                                                   |
| performance: {                                                    |
|                                                                   |
| total_return: 0.082, // 累计收益率                                |
|                                                                   |
| annualized_return: 0.34,                                          |
|                                                                   |
| max_drawdown: -0.045,                                             |
|                                                                   |
| sharpe_ratio: 1.82,                                               |
|                                                                   |
| calmar_ratio: 7.6,                                                |
|                                                                   |
| win_rate: 0.63,                                                   |
|                                                                   |
| total_trades: 12                                                  |
|                                                                   |
| },                                                                |
|                                                                   |
| daily_records: \[ // 逐日分析记录                                 |
|                                                                   |
| { date, analysis_id, action, confidence, actual_return_next_day } |
|                                                                   |
| \],                                                               |
|                                                                   |
| total_cost: { tokens: 186000, usd: 0.45 },                        |
|                                                                   |
| created_at: ISODate                                               |
|                                                                   |
| }                                                                 |
+-------------------------------------------------------------------+

**其他集合（沿用 v1.0，部分字段更新）**

  ------------------------------------------------------------------------
  **集合名**        **主要字段（v2.0 变更）**         **用途**
  ----------------- --------------------------------- --------------------
  watchlist         symbol, name, market_type,        自选股管理
                    group_tags,                       
                    auto_analysis_enabled,            
                    schedule_cron, preferred_config,  
                    last_analyzed_at                  

  scheduled_tasks   task_type, symbol, status,        定时任务记录
                    retry_count, scheduled_at,        
                    result_analysis_id, error_message 

  cost_records      analysis_id, provider, model,     费用明细，月度统计
                    input_tokens, output_tokens,      
                    cost_usd, created_at（v2.0        
                    新增集合）                        

  memory_patterns   pattern_key, description, symbol, 长期模式记忆
                    evidence_count,                   
                    last_updated（v2.0 新增集合）     
  ------------------------------------------------------------------------

**6. 配置文件详细设计**

**6.1 default.yaml 完整结构（v2.0 更新版）**

+-------------------------------------------------------------------+
| \# config/default.yaml --- PSTDS v2.0 默认配置                    |
|                                                                   |
| \# ─── 时间隔离配置（v2.0 新增，不可关闭）────────────────────    |
|                                                                   |
| temporal:                                                         |
|                                                                   |
| enforce_isolation: true \# 强制时间隔离，不可设为 false           |
|                                                                   |
| audit_log_path: \'./data/logs/temporal_audit.jsonl\'              |
|                                                                   |
| news_timestamp_strict: true \# 严格校验新闻时间戳                 |
|                                                                   |
| \# ─── LLM 配置 ──────────────────────────────────────────────    |
|                                                                   |
| llm:                                                              |
|                                                                   |
| provider: \'ollama\' \# 默认本地运行                              |
|                                                                   |
| deep_think_model: \'qwen3:4b\'                                    |
|                                                                   |
| quick_think_model: \'qwen3:4b\'                                   |
|                                                                   |
| temperature: 0.0 \# 生产模式固定 0.0，不可被用户覆盖              |
|                                                                   |
| max_debate_rounds: 2                                              |
|                                                                   |
| ollama_base_url: \'http://localhost:11434\'                       |
|                                                                   |
| token_budget:                                                     |
|                                                                   |
| l0_limit: 5000                                                    |
|                                                                   |
| l1_limit: 20000                                                   |
|                                                                   |
| l2_limit: 60000                                                   |
|                                                                   |
| l3_limit: 120000                                                  |
|                                                                   |
| monthly_cost_alert_usd: 10.0 \# 月度费用告警阈值                  |
|                                                                   |
| auto_fallback_to_local: true \# 超限自动切换本地模型              |
|                                                                   |
| \# ─── 分析配置 ──────────────────────────────────────────────    |
|                                                                   |
| analysis:                                                         |
|                                                                   |
| default_depth: 2 \# L0-L3                                         |
|                                                                   |
| risk_profile: \'balanced\' \# conservative/balanced/aggressive    |
|                                                                   |
| enable_volatility_adjustment: true                                |
|                                                                   |
| analysts: \[\'technical\', \'fundamentals\', \'news\',            |
| \'sentiment\'\]                                                   |
|                                                                   |
| debate_referee_enabled: true                                      |
|                                                                   |
| min_debate_quality_score: 5.0 \# 低于此分数标记低置信度           |
|                                                                   |
| consecutive_buy_alert: 3 \# 连续 N 次 BUY 触发加强空方辩论        |
|                                                                   |
| \# ─── 数据源配置 ────────────────────────────────────────────    |
|                                                                   |
| data:                                                             |
|                                                                   |
| us_stock_primary: \'yfinance\'                                    |
|                                                                   |
| us_stock_fallback: \'alpha_vantage\'                              |
|                                                                   |
| cn_a_stock_primary: \'akshare\'                                   |
|                                                                   |
| hk_stock_primary: \'akshare\'                                     |
|                                                                   |
| hk_stock_fallback: \'yfinance\'                                   |
|                                                                   |
| cache_ttl_hours: 24                                               |
|                                                                   |
| news_ttl_hours: 6                                                 |
|                                                                   |
| news_relevance_threshold: 0.6                                     |
|                                                                   |
| max_news_tokens_per_item: 500 \# 新闻摘要 Token 截断              |
|                                                                   |
| max_fundamentals_tokens: 2000 \# 财报摘要 Token 截断              |
|                                                                   |
| \# ─── 存储配置 ──────────────────────────────────────────────    |
|                                                                   |
| storage:                                                          |
|                                                                   |
| mongodb_uri: \'mongodb://localhost:27017\'                        |
|                                                                   |
| mongodb_db: \'pstds\'                                             |
|                                                                   |
| sqlite_path: \'./data/cache.db\'                                  |
|                                                                   |
| parquet_dir: \'./data/raw\'                                       |
|                                                                   |
| reports_dir: \'./data/reports\'                                   |
|                                                                   |
| chromadb_path: \'./data/vector_memory\'                           |
|                                                                   |
| \# ─── 并行配置 ──────────────────────────────────────────────    |
|                                                                   |
| concurrency:                                                      |
|                                                                   |
| max_parallel_stocks: 3 \# 最大并发分析股票数                      |
|                                                                   |
| rate_limit_rps: 5 \# LLM API 每秒请求限制                         |
|                                                                   |
| \# ─── 通知配置 ──────────────────────────────────────────────    |
|                                                                   |
| notify:                                                           |
|                                                                   |
| desktop_enabled: true                                             |
|                                                                   |
| email_enabled: false                                              |
|                                                                   |
| smtp_host: \'\'                                                   |
|                                                                   |
| smtp_port: 587                                                    |
|                                                                   |
| smtp_user: \'\'                                                   |
|                                                                   |
| smtp_to: \'\'                                                     |
+-------------------------------------------------------------------+

**7. 回测引擎详细设计**

**7.1 BacktestRunner 主控类**

+-------------------------------------------------------------------+
| \# pstds/backtest/runner.py                                       |
|                                                                   |
| BacktestRunner 初始化参数：                                       |
|                                                                   |
| symbol: str                                                       |
|                                                                   |
| start_date: date                                                  |
|                                                                   |
| end_date: date                                                    |
|                                                                   |
| analysis_config: dict \# 分析深度、LLM 配置等                     |
|                                                                   |
| initial_capital: float \# 初始模拟资金（默认 100000）             |
|                                                                   |
| commission_rate: float \# 手续费率（默认 0.001）                  |
|                                                                   |
| slippage_bps: int \# 滑点基点（默认 5bps）                        |
|                                                                   |
| run() 执行流程：                                                  |
|                                                                   |
| 1\. 初始化 TradingCalendar，获取 \[start_date, end_date\]         |
| 交易日列表                                                        |
|                                                                   |
| 2\. 初始化 VirtualPortfolio（initial_capital）                    |
|                                                                   |
| 3\. 逐日迭代：                                                    |
|                                                                   |
| a\. 创建 TemporalContext.for_backtest(current_date)               |
|                                                                   |
| b\. 调用 ExtendedTradingAgentsGraph.propagate_backtest()          |
|                                                                   |
| c\. SignalExecutor 执行模拟交易                                   |
|                                                                   |
| d\. PerformanceCalculator 更新日度绩效                            |
|                                                                   |
| e\. 保存当日快照到 MongoDB backtest_snapshots                     |
|                                                                   |
| 4\. BacktestReportGenerator 生成完整报告                          |
|                                                                   |
| 5\. 保存到 MongoDB backtest_results                               |
+-------------------------------------------------------------------+

**7.2 VirtualPortfolio 虚拟账户**

+-------------------------------------------------------------------+
| \# pstds/backtest/portfolio.py                                    |
|                                                                   |
| VirtualPortfolio 管理：                                           |
|                                                                   |
| cash: float \# 可用现金                                           |
|                                                                   |
| positions: Dict\[str, float\] \# 持仓量                           |
|                                                                   |
| trade_history: List\[Trade\] \# 历史交易记录                      |
|                                                                   |
| buy(symbol, shares, price) → Trade                                |
|                                                                   |
| cost = shares \* price \* (1 + commission_rate)                   |
|                                                                   |
| slippage = price \* slippage_bps / 10000                          |
|                                                                   |
| 实际成交价 = price + slippage                                     |
|                                                                   |
| sell(symbol, shares, price) → Trade                               |
|                                                                   |
| 同上，方向相反                                                    |
|                                                                   |
| get_portfolio_value(current_prices) → float                       |
|                                                                   |
| = cash + sum(positions\[s\] \* current_prices\[s\] for s in       |
| positions)                                                        |
+-------------------------------------------------------------------+

**7.3 PerformanceCalculator 绩效指标计算**

  ------------------------------------------------------------------------
  **指标**           **计算公式说明**                   **更新频率**
  ------------------ ---------------------------------- ------------------
  累计收益率         (当日组合价值 - 初始资金) /        每日
                     初始资金                           

  最大回撤           max((peak - trough) /              每日
                     peak，历史滚动)                    

  夏普比率（年化）   (年化收益 - 无风险利率) /          回测结束
                     年化波动率                         

  卡尔马比率         年化收益率 / 最大回撤绝对值        回测结束

  信息比率           (组合收益 - 基准收益) /            回测结束
                     超额收益标准差                     

  胜率               盈利交易次数 / 总交易次数          实时更新

  预测准确率         决策方向与次日实际涨跌一致的比率   每日
  ------------------------------------------------------------------------

**8. 开发路线图（v2.0 更新版）**

  -------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  **阶段**            **目标版本**   **主要交付物**                                                                              **关键成功标准**
  ------------------- -------------- ------------------------------------------------------------------------------------------- ------------------------------------------
  Phase 0             v0.1           Docker Compose 一键启动、MongoDB 连通、TradingAgents 原版跑通                               原版 AAPL 分析可成功执行
  环境搭建（1周）                                                                                                                

  Phase 1             v0.3           TemporalGuard 完整实现、时间隔离单元测试套件（覆盖率100%）、提示词规范化、LLM temperature=0 AAPL 2024-01→03
  时间隔离（2周）                    锁定                                                                                        回归测试通过：无实时数据泄露，决策不全为
                                                                                                                                 BUY

  Phase 2             v0.5           AKShare 适配器、SQLite 缓存、市场路由、Parquet 原始存储、数据质量守卫                       A股 / 港股数据获取正常，数据质量报告输出
  数据层扩展（2周）                                                                                                              

  Phase 3 核心 Web    v0.7           Streamlit 主分析页（L1/L2 深度）、实时进度、K线图组件、结构化决策展示（5档）、成本仪表盘    完整分析流程端到端可用，成本记录正常
  UI（3周）                                                                                                                      

  Phase 4             v0.9           BacktestRunner、VirtualPortfolio、PerformanceCalculator、回测绩效报告页                     AAPL
  回测引擎（2周）                                                                                                                2024年全年回测，夏普比率等指标正常输出

  Phase 5             v1.0           自选股管理、批量并行分析、定时任务、历史记录查询、报告导出（PDF/DOCX/MD）、邮件通知、国产   完整文档 + 全功能可用
  功能完善（2周）                    LLM 适配、完整文档                                                                          

  Phase 6             v1.1           ChromaDB 向量记忆、辩论裁判员、组合级风险分析、Trading-R1                                   记忆系统可用，Trading-R1 待官方发布
  高级功能（TBD）                    模型集成（待开源）、持仓风险仪表盘                                                          
  -------------------------------------------------------------------------------------------------------------------------------------------------------------------------

  --------------------------------------------------------------------------------------------------------------------------------
  *里程碑验证：Phase 1 结束时必须通过「AAPL
  前视偏差回归测试」（test_backtest_no_lookahead.py），这是系统可信度的最低门槛。在此测试通过前，不得进行任何回测绩效对外声明。*

  --------------------------------------------------------------------------------------------------------------------------------

  -------------------------------------------------------------------------------------------------------------------------
  *重要免责声明：本系统为个人研究辅助工具。所有分析结果、投资建议均由 LLM
  自动生成，存在固有的不确定性。投资有风险，入市须谨慎。本系统不构成任何形式的投资建议，开发者对投资损失不承担任何责任。*

  -------------------------------------------------------------------------------------------------------------------------
