# pstds/storage/mongo_store.py
# MongoDB 持久化层 - Phase 4 Task 1 (P4-T1)
# ISD v1.0 Section 5: MongoDB 集合设计

from typing import Optional, List, Dict, Any
from datetime import datetime, date, UTC
from hashlib import sha256
import json
import os

try:
    from pymongo import MongoClient, ASCENDING, DESCENDING
    from pymongo.errors import ConnectionFailure
    PYMONGO_AVAILABLE = True
except ImportError:
    PYMONGO_AVAILABLE = False
    MongoClient = None


class MongoStore:
    """
    MongoDB 持久化存储层

    实现 analyses 集合的读写操作，支持分析结果的持久化。
    根据 ISD v1.0 Section 5.1 设计的文档结构。
    """

    def __init__(
        self,
        connection_string: Optional[str] = None,
        database_name: str = "pstds",
    ):
        """
        初始化 MongoDB 连接

        Args:
            connection_string: MongoDB 连接字符串（默认为 localhost:27017）
            database_name: 数据库名称（默认为 pstds）
        """
        if not PYMONGO_AVAILABLE:
            print("pymongo 未安装，MongoDB 功能不可用。请运行: pip install pymongo")
            self.client = None
            self.db = None
            self.analyses_collection = None
            return

        if connection_string is None:
            connection_string = os.getenv(
                "MONGODB_CONNECTION_STRING",
                "mongodb://localhost:27017/"
            )

        try:
            self.client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)
            self.db = self.client[database_name]
            self.analyses_collection = self.db["analyses"]

            # 创建索引
            self._ensure_indexes()

            # 测试连接
            self.client.admin.command('ping')
            print(f"MongoDB 连接成功: {database_name}")

        except ConnectionFailure as e:
            print(f"MongoDB 连接失败: {e}")
            self.client = None
            self.db = None
            self.analyses_collection = None

    def _ensure_indexes(self):
        """
        确保必要的索引存在

        - symbol + analysis_date: 组合索引，用于查询特定股票的特定日期
        - created_at: 时间索引，用于时间排序
        - input_hash: 哈希索引，用于去重
        """
        if self.analyses_collection is None:
            return

        # symbol + analysis_date 组合索引
        self.analyses_collection.create_index([
            ("symbol", ASCENDING),
            ("analysis_date", DESCENDING)
        ])

        # created_at 时间索引
        self.analyses_collection.create_index("created_at", direction=DESCENDING)

        # input_hash 哈希索引
        self.analyses_collection.create_index("input_hash", unique=True)

    def _compute_input_hash(
        self,
        symbol: str,
        analysis_date: date,
        config: Dict[str, Any],
    ) -> str:
        """
        计算输入数据的 SHA-256 哈希值

        用于缓存命中检测，相同输入不应重复分析。

        Args:
            symbol: 股票代码
            analysis_date: 分析日期
            config: LLM 配置等输入参数

        Returns:
            SHA-256 哈希字符串（前缀 "sha256:"）
        """
        # 构建哈希输入
        hash_input = {
            "symbol": symbol,
            "analysis_date": str(analysis_date),
            "config": config,
        }

        # 计算 SHA-256
        hash_bytes = sha256(
            json.dumps(hash_input, sort_keys=True).encode('utf-8')
        ).hexdigest()

        return f"sha256:{hash_bytes}"

    def save_analysis(self, state: Dict[str, Any]) -> str:
        """
        保存分析结果到 analyses 集合

        序列化 GraphState，写入 analyses 集合，返回 _id。

        Args:
            state: 完整的分析状态，必须包含：
                - symbol: 股票代码
                - analysis_date: 分析基准日期
                - decision: 结构化 TradeDecision JSON
                - temporal: 审计字段
                - config: LLM 配置
                - reports: 各 Agent 输出
                - cost: 成本统计

        Returns:
            MongoDB 文档 _id

        Raises:
            ValueError: 如果 MongoDB 未连接或缺少必需字段
        """
        if self.analyses_collection is None:
            raise ValueError("MongoDB 未连接，无法保存分析结果")

        # 验证必需字段
        required_fields = ["symbol", "analysis_date", "decision", "temporal", "config"]
        for field in required_fields:
            if field not in state:
                raise ValueError(f"缺少必需字段: {field}")

        # 准备文档
        now = datetime.now(UTC)

        doc = {
            "symbol": state["symbol"],
            "market_type": state.get("market_type", "US"),
            "analysis_date": str(state["analysis_date"]),
            "created_at": now,
            "mode": state.get("mode", "LIVE"),
            "config": state.get("config", {}),
            "temporal": state.get("temporal", {}),
            "data_quality": state.get("data_quality", {
                "score": 100.0,
                "missing_fields": [],
                "anomaly_alerts": [],
                "fallbacks_used": [],
            }),
            "reports": state.get("reports", {}),
            "decision": state["decision"],
            "input_hash": self._compute_input_hash(
                state["symbol"],
                state["analysis_date"],
                state.get("config", {})
            ),
            "cost": state.get("cost", {
                "total_tokens": 0,
                "estimated_usd": 0.0,
                "actual_usd": 0.0,
            }),
        }

        # 插入文档
        try:
            result = self.analyses_collection.insert_one(doc)
            return str(result.inserted_id)
        except Exception as e:
            print(f"MongoDB 插入失败: {e}")
            raise

    def find_by_id(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        """
        根据 _id 查找分析记录

        Args:
            analysis_id: MongoDB 文档 _id

        Returns:
            分析文档字典，不存在则返回 None
        """
        if self.analyses_collection is None:
            return None

        try:
            from bson import ObjectId
            return self.analyses_collection.find_one({"_id": ObjectId(analysis_id)})
        except Exception as e:
            print(f"MongoDB 查询失败: {e}")
            return None

    def find_by_symbol_date(
        self,
        symbol: str,
        analysis_date: date,
    ) -> Optional[Dict[str, Any]]:
        """
        根据股票代码和分析日期查找分析记录

        Args:
            symbol: 股票代码
            analysis_date: 分析日期

        Returns:
            分析文档字典，不存在则返回 None
        """
        if self.analyses_collection is None:
            return None

        try:
            return self.analyses_collection.find_one({
                "symbol": symbol,
                "analysis_date": str(analysis_date),
            })
        except Exception as e:
            print(f"MongoDB 查询失败: {e}")
            return None

    def list_analyses(
        self,
        symbol: Optional[str] = None,
        limit: int = 50,
        skip: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        列出分析记录（支持分页）

        Args:
            symbol: 股票代码（可选，不传则查询所有）
            limit: 返回数量限制（默认 50）
            skip: 跳过数量（用于分页，默认 0）

        Returns:
            分析文档列表，按 created_at 降序排列
        """
        if self.analyses_collection is None:
            return []

        try:
            query = {}
            if symbol:
                query["symbol"] = symbol

            cursor = self.analyses_collection.find(query).sort(
                "created_at", DESCENDING
            ).skip(skip).limit(limit)

            return list(cursor)
        except Exception as e:
            print(f"MongoDB 查询失败: {e}")
            return []

    def find_by_input_hash(self, input_hash: str) -> Optional[Dict[str, Any]]:
        """
        根据输入哈希查找分析记录（用于缓存命中）

        Args:
            input_hash: 输入哈希值（格式: "sha256:..."）

        Returns:
            分析文档字典，不存在则返回 None
        """
        if self.analyses_collection is None:
            return None

        try:
            return self.analyses_collection.find_one({"input_hash": input_hash})
        except Exception as e:
            print(f"MongoDB 查询失败: {e}")
            return None

    def update_cost_record(
        self,
        analysis_id: str,
        actual_tokens: int,
        actual_cost_usd: float,
    ) -> bool:
        """
        更新分析的实际成本（在分析完成后调用）

        Args:
            analysis_id: MongoDB 文档 _id
            actual_tokens: 实际使用的 token 数量
            actual_cost_usd: 实际成本（USD）

        Returns:
            是否更新成功
        """
        if self.analyses_collection is None:
            return False

        try:
            from bson import ObjectId
            self.analyses_collection.update_one(
                {"_id": ObjectId(analysis_id)},
                {
                    "$set": {
                        "cost.actual_tokens": actual_tokens,
                        "cost.actual_usd": actual_cost_usd,
                    }
                }
            )
            return True
        except Exception as e:
            print(f"MongoDB 更新失败: {e}")
            return False

    def delete_analysis(self, analysis_id: str) -> bool:
        """
        删除分析记录

        Args:
            analysis_id: MongoDB 文档 _id

        Returns:
            是否删除成功
        """
        if self.analyses_collection is None:
            return False

        try:
            from bson import ObjectId
            result = self.analyses_collection.delete_one({
                "_id": ObjectId(analysis_id)
            })
            return result.deleted_count > 0
        except Exception as e:
            print(f"MongoDB 删除失败: {e}")
            return False

    def close(self):
        """
        关闭 MongoDB 连接
        """
        if self.client:
            self.client.close()
            self.client = None
            self.db = None
            self.analyses_collection = None
