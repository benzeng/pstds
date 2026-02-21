# pstds/agents/result_saver.py
# 结果持久化节点 - Phase 4 Task 2 (P4-T2)
# ISD v1.0: result_persistence_node 作为 LangGraph 最后节点

from typing import Dict, Any
from datetime import datetime
from pstds.storage.mongo_store import MongoStore
from pstds.memory.episodic import EpisodicMemory


class ResultPersistenceNode:
    """
    结果持久化节点

    作为 LangGraph 的最后节点，负责：
    1. 调用 MongoStore.save_analysis() 持久化分析结果
    2. 更新 ChromaDB 向量记忆（如果可用）
    3. 记录实际成本（如果 API 返回了 token 使用情况）
    """

    def __init__(
        self,
        mongo_store: MongoStore,
        episodic_memory: EpisodicMemory = None,
    ):
        """
        初始化结果持久化节点

        Args:
            mongo_store: MongoDB 存储实例
            episodic_memory: 情景记忆实例（可选）
        """
        self.mongo_store = mongo_store
        self.episodic_memory = episodic_memory

    def save_result(
        self,
        state: Dict[str, Any],
        actual_tokens: int = None,
        actual_cost_usd: float = None,
    ) -> str:
        """
        保存分析结果

        作为 LangGraph 节点的执行逻辑，处理最终状态并持久化。

        Args:
            state: 完整的分析状态，必须包含：
                - symbol: 股票代码
                - analysis_date: 分析基准日期
                - final_trade_decision: 最终决策
                - debate_quality_report: 辩论质量报告
                - cost_estimate: 成本估算
                - temporal: 时间上下文
                - config: LLM 配置
            actual_tokens: 实际使用的 token 数量（可选）
            actual_cost_usd: 实际成本（可选）

        Returns:
            MongoDB 文档 _id

        Raises:
            ValueError: 如果 MongoDB 未连接或缺少必需字段
        """
        if self.mongo_store is None or self.mongo_store.analyses_collection is None:
            raise ValueError("MongoStore 未初始化，无法保存结果")

        # 准备 TradeDecision 结构化数据
        decision_data = state.get("final_trade_decision")
        if decision_data is None:
            raise ValueError("state 中缺少 final_trade_decision")

        # 如果是 TradeDecision 对象，转换为字典
        if hasattr(decision_data, "model_dump"):
            decision_dict = decision_data.model_dump()
        elif hasattr(decision_data, "dict"):
            decision_dict = decision_data.dict()
        else:
            decision_dict = decision_data

        # 准备保存状态
        save_state = {
            "symbol": state.get("symbol"),
            "analysis_date": state.get("analysis_date") or state.get("trade_date"),
            "mode": state.get("mode", "LIVE"),
            "market_type": state.get("market_type", "US"),
            "decision": decision_dict,
            "temporal": state.get("temporal", {}),
            "config": state.get("config", {}),
            "data_quality": state.get("data_quality", {
                "score": 100.0,
                "missing_fields": [],
                "anomaly_alerts": [],
                "fallbacks_used": [],
            }),
            "reports": {
                "debate_quality_report": state.get("debate_quality_report"),
                "cost_estimate": state.get("cost_estimate"),
            },
            "cost": {
                "total_tokens": state.get("cost_estimate", {}).get("estimated_tokens", 0),
                "estimated_usd": state.get("cost_estimate", {}).get("estimated_cost_usd", 0.0),
            },
        }

        # 保存到 MongoDB
        try:
            analysis_id = self.mongo_store.save_analysis(save_state)
            print(f"分析结果已保存到 MongoDB: {analysis_id}")

            # 更新实际成本（如果有）
            if actual_tokens is not None and actual_cost_usd is not None:
                self.mongo_store.update_cost_record(
                    analysis_id,
                    actual_tokens,
                    actual_cost_usd,
                )

            # 更新向量记忆（如果可用）
            if self.episodic_memory is not None:
                self.episodic_memory.add_decision(decision_dict)
                print(f"决策已添加到情景记忆")

            return analysis_id

        except Exception as e:
            print(f"保存分析结果失败: {e}")
            raise

    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        LangGraph 节点调用接口

        Args:
            state: 当前 GraphState

        Returns:
            更新后的 GraphState，包含 analysis_id 字段
        """
        analysis_id = self.save_result(state)
        state["analysis_id"] = analysis_id
        state["saved_at"] = datetime.utcnow().isoformat()
        return state
