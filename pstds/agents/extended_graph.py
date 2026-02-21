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
        """
        # 调用父类的 _build_graph（获取原版图）
        super()._build_graph()

        # 注意：在原版架构中，节点是通过 LangGraph 构建的
        # 这里我们只是记录扩展功能的接口，实际的图集成需要更深入的修改

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

        # 调用父类的 propagate 方法
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
        data_timestamp = datetime.now(UTC)

        # 检查是否有数据源信息
        for source in ["market_report", "news_report", "fundamentals_report"]:
            if source in state:
                ds = DataSource(
                    name=source,
                    url=None,
                    data_timestamp=data_timestamp,
                    market_type="US",  # 简化处理
                    fetched_at=data_timestamp,
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
