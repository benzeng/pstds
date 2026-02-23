**个人专用股票交易决策系统**

PSTDS — Personal Stock Trading Decision System

**功能需求文档（FRD）v3.0**

工程质量基线 + 功能补全 + 组合分析扩展 \| 2026年3月 \| 版本 v3.0

# 1. 文档说明

## 1.1 编写目的

本文档在 PSTDS v2.0 FRD 基础上，综合 v2.0 实现阶段发现的工程质量问题与功能缺口，形成 v3.0 版功能需求规范。v3.0 的核心目标是将系统从「可运行的原型」升级为「生产可信赖的工具」，主要工作分三个层次：工程质量基线修复（已完成）、v2.0 设计补全、组合分析能力扩展。

## 1.2 v2.0 → v3.0 核心改进要点

<table>
<colgroup>
<col style="width: 33%" />
<col style="width: 33%" />
<col style="width: 33%" />
</colgroup>
<thead>
<tr class="header">
<th><strong>改进维度</strong></th>
<th><strong>v2.0 设计/实现状态</strong></th>
<th><strong>v3.0 改进内容</strong></th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td>工程质量（已完成）</td>
<td>API Key 明文存储、Parquet 去重缺失<br />
TTL 单位 bug、ImportError 等 9 项缺陷</td>
<td>所有缺陷在 v3.0 开发启动前已修复<br />
详见附录 A 变更日志</td>
</tr>
<tr class="even">
<td>新闻处理</td>
<td>news_filter.py 未实现，仅占位符</td>
<td>完整实现三级相关性过滤器<br />
（TF-IDF+向量相似度）+ 语义去重</td>
</tr>
<tr class="odd">
<td>记忆系统</td>
<td>仅 episodic.py 骨架<br />
short_term/pattern/reflection 均未实现</td>
<td>完整三层记忆架构：短期工作记忆<br />
情景记忆（ChromaDB）、长期模式记忆</td>
</tr>
<tr class="even">
<td>国产 LLM</td>
<td>LLMFactory 预留槽位<br />
DeepSeek/DashScope 适配器未实现</td>
<td>完整实现 DeepSeek 和阿里 Qwen 适配器<br />
含流式输出和 Token 计费</td>
</tr>
<tr class="odd">
<td>回测报告</td>
<td>BacktestReportGenerator 未实现</td>
<td>完整实现，含净值曲线、逐日决策记录<br />
绩效归因分析</td>
</tr>
<tr class="even">
<td>组合分析（新增）</td>
<td>v2.0 无此功能</td>
<td>新增 portfolio/ 模块：多股票相关性矩阵<br />
风险集中度分析、仓位建议引擎</td>
</tr>
<tr class="odd">
<td>Web UI</td>
<td>K线图基础实现，多页面功能不完整</td>
<td>组合热力图、历史决策准确率趋势图<br />
深色主题完善、全屏 K 线图</td>
</tr>
<tr class="even">
<td>Trading-R1</td>
<td>接口预留，模型未开源</td>
<td>维持接口预留，补充本地 fine-tune<br />
接入指南（v3.x 正式集成）</td>
</tr>
</tbody>
</table>

## 1.3 术语说明（v3.0 新增术语）

| **术语**          | **说明**                                                        |
|-------------------|-----------------------------------------------------------------|
| PortfolioAnalyzer | 组合分析器，计算多股票相关性矩阵、风险集中度、组合级 VaR        |
| PositionAdvisor   | 仓位建议引擎，结合各股 TradeDecision 和组合约束给出仓位分配建议 |
| NewsFilter        | 三级新闻过滤器：时间隔离 → 语义相关性 → 内容去重                |
| EpisodicMemory    | ChromaDB 情景记忆，存储近 90 天决策向量，支持语义相似检索       |
| PatternMemory     | MongoDB 长期模式记忆，从历史决策提炼有效规律                    |
| ReflectionEngine  | 反事实记忆引擎，对比预测与实际结果，触发模式提炼                |
| BacktestReport    | 回测报告完整对象，含绩效指标、净值曲线、逐日决策记录、归因分析  |

# 2. 产品概述

本节内容相较 v2.0 FRD 无结构性变化，仅版本号更新为 v3.0。产品定位、核心设计原则（时间隔离优先、确定性输出、成本可控、隐私优先、可解释性、多市场覆盖、渐进增强）及使用场景均保持不变。新增场景 E（组合管理）见第 3.8 节。

## 2.1 用户故事（v3.0 新增/变更）

| **ID** | **功能描述**                                   | **验收标准**                                  | **状态**     |
|--------|------------------------------------------------|-----------------------------------------------|--------------|
| US-11  | 对自选股列表进行组合级分析，查看各股相关性矩阵 | 相关性热力图可视化，高相关对（\>0.7）标红预警 | 🆕 v3.0      |
| US-12  | 基于组合现状获取仓位调整建议                   | 建议含具体仓位比例、理由和风险提示            | 🆕 v3.0      |
| US-13  | 查看历史分析决策的准确率趋势                   | 月度统计涨跌方向预测准确率折线图              | 🆕 v3.0      |
| US-14  | 系统自动从历史决策中提炼有效规律               | 长期模式记忆每周触发一次提炼，结果可查看      | 🆕 v3.0      |
| US-07  | 对指定历史区间进行回测，查看完整绩效报告       | 新增归因分析、净值曲线导出 PNG，历史报告检索  | ♻️ v3.0 增强 |
| US-03  | 批量提交多只股票进行并行分析                   | 新增组合级聚合视图                            | ♻️ v3.0 增强 |

# 3. 核心功能需求

## 3.1 数据时间隔离层（TemporalGuard）——维持 v2.0 设计

本节内容与 v2.0 FRD 第 3.1 节完全一致，不作变更。FR-TG01/02/03 均已实现并通过 TG-001 至 TG-012 全部测试用例。v3.0 中此层为只读稳定层。

## 3.2 核心智能体引擎——维持 v2.0 设计并修复工程缺陷

智能体角色和 LangGraph 工作流图与 v2.0 FRD 第 3.2 节一致。v3.0 变更：

1.  ① extended_graph.py 中的 monkey-patch 实现维持现状（标注为技术债 BUG-002，v3.x 专项重构）。

2.  ② validate_output_with_retry 重试时现在重新调用 LLM 并将错误信息反馈给模型，而非重试相同输出。

3.  ③ AuditLogger 实例化移至 filter_news 函数外部，消除每条新闻创建一次 logger 的性能问题。

## 3.3 结构化输出与确定性需求——维持 v2.0 设计

与 v2.0 FRD 第 3.3 节一致。FR-SO01/02/03 均已实现。

## 3.4 分析深度分级需求——维持 v2.0 设计

L0-L3 四级分析深度及 FR-CL01/02/03 与 v2.0 FRD 第 3.4 节一致。

## 3.5 新闻处理流水线（v3.0 补全实现）

⚠️ 此功能在 v2.0 FRD 中已设计（FR-D05/06/07），但 news_filter.py 未实现。v3.0 补全为核心可交付物。

FR-NF01：三级过滤流水线

- 第一级：时间隔离过滤（已由 TemporalGuard 实现）。

- 第二级：语义相关性评分——使用 TF-IDF 计算新闻与股票关键词余弦相似度；若 ChromaDB 可用则使用句向量相似度；阈值 0.6，低于此值丢弃并计数。

- 第三级：内容语义去重——计算通过第二级的新闻两两相似度，相似度 \> 0.85 的视为重复，保留时间最早的一条（确保时间隔离）。

FR-NF02：NewsFilter 输出标准化 NewsFilterResult 对象：

> NewsFilterResult:  
> passed: List\[NewsItem\] \# 通过三级过滤的新闻  
> dropped_future: int \# 第一级丢弃数  
> dropped_irrelevant: int \# 第二级丢弃数  
> dropped_duplicate: int \# 第三级丢弃数  
> filter_duration_ms: float \# 过滤耗时（毫秒）

FR-NF03：过滤统计写入 data_quality_report，在 UI 数据质量面板中展示各级丢弃数量。

## 3.6 完整记忆系统（v3.0 补全实现）

⚠️ v2.0 仅实现 episodic.py 骨架。v3.0 补全三层架构并实现反事实记忆提炼机制。

| **记忆层次** | **存储引擎**            | **时间跨度** | **v3.0 新增需求**                                                                 |
|--------------|-------------------------|--------------|-----------------------------------------------------------------------------------|
| 短期工作记忆 | Python 内存（dict）     | 单次分析会话 | FR-MEM01：GraphState 快照可序列化，支持会话恢复                                   |
| 中期情景记忆 | ChromaDB 向量库         | 近 90 天     | FR-MEM02：search_similar() 返回相似场景时同时返回该场景的实际结果（实现反馈闭环） |
| 长期模式记忆 | MongoDB memory_patterns | 永久积累     | FR-MEM03：每周自动触发一次模式提炼任务，将高价值规律写入 pattern 集合             |

FR-MEM04：反事实记忆（ReflectionEngine）实现要点：

- 每次分析后 T+1 个交易日，系统自动获取实际价格变化，与预测方向对比，记录到 MongoDB reflection_records 集合。

- 每周一次批量提炼：从 reflection_records 中提取高置信度且准确的预测模式，写入 memory_patterns。

- 提炼结果在 UI「历史分析」页面的「决策准确率趋势」中可视化展示。

## 3.7 国产 LLM 适配器（v3.0 补全实现）

⚠️ v2.0 LLMFactory 有 DeepSeek 和 DashScope 槽位但未实现。v3.0 完整交付。

| **适配器**       | **提供商**               | **v3.0 新增需求**                                                                                         |
|------------------|--------------------------|-----------------------------------------------------------------------------------------------------------|
| DeepSeekAdapter  | DeepSeek（深度求索）     | FR-LLM01：支持 deepseek-reasoner（深思）和 deepseek-chat（快速）；支持流式输出；计费按实际 usage 字段核算 |
| DashScopeAdapter | 阿里云 DashScope（Qwen） | FR-LLM02：支持 qwen-max / qwen-turbo；中文 A 股分析场景优化提示词；支持阿里云 Token 计费格式转换          |

FR-LLM03：所有新适配器必须通过现有 LLMFactory 统一接口，temperature 强制为 0.0，支持 budget_tokens 上限参数。

## 3.8 多股票组合分析（v3.0 全新功能）

🆕 此为 v3.0 最大新增功能模块，v2.0 设计文档中完全没有。新增 pstds/portfolio/ 模块和对应 Web 页面。

FR-PA01：相关性分析

- 输入：自选股列表（最多 20 只）+ analysis_date，输出皮尔逊相关性矩阵（基于近 60 个交易日收益率），高相关对（\> 0.7）标红预警。

- 所有数据访问经过 TemporalGuard 校验，支持 BACKTEST 模式。

FR-PA02：风险集中度评估

- 行业/板块集中度：计算各行业持仓权重，超过 40% 时警告。

- 组合级 VaR：基于历史模拟法计算 95% 置信度单日最大亏损。

- 组合相关性风险：所有持仓两两相关性均值 \> 0.6 时标记「高度同质化」警告。

FR-PA03：仓位建议引擎（PositionAdvisor）

- 输入：各股 TradeDecision（含 confidence/conviction）+ 当前持仓 + 风险偏好配置。

- 输出：建议仓位分配比例表，基于最大夏普比率优化（等权或按 confidence 加权可配置）。

- 约束：单只股票仓位上限 30%（可配置），高相关对之间总仓位上限 50%。

FR-PA04：组合分析不调用 LLM，纯量化本地计算，无额外 API 成本。

FR-PA05：Web 组合分析页面（pages/08_portfolio_analysis.py）

- 相关性热力图（Plotly 交互式，悬停显示具体数值）。

- 组合风险仪表盘（VaR、最大回撤、行业集中度）。

- 仓位建议表格（含每只股票建议比例和原因）。

- 支持导出为 PDF/Word 格式的组合分析报告。

## 3.9 回测报告生成器（v3.0 补全实现）

⚠️ v2.0 设计了 BacktestReportGenerator 但 report.py 未实现。v3.0 完整交付。

FR-BR01：BacktestReportGenerator 输出完整回测报告，包含：

- 绩效指标摘要（夏普、最大回撤、年化收益、胜率、卡尔马比率）。

- 逐日净值曲线数据（可导出为 Plotly 图表 PNG 或交互式 HTML）。

- 逐日决策记录表（日期、信号、置信度、实际涨跌、盈亏）。

- 归因分析：将盈亏来源分解为「多空信号贡献」「波动率调整贡献」「数据质量影响」三类。

FR-BR02：回测报告支持导出为 PDF/Word/Markdown 格式，复用 pstds/export/ 模块。

FR-BR03：回测报告保存到 MongoDB backtest_results，UI 回测历史页面可检索。

## 3.10 Web UI 升级（v3.0 增强）

| **页面/组件**                        | **v2.0 状态**     | **v3.0 升级内容**                                          |
|--------------------------------------|-------------------|------------------------------------------------------------|
| K 线图（chart.py）                   | 基础四层布局      | 全屏模式；技术指标叠加开关；1D/5D/1M/3M/1Y 周期切换        |
| 历史记录（03_history.py）            | 检索过滤          | 新增决策准确率趋势折线图（月度）；与 ReflectionEngine 联动 |
| 回测（04_backtest.py）               | 基础配置+指标展示 | 净值曲线导出 PNG；归因分析可视化；历史报告检索             |
| 组合分析（08_portfolio_analysis.py） | 不存在            | 全新页面：相关性热力图 + 风险仪表盘 + 仓位建议             |
| 深色主题                             | 部分支持          | 全页面深色主题统一，图表配色适配                           |

# 4. 数据管理需求（v3.0 变更部分）

## 4.1 市场数据获取——维持 v2.0 设计

v2.0 FRD 第 4.1 节内容不变（FR-D01 至 FR-D04）。新增：

- FR-D11：组合分析所需多股票批量 OHLCV 数据，通过 DataRouter 并行异步获取，共享同一 TemporalContext。

## 4.2 新闻与情绪数据——v3.0 补全 NewsFilter

FR-D05 至 FR-D08 维持 v2.0 设计。v3.0 补全实现细节见第 3.5 节（FR-NF01 至 FR-NF03）。

## 4.3 数据持久化——v3.0 新增集合

| **存储组件**               | **存储内容**                              | **保留策略**           | **状态**    |
|----------------------------|-------------------------------------------|------------------------|-------------|
| MongoDB portfolio_analyses | 组合分析结果（相关性矩阵、VaR、仓位建议） | 永久保留，≥ 1 年       | 🆕 新增     |
| MongoDB reflection_records | 预测与实际结果对比记录                    | 永久保留，用于模式提炼 | 🆕 新增     |
| MongoDB memory_patterns    | 长期模式记忆条目                          | 永久积累               | ♻️ 补全实现 |
| ChromaDB vector_memory/    | 近 90 天决策向量嵌入                      | 滚动窗口 90 天         | ♻️ 骨架补全 |
| 其他集合                   | 见 v2.0 FRD 第 4.3 节                     | 同 v2.0                | ✅ 不变     |

# 5. 回测引擎需求（v3.0 补全 BacktestReportGenerator）

v2.0 FRD 第 5 节的 FR-BT01 至 FR-BT05 全部维持。v3.0 补全：

- FR-BT06：BacktestReportGenerator 必须实现，具体需求见第 3.9 节（FR-BR01 至 FR-BR03）。

- FR-BT07：回测页面新增「历史报告」标签页，支持检索和对比不同参数配置的回测结果。

# 6. LLM 管理需求（v3.0 变更部分）

## 6.1 支持的 LLM 提供商（v3.0 更新）

| **提供商**         | **代表模型（深度/快速）**            | **适用场景**         | **v3.0 状态**     |
|--------------------|--------------------------------------|----------------------|-------------------|
| OpenAI             | gpt-4o / gpt-4o-mini                 | 全部 Agent           | ✅ 已实现         |
| Anthropic          | claude-sonnet-4-6 / claude-haiku-4-5 | 全部 Agent           | ✅ 已实现         |
| Google Gemini      | gemini-2.5-pro / gemini-2.0-flash    | 全部 Agent           | ✅ 已实现         |
| DeepSeek           | deepseek-reasoner / deepseek-chat    | 全部 Agent，成本优势 | 🆕 v3.0 实现      |
| 阿里 DashScope     | qwen-max / qwen-turbo                | A股分析优化          | 🆕 v3.0 实现      |
| Ollama 本地        | Qwen3-4B-Q4_K_M                      | 批量筛选/成本控制    | ✅ 已实现         |
| OpenRouter         | 聚合多提供商按需路由                 | 全部 Agent           | ✅ 已实现         |
| Trading-R1（预留） | Qwen 金融微调版（待开源）            | 交易员+风险管理      | ⏳ 接口预留，v3.x |

v2.0 FRD 第 6.2 节内容不变（FR-L01 至 FR-L05）。DeepSeek 和 DashScope 纳入分级路由，具体映射见 DDD v3.0 第 4.4 节。

# 7. 用户界面需求（v3.0 变更部分）

FR-UI01 至 FR-UI08 维持 v2.0 设计。v3.0 变更：

- FR-UI09：新增组合分析页面（pages/08_portfolio_analysis.py），见第 3.8 节 FR-PA05。

- FR-UI10：历史记录页面新增「决策准确率趋势」子标签页。

- FR-UI11：K线图组件新增全屏模式和时间周期切换（1D/5D/1M/3M/1Y）。

- FR-UI12：全页面深色主题统一（Streamlit theme 配置 + Plotly dark template）。

- 导出新增：FR-EX03 组合分析报告（PDF/Word），FR-EX04 回测报告（PDF/Word）。

# 8. 非功能性需求（v3.0 更新）

<table>
<colgroup>
<col style="width: 33%" />
<col style="width: 33%" />
<col style="width: 33%" />
</colgroup>
<thead>
<tr class="header">
<th><strong>NFR 类别</strong></th>
<th><strong>量化指标</strong></th>
<th><strong>v3.0 变更说明</strong></th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td>可信度（最高优先）</td>
<td>回测结果前视偏差为零</td>
<td>✅ 维持，v2.0 已通过 REG-001 至 REG-005</td>
</tr>
<tr class="even">
<td>成本效益</td>
<td>L2 深度分析 &lt; $0.30/次<br />
组合分析（纯量化）&lt; $0.01</td>
<td>组合分析不调用 LLM，纯本地计算</td>
</tr>
<tr class="odd">
<td>确定性</td>
<td>相同输入 95% 结果一致</td>
<td>✅ 维持</td>
</tr>
<tr class="even">
<td>响应速度</td>
<td>L1 &lt; 4 分钟；L2 &lt; 15 分钟<br />
组合分析 &lt; 30 秒（20 只股票）</td>
<td>新增组合分析响应时间要求</td>
</tr>
<tr class="odd">
<td>记忆系统</td>
<td>情景检索 P99 &lt; 200ms</td>
<td>新增 ChromaDB 查询性能要求</td>
</tr>
<tr class="even">
<td>测试覆盖率</td>
<td>pstds/temporal/ &gt; 95%<br />
pstds/portfolio/ &gt; 80%<br />
总体 &gt; 80%</td>
<td>新增 portfolio/ 模块覆盖率要求</td>
</tr>
<tr class="odd">
<td>运行环境</td>
<td>Python 3.11+，Docker Compose</td>
<td>✅ 不变</td>
</tr>
</tbody>
</table>

# 9. 功能范围边界与免责声明（v3.0 更新）

Out of Scope 与 v2.0 FRD 第 9.1 节一致，不变。

## 9.1 v3.0 新增已知约束

- ChromaDB 三层记忆系统需要历史数据积累，新部署实例的模式提炼效果在前 30 天有限。

- 组合分析相关性矩阵基于近 60 个交易日数据，数据不足时退化为单只分析模式。

- DeepSeek/Qwen 适配器计费格式与 OpenAI 不同，cost_estimator 中需维护独立计费换算表。

- Trading-R1 微调模型权重尚未开源，v3.0 仅保留接口预留，正式集成推迟至 v3.x。

⚠️ 重要免责声明：PSTDS 系统仅为个人研究辅助工具，所有分析结果和投资建议（含组合分析仓位建议）仅供参考，不构成任何形式的投资建议或财务顾问意见。最终投资决策须由用户自主判断，系统开发者不承担因使用本系统产生的任何投资损失责任。

# 附录 A：v2.0 → v3.0 变更日志

| **变更类型**         | **文件/模块**                      | **变更描述**                                                 |
|----------------------|------------------------------------|--------------------------------------------------------------|
| 🐛 Bug Fix（已完成） | config/default.yaml + config.py    | S1：API Key 改走环境变量，禁止明文存储                       |
| 🐛 Bug Fix（已完成） | pstds/backtest/executor.py         | S2：修复线程安全，不临时修改共享 position_sizes              |
| 🐛 Bug Fix（已完成） | pstds/data/cache.py                | S3：Parquet 追加前去重；M2：TTL 单位区分 hours/days          |
| 🐛 Bug Fix（已完成） | pstds/backtest/performance.py      | M3：胜率计算改为 FIFO 买卖队列匹配                           |
| 🐛 Bug Fix（已完成） | pstds/data/router.py               | L2：修复 ImportError（pstds.fallback → pstds.data.fallback） |
| 🐛 Bug Fix（已完成） | pstds/data/cache.py                | L3：OHLCV 缓存读取补上 \_is_expired 校验                     |
| 🐛 Bug Fix（已完成） | pstds/data/quality_guard.py        | L4：每次验证前重置 DataQualityReport                         |
| 🐛 Bug Fix（已完成） | pyproject.toml                     | L6：include 列表补入 pstds\*、web\*                          |
| ✨ 功能补全          | pstds/data/news_filter.py          | 新增文件：三级新闻过滤器                                     |
| ✨ 功能补全          | pstds/memory/short_term.py         | 新增文件：短期工作记忆                                       |
| ✨ 功能补全          | pstds/memory/pattern.py            | 新增文件：长期模式记忆                                       |
| ✨ 功能补全          | pstds/memory/reflection.py         | 新增文件：反事实记忆与提炼引擎                               |
| ✨ 功能补全          | pstds/llm/deepseek.py              | 新增文件：DeepSeek 适配器                                    |
| ✨ 功能补全          | pstds/llm/dashscope.py             | 新增文件：阿里 Qwen 适配器                                   |
| ✨ 功能补全          | pstds/storage/models.py            | 新增文件：MongoDB 文档模型定义                               |
| ✨ 功能补全          | pstds/backtest/report.py           | 新增文件：BacktestReportGenerator                            |
| 🆕 新增功能          | pstds/portfolio/                   | 新增目录：组合分析模块（FR-PA01 至 FR-PA05）                 |
| 🆕 新增功能          | web/pages/08_portfolio_analysis.py | 新增文件：组合分析 Web 页面                                  |
| 🆕 新增功能          | MongoDB portfolio_analyses 集合    | 新增集合：组合分析结果持久化                                 |
| 🆕 新增功能          | MongoDB reflection_records 集合    | 新增集合：预测 vs 实际对比记录                               |
| ♻️ 增强              | web/components/chart.py            | 全屏模式、时间周期切换、深色主题                             |
| ♻️ 增强              | web/pages/03_history.py            | 新增决策准确率趋势折线图                                     |
| ♻️ 增强              | web/pages/04_backtest.py           | 归因分析、净值曲线导出、历史报告检索                         |
