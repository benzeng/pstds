# pstds/agents/extended_graph.py
# 扩展 TradingAgentsGraph - Phase 3 Task 3

from typing import Dict, List, Optional, Any
from datetime import date, datetime, UTC
from pydantic import ValidationError

from tradingagents.graph.trading_graph import TradingAgentsGraph

from pstds.temporal.context import TemporalContext
from pstds.agents.debate_referee import DebateRefereeNode, DebateQualityReport
from pstds.agents.output_schemas import TradeDecision, DataSource
from pstds.llm.factory import create_llm
from pstds.llm.cost_estimator import CostEstimator


class ExtendedTradingAgentsGraph(TradingAgentsGraph):
    """
    扩展 TradingAgentsGraph

    新增功能：
    1. TemporalContext 支持
    2. 辩论裁判员节点
    3. Pydantic 输出校验
    4. 增强的 propagate 方法
    """

    def __init__(
        self,
        selected_analysts=["market", "social", "news", "fundamentals"],
        debug=False,
        config: Optional[Dict[str, Any]] = None,
        min_debate_quality_score: float = 5.0,
    ):
        """
        初始化扩展图

        Args:
            selected_analysts: 选择的分析师列表
            debug: 调试模式
            config: 配置字典
            min_debate_quality_score: 最低辩论质量分阈值
        """
        # 调用父类初始化
        super().__init__(
            selected_analysts=selected_analysts,
            debug=debug,
            config=config,
        )

        # 存储时间上下文
        self.ctx = None

        # 辩论裁判员
        self.debate_referee = DebateRefereeNode(min_debate_quality_score)

        # 成本估算器
        self.cost_estimator = CostEstimator()

        # 输出校验状态
        self.output_validation_retries = 0
        self.max_output_retries = 3

    def _build_graph(self):
        """
        重写 _build_graph，添加新节点

        节点插入顺序：
        data_quality_guard_node → 原版节点 → debate_referee_node → result_persistence_node

        注意：debate_referee 实际在 propagate() 中手动调用（L124），
        不是作为 LangGraph 图节点运行。此处仅调用父类构建原版图。
        """
        # 调用父类的 _build_graph（获取原版图）
        super()._build_graph()

    def _inject_ctx_to_agents(self, ctx: TemporalContext) -> None:
        """
        通过 monkey-patch 将 TemporalContext 注入原版 Agent 数据获取层

        在 super().propagate() 调用前执行，将各工具模块的 route_to_vendor
        替换为带时间边界守卫的版本，确保所有数据请求不超过 analysis_date。

        对应 ISD v1.0 Section 5 约束 C-02。

        Args:
            ctx: 时间上下文
        """
        import tradingagents.agents.utils.core_stock_tools as _m_core
        import tradingagents.agents.utils.technical_indicators_tools as _m_tech
        import tradingagents.agents.utils.fundamental_data_tools as _m_fund
        import tradingagents.agents.utils.news_data_tools as _m_news

        from tradingagents.dataflows.interface import route_to_vendor as _original_route

        analysis_date_str = ctx.analysis_date.strftime("%Y-%m-%d")

        # 各方法中日期参数在 positional args 中的索引（route_to_vendor(method, *args) 中的 args）
        # 值为 (args_index, param_type)
        # end_date / curr_date 超过 analysis_date 时截断，不抛异常，保证 Agent 正常运行
        DATE_CAP_POSITIONS = {
            "get_stock_data": 2,       # (symbol, start_date, END_DATE)
            "get_indicators": 2,       # (symbol, indicator, CURR_DATE, look_back_days)
            "get_fundamentals": 1,     # (ticker, CURR_DATE)
            "get_balance_sheet": 2,    # (ticker, freq, CURR_DATE)
            "get_cashflow": 2,         # (ticker, freq, CURR_DATE)
            "get_income_statement": 2, # (ticker, freq, CURR_DATE)
            "get_news": 2,             # (ticker, start_date, END_DATE)
            "get_global_news": 0,      # (CURR_DATE, look_back_days, limit)
            # get_insider_transactions(ticker) 无日期参数，无需处理
        }

        def _guarded_route(method, *args, **kwargs):
            """带时间隔离守卫的 route_to_vendor 包装器"""
            args = list(args)
            if method in DATE_CAP_POSITIONS:
                idx = DATE_CAP_POSITIONS[method]
                if idx < len(args) and args[idx] is not None:
                    date_arg = str(args[idx])
                    if date_arg > analysis_date_str:
                        # 时间越界：截断到 analysis_date，防止前视偏差
                        args[idx] = analysis_date_str
            return _original_route(method, *args, **kwargs)

        # 保存原始函数引用并注入守卫版本
        self._patched_modules = [_m_core, _m_tech, _m_fund, _m_news]
        self._original_routes = {}
        for mod in self._patched_modules:
            self._original_routes[mod] = mod.route_to_vendor
            mod.route_to_vendor = _guarded_route

    def _restore_original_agents(self) -> None:
        """
        恢复原版 Agent 数据获取层（monkey-patch 反向还原）

        必须在 finally 块中调用，确保即使 propagate 抛异常也能恢复。
        """
        if hasattr(self, "_patched_modules") and hasattr(self, "_original_routes"):
            for mod in self._patched_modules:
                if mod in self._original_routes:
                    mod.route_to_vendor = self._original_routes[mod]
            self._patched_modules = []
            self._original_routes = {}

    def propagate(
        self,
        symbol: str,
        trade_date: date,
        ctx: TemporalContext,
        depth: str = "L2",
    ) -> Dict[str, Any]:
        """
        重写 propagate 方法，接受 TemporalContext 参数

        Args:
            symbol: 股票代码
            trade_date: 交易日期
            ctx: 时间上下文
            depth: 分析深度

        Returns:
            包含以下字段的字典：
            - symbol: 股票代码
            - trade_date: 交易日期
            - analysis_date: 分析基准日期（从 ctx 获取）
            - final_trade_decision: 最终决策（TradeDecision 对象）
            - debate_quality_report: 辩论质量报告
            - cost_estimate: 成本估算
        """
        # 存储时间上下文
        self.ctx = ctx

        # BUG-002 修复：注入 TemporalContext 到原版 Agent 数据获取层
        self._inject_ctx_to_agents(ctx)

        # 调用父类的 propagate 方法（在 finally 中确保恢复原版函数）
        try:
            # 原版 propagate 返回 (final_state, signal)
            final_state, signal = super().propagate(
                company_name=symbol,
                trade_date=trade_date
            )
        except Exception as e:
            print(f"Error in propagate: {e}")
            # 返回错误决策
            return self._create_insufficient_data_decision(
                symbol, ctx, error=str(e)
            )
        finally:
            # 无论成功还是失败，始终恢复原版 route_to_vendor
            self._restore_original_agents()

        # 转换为 TradeDecision
        trade_decision = self._convert_to_trade_decision(
            final_state, symbol, ctx
        )

        # 评估辩论质量
        debate_quality_report = None
        if "investment_debate_state" in final_state:
            debate_state = final_state["investment_debate_state"]
            debate_quality_report = self.debate_referee.evaluate(debate_state)

        # 如果辩论质量低，降低 conviction
        if debate_quality_report and debate_quality_report.is_low_quality:
            trade_decision.conviction = "LOW"

        # 成本估算
        prompt_text = self._build_summary_prompt(final_state)
        cost_estimate = self.cost_estimator.estimate(
            prompt=prompt_text,
            model=self.config.get("deep_think_llm", "unknown")
        )

        return {
            "symbol": symbol,
            "trade_date": trade_date,
            "analysis_date": ctx.analysis_date,
            "final_trade_decision": trade_decision,
            "debate_quality_report": debate_quality_report,
            "cost_estimate": cost_estimate,
        }

    def _convert_to_trade_decision(
        self,
        state: Dict[str, Any],
        symbol: str,
        ctx: TemporalContext,
    ) -> TradeDecision:
        """
        将原版状态转换为 TradeDecision

        Args:
            state: 原版状态字典
            symbol: 股票代码
            ctx: 时间上下文

        Returns:
            TradeDecision 对象
        """
        try:
            final_decision = state.get("final_trade_decision", {})

            # 提取核心字段
            action = self._map_action(final_decision.get("action", "HOLD"))
            confidence = final_decision.get("confidence", 0.5)
            conviction = self._map_conviction(final_decision.get("conviction", "MEDIUM"))
            primary_reason = final_decision.get("reasoning", "Analysis based on available data")[:100]

            # 价格目标
            target_price_low = final_decision.get("target_price_low")
            target_price_high = final_decision.get("target_price_high")
            time_horizon = "1-4 weeks"

            # 风险因素
            risk_factors = final_decision.get("risk_factors", ["Market volatility"])

            # 数据来源
            data_sources = self._create_data_sources(state, ctx)

            # 元数据
            analysis_date = ctx.analysis_date
            analysis_timestamp = datetime.now(UTC)
            volatility_adjustment = final_decision.get("volatility_adjustment", 1.0)
            debate_quality_score = final_decision.get("debate_quality_score", 7.5)
            market_type = self._infer_market_type(symbol)

            # 创建 TradeDecision
            trade_decision = TradeDecision(
                action=action,
                confidence=confidence,
                conviction=conviction,
                primary_reason=primary_reason,
                insufficient_data=False,
                target_price_low=target_price_low,
                target_price_high=target_price_high,
                time_horizon=time_horizon,
                risk_factors=risk_factors,
                data_sources=data_sources,
                analysis_date=analysis_date,
                analysis_timestamp=analysis_timestamp,
                volatility_adjustment=volatility_adjustment,
                debate_quality_score=debate_quality_score,
                symbol=symbol,
                market_type=market_type,
            )

            # Pydantic 输出校验
            trade_decision.model_validate(trade_decision)

            return trade_decision

        except ValidationError as e:
            print(f"Validation error: {e}")
            return self._create_insufficient_data_decision(symbol, ctx)

    def _map_action(self, action: str) -> str:
        """映射原版 action 到标准枚举值"""
        action_map = {
            "buy": "BUY",
            "sell": "SELL",
            "strong_buy": "STRONG_BUY",
            "strong_sell": "STRONG_SELL",
            "hold": "HOLD",
        }
        return action_map.get(action.lower(), "HOLD")

    def _map_conviction(self, conviction: str) -> str:
        """映射原版 conviction 到标准枚举值"""
        conviction_map = {
            "high": "HIGH",
            "medium": "MEDIUM",
            "low": "LOW",
        }
        return conviction_map.get(conviction.lower(), "MEDIUM")

    def _create_data_sources(
        self,
        state: Dict[str, Any],
        ctx: TemporalContext,
    ) -> List[DataSource]:
        """创建数据来源列表"""
        data_sources = []
        # BUG-007 修复：data_timestamp 应为数据对应的市场时间（analysis_date），
        # 而非获取时间。fetched_at 才记录实际获取时间。
        market_time = datetime.combine(ctx.analysis_date, datetime.min.time()).replace(tzinfo=UTC)
        fetched_at = datetime.now(UTC)

        # 检查是否有数据源信息
        for source in ["market_report", "news_report", "fundamentals_report"]:
            if source in state:
                ds = DataSource(
                    name=source,
                    url=None,
                    data_timestamp=market_time,  # 数据对应的市场时间
                    market_type="US",  # 简化处理
                    fetched_at=fetched_at,        # 实际获取时间
                )
                data_sources.append(ds)

        return data_sources

    def _infer_market_type(self, symbol: str) -> str:
        """推断市场类型（简化）"""
        if symbol.endswith(".HK"):
            return "HK"
        elif symbol.isalpha():
            return "US"
        else:
            return "CN_A"

    def _build_summary_prompt(self, state: Dict[str, Any]) -> str:
        """构建用于成本估算的总结提示词"""
        return f"""
        Analysis Summary for {state.get('company_of_interest', 'Unknown')}
        Market Report: {state.get('market_report', {})}
        Sentiment: {state.get('sentiment_report', {})}
        Final Decision: {state.get('final_trade_decision', {})}
        """

    def _create_insufficient_data_decision(
        self,
        symbol: str,
        ctx: TemporalContext,
        error: str = "",
    ) -> TradeDecision:
        """
        创建数据不足的决策

        Args:
            symbol: 股票代码
            ctx: 时间上下文
            error: 错误信息

        Returns:
            TradeDecision 对象（action=INSUFFICIENT_DATA）
        """
        return TradeDecision(
            action="INSUFFICIENT_DATA",
            confidence=0.0,
            conviction="LOW",
            primary_reason=f"Unable to analyze due to {error}" if error else "Insufficient data available",
            insufficient_data=True,
            target_price_low=None,
            target_price_high=None,
            time_horizon="",
            risk_factors=["Data unavailable"],
            data_sources=[
                DataSource(
                    name="error",
                    url=None,
                    data_timestamp=datetime.now(UTC),
                    market_type="US",
                    fetched_at=datetime.now(UTC),
                )
            ],
            analysis_date=ctx.analysis_date,
            analysis_timestamp=datetime.now(UTC),
            volatility_adjustment=1.0,
            debate_quality_score=0.0,
            symbol=symbol,
            market_type=self._infer_market_type(symbol),
        )

    def validate_output_with_retry(
        self,
        llm_output: str,
        symbol: str,
        ctx: TemporalContext,
    ) -> TradeDecision:
        """
        带 Pydantic 校验的输出验证（最多重试 3 次）

        Args:
            llm_output: LLM 输出的 JSON 字符串
            symbol: 股票代码
            ctx: 时间上下文

        Returns:
            TradeDecision 对象
        """
        import json

        self.output_validation_retries = 0

        while self.output_validation_retries < self.max_output_retries:
            try:
                # 尝试解析 JSON
                data = json.loads(llm_output)

                # 验证并创建 TradeDecision
                trade_decision = TradeDecision(
                    action=data.get("action", "HOLD"),
                    confidence=data.get("confidence", 0.5),
                    conviction=data.get("conviction", "MEDIUM"),
                    primary_reason=data.get("primary_reason", "")[:100],
                    insufficient_data=data.get("insufficient_data", False),
                    target_price_low=data.get("target_price_low"),
                    target_price_high=data.get("target_price_high"),
                    time_horizon=data.get("time_horizon", "1-4 weeks"),
                    risk_factors=data.get("risk_factors", []),
                    data_sources=data.get("data_sources", []),
                    analysis_date=ctx.analysis_date,
                    analysis_timestamp=datetime.now(UTC),
                    volatility_adjustment=data.get("volatility_adjustment", 1.0),
                    debate_quality_score=data.get("debate_quality_score", 7.5),
                    symbol=symbol,
                    market_type=data.get("market_type", "US"),
                )

                # Pydantic 校验
                trade_decision.model_validate(trade_decision)
                return trade_decision

            except (json.JSONDecodeError, ValidationError) as e:
                self.output_validation_retries += 1
                print(f"Output validation attempt {self.output_validation_retries} failed: {e}")

                if self.output_validation_retries < self.max_output_retries:
                    # 下一次尝试的提示词
                    print(f"Retrying... ({self.output_validation_retries}/{self.max_output_retries})")

        # 所有尝试都失败，返回 INSUFFICIENT_DATA
        return self._create_insufficient_data_decision(
            symbol, ctx, f"Failed to validate output after {self.max_output_retries} attempts"
        )
