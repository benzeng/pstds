**个人专用股票交易决策系统**

PSTDS — Personal Stock Trading Decision System

**接口与数据契约规范（ISD）v2.0**

Internal Interface & Schema Design \| 2026年3月 \| 版本 v2.0

# 1. 文档目的

本文档定义 PSTDS v3.0 各模块之间的内部接口契约、数据结构规范和错误码体系。它是 Claude Code 编码阶段的直接参考文档，开发者在实现每个模块时，必须严格遵守本文档定义的接口签名、字段类型和约束条件。

v2.0 相较 ISD v1.0 的变更：新增 NewsFilterStats、PortfolioImpact、PositionAdvice、ReflectionRecord 四个数据类型；新增 PortfolioAnalyzer、NewsFilter、DeepSeekClient、DashScopeClient 四个接口契约；扩展错误码体系（新增 E011、E012）；更新 TradeDecision 模型（新增 portfolio_impact 字段）。

> 接口契约原则：接口一旦在本文档中定义，在同一版本内不得变更。ISD v1.0 中定义的所有接口在 v2.0 中完全兼容，仅为追加式扩展。

# 2. 核心数据类型规范

## 2.1 基础值类型（与 ISD v1.0 相同）

> 📌 Symbol / AnalysisDate / MarketType / AnalysisMode / DepthLevel / ActionType / Confidence / ConvictionLevel / TokenCount / CostUSD 类型定义与 ISD v1.0 第 2.1 节完全一致。

## 2.2 TemporalContext（无变更）

> 📌 与 ISD v1.0 第 2.2 节完全一致。frozen=True dataclass，for_live() / for_backtest() / get_prompt_prefix() 方法签名不变。

## 2.3 NewsFilterStats（v2.0 新增）

```python
# pstds/data/news_filter.py  
from dataclasses import dataclass  
  
@dataclass  
class NewsFilterStats:  
raw_count: int # 原始新闻条数  
after_temporal: int # L1时间戳过滤后  
after_relevance: int # L2相关性过滤后  
after_dedup: int # L3语义去重后（最终进入分析的数量）  
  
@property  
def temporal_filtered(self) -> int:  
return self.raw_count - self.after_temporal  
  
@property  
def relevance_filtered(self) -> int:  
return self.after_temporal - self.after_relevance  
  
@property  
def dedup_filtered(self) -> int:  
return self.after_relevance - self.after_dedup
```

## 2.4 PortfolioImpact（v2.0 新增）

```python
# pstds/portfolio/advisor.py  
from dataclasses import dataclass, field  
from typing import List, Tuple  
  
@dataclass  
class PortfolioImpact:  
"""批量分析时由 PortfolioCoordinator 填充，单股分析时 TradeDecision.portfolio_impact = None"""  
original_weight: float # 单股决策映射的初始仓位比例  
adjusted_weight: float # HHI约束调整后的仓位比例  
adjustment_reason: str # 调整原因说明  
high_correlation_pairs: List[Tuple[str, float]] = field(default_factory=list)  
# [(symbol, corr_coef), ...] 与本股高相关（>阈值）的股票对  
portfolio_hhi: float = 0.0 # 包含本股调整后的组合HHI
```

## 2.5 PositionAdvice（v2.0 新增）

```python
@dataclass  
class PositionAdvice:  
symbol: str  
initial_weight: float # ACTION_TO_WEIGHT 映射的原始建议仓位  
adjusted_weight: float # 组合约束调整后  
adjustment_reason: str  
operation: str # "BUY" | "SELL" | "HOLD"（相对当前持仓的操作）  
current_weight: Optional[float] = None # 当前实际持仓比例（用户提供时填充）
```

## 2.6 ReflectionRecord（v2.0 新增）

```python
@dataclass  
class ReflectionRecord:  
analysis_id: str # 关联 analyses 集合 _id  
symbol: str  
analysis_date: date  
predicted_action: str # 预测 action（BUY/SELL/HOLD/...）  
predicted_confidence: float # 预测置信度  
actual_return_next_day: float # 次日实际收益率（正=上涨，负=下跌）  
prediction_correct: bool # 方向预测是否正确  
# BUY预测且actual_return>0 = True  
# SELL预测且actual_return<0 = True  
# HOLD不计入准确率统计  
created_at: datetime # T+1日收盘后写入时间
```

## 2.7 NewsItem / OHLCVRecord / DataSource（无变更）

> 📌 与 ISD v1.0 第 2.3、2.4、2.5 节完全一致。

# 3. TradeDecision 标准决策模型（v2.0 更新）

```python
⚠️ TradeDecision 在 ISD v1.0 版本的所有字段和校验规则保持不变，v2.0 仅追加一个可选字段。

class TradeDecision(BaseModel):  
# ─── 以下字段与 ISD v1.0 完全一致 ──────────────────────────────  
action: Literal["STRONG_BUY","BUY","HOLD","SELL","STRONG_SELL","INSUFFICIENT_DATA"]  
confidence: float = Field(ge=0.0, le=1.0)  
conviction: Literal["HIGH", "MEDIUM", "LOW"]  
primary_reason: str = Field(max_length=100)  
insufficient_data: bool = False  
target_price_low: Optional[float] = Field(default=None, gt=0)  
target_price_high: Optional[float] = Field(default=None, gt=0)  
time_horizon: str  
risk_factors: List[str] = Field(min_length=1)  
data_sources: List[DataSource] = Field(min_length=1)  
analysis_date: date  
analysis_timestamp: datetime  
volatility_adjustment: float = Field(ge=0.5, le=2.0)  
debate_quality_score: float = Field(ge=0.0, le=10.0)  
symbol: str  
market_type: MarketType  
# ─── v2.0 新增字段 ──────────────────────────────────────────────  
portfolio_impact: Optional[PortfolioImpact] = None  
# 单股分析时为 None；批量分析经 PortfolioCoordinator 后填充  
  
# 校验规则（与 ISD v1.0 相同，不重复列出）
```

# 4. 新增接口契约

## 4.1 NewsFilter 接口契约

```python
# pstds/data/news_filter.py  
class NewsFilter:  
def __init__(  
self,  
relevance_threshold: float = 0.6, # L2相关性过滤阈值  
dedup_threshold: float = 0.85, # L3语义去重阈值  
method: Literal["tfidf", "embedding"] = "tfidf",  
): ...  
  
def filter(  
self,  
news_list: List[NewsItem],  
symbol: str,  
company_name: str,  
ctx: TemporalContext,  
) -> Tuple[List[NewsItem], NewsFilterStats]:  
"""  
串联执行三级过滤：  
L1: TemporalGuard.filter_news()（复用，不重新实现）  
L2: 相关性评分过滤（TF-IDF 或 embedding）  
L3: 语义去重（余弦相似度 > dedup_threshold 的副本删除，保留最早）  
  
约束：  
- 纯函数，不修改输入列表  
- 不抛出异常（内部错误退化为返回原列表+警告日志）  
- L2/L3 失败时静默降级到上一级输出  
"""  
...
```

## 4.2 PortfolioAnalyzer 接口契约

```python
# pstds/portfolio/analyzer.py  
class PortfolioAnalyzer:  
def correlation_matrix(  
self,  
symbols: List[str], # 至少2只，最多20只  
ctx: TemporalContext, # 必填，时间隔离上下文  
window_days: Optional[int] = None, # None时使用配置默认值  
) -> Optional[pd.DataFrame]:  
"""  
返回：N×N Pearson相关系数矩阵，index和columns均为symbols  
不满足 min_common_days（默认30）时返回 None，记录 DataQualityError 级别警告  
end_date 强制为 ctx.analysis_date（TemporalGuard 校验）  
"""  
  
def hhi(self, weights: Dict[str, float]) -> float:  
"""赫芬达尔指数 = sum(w_i^2)，范围 0-1，无需 ctx"""  
  
def volatility_contribution(  
self,  
symbols: List[str],  
weights: Dict[str, float], # 权重须归一化（总和≤1）  
ctx: TemporalContext,  
) -> Dict[str, float]: # symbol -> 贡献百分比（总和=100%）  
  
def stress_test(  
self,  
symbols: List[str],  
weights: Dict[str, float],  
ctx: TemporalContext,  
) -> float: # 负数，表示组合损失比例  
"""使用各股历史窗口内的最大单日跌幅作为压力情景  
明确标注：此为历史情景假设，不是概率预测  
"""
```

## 4.3 PositionAdvisor 接口契约

```python
class PositionAdvisor:  
def advise(  
self,  
decisions: List[TradeDecision],  
ctx: TemporalContext,  
current_positions: Optional[Dict[str, float]] = None,  
# symbol -> 当前仓位比例（0.0-1.0）  
) -> List[PositionAdvice]:  
"""  
算法步骤：  
1. ACTION_TO_WEIGHT 映射 → initial_weight  
2. 调用 PortfolioAnalyzer.correlation_matrix()  
3. 计算调整前 HHI  
4. 若 HHI > max_hhi：  
a. 识别高相关对（>high_correlation_threshold）  
b. 对高相关股票仓位按比例缩减直到 HHI ≤ max_hhi  
5. 若提供 current_positions：转换为增减操作  
adjusted - current > 0 → operation="BUY"  
adjusted - current < 0 → operation="SELL"  
|adjusted - current| < 0.02 → operation="HOLD"  
6. 返回 List[PositionAdvice]，总仓位保证 ≤ 100%  
"""
```

## 4.4 DeepSeekClient / DashScopeClient 接口契约

```python
# 两个客户端实现相同的 BaseLLMClient Protocol  
class DeepSeekClient:  
SUPPORTED_MODELS = ["deepseek-reasoner", "deepseek-chat"]  
  
def __init__(self, model: str, budget_tokens: int = 60000):  
"""从 DEEPSEEK_API_KEY 环境变量读取 Key  
未设置时抛出 ConfigurationError（E010）  
"""  
  
def invoke(  
self,  
messages: List[dict], # OpenAI格式 {role, content}  
system: str = "",  
) -> str:  
"""temperature=0.0（硬编码，不可配置）  
429响应：指数退避重试（1/2/4秒，3次）→ LLMRateLimitError（E006）  
其他HTTP错误：记录日志 → DataAdapterError（E003）  
"""  
  
class DashScopeClient:  
SUPPORTED_MODELS = ["qwen-max", "qwen-plus", "qwen-turbo"]  
# 接口签名与 DeepSeekClient 完全相同，Key 变量为 DASHSCOPE_API_KEY
```

## 4.5 MarketDataAdapter Protocol（无变更）

> 📌 与 ISD v1.0 第 4 节完全一致。所有适配器方法签名、返回值规范和异常处理策略不变。

## 4.6 TemporalGuard 接口（无变更）

> 📌 与 ISD v1.0 第 5 节完全一致。TemporalViolationError / RealtimeAPIBlockedError / validate_timestamp / filter_news / assert_backtest_safe / inject_temporal_prompt 全部不变。

# 5. 错误码体系（v2.0 更新）

> 📌 E001-E010 与 ISD v1.0 第 6 节完全一致。v2.0 新增 E011、E012。

| **错误码** | **异常类**               | **触发场景**                     | **处理策略**                                    |
|------------|--------------------------|----------------------------------|-------------------------------------------------|
| E001       | TemporalViolationError   | 数据时间戳 \> analysis_date      | 记录审计日志，跳过该数据项，不终止流程          |
| E002       | RealtimeAPIBlockedError  | BACKTEST模式调用实时API          | 记录日志，返回本地缓存，无缓存则报错            |
| E003       | DataAdapterError         | 数据源连接失败或返回空           | 触发FallbackManager，切换备用数据源             |
| E004       | BudgetExceededError      | Token消耗超出预算上限            | 降级到更低depth level或截断输入                 |
| E005       | LLMOutputValidationError | Pydantic校验失败                 | 最多重试3次，仍失败则 action=INSUFFICIENT_DATA  |
| E006       | LLMRateLimitError        | API触发限流（429）               | 指数退避重试（1/2/4秒，最多3次）                |
| E007       | DebateQualityError       | 辩论质量分\<5.0                  | 标记 conviction=LOW，UI显示警告，不终止         |
| E008       | DataQualityError         | 数据质量分\<60                   | UI显示警告，analysis继续但标记低质量            |
| E009       | MarketNotSupportedError  | Symbol格式无法识别               | 返回明确错误信息，不进入分析流程                |
| E010       | ConfigurationError       | 必需配置缺失（如API Key）        | 启动时检查，缺失则阻止分析并提示用户            |
| E011       | PortfolioDataError       | 组合分析共同交易日不足（\<30天） | 返回None相关性矩阵，UI显示警告，跳过HHI约束调整 |
| E012       | ReflectionScheduleError  | T+1反事实任务注册失败            | 记录警告日志，静默跳过，不影响主分析流程        |

# 6. 模块间依赖关系（v2.0 更新）

在 ISD v1.0 第 7 节的依赖规则基础上，v2.0 新增以下规则：

```python
允许的依赖方向（从上到下，禁止反向）：  
  
web/ (展示层)  
↓ 只可调用  
pstds/scheduler/ + pstds/agents/ + pstds/portfolio/coordinator.py（协调层）  
↓ 只可调用  
pstds/portfolio/analyzer.py + pstds/portfolio/advisor.py（组合计算层）  
pstds/data/ + pstds/memory/（数据服务层）  
↓ 只可调用  
pstds/temporal/（时间隔离层）  
↓ 只可调用  
pstds/storage/ + pstds/llm/（基础设施）  
  
v2.0 新增特殊规则：  
- pstds/portfolio/analyzer.py 可以调用 pstds/data/（获取OHLCV），但不可调用 pstds/agents/  
- pstds/memory/ 可以调用 pstds/storage/（MongoDB/ChromaDB），但不可调用 pstds/agents/  
- pstds/data/news_filter.py 只可调用 pstds/temporal/ 和 sklearn/sentence-transformers  
- tradingagents/ 目录不得导入 pstds/ 中的任何模块（同 v1.0）
```
