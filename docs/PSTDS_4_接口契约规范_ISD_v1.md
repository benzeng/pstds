**个人专用股票交易决策系统**

*PSTDS --- Personal Stock Trading Decision System*

**接口与数据契约规范（ISD）v1.0**

Internal Interface & Schema Design \| 2026年2月 \| 版本 v1.0

**1. 文档目的**

本文档定义 PSTDS
各模块之间的内部接口契约、数据结构规范和错误码体系。它是 Claude Code
编码阶段的直接参考文档------开发者（或 AI
编码助手）在实现每个模块时，必须严格遵守本文档定义的接口签名、字段类型和约束条件，以确保模块间的互操作性和系统整体的确定性行为。

  -----------------------------------------------------------------------------------------------------------------------
  *接口契约原则：接口一旦在本文档中定义，在同一版本内不得变更。如需变更，必须同步更新本文档并在变更日志中记录。这是确保
  Claude Code 多轮编码会话一致性的关键机制。*

  -----------------------------------------------------------------------------------------------------------------------

**2. 核心数据类型规范**

**2.1 基础值类型**

  ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  **类型名称**      **Python 类型**                                                                             **约束**                                   **示例**
  ----------------- ------------------------------------------------------------------------------------------- ------------------------------------------ ---------------------
  Symbol            str                                                                                         1-10位，A股6位数字/美股1-5位字母/.HK后缀   \'AAPL\', \'600519\',
                                                                                                                                                           \'0700.HK\'

  AnalysisDate      datetime.date                                                                               不得超过当前日期                           date(2024, 3, 15)

  MarketType        Literal\[\'US\',\'CN_A\',\'HK\'\]                                                           枚举值                                     \'CN_A\'

  AnalysisMode      Literal\[\'LIVE\',\'BACKTEST\'\]                                                            枚举值                                     \'BACKTEST\'

  DepthLevel        Literal\[\'L0\',\'L1\',\'L2\',\'L3\'\]                                                      枚举值                                     \'L2\'

  ActionType        Literal\[\'STRONG_BUY\',\'BUY\',\'HOLD\',\'SELL\',\'STRONG_SELL\',\'INSUFFICIENT_DATA\'\]   枚举值                                     \'BUY\'

  Confidence        float                                                                                       ge=0.0, le=1.0                             0.72

  ConvictionLevel   Literal\[\'HIGH\',\'MEDIUM\',\'LOW\'\]                                                      枚举值                                     \'MEDIUM\'

  TokenCount        int                                                                                         ge=0                                       38420

  CostUSD           float                                                                                       ge=0.0                                     0.11
  ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

**2.2 TemporalContext（时间上下文）**

+-------------------------------------------------------------------+
| \# pstds/temporal/context.py                                      |
|                                                                   |
| from dataclasses import dataclass, field                          |
|                                                                   |
| from datetime import date, datetime                               |
|                                                                   |
| from typing import Literal                                        |
|                                                                   |
| \@dataclass(frozen=True) \# 不可变，防止运行时篡改                |
|                                                                   |
| class TemporalContext:                                            |
|                                                                   |
| analysis_date: date \# 分析基准日期（必填）                       |
|                                                                   |
| mode: Literal\[\'LIVE\', \'BACKTEST\'\] \# 运行模式               |
|                                                                   |
| created_at: datetime = field(default_factory=lambda:              |
| datetime.utcnow())                                                |
|                                                                   |
| session_id: str = field(default_factory=lambda: str(uuid4()))     |
|                                                                   |
| \@classmethod                                                     |
|                                                                   |
| def for_live(cls, analysis_date: date) -\> \'TemporalContext\':   |
|                                                                   |
| return cls(analysis_date=analysis_date, mode=\'LIVE\')            |
|                                                                   |
| \@classmethod                                                     |
|                                                                   |
| def for_backtest(cls, sim_date: date) -\> \'TemporalContext\':    |
|                                                                   |
| return cls(analysis_date=sim_date, mode=\'BACKTEST\')             |
|                                                                   |
| def get_prompt_prefix(self) -\> str:                              |
|                                                                   |
| return (                                                          |
|                                                                   |
| f\'【时间隔离声明】你当前正在分析 {self.analysis_date}            |
| 这一天的市场情况。\'                                              |
|                                                                   |
| f\'不得引用该日期之后发生的任何事件、数据或新闻。\'               |
|                                                                   |
| f\'你的所有分析必须基于以下明确提供的数据，\'                     |
|                                                                   |
| f\'不得使用训练记忆中的具体财务数字或新闻内容。\'                 |
|                                                                   |
| f\'若提供数据不足以支撑结论，输出 INSUFFICIENT_DATA 标志。\'      |
|                                                                   |
| )                                                                 |
+-------------------------------------------------------------------+

**2.3 NewsItem（新闻数据项）**

+-------------------------------------------------------------------+
| \# pstds/data/models.py                                           |
|                                                                   |
| from pydantic import BaseModel, HttpUrl, validator                |
|                                                                   |
| from datetime import datetime                                     |
|                                                                   |
| class NewsItem(BaseModel):                                        |
|                                                                   |
| title: str \# 新闻标题                                            |
|                                                                   |
| content: str \# 新闻正文（截断至 500 tokens）                     |
|                                                                   |
| published_at: datetime \# 发布时间（UTC）                         |
|                                                                   |
| source: str \# 来源名称                                           |
|                                                                   |
| url: Optional\[HttpUrl\] \# 原始链接                              |
|                                                                   |
| relevance_score: float \# 相关性评分 0.0-1.0                      |
|                                                                   |
| market_type: MarketType                                           |
|                                                                   |
| symbol: str                                                       |
|                                                                   |
| \@validator(\'relevance_score\')                                  |
|                                                                   |
| def score_must_be_valid(cls, v):                                  |
|                                                                   |
| assert 0.0 \<= v \<= 1.0, \'relevance_score 必须在 0-1 之间\'     |
|                                                                   |
| return v                                                          |
|                                                                   |
| \# 注意：TemporalGuard 会在返回前过滤 published_at \>             |
| analysis_date 的项目                                              |
+-------------------------------------------------------------------+

**2.4 OHLCVRecord（行情数据）**

+-------------------------------------------------------------------+
| \# pstds/data/models.py                                           |
|                                                                   |
| class OHLCVRecord(BaseModel):                                     |
|                                                                   |
| symbol: str                                                       |
|                                                                   |
| date: datetime \# UTC datetime                                    |
|                                                                   |
| open: float = Field(gt=0)                                         |
|                                                                   |
| high: float = Field(gt=0)                                         |
|                                                                   |
| low: float = Field(gt=0)                                          |
|                                                                   |
| close: float = Field(gt=0)                                        |
|                                                                   |
| volume: int = Field(ge=0)                                         |
|                                                                   |
| adj_close: Optional\[float\]                                      |
|                                                                   |
| data_source: str \#                                               |
| \'yfinance\'\|\'akshare\'\|\'alphavantage\'\|\'local\'            |
|                                                                   |
| fetched_at: datetime \# 数据获取时间（UTC）                       |
|                                                                   |
| \@validator(\'high\')                                             |
|                                                                   |
| def high_gte_low(cls, v, values):                                 |
|                                                                   |
| if \'low\' in values:                                             |
|                                                                   |
| assert v \>= values\[\'low\'\], \'high 必须 \>= low\'             |
|                                                                   |
| return v                                                          |
+-------------------------------------------------------------------+

**2.5 DataSource（数据引用来源）**

+-------------------------------------------------------------------+
| class DataSource(BaseModel):                                      |
|                                                                   |
| name: str \# 数据源名称                                           |
|                                                                   |
| url: Optional\[HttpUrl\] \# 原始 URL                              |
|                                                                   |
| data_timestamp: datetime \# 数据时间戳（已通过时间隔离校验）      |
|                                                                   |
| market_type: MarketType                                           |
|                                                                   |
| fetched_at: datetime \# 获取时间（UTC）                           |
+-------------------------------------------------------------------+

**3. TradeDecision 标准决策模型**

  --------------------------------------------------------------------------------
  *TradeDecision
  是系统最核心的输出数据结构，所有最终决策节点的输出必须严格符合此模型。Pydantic
  校验失败时，最多重试 3 次，仍失败则输出错误记录并将 action 置为
  INSUFFICIENT_DATA。*

  --------------------------------------------------------------------------------

+-------------------------------------------------------------------------------------------+
| \# pstds/agents/output_schemas.py                                                         |
|                                                                                           |
| from pydantic import BaseModel, Field, validator                                          |
|                                                                                           |
| from typing import List, Optional, Literal                                                |
|                                                                                           |
| from datetime import date, datetime                                                       |
|                                                                                           |
| class TradeDecision(BaseModel):                                                           |
|                                                                                           |
| \# ─── 核心决策字段 ────────────────────────────────                                      |
|                                                                                           |
| action:                                                                                   |
| Literal\[\'STRONG_BUY\',\'BUY\',\'HOLD\',\'SELL\',\'STRONG_SELL\',\'INSUFFICIENT_DATA\'\] |
|                                                                                           |
| confidence: float = Field(ge=0.0, le=1.0) \# 综合置信度                                   |
|                                                                                           |
| conviction: Literal\[\'HIGH\', \'MEDIUM\', \'LOW\'\]                                      |
|                                                                                           |
| primary_reason: str = Field(max_length=100) \# 主要决策理由                               |
|                                                                                           |
| insufficient_data: bool = False \# 数据不足标志                                           |
|                                                                                           |
| \# ─── 价格目标 ────────────────────────────────────                                      |
|                                                                                           |
| target_price_low: Optional\[float\] = Field(default=None, gt=0)                           |
|                                                                                           |
| target_price_high: Optional\[float\] = Field(default=None, gt=0)                          |
|                                                                                           |
| time_horizon: str \# 如 \'2-4 weeks\'                                                     |
|                                                                                           |
| \# ─── 风险与来源 ──────────────────────────────────                                      |
|                                                                                           |
| risk_factors: List\[str\] = Field(min_length=1)                                           |
|                                                                                           |
| data_sources: List\[DataSource\] = Field(min_length=1)                                    |
|                                                                                           |
| \# ─── 元数据 ──────────────────────────────────────                                      |
|                                                                                           |
| analysis_date: date \# 分析基准日期                                                       |
|                                                                                           |
| analysis_timestamp: datetime \# 分析完成时间（UTC）                                       |
|                                                                                           |
| volatility_adjustment: float = Field(ge=0.5, le=2.0)                                      |
|                                                                                           |
| debate_quality_score: float = Field(ge=0.0, le=10.0)                                      |
|                                                                                           |
| symbol: str                                                                               |
|                                                                                           |
| market_type: MarketType                                                                   |
|                                                                                           |
| \# ─── 校验规则 ────────────────────────────────────                                      |
|                                                                                           |
| \@validator(\'target_price_high\')                                                        |
|                                                                                           |
| def high_gte_low(cls, v, values):                                                         |
|                                                                                           |
| if v and values.get(\'target_price_low\'):                                                |
|                                                                                           |
| assert v \>= values\[\'target_price_low\'\], \'目标价上限必须 \>= 下限\'                  |
|                                                                                           |
| return v                                                                                  |
|                                                                                           |
| \@validator(\'action\')                                                                   |
|                                                                                           |
| def action_consistent_with_insufficient(cls, v, values):                                  |
|                                                                                           |
| if values.get(\'insufficient_data\') and v != \'INSUFFICIENT_DATA\':                      |
|                                                                                           |
| raise ValueError(\'insufficient_data=True 时 action 必须为 INSUFFICIENT_DATA\')           |
|                                                                                           |
| return v                                                                                  |
+-------------------------------------------------------------------------------------------+

**4. MarketDataAdapter 接口契约**

所有数据适配器必须实现以下方法签名，TemporalContext
为必传参数，不可省略。

+-----------------------------------------------------------------------------------------------------+
| \# pstds/data/adapters/base.py                                                                      |
|                                                                                                     |
| from typing import Protocol, List, Literal                                                          |
|                                                                                                     |
| from datetime import date                                                                           |
|                                                                                                     |
| import pandas as pd                                                                                 |
|                                                                                                     |
| from pstds.temporal.context import TemporalContext                                                  |
|                                                                                                     |
| from pstds.data.models import NewsItem, OHLCVRecord                                                 |
|                                                                                                     |
| class MarketDataAdapter(Protocol):                                                                  |
|                                                                                                     |
| def get_ohlcv(                                                                                      |
|                                                                                                     |
| self,                                                                                               |
|                                                                                                     |
| symbol: str,                                                                                        |
|                                                                                                     |
| start_date: date,                                                                                   |
|                                                                                                     |
| end_date: date,                                                                                     |
|                                                                                                     |
| interval: Literal\[\'1d\', \'1wk\', \'1mo\'\],                                                      |
|                                                                                                     |
| ctx: TemporalContext, \# 必填，时间隔离上下文                                                       |
|                                                                                                     |
| ) -\> pd.DataFrame:                                                                                 |
|                                                                                                     |
| \"\"\"                                                                                              |
|                                                                                                     |
| 返回：标准化 DataFrame                                                                              |
|                                                                                                     |
| 列名固定：\[\'date\',\'open\',\'high\',\'low\',\'close\',\'volume\',\'adj_close\',\'data_source\'\] |
|                                                                                                     |
| \- date 列：UTC datetime                                                                            |
|                                                                                                     |
| \- 内部调用 TemporalGuard.validate_timestamp(end_date, ctx)                                         |
|                                                                                                     |
| \"\"\"                                                                                              |
|                                                                                                     |
| \...                                                                                                |
|                                                                                                     |
| def get_fundamentals(                                                                               |
|                                                                                                     |
| self,                                                                                               |
|                                                                                                     |
| symbol: str,                                                                                        |
|                                                                                                     |
| as_of_date: date, \# 返回该日期可用的最新财报                                                       |
|                                                                                                     |
| ctx: TemporalContext,                                                                               |
|                                                                                                     |
| ) -\> dict:                                                                                         |
|                                                                                                     |
| \"\"\"                                                                                              |
|                                                                                                     |
| 必含字段：pe_ratio, pb_ratio, roe, revenue, net_income,                                             |
|                                                                                                     |
| earnings_date, report_period, data_source, fetched_at                                               |
|                                                                                                     |
| 缺失字段用 None 填充，不得抛出异常                                                                  |
|                                                                                                     |
| \"\"\"                                                                                              |
|                                                                                                     |
| \...                                                                                                |
|                                                                                                     |
| def get_news(                                                                                       |
|                                                                                                     |
| self,                                                                                               |
|                                                                                                     |
| symbol: str,                                                                                        |
|                                                                                                     |
| days_back: int,                                                                                     |
|                                                                                                     |
| ctx: TemporalContext,                                                                               |
|                                                                                                     |
| ) -\> List\[NewsItem\]:                                                                             |
|                                                                                                     |
| \"\"\"                                                                                              |
|                                                                                                     |
| 内部调用 TemporalGuard.filter_news() 过滤未来新闻                                                   |
|                                                                                                     |
| 返回的 NewsItem 列表已通过时间隔离校验                                                              |
|                                                                                                     |
| relevance_score \< 0.6 的项目在内部过滤                                                             |
|                                                                                                     |
| \"\"\"                                                                                              |
|                                                                                                     |
| \...                                                                                                |
|                                                                                                     |
| def is_available(self, symbol: str) -\> bool: \...                                                  |
|                                                                                                     |
| def get_market_type(self, symbol: str) -\> Literal\[\'US\', \'CN_A\', \'HK\'\]: \...                |
+-----------------------------------------------------------------------------------------------------+

**4.1 适配器返回值校验规则**

  -----------------------------------------------------------------------------------------------------
  **方法**           **成功返回**                   **空数据处理**                 **异常处理**
  ------------------ ------------------------------ ------------------------------ --------------------
  get_ohlcv          非空 DataFrame，行数 ≥ 1       返回空                         记录错误日志，触发
                                                    DataFrame（0行），不抛出异常   FallbackManager

  get_fundamentals   包含所有必需 key 的 dict       缺失字段填 None，返回完整 dict 记录错误日志，触发
                                                                                   FallbackManager

  get_news           List\[NewsItem\]，可为空列表   返回 \[\]，不抛出异常          记录错误日志，返回
                                                                                   \[\]

  is_available       bool                           ---                            捕获异常，返回 False
  -----------------------------------------------------------------------------------------------------

**5. TemporalGuard 接口契约**

+-------------------------------------------------------------------+
| \# pstds/temporal/guard.py                                        |
|                                                                   |
| from datetime import datetime, date                               |
|                                                                   |
| from typing import List                                           |
|                                                                   |
| from pstds.data.models import NewsItem                            |
|                                                                   |
| from pstds.temporal.context import TemporalContext                |
|                                                                   |
| class TemporalViolationError(Exception):                          |
|                                                                   |
| \"\"\"数据时间戳违反时间隔离规则时抛出\"\"\"                      |
|                                                                   |
| def \_\_init\_\_(self, data_timestamp, analysis_date,             |
| caller_info: str):                                                |
|                                                                   |
| self.data_timestamp = data_timestamp                              |
|                                                                   |
| self.analysis_date = analysis_date                                |
|                                                                   |
| self.caller_info = caller_info                                    |
|                                                                   |
| super().\_\_init\_\_(                                             |
|                                                                   |
| f\'时间违规: 数据时间戳 {data_timestamp} \> analysis_date         |
| {analysis_date}\'                                                 |
|                                                                   |
| f\' (调用方: {caller_info})\'                                     |
|                                                                   |
| )                                                                 |
|                                                                   |
| class RealtimeAPIBlockedError(Exception):                         |
|                                                                   |
| \"\"\"BACKTEST 模式下调用实时 API 时抛出\"\"\"                    |
|                                                                   |
| pass                                                              |
|                                                                   |
| class TemporalGuard:                                              |
|                                                                   |
| \@staticmethod                                                    |
|                                                                   |
| def validate_timestamp(                                           |
|                                                                   |
| data_timestamp: datetime \| date,                                 |
|                                                                   |
| ctx: TemporalContext,                                             |
|                                                                   |
| caller_info: str = \'\',                                          |
|                                                                   |
| ) -\> None:                                                       |
|                                                                   |
| \"\"\"                                                            |
|                                                                   |
| 校验数据时间戳是否不晚于 ctx.analysis_date。                      |
|                                                                   |
| 违规时：记录审计日志 + 抛出 TemporalViolationError。              |
|                                                                   |
| \"\"\"                                                            |
|                                                                   |
| \...                                                              |
|                                                                   |
| \@staticmethod                                                    |
|                                                                   |
| def filter_news(                                                  |
|                                                                   |
| news_list: List\[NewsItem\],                                      |
|                                                                   |
| ctx: TemporalContext,                                             |
|                                                                   |
| ) -\> List\[NewsItem\]:                                           |
|                                                                   |
| \"\"\"                                                            |
|                                                                   |
| 过滤 published_at \> ctx.analysis_date 的新闻。                   |
|                                                                   |
| 记录过滤数量到审计日志。                                          |
|                                                                   |
| 返回：通过时间校验的 NewsItem 列表（原列表的子集）。              |
|                                                                   |
| \"\"\"                                                            |
|                                                                   |
| \...                                                              |
|                                                                   |
| \@staticmethod                                                    |
|                                                                   |
| def assert_backtest_safe(ctx: TemporalContext, api_name: str) -\> |
| None:                                                             |
|                                                                   |
| \"\"\"                                                            |
|                                                                   |
| BACKTEST 模式下调用实时 API 前必须调用此方法。                    |
|                                                                   |
| ctx.mode == \'BACKTEST\' 时抛出 RealtimeAPIBlockedError。         |
|                                                                   |
| \"\"\"                                                            |
|                                                                   |
| \...                                                              |
|                                                                   |
| \@staticmethod                                                    |
|                                                                   |
| def inject_temporal_prompt(base_prompt: str, ctx:                 |
| TemporalContext) -\> str:                                         |
|                                                                   |
| \"\"\"                                                            |
|                                                                   |
| 在 base_prompt 前插入 ctx.get_prompt_prefix()。                   |
|                                                                   |
| 返回：完整系统提示词字符串。                                      |
|                                                                   |
| \"\"\"                                                            |
|                                                                   |
| return ctx.get_prompt_prefix() + \'\\n\\n\' + base_prompt         |
+-------------------------------------------------------------------+

**6. 错误码体系**

  --------------------------------------------------------------------------------------------------------------
  **错误码**   **异常类**                 **触发场景**                **处理策略**
  ------------ -------------------------- --------------------------- ------------------------------------------
  E001         TemporalViolationError     数据时间戳 \> analysis_date 记录审计日志，跳过该数据项，不终止流程

  E002         RealtimeAPIBlockedError    BACKTEST 模式调用实时 API   记录日志，返回本地缓存数据，无缓存则报错

  E003         DataAdapterError           数据源连接失败或返回空      触发 FallbackManager，切换备用数据源

  E004         BudgetExceededError        Token 消耗超出预算上限      降级到更低 depth level 或截断输入

  E005         LLMOutputValidationError   Pydantic                    最多重试 3 次，仍失败则
                                          校验失败（TradeDecision）   action=INSUFFICIENT_DATA

  E006         LLMRateLimitError          API 触发限流（429）         指数退避重试，最多 3 次，间隔 1/2/4 秒

  E007         DebateQualityError         辩论质量分 \< 5.0           标记 conviction=LOW，UI
                                                                      显示警告，不终止流程

  E008         DataQualityError           数据质量分 \< 60            UI 显示警告，analysis 继续但标记低质量

  E009         MarketNotSupportedError    Symbol 格式无法识别         返回明确错误信息，不进入分析流程

  E010         ConfigurationError         必需配置缺失（如 API Key）  启动时检查，缺失则阻止分析并提示用户
  --------------------------------------------------------------------------------------------------------------

**7. 模块间依赖关系**

以下依赖关系图定义了各模块的导入规则。禁止出现循环依赖，禁止跨层直接调用（如展示层直接调用数据适配器）。

+-------------------------------------------------------------------+
| 允许的依赖方向（从上到下，禁止反向）：                            |
|                                                                   |
| web/ (展示层)                                                     |
|                                                                   |
| ↓ 只可调用                                                        |
|                                                                   |
| pstds/scheduler/ + pstds/agents/ (协调层+引擎层)                  |
|                                                                   |
| ↓ 只可调用                                                        |
|                                                                   |
| pstds/data/ (数据服务层)                                          |
|                                                                   |
| ↓ 只可调用                                                        |
|                                                                   |
| pstds/temporal/ (时间隔离层)                                      |
|                                                                   |
| ↓ 只可调用                                                        |
|                                                                   |
| pstds/storage/ + pstds/llm/ (基础设施)                            |
|                                                                   |
| 特殊规则：                                                        |
|                                                                   |
| \- pstds/temporal/ 不得导入任何其他 pstds 模块（防循环）          |
|                                                                   |
| \- pstds/agents/output_schemas.py 只可导入 pydantic 和标准库      |
|                                                                   |
| \- tradingagents/ 目录不得导入 pstds/ 中的任何模块                |
+-------------------------------------------------------------------+
