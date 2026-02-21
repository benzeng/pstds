# pstds/memory/episodic.py
# 情景记忆系统 - Phase 3 Task 5

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, UTC
import json
from pathlib import Path

try:
    import chromadb
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False


class EpisodicMemory:
    """
    情景记忆系统（简化版）

    使用 ChromaDB 存储近 90 天分析决策的向量表示。
    提供 add_decision(trade_decision) 和 search_similar(symbol, context_desc) 接口。
    """

    def __init__(
        self,
        persist_directory: str = "./data/vector_memory",
        collection_name: str = "trading_decisions",
    ):
        """
        初始化情景记忆

        Args:
            persist_directory: ChromaDB 持久化目录
            collection_name: 集合名称
        """
        if not CHROMADB_AVAILABLE:
            print("ChromaDB 未安装，跳过向量记忆功能。请运行: pip install chromadb")
            self.client = None
            self.collection = None
            return

        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)

        self.collection_name = collection_name

        # 初始化 ChromaDB
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory / collection_name)
        )

        # 获取或创建集合
        try:
            self.collection = self.client.get_collection(collection_name)
        except:
            self.collection = self.client.create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"}
            )

    def add_decision(self, trade_decision: Dict[str, Any]) -> str:
        """
        添加交易决策到记忆

        Args:
            trade_decision: TradeDecision 字典（需包含 symbol, action, primary_reason 等字段）

        Returns:
            记录 ID
        """
        if not self.client:
            return ""

        # 创建文档内容
        symbol = trade_decision.get("symbol", "unknown")
        action = trade_decision.get("action", "unknown")
        primary_reason = trade_decision.get("primary_reason", "")
        confidence = trade_decision.get("confidence", 0.0)

        # 构建文档文本
        document_text = f"""
        Symbol: {symbol}
        Action: {action}
        Primary Reason: {primary_reason}
        Confidence: {confidence}
        Analysis Date: {trade_decision.get("analysis_date", "")}
        """
        # 生成简单向量表示（在真实实现中应使用 embedding 模型）
        # 这里使用简化的向量表示
        document_metadata = {
            "symbol": symbol,
            "action": action,
            "confidence": confidence,
            "timestamp": datetime.now(UTC).isoformat(),
            "decision_type": "trade",
        }

        # 添加到 ChromaDB
        try:
            self.collection.add(
                documents=[document_text],
                metadatas=[document_metadata],
                ids=[f"{symbol}_{action}_{datetime.now(UTC).isoformat()}"]
            )
            return self.collection.last_insert_id
        except Exception as e:
            print(f"Error adding to ChromaDB: {e}")
            return ""

    def search_similar(
        self,
        symbol: str,
        context_desc: str,
        n_results: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        搜索相似的历史决策

        Args:
            symbol: 股票代码
            context_desc: 上下文描述
            n_results: 返回结果数量

        Returns:
            相似决策列表，按相似度排序
        """
        if not self.client:
            return []

        try:
            # 查询 ChromaDB
            results = self.collection.query(
                query_texts=[context_desc],
                n_results=n_results,
                where={"symbol": symbol},
                include=["metadatas", "documents", "distances"]
            )

            # 格式化返回结果
            decisions = []
            for i, result in enumerate(results):
                metadata = result["metadatas"][0]
                document = result["documents"][0]
                distance = result["distances"][0]

                decisions.append({
                    "id": result["ids"][0],
                    "symbol": metadata.get("symbol", ""),
                    "action": metadata.get("action", ""),
                    "confidence": metadata.get("confidence", 0.0),
                    "timestamp": metadata.get("timestamp", ""),
                    "similarity_score": 1 - distance,
                    "content": document,
                })

            return decisions

        except Exception as e:
            print(f"Error searching ChromaDB: {e}")
            return []

    def get_recent_decisions(
        self,
        symbol: Optional[str] = None,
        days_back: int = 30,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        获取最近的决策记录

        Args:
            symbol: 股票代码（None 表示全部）
            days_back: 向前查询的天数
            limit: 返回数量限制

        Returns:
            决策记录列表
        """
        if not self.client:
            return []

        try:
            # 构建查询条件
            where_clause = None
            if symbol:
                where_clause = {"symbol": symbol}

            # 获取所有记录
            all_results = self.collection.get(
                where=where_clause,
                limit=limit,
                include=["metadatas", "documents"]
            )

            # 过滤最近 N 天的记录
            now = datetime.now(UTC)
            cutoff_date = now - timedelta(days=days_back)

            recent_results = []
            for i, result in enumerate(all_results):
                metadata = result["metadatas"][0]
                timestamp_str = metadata.get("timestamp", "")

                if timestamp_str:
                    try:
                        record_date = datetime.fromisoformat(timestamp_str)
                        if record_date >= cutoff_date:
                            recent_results.append({
                                "id": result["id"],
                                **metadata,
                                "content": result["documents"][0],
                            })
                    except:
                        pass

            return recent_results

        except Exception as e:
            print(f"Error getting recent decisions: {e}")
            return []

    def clear_old_records(self, days_to_keep: int = 90) -> int:
        """
        清除旧记录（保留最近 N 天）

        Args:
            days_to_keep: 保留天数（默认 90 天）

        Returns:
            删除的记录数量
        """
        if not self.client:
            return 0

        try:
            cutoff_date = datetime.now(UTC) - timedelta(days=days_to_keep)
            cutoff_str = cutoff_date.isoformat()

            # 获取需要删除的记录
            old_records = self.collection.get(
                where={"timestamp": {"$lt": cutoff_str}},
                include=["ids"]
            )

            # 删除
            if old_records["ids"]:
                self.collection.delete(ids=old_records["ids"])

            return len(old_records["ids"])

        except Exception as e:
            print(f"Error clearing old records: {e}")
            return 0
