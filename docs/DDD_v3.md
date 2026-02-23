**个人专用股票交易决策系统**

PSTDS — Personal Stock Trading Decision System

**详细设计文档（DDD）v3.0**

工程质量基线 + 功能补全 + 组合分析扩展 \| 2026年3月 \| 版本 v3.0

# 1. 项目目录结构（v3.0 更新）

v3.0 在 v2.0 目录结构基础上新增 pstds/portfolio/ 模块，补全 memory/ 三个文件，新增 pstds/llm/deepseek.py 和 dashscope.py，新增 pstds/backtest/report.py，新增 pstds/data/news_filter.py，新增 pstds/storage/models.py。

```python
pstds/ ← 项目根目录  
├── tradingagents/ ← 原版 TradingAgents 核心（不修改）  
│  
├── pstds/ ← 本项目扩展代码  
│ ├── temporal/ ← 时间隔离层（✅ v2.0 已实现，v3.0 不变）  
│ │ ├── context.py  
│ │ ├── guard.py  
│ │ └── audit.py  
│ │  
│ ├── data/ ← 数据服务层  
│ │ ├── adapters/ ← 市场数据适配器（✅ v2.0 已实现，v3.0 不变）  
│ │ │ ├── base.py  
│ │ │ ├── yfinance_adapter.py  
│ │ │ ├── akshare_adapter.py  
│ │ │ ├── alphavantage_adapter.py  
│ │ │ └── local_csv_adapter.py  
│ │ ├── news_filter.py ← 🆕 v3.0 新增：三级新闻过滤器  
│ │ ├── cache.py ← ✅ v2.0 已实现（bug 已修）  
│ │ ├── router.py ← ✅ v2.0 已实现（bug 已修）  
│ │ ├── quality_guard.py ← ✅ v2.0 已实现（bug 已修）  
│ │ ├── models.py ← ✅ v2.0 已实现  
│ │ └── fallback.py ← ✅ v2.0 已实现  
│ │  
│ ├── agents/ ← Agent 扩展（✅ v2.0 已实现，v3.0 不变）  
│ │ ├── extended_graph.py ← ♻️ 微调：NewsFilter 调用点、retry 改进  
│ │ ├── debate_referee.py  
│ │ ├── result_saver.py  
│ │ └── output_schemas.py  
│ │  
│ ├── llm/ ← LLM 适配器扩展  
│ │ ├── factory.py ← ✅ v2.0 已实现  
│ │ ├── deepseek.py ← 🆕 v3.0 新增：DeepSeek 适配器  
│ │ ├── dashscope.py ← 🆕 v3.0 新增：阿里 Qwen 适配器  
│ │ └── cost_estimator.py ← ♻️ v3.0 更新：新增 DeepSeek/Qwen 计费表  
│ │  
│ ├── portfolio/ ← 🆕 v3.0 全新模块：组合分析  
│ │ ├── __init__.py  
│ │ ├── analyzer.py ← PortfolioAnalyzer（相关性、VaR）  
│ │ ├── advisor.py ← PositionAdvisor（仓位建议）  
│ │ └── models.py ← PortfolioAnalysisResult、PositionAdvice 等  
│ │  
│ ├── backtest/ ← 回测引擎  
│ │ ├── runner.py ← ✅ v2.0 已实现  
│ │ ├── calendar.py ← ✅ v2.0 已实现  
│ │ ├── portfolio.py ← ✅ v2.0 已实现（bug 已修）  
│ │ ├── executor.py ← ✅ v2.0 已实现（bug 已修）  
│ │ ├── performance.py ← ✅ v2.0 已实现（bug 已修）  
│ │ └── report.py ← 🆕 v3.0 新增：BacktestReportGenerator  
│ │  
│ ├── memory/ ← 记忆系统  
│ │ ├── short_term.py ← 🆕 v3.0 新增：短期工作记忆  
│ │ ├── episodic.py ← ♻️ v3.0 补全：骨架 → 完整实现  
│ │ ├── pattern.py ← 🆕 v3.0 新增：长期模式记忆  
│ │ └── reflection.py ← 🆕 v3.0 新增：反事实记忆与提炼  
│ │  
│ ├── scheduler/ ← 任务调度（✅ v2.0 已实现）  
│ │ ├── scheduler.py ← ♻️ v3.0 新增反事实记忆周任务  
│ │ └── task_queue.py  
│ │  
│ ├── storage/ ← 持久化层  
│ │ ├── mongo_store.py ← ✅ v2.0 已实现  
│ │ ├── watchlist_store.py ← ✅ v2.0 已实现  
│ │ └── models.py ← 🆕 v3.0 新增：MongoDB 文档模型定义  
│ │  
│ ├── export/ ← 报告导出（✅ v2.0 已实现）  
│ │ ├── pdf_exporter.py ← ♻️ v3.0 支持组合/回测报告  
│ │ ├── docx_exporter.py ← ♻️ v3.0 支持组合/回测报告  
│ │ └── md_exporter.py  
│ │  
│ ├── notify/ ← 通知模块（✅ v2.0 已实现，v3.0 不变）  
│ │ ├── desktop.py  
│ │ └── email_notify.py  
│ │  
│ └── config.py ← ✅ v2.0 已实现（S1 bug 已修）  
│  
├── web/ ← Streamlit Web App  
│ ├── app.py ← ✅ v2.0 已实现  
│ ├── pages/  
│ │ ├── 01_analysis.py ← ✅ v2.0 已实现  
│ │ ├── 02_watchlist.py ← ✅ v2.0 已实现  
│ │ ├── 03_history.py ← ♻️ v3.0 新增决策准确率趋势图  
│ │ ├── 04_backtest.py ← ♻️ v3.0 归因分析、历史报告检索  
│ │ ├── 05_cost.py ← ✅ v2.0 已实现  
│ │ ├── 06_portfolio.py ← ♻️ v3.0 与 PortfolioAnalyzer 联动  
│ │ ├── 07_settings.py ← ♻️ v3.0 新增 DeepSeek/Qwen 配置  
│ │ └── 08_portfolio_analysis.py ← 🆕 v3.0 全新：组合分析页面  
│ └── components/  
│ ├── chart.py ← ♻️ v3.0 全屏模式、时间周期、深色主题  
│ └── report_card.py ← ✅ v2.0 已实现  
│  
├── tests/  
│ ├── unit/  
│ │ ├── test_temporal_guard.py ← ✅ TG-001~TG-012 全部通过  
│ │ ├── test_output_schemas.py ← ✅ PM-001~PM-008 全部通过  
│ │ ├── test_market_router.py ← ✅ RT-001~RT-008 全部通过  
│ │ ├── test_news_filter.py ← 🆕 v3.0 新增（NF 系列测试用例）  
│ │ ├── test_portfolio_analyzer.py ← 🆕 v3.0 新增（PA 系列测试用例）  
│ │ └── test_memory_system.py ← 🆕 v3.0 新增（MEM 系列测试用例）  
│ ├── adapters/ ← ✅ v2.0 已实现  
│ └── integration/ ← ✅ v2.0 已实现，v3.0 补充组合分析集成测试  
│  
├── config/  
│ ├── default.yaml ← ♻️ v3.0 新增 portfolio/memory/llm 配置项  
│ └── user.yaml ← gitignore（已修复 S1 安全问题）  
│  
├── data/ ← 运行时数据（gitignore）  
├── docker-compose.yml ← ♻️ v3.0 新增环境变量  
├── Dockerfile  
├── requirements.txt ← ♻️ v3.0 新增依赖  
└── start.py
```

# 2. 新增/补全模块详细设计

## 2.1 pstds/data/news_filter.py（v3.0 新增）

```python
# pstds/data/news_filter.py  
  
from dataclasses import dataclass  
from typing import List, Optional  
from datetime import datetime  
import time  
from sklearn.feature_extraction.text import TfidfVectorizer  
from sklearn.metrics.pairwise import cosine_similarity  
import numpy as np  
from pstds.data.models import NewsItem  
from pstds.temporal.context import TemporalContext  
from pstds.temporal.guard import TemporalGuard  
  
@dataclass  
class NewsFilterResult:  
passed: List[NewsItem]  
dropped_future: int  
dropped_irrelevant: int  
dropped_duplicate: int  
filter_duration_ms: float  
  
class NewsFilter:  
def __init__(  
self,  
relevance_threshold: float = 0.6, # 第二级相关性阈值  
dedup_threshold: float = 0.85, # 第三级去重阈值  
):  
self.relevance_threshold = relevance_threshold  
self.dedup_threshold = dedup_threshold  
  
def filter(  
self,  
news_list: List[NewsItem],  
symbol: str,  
ctx: TemporalContext,  
keywords: Optional[List[str]] = None,  
) -> NewsFilterResult:  
t0 = time.monotonic()  
  
# 第一级：时间隔离（委托 TemporalGuard）  
compliant = TemporalGuard.filter_news(news_list, ctx)  
dropped_future = len(news_list) - len(compliant)  
  
# 第二级：语义相关性评分  
kw = keywords or [symbol]  
relevant = [n for n in compliant if self._score_relevance(n, kw) >= self.relevance_threshold]  
dropped_irrelevant = len(compliant) - len(relevant)  
  
# 第三级：语义去重（保留时间最早的）  
deduped = self._deduplicate(relevant)  
dropped_duplicate = len(relevant) - len(deduped)  
  
return NewsFilterResult(  
passed=deduped,  
dropped_future=dropped_future,  
dropped_irrelevant=dropped_irrelevant,  
dropped_duplicate=dropped_duplicate,  
filter_duration_ms=(time.monotonic() - t0) * 1000,  
)  
  
def _score_relevance(self, news: NewsItem, keywords: List[str]) -> float:  
"""TF-IDF 余弦相似度；若 ChromaDB 向量可用则使用句向量"""  
text = f"{news.title} {news.content}"  
query = " ".join(keywords)  
try:  
vec = TfidfVectorizer().fit_transform([text, query])  
return float(cosine_similarity(vec[0], vec[1])[0][0])  
except Exception:  
return 1.0 # 无法计算时默认通过  
  
def _deduplicate(self, news_list: List[NewsItem]) -> List[NewsItem]:  
"""两两相似度 > dedup_threshold 时保留最早一条"""  
if len(news_list) <= 1:  
return news_list  
texts = [f"{n.title} {n.content}" for n in news_list]  
try:  
tfidf = TfidfVectorizer().fit_transform(texts)  
sim_matrix = cosine_similarity(tfidf)  
except Exception:  
return news_list  
kept_indices = []  
removed = set()  
sorted_by_time = sorted(range(len(news_list)),  
key=lambda i: news_list[i].published_at)  
for i in sorted_by_time:  
if i in removed:  
continue  
kept_indices.append(i)  
for j in sorted_by_time:  
if j != i and j not in removed and sim_matrix[i][j] > self.dedup_threshold:  
removed.add(j)  
return [news_list[i] for i in sorted(kept_indices,  
key=lambda i: news_list[i].published_at)]
```

## 2.2 pstds/portfolio/models.py（v3.0 新增）

```python
# pstds/portfolio/models.py  
  
from dataclasses import dataclass, field  
from typing import List, Dict, Tuple, Optional  
from datetime import date  
import pandas as pd  
  
@dataclass  
class PortfolioAnalysisResult:  
symbols: List[str]  
analysis_date: date  
correlation_matrix: pd.DataFrame # shape: n×n，index/columns 为 symbol  
high_correlation_pairs: List[Tuple[str,str,float]] # (sym1, sym2, corr) corr > 0.7  
sector_weights: Dict[str, float] # {sector_name: weight}  
sector_concentration_warning: bool # 任一行业权重 > 40%  
portfolio_var_95: Optional[float] # 历史模拟 VaR（仅有持仓权重时计算）  
homogeneity_warning: bool # 均值相关性 > 0.6  
data_quality_score: float # 0-100  
analysis_id: str # UUID  
  
@dataclass  
class PositionAdvice:  
weights: Dict[str, float] # {symbol: recommended_weight}，总和 = 1.0  
rationale: Dict[str, str] # {symbol: 建议原因说明}  
risk_warnings: List[str] # 组合级风险警告列表  
optimization_method: str # 'equal_weight'|'confidence_weighted'|'max_sharpe'  
constraint_violations: List[str] # 约束违反说明（若有）
```

## 2.3 pstds/portfolio/analyzer.py（v3.0 新增）

```python
# pstds/portfolio/analyzer.py  
  
import uuid  
import numpy as np  
import pandas as pd  
from typing import List, Optional, Dict  
from datetime import date  
from pstds.portfolio.models import PortfolioAnalysisResult  
from pstds.temporal.context import TemporalContext  
from pstds.data.router import DataRouter  
  
class PortfolioAnalyzer:  
def __init__(self, data_router: DataRouter):  
self._router = data_router  
  
def analyze(  
self,  
symbols: List[str],  
ctx: TemporalContext, # 必填，TemporalGuard 校验  
positions: Optional[Dict[str, float]] = None, # {symbol: weight}  
lookback_days: int = 60,  
) -> PortfolioAnalysisResult:  
assert len(symbols) <= 20, "最多支持 20 只股票"  
  
# 1. 批量获取 OHLCV（共享同一 TemporalContext）  
ohlcv_batch = {}  
quality_scores = []  
for sym in symbols:  
df = self._router.get_ohlcv(sym, lookback_days=lookback_days, ctx=ctx)  
if df is not None and len(df) >= 10:  
ohlcv_batch[sym] = df  
quality_scores.append(min(len(df) / lookback_days * 100, 100))  
  
if len(ohlcv_batch) < 2:  
# 数据不足，退化为空结果  
return self._empty_result(symbols, ctx.analysis_date)  
  
# 2. 计算日收益率矩阵  
returns = pd.DataFrame({  
sym: df['close'].pct_change().dropna()  
for sym, df in ohlcv_batch.items()  
}).dropna()  
  
# 3. 相关性矩阵  
corr_matrix = returns.corr()  
high_pairs = [  
(s1, s2, float(corr_matrix.loc[s1, s2]))  
for i, s1 in enumerate(corr_matrix.columns)  
for j, s2 in enumerate(corr_matrix.columns)  
if i < j and abs(corr_matrix.loc[s1, s2]) > 0.7  
]  
  
# 4. 组合 VaR（历史模拟法，95% 置信度）  
var_95 = None  
if positions:  
w = np.array([positions.get(s, 0) for s in returns.columns])  
portfolio_returns = returns.values @ w  
var_95 = float(np.percentile(portfolio_returns, 5))  
  
# 5. 行业集中度（从基本面数据获取 sector）  
sector_weights = self._calc_sector_weights(symbols, positions, ctx)  
sector_warning = any(v > 0.4 for v in sector_weights.values())  
  
# 6. 同质化预警  
mean_corr = float(corr_matrix.values[np.triu_indices_from(corr_matrix.values, k=1)].mean())  
homogeneity_warning = mean_corr > 0.6  
  
return PortfolioAnalysisResult(  
symbols=list(ohlcv_batch.keys()),  
analysis_date=ctx.analysis_date,  
correlation_matrix=corr_matrix,  
high_correlation_pairs=high_pairs,  
sector_weights=sector_weights,  
sector_concentration_warning=sector_warning,  
portfolio_var_95=var_95,  
homogeneity_warning=homogeneity_warning,  
data_quality_score=float(np.mean(quality_scores)) if quality_scores else 0.0,  
analysis_id=str(uuid.uuid4()),  
)  
  
def _calc_sector_weights(self, symbols, positions, ctx) -> Dict[str, float]:  
"""获取各股行业，计算持仓权重分布"""  
sector_map = {}  
for sym in symbols:  
try:  
fund = self._router.get_fundamentals(sym, ctx.analysis_date, ctx)  
sector_map[sym] = fund.get('sector', 'Unknown') if fund else 'Unknown'  
except Exception:  
sector_map[sym] = 'Unknown'  
if not positions:  
equal_w = 1.0 / len(symbols)  
positions = {s: equal_w for s in symbols}  
result: Dict[str, float] = {}  
for sym, sector in sector_map.items():  
result[sector] = result.get(sector, 0) + positions.get(sym, 0)  
return result  
  
def _empty_result(self, symbols, analysis_date) -> PortfolioAnalysisResult:  
return PortfolioAnalysisResult(  
symbols=symbols, analysis_date=analysis_date,  
correlation_matrix=pd.DataFrame(), high_correlation_pairs=[],  
sector_weights={}, sector_concentration_warning=False,  
portfolio_var_95=None, homogeneity_warning=False,  
data_quality_score=0.0, analysis_id=str(uuid.uuid4()),  
)
```

## 2.4 pstds/portfolio/advisor.py（v3.0 新增）

```python
# pstds/portfolio/advisor.py  
  
from typing import List, Optional, Dict, Literal  
import numpy as np  
from pstds.portfolio.models import PortfolioAnalysisResult, PositionAdvice  
from pstds.agents.output_schemas import TradeDecision  
  
# 单只股票最大仓位  
MAX_SINGLE_POSITION = 0.30  
# 高相关对（>0.7）总仓位上限  
MAX_CORR_PAIR_POSITION = 0.50  
  
class PositionAdvisor:  
def advise(  
self,  
decisions: List[TradeDecision],  
analysis: PortfolioAnalysisResult,  
risk_profile: Literal['conservative', 'balanced', 'aggressive'],  
current_positions: Optional[Dict[str, float]] = None,  
) -> PositionAdvice:  
# 过滤 BUY/STRONG_BUY 的决策  
buy_decisions = [d for d in decisions if d.action in ('BUY', 'STRONG_BUY', 'HOLD')]  
if not buy_decisions:  
return PositionAdvice(  
weights={d.symbol: 0.0 for d in decisions},  
rationale={d.symbol: '无 BUY/HOLD 信号' for d in decisions},  
risk_warnings=['所有股票均为 SELL/INSUFFICIENT_DATA，建议空仓'],  
optimization_method='none',  
constraint_violations=[],  
)  
  
# 按置信度加权（基础）  
method = 'confidence_weighted'  
symbols = [d.symbol for d in buy_decisions]  
confs = np.array([d.confidence for d in buy_decisions])  
raw_weights = confs / confs.sum()  
  
# 应用保守/激进调整  
if risk_profile == 'conservative':  
raw_weights = raw_weights * 0.7 # 最多持仓 70%，留 30% 现金  
elif risk_profile == 'aggressive':  
pass # 全仓  
  
# 应用单只上限约束  
weights = np.minimum(raw_weights, MAX_SINGLE_POSITION)  
if weights.sum() > 0:  
weights = weights / weights.sum() * min(raw_weights.sum(), 1.0)  
  
weights_dict = {sym: float(w) for sym, w in zip(symbols, weights)}  
  
# 检查高相关对约束  
violations = []  
for s1, s2, corr in analysis.high_correlation_pairs:  
if s1 in weights_dict and s2 in weights_dict:  
pair_weight = weights_dict[s1] + weights_dict[s2]  
if pair_weight > MAX_CORR_PAIR_POSITION:  
violation = f"{s1}+{s2} 相关性 {corr:.2f}，合计仓位 {pair_weight:.1%} 超过上限 {MAX_CORR_PAIR_POSITION:.0%}"  
violations.append(violation)  
# 等比缩减  
factor = MAX_CORR_PAIR_POSITION / pair_weight  
weights_dict[s1] *= factor  
weights_dict[s2] *= factor  
  
# 补全 SELL/INSUFFICIENT_DATA 的股票（权重为 0）  
for d in decisions:  
if d.symbol not in weights_dict:  
weights_dict[d.symbol] = 0.0  
  
rationale = {  
d.symbol: (f"置信度 {d.confidence:.0%}，{d.action}；建议仓位 {weights_dict[d.symbol]:.1%}"  
if d.action in ('BUY','STRONG_BUY','HOLD')  
else f"{d.action}，不建议持仓")  
for d in decisions  
}  
  
risk_warnings = []  
if analysis.homogeneity_warning:  
risk_warnings.append("⚠️ 组合高度同质化（平均相关性 > 0.6），波动风险集中")  
if analysis.sector_concentration_warning:  
risk_warnings.append("⚠️ 行业集中度过高（某行业权重 > 40%）")  
  
return PositionAdvice(  
weights=weights_dict,  
rationale=rationale,  
risk_warnings=risk_warnings,  
optimization_method=method,  
constraint_violations=violations,  
)
```

## 2.5 pstds/memory/short_term.py（v3.0 新增）

```python
# pstds/memory/short_term.py  
  
import json  
import uuid  
from pathlib import Path  
from typing import Optional  
from datetime import datetime  
  
SNAPSHOT_DIR = Path("./data/snapshots")  
MAX_SNAPSHOTS = 5  
  
class ShortTermMemory:  
"""短期工作记忆：GraphState 快照序列化，支持会话恢复"""  
  
def __init__(self, snapshot_dir: Path = SNAPSHOT_DIR):  
self.snapshot_dir = snapshot_dir  
self.snapshot_dir.mkdir(parents=True, exist_ok=True)  
  
def save_snapshot(self, state: dict, analysis_id: str) -> str:  
"""序列化 GraphState 快照到文件，返回快照 ID"""  
snapshot_id = f"{analysis_id}_{datetime.utcnow().strftime('%Y%m%dT%H%M%S')}"  
path = self.snapshot_dir / f"{snapshot_id}.json"  
# 过滤不可序列化的字段（如 DataFrame）  
serializable = {k: v for k, v in state.items()  
if isinstance(v, (str, int, float, bool, list, dict, type(None)))}  
path.write_text(json.dumps(serializable, default=str, ensure_ascii=False))  
self._cleanup_old_snapshots()  
return snapshot_id  
  
def restore_snapshot(self, snapshot_id: str) -> Optional[dict]:  
"""从文件恢复 GraphState 快照"""  
path = self.snapshot_dir / f"{snapshot_id}.json"  
if not path.exists():  
return None  
return json.loads(path.read_text())  
  
def _cleanup_old_snapshots(self):  
"""保留最近 MAX_SNAPSHOTS 个快照"""  
files = sorted(self.snapshot_dir.glob("*.json"), key=lambda f: f.stat().st_mtime)  
for old in files[:-MAX_SNAPSHOTS]:  
old.unlink(missing_ok=True)
```

## 2.6 pstds/memory/pattern.py（v3.0 新增）

```python
# pstds/memory/pattern.py  
  
from dataclasses import dataclass  
from typing import List, Optional  
from datetime import datetime  
  
@dataclass  
class MemoryPattern:  
pattern_key: str # 如 "AAPL_high_volatility_bearish_signal"  
description: str # 可读描述  
symbol: Optional[str] # 特定股票（None 表示通用规律）  
market_condition: str # 'trending_up'|'trending_down'|'ranging'|'high_volatility'  
win_rate: float # 历史胜率（方向预测准确率）  
sample_count: int # 样本数  
evidence_ids: List[str] # 支撑此规律的 reflection_record IDs  
last_updated: datetime  
is_active: bool # 胜率低于 55% 后标记为非活跃  
  
class PatternMemory:  
"""长期模式记忆，从 MongoDB memory_patterns 集合读写"""  
  
def __init__(self, mongo_store):  
self._store = mongo_store  
  
def add_or_update_pattern(self, pattern: MemoryPattern) -> None:  
"""新增或更新（upsert，以 pattern_key 为唯一键）"""  
self._store.upsert_pattern(pattern)  
  
def get_patterns(self, symbol: Optional[str] = None,  
min_win_rate: float = 0.6,  
min_samples: int = 10) -> List[MemoryPattern]:  
"""获取活跃规律，按 win_rate 降序"""  
return self._store.query_patterns(symbol=symbol, min_win_rate=min_win_rate,  
min_samples=min_samples, is_active=True)
```

## 2.7 pstds/memory/reflection.py（v3.0 新增）

```python
# pstds/memory/reflection.py  
  
from dataclasses import dataclass  
from typing import List, Optional  
from datetime import date, timedelta  
  
@dataclass  
class ReflectionRecord:  
analysis_id: str  
symbol: str  
analysis_date: date  
predicted_action: str # BUY/SELL/HOLD 等  
predicted_confidence: float  
actual_return_next_day: Optional[float] # T+1 实际涨跌幅  
is_direction_correct: Optional[bool] # 预测方向与实际涨跌是否一致  
created_at: str  
  
@dataclass  
class MonthlyAccuracy:  
year_month: str # '2024-03'  
total: int  
correct: int  
accuracy: float # correct / total  
  
@dataclass  
class RefinementReport:  
patterns_added: int  
patterns_updated: int  
samples_processed: int  
  
class ReflectionEngine:  
def __init__(self, mongo_store, data_router, pattern_memory):  
self._store = mongo_store  
self._router = data_router  
self._patterns = pattern_memory  
  
def record_outcome(self, analysis_id: str,  
symbol: str,  
analysis_date: date,  
predicted_action: str,  
predicted_confidence: float) -> None:  
"""T+1 自动获取实际价格变化，写入 reflection_records"""  
next_day = self._get_next_trading_day(analysis_date, symbol)  
actual_return = self._fetch_actual_return(symbol, analysis_date, next_day)  
is_correct = self._evaluate_direction(predicted_action, actual_return)  
record = ReflectionRecord(  
analysis_id=analysis_id, symbol=symbol,  
analysis_date=analysis_date, predicted_action=predicted_action,  
predicted_confidence=predicted_confidence,  
actual_return_next_day=actual_return,  
is_direction_correct=is_correct,  
created_at=str(date.today()),  
)  
self._store.insert_reflection(record)  
  
def run_weekly_refinement(self) -> RefinementReport:  
"""每周一次批量提炼：high-confidence correct → memory_patterns"""  
records = self._store.get_reflection_records(  
min_confidence=0.7, is_direction_correct=True)  
# 按 symbol + market_condition 聚合，计算胜率  
groups = {}  
for r in records:  
key = f"{r.symbol}_{self._classify_market(r)}"  
groups.setdefault(key, []).append(r)  
added = updated = 0  
for key, group in groups.items():  
if len(group) < 10:  
continue  
win_rate = sum(1 for r in group if r.is_direction_correct) / len(group)  
if win_rate < 0.65:  
continue  
from pstds.memory.pattern import MemoryPattern  
from datetime import datetime  
pattern = MemoryPattern(  
pattern_key=key, description=f"Auto-refined: {key}",  
symbol=group[0].symbol, market_condition=self._classify_market(group[0]),  
win_rate=win_rate, sample_count=len(group),  
evidence_ids=[r.analysis_id for r in group[-10:]],  
last_updated=datetime.utcnow(), is_active=True,  
)  
existing = self._patterns.get_patterns(symbol=group[0].symbol)  
if any(p.pattern_key == key for p in existing):  
updated += 1  
else:  
added += 1  
self._patterns.add_or_update_pattern(pattern)  
return RefinementReport(patterns_added=added, patterns_updated=updated,  
samples_processed=len(records))  
  
def get_accuracy_trend(self, symbol: Optional[str] = None,  
months: int = 6) -> List[MonthlyAccuracy]:  
"""月度预测准确率，供 UI 折线图"""  
return self._store.get_monthly_accuracy(symbol=symbol, months=months)  
  
def _get_next_trading_day(self, d: date, symbol: str) -> date:  
return d + timedelta(days=1) # 简化：实际需查 TradingCalendar  
  
def _fetch_actual_return(self, symbol: str, from_date: date, to_date: date):  
try:  
from pstds.temporal.context import TemporalContext  
ctx = TemporalContext.for_live(to_date)  
df = self._router.get_ohlcv(symbol, lookback_days=5, ctx=ctx)  
if df is not None and len(df) >= 2:  
return float((df.iloc[-1]['close'] - df.iloc[-2]['close']) / df.iloc[-2]['close'])  
except Exception:  
pass  
return None  
  
def _evaluate_direction(self, action: str, actual_return: Optional[float]) -> Optional[bool]:  
if actual_return is None:  
return None  
if action in ('BUY', 'STRONG_BUY'):  
return actual_return > 0  
if action in ('SELL', 'STRONG_SELL'):  
return actual_return < 0  
return None # HOLD 不评估方向  
  
def _classify_market(self, record) -> str:  
return 'unknown' # 实际实现需基于当日 VIX/波动率
```

## 2.8 pstds/backtest/report.py（v3.0 新增）

```python
# pstds/backtest/report.py  
  
from dataclasses import dataclass, field  
from typing import List, Tuple  
from datetime import date  
import pandas as pd  
from pstds.backtest.performance import PerformanceMetrics  
  
@dataclass  
class DailyRecord:  
date: date  
action: str  
confidence: float  
debate_quality_score: float  
actual_return_next_day: float # 实际次日涨跌幅  
pnl: float # 当日盈亏（绝对值）  
portfolio_value: float  
  
@dataclass  
class AttributionReport:  
signal_contribution: float # 多空信号贡献（%）  
volatility_adj_contribution: float # 波动率调整贡献（%）  
data_quality_impact: float # 数据质量影响（%）  
unexplained: float # 残差  
  
@dataclass  
class BacktestReport:  
backtest_id: str  
symbol: str  
date_range: Tuple[date, date]  
config: dict  
performance: PerformanceMetrics  
nav_curve: pd.DataFrame # columns: [date, portfolio_value, benchmark_value]  
daily_records: List[DailyRecord]  
attribution: AttributionReport  
total_cost: dict # {tokens, usd}  
  
class BacktestReportGenerator:  
def generate(self, backtest_id: str, symbol: str,  
date_range: Tuple[date, date], config: dict,  
performance: PerformanceMetrics,  
daily_records: List[DailyRecord],  
benchmark_nav: pd.Series,  
total_cost: dict) -> BacktestReport:  
nav_curve = pd.DataFrame({  
'date': [r.date for r in daily_records],  
'portfolio_value': [r.portfolio_value for r in daily_records],  
'benchmark_value': benchmark_nav.values[:len(daily_records)],  
})  
attribution = self._calculate_attribution(daily_records)  
return BacktestReport(  
backtest_id=backtest_id, symbol=symbol, date_range=date_range,  
config=config, performance=performance, nav_curve=nav_curve,  
daily_records=daily_records, attribution=attribution, total_cost=total_cost,  
)  
  
def _calculate_attribution(self, records: List[DailyRecord]) -> AttributionReport:  
"""简化归因：按信号正确率计算各维度贡献"""  
if not records:  
return AttributionReport(0.0, 0.0, 0.0, 1.0)  
correct = [r for r in records if (r.action in ('BUY','STRONG_BUY') and r.actual_return_next_day > 0)  
or (r.action in ('SELL','STRONG_SELL') and r.actual_return_next_day < 0)]  
signal_contrib = len(correct) / len(records) * 0.7  
vol_contrib = sum(r.pnl for r in records if r.confidence > 0.8) / max(abs(sum(r.pnl for r in records)), 1e-6) * 0.15  
quality_impact = -0.05 if any(r.debate_quality_score < 5 for r in records) else 0.0  
unexplained = 1.0 - signal_contrib - abs(vol_contrib) - abs(quality_impact)  
return AttributionReport(  
signal_contribution=round(signal_contrib, 4),  
volatility_adj_contribution=round(vol_contrib, 4),  
data_quality_impact=round(quality_impact, 4),  
unexplained=round(max(unexplained, 0), 4),  
)  
  
def export_pdf(self, report: BacktestReport, output_path: str) -> None:  
from pstds.export.pdf_exporter import PDFExporter  
PDFExporter().export_backtest(report, output_path)  
  
def export_docx(self, report: BacktestReport, output_path: str) -> None:  
from pstds.export.docx_exporter import DocxExporter  
DocxExporter().export_backtest(report, output_path)  
  
def export_markdown(self, report: BacktestReport, output_path: str) -> None:  
from pstds.export.md_exporter import MarkdownExporter  
MarkdownExporter().export_backtest(report, output_path)
```

## 2.9 pstds/storage/models.py（v3.0 新增）

```python
# pstds/storage/models.py  
# MongoDB 文档模型定义（使用 TypedDict 提供类型提示）  
  
from typing import TypedDict, List, Optional  
from datetime import date, datetime  
  
class AnalysisDocument(TypedDict):  
_id: str # UUID  
symbol: str  
market_type: str # 'US'|'CN_A'|'HK'  
analysis_date: str # ISO date string  
created_at: datetime  
mode: str # 'LIVE'|'BACKTEST'  
config: dict # llm_provider, model, temperature, depth_level  
temporal: dict # compliant_news_count, filtered_news_count, violations  
data_quality: dict # score, missing_fields, anomaly_alerts, news_filter_stats  
reports: dict # market/sentiment/news/fundamentals/debate/trader/risk/final  
decision: dict # TradeDecision JSON  
input_hash: str # sha256 of (inputs + config)  
cost: dict # total_tokens, estimated_usd, actual_usd  
  
class PortfolioAnalysisDocument(TypedDict):  
_id: str # UUID = analysis_id  
symbols: List[str]  
analysis_date: str  
created_at: datetime  
correlation_matrix: dict # {symbol: {symbol: corr_value}}（DataFrame → dict）  
high_correlation_pairs: List[dict] # [{sym1, sym2, corr}]  
sector_weights: dict  
sector_concentration_warning: bool  
portfolio_var_95: Optional[float]  
homogeneity_warning: bool  
data_quality_score: float  
position_advice: Optional[dict] # PositionAdvice JSON（若有）  
  
class ReflectionRecord(TypedDict):  
analysis_id: str  
symbol: str  
analysis_date: str  
predicted_action: str  
predicted_confidence: float  
actual_return_next_day: Optional[float]  
is_direction_correct: Optional[bool]  
created_at: str  
  
class MemoryPatternDocument(TypedDict):  
pattern_key: str # 唯一键  
description: str  
symbol: Optional[str]  
market_condition: str  
win_rate: float  
sample_count: int  
evidence_ids: List[str]  
last_updated: datetime  
is_active: bool  
  
class BacktestResultDocument(TypedDict):  
_id: str  
symbol: str  
date_range: dict # {start, end}  
config: dict  
performance: dict # 绩效指标  
daily_records: List[dict]  
attribution: dict  
nav_curve: List[dict] # [{date, portfolio_value, benchmark_value}]  
total_cost: dict  
created_at: datetime  
  
class CostRecord(TypedDict):  
analysis_id: str  
provider: str  
model: str  
input_tokens: int  
output_tokens: int  
cost_usd: float  
created_at: datetime
```

# 3. 配置文件更新（default.yaml v3.0 变更部分）

```python
# config/default.yaml — v3.0 新增/变更配置项（其余与 v2.0 一致）  
  
# ─── 组合分析配置（v3.0 新增）────────────────────────────────  
portfolio:  
max_symbols: 20 # 组合分析最多股票数  
correlation_lookback_days: 60 # 相关性计算回看天数  
high_corr_threshold: 0.70 # 高相关预警阈值  
max_single_position: 0.30 # 单只最大仓位  
max_corr_pair_position: 0.50 # 高相关对总仓位上限  
sector_concentration_limit: 0.40 # 行业集中度上限  
  
# ─── 记忆系统配置（v3.0 补全）────────────────────────────────  
memory:  
episodic_window_days: 90 # 情景记忆滚动窗口  
pattern_min_win_rate: 0.65 # 模式提炼最低胜率  
pattern_min_samples: 10 # 模式提炼最低样本数  
reflection_schedule: "0 2 * * MON" # 反事实提炼 Cron（每周一 02:00）  
reflection_confidence_threshold: 0.70 # 纳入提炼的最低置信度  
snapshot_max_count: 5 # 短期记忆快照最大保留数  
embedding_provider: "local" # 'openai'|'local'（sentence-transformers）  
  
# ─── 新闻过滤配置（v3.0 补全）────────────────────────────────  
news_filter:  
relevance_threshold: 0.60 # 第二级相关性阈值  
dedup_threshold: 0.85 # 第三级去重相似度阈值  
  
# ─── LLM 配置（v3.0 新增 DeepSeek/DashScope）────────────────  
llm:  
# ... 原有配置不变 ...  
deepseek_base_url: "https://api.deepseek.com"  
dashscope_base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"  
# API Keys 通过环境变量注入，禁止写入此文件  
# DEEPSEEK_API_KEY=...  
# DASHSCOPE_API_KEY=...
```

# 4. 开发路线图（v3.0 更新版）

<table>
<colgroup>
<col style="width: 25%" />
<col style="width: 25%" />
<col style="width: 25%" />
<col style="width: 25%" />
</colgroup>
<thead>
<tr class="header">
<th><strong>阶段</strong></th>
<th><strong>目标版本</strong></th>
<th><strong>主要交付物</strong></th>
<th><strong>v3.0 状态</strong></th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td>Phase 0-3<br />
(v0.1-v0.7)</td>
<td>v0.7</td>
<td>环境搭建、时间隔离、数据层、<br />
核心 Web UI（CCG v1.0 定义的阶段）</td>
<td>✅ 已完成（含 bug 修复）</td>
</tr>
<tr class="even">
<td>Phase 4<br />
(v0.9)</td>
<td>v0.9</td>
<td>回测引擎（BacktestRunner 等）</td>
<td>✅ 已完成（executor/performance bug 已修）</td>
</tr>
<tr class="odd">
<td>Phase 5<br />
(v1.0)</td>
<td>v1.0</td>
<td>功能完善、文档</td>
<td>✅ 已完成（部分功能待补全）</td>
</tr>
<tr class="even">
<td>Phase 6<br />
v3.0-A<br />
(2-3周)</td>
<td>v3.0-A</td>
<td>① news_filter.py（三级过滤）<br />
② backtest/report.py<br />
③ storage/models.py<br />
④ llm/deepseek.py + dashscope.py<br />
⑤ 对应单元测试（NF/BR 系列）</td>
<td>🎯 优先完成</td>
</tr>
<tr class="odd">
<td>Phase 7<br />
v3.0-B<br />
(2-3周)</td>
<td>v3.0-B</td>
<td>① memory/ 三层完整架构<br />
② scheduler 周任务（ReflectionEngine）<br />
③ UI：history 准确率趋势、backtest 归因<br />
④ 对应测试（MEM/REF 系列）</td>
<td>🎯 紧随其后</td>
</tr>
<tr class="even">
<td>Phase 8<br />
v3.0-C<br />
(3-4周)</td>
<td>v3.0-C</td>
<td>① portfolio/ 模块（PortfolioAnalyzer + PositionAdvisor）<br />
② pages/08_portfolio_analysis.py<br />
③ 组合分析集成测试（PA 系列）<br />
④ 组合报告导出（PDF/Word）</td>
<td>🎯 最大新功能</td>
</tr>
<tr class="odd">
<td>Phase 9<br />
v3.0-D<br />
(1-2周)</td>
<td>v3.0</td>
<td>① Web UI 全面升级（全屏 K 线、深色主题）<br />
② 最终验证（所有测试通过）<br />
③ docker-compose.yml 更新<br />
④ 文档更新</td>
<td>🎯 收尾</td>
</tr>
<tr class="even">
<td>v3.x（TBD）</td>
<td>v3.x</td>
<td>① monkey-patch 架构重构（依赖注入）<br />
② Trading-R1 正式集成（待模型开源）</td>
<td>⏳ 后续规划</td>
</tr>
</tbody>
</table>
