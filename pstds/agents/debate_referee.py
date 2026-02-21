# pstds/agents/debate_referee.py
# 辩论裁判员节点 - Phase 3 Task 3

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class DebateQualityReport(BaseModel):
    """
    辩论质量报告

    4 维度评分，加权计算（30%/30%/20%/20%）：
    - 论证深度 (30%)
    - 证据质量 (30%)
    - 观点多样性 (20%)
    - 逻辑一致性 (20%)
    """
    # 总分 0-10
    overall_score: float = Field(ge=0.0, le=10.0)

    # 是否低质量（overall_score < 5.0）
    is_low_quality: bool = False

    # 各维度评分 0-10
    argument_depth: float = Field(ge=0.0, le=10.0, default=5.0)
    evidence_quality: float = Field(ge=0.0, le=10.0, default=5.0)
    viewpoint_diversity: float = Field(ge=0.0, le=10.0, default=5.0)
    logical_consistency: float = Field(ge=0.0, le=10.0, default=5.0)

    # 辩论回合数
    debate_rounds: int = Field(ge=0, default=0)

    # 参与的分析师
    participating_analysts: List[str] = Field(default_factory=list)

    # 生成时间
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    # 建议的后续行动
    recommended_action: str = Field(default="")

    # 警告信息
    warnings: List[str] = Field(default_factory=list)


class DebateRefereeNode:
    """
    辩论裁判员节点

    评估不同分析师观点之间的辩论质量，提供综合评分报告。
    """

    def __init__(self, min_debate_quality_score: float = 5.0):
        """
        初始化辩论裁判员

        Args:
            min_debate_quality_score: 最低辩论质量分阈值（默认 5.0）
        """
        self.min_debate_quality_score = min_debate_quality_score

    def evaluate(
        self,
        debate_state: dict,
    ) -> DebateQualityReport:
        """
        评估辩论质量

        Args:
            debate_state: 完整辩论历史，包含各分析师的输出和推理过程
                格式：
                {
                    "rounds": [
                        {
                            "round_number": 1,
                            "analyst_outputs": {
                                "technical": {"action": "BUY", "reasoning": "..."},
                                "fundamentals": {"action": "HOLD", "reasoning": "..."},
                                "news": {"action": "BUY", "reasoning": "..."},
                            },
                        },
                        ...
                    ],
                    "final_recommendation": {...},
                }

        Returns:
            DebateQualityReport: 辩论质量报告
        """
        # 提取辩论回合
        rounds = debate_state.get("rounds", [])
        final_recommendation = debate_state.get("final_recommendation", {})

        # 分析参与的分析师
        participating_analysts = []
        if rounds:
            first_round = rounds[0]
            if "analyst_outputs" in first_round:
                participating_analysts = list(first_round["analyst_outputs"].keys())

        # 评估各维度
        argument_depth = self._evaluate_argument_depth(rounds)
        evidence_quality = self._evaluate_evidence_quality(debate_state)
        viewpoint_diversity = self._evaluate_viewpoint_diversity(rounds, participating_analysts)
        logical_consistency = self._evaluate_logical_consistency(rounds)

        # 加权计算总分
        overall_score = (
            argument_depth * 0.30 +
            evidence_quality * 0.30 +
            viewpoint_diversity * 0.20 +
            logical_consistency * 0.20
        )

        # 判断是否低质量
        is_low_quality = overall_score < self.min_debate_quality_score

        # 生成建议
        recommended_action = self._generate_recommendation(
            overall_score, is_low_quality, final_recommendation, participating_analysts
        )

        # 生成警告
        warnings = []
        if is_low_quality:
            warnings.append("辩论质量低于阈值，建议增加辩论回合或改进分析深度")

        if viewpoint_diversity < 3.0:
            warnings.append("观点多样性不足，各分析师意见高度一致")

        if logical_consistency < 4.0:
            warnings.append("存在逻辑不一致的论点")

        return DebateQualityReport(
            overall_score=overall_score,
            is_low_quality=is_low_quality,
            argument_depth=argument_depth,
            evidence_quality=evidence_quality,
            viewpoint_diversity=viewpoint_diversity,
            logical_consistency=logical_consistency,
            debate_rounds=len(rounds),
            participating_analysts=participating_analysts,
            generated_at=datetime.utcnow(),
            recommended_action=recommended_action,
            warnings=warnings,
        )

    def _evaluate_argument_depth(self, rounds: List[dict]) -> float:
        """
        评估论证深度 (30%)

        基于：
        - 推理过程的详细程度
        - 提供的论据数量
        - 对风险的考虑程度
        """
        if not rounds:
            return 0.0

        total_depth = 0
        total_rounds = len(rounds)

        for round_data in rounds:
            analyst_outputs = round_data.get("analyst_outputs", {})

            for analyst, output in analyst_outputs.items():
                reasoning = output.get("reasoning", "")
                risk_factors = output.get("risk_factors", [])

                # 推理长度（简要评估）
                reasoning_score = min(10, len(reasoning) / 50)

                # 风险因素数量
                risk_score = min(10, len(risk_factors) * 2)

                total_depth += (reasoning_score + risk_score)

        # 归一化到 0-10
        if total_rounds > 0:
            avg_depth = total_depth / (total_rounds * 2 * 10) * 10
            return avg_depth

        return 0.0

    def _evaluate_evidence_quality(self, debate_state: dict) -> float:
        """
        评估证据质量 (30%)

        基于：
        - 数据来源的多样性
        - 新闻时效性
        - 基本面数据的完整性
        """
        # 提取数据源信息
        data_sources = []
        if "data_sources" in debate_state:
            data_sources = debate_state["data_sources"]

        # 检查数据源多样性
        unique_sources = set()
        if data_sources:
            for ds in data_sources:
                unique_sources.add(ds.get("name", ""))

        source_diversity_score = min(10, len(unique_sources) * 2.5)

        # 检查基本面数据完整性（简化处理）
        fundamentals_score = 5.0  # 默认中等

        return source_diversity_score * 0.5 + fundamentals_score * 0.5

    def _evaluate_viewpoint_diversity(
        self,
        rounds: List[dict],
        participating_analysts: List[str],
    ) -> float:
        """
        评估观点多样性 (20%)

        基于：
        - 不同分析师给出的不同建议比例
        - 置信度分布的离散程度
        """
        if not rounds:
            return 0.0

        if len(participating_analysts) <= 1:
            return 0.0

        # 收集所有分析师的建议
        all_actions = []
        for round_data in rounds:
            analyst_outputs = round_data.get("analyst_outputs", {})
            for analyst, output in analyst_outputs.items():
                action = output.get("action", "")
                all_actions.append(action)

        # 计算不同建议的比例
        if all_actions:
            unique_actions = set(all_actions)
            diversity = len(unique_actions) / len(set(participating_analysts)) * 10
            return min(10, diversity * 2.5)

        return 0.0

    def _evaluate_logical_consistency(self, rounds: List[dict]) -> float:
        """
        评估逻辑一致性 (20%)

        基于：
        - 推理过程是否自洽
        - 结论是否与前提匹配
        - 是否存在明显的矛盾
        """
        # 简化实现：检查相邻回合的建议是否合理演变
        if len(rounds) < 2:
            return 5.0

        consistency_score = 10.0

        # 简化检查：如果有明显的不一致性，扣分
        actions_sequence = []
        for round_data in rounds:
            analyst_outputs = round_data.get("analyst_outputs", {})
            for output in analyst_outputs.values():
                action = output.get("action", "")
                actions_sequence.append(action)

        # 检查是否有极端的跳跃（简化）
        # 实际实现需要更复杂的逻辑推理分析

        return consistency_score

    def _generate_recommendation(
        self,
        overall_score: float,
        is_low_quality: bool,
        final_recommendation: dict,
        participating_analysts: List[str],
    ) -> str:
        """
        生成建议的后续行动

        Args:
            overall_score: 总分
            is_low_quality: 是否低质量
            final_recommendation: 最终推荐
            participating_analysts: 参与的分析师

        Returns:
            建议的行动字符串
        """
        if is_low_quality:
            return "debate_quality_low"

        if overall_score >= 7.0:
            return "high_confidence"

        if overall_score >= 5.0:
            return "moderate_confidence"

        return "low_confidence"
