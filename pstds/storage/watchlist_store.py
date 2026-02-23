# pstds/storage/watchlist_store.py
# 自选股持久化存储模块

from typing import Optional, List, Dict, Any
from datetime import datetime, UTC
import os

try:
    from pymongo import MongoClient, ASCENDING, DESCENDING
    from pymongo.errors import ConnectionFailure
    PYMONGO_AVAILABLE = True
except ImportError:
    PYMONGO_AVAILABLE = False
    MongoClient = None

# 导入配置加载器
try:
    from pstds.config import get_config
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False


class WatchlistStore:
    """
    自选股持久化存储层

    使用 MongoDB watchlist 集合存储用户的自选股列表。
    支持完整的 CRUD 操作。
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
            print("pymongo 未安装，WatchlistStore 功能不可用。请运行: pip install pymongo")
            self.client = None
            self.db = None
            self.watchlist_collection = None
            return

        # 从配置文件加载 MongoDB 连接信息
        if connection_string is None or database_name is None:
            if CONFIG_AVAILABLE:
                config = get_config()
                connection_string = connection_string or config.get_mongodb_connection_string()
                database_name = database_name or config.get_mongodb_database_name()
            else:
                connection_string = connection_string or os.getenv(
                    "MONGODB_CONNECTION_STRING",
                    "mongodb://localhost:27017/"
                )
                database_name = database_name or "pstds"

        try:
            self.client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)
            self.db = self.client[database_name]
            self.watchlist_collection = self.db["watchlist"]

            # 创建索引
            self._ensure_indexes()

            # 测试连接
            self.client.admin.command('ping')
            print(f"WatchlistStore MongoDB 连接成功: {database_name}")

        except ConnectionFailure as e:
            print(f"WatchlistStore MongoDB 连接失败: {e}")
            self.client = None
            self.db = None
            self.watchlist_collection = None

    def _ensure_indexes(self):
        """
        确保必要的索引存在

        - symbol: 唯一索引，用于快速查找
        - created_at: 时间索引，用于排序
        - market_type: 市场类型索引，用于筛选
        """
        if self.watchlist_collection is None:
            return

        # symbol 唯一索引
        try:
            self.watchlist_collection.create_index("symbol", unique=True)
        except Exception:
            pass  # 索引可能已存在

        # created_at 时间索引
        self.watchlist_collection.create_index([("created_at", DESCENDING)])

        # market_type 市场类型索引
        self.watchlist_collection.create_index("market_type")

    def add_stock(
        self,
        symbol: str,
        name: str,
        market_type: str = "US",
        group_tags: Optional[List[str]] = None,
        auto_analysis_enabled: bool = True,
    ) -> bool:
        """
        添加股票到自选股

        Args:
            symbol: 股票代码
            name: 公司名称
            market_type: 市场类型（US, CN_A, HK）
            group_tags: 标签分组列表
            auto_analysis_enabled: 是否启用自动分析

        Returns:
            是否添加成功
        """
        if self.watchlist_collection is None:
            return False

        try:
            doc = {
                "symbol": symbol.upper(),
                "name": name,
                "market_type": market_type,
                "group_tags": group_tags or [],
                "auto_analysis_enabled": auto_analysis_enabled,
                "last_analyzed_at": None,
                "created_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
            }

            # 使用 insert_one 检查唯一性
            self.watchlist_collection.insert_one(doc)
            return True

        except Exception as e:
            error_msg = str(e)
            if "duplicate key error" in error_msg or "E11000" in error_msg:
                return False
            else:
                return False

    def get_all(self, market_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取所有自选股

        Args:
            market_type: 市场类型筛选（可选）

        Returns:
            股票列表
        """
        if self.watchlist_collection is None:
            return []

        try:
            query = {}
            if market_type:
                query["market_type"] = market_type

            cursor = self.watchlist_collection.find(query).sort("created_at", ASCENDING)
            return list(cursor)
        except Exception as e:
            print(f"获取自选股失败: {e}")
            return []

    def get_by_symbol(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        根据股票代码获取股票

        Args:
            symbol: 股票代码

        Returns:
            股票信息字典，不存在则返回 None
        """
        if self.watchlist_collection is None:
            return None

        try:
            return self.watchlist_collection.find_one({"symbol": symbol.upper()})
        except Exception as e:
            print(f"获取股票失败: {e}")
            return None

    def update_stock(
        self,
        symbol: str,
        name: Optional[str] = None,
        market_type: Optional[str] = None,
        group_tags: Optional[List[str]] = None,
        auto_analysis_enabled: Optional[bool] = None,
    ) -> bool:
        """
        更新股票信息

        Args:
            symbol: 股票代码
            name: 公司名称（可选）
            market_type: 市场类型（可选）
            group_tags: 标签分组（可选）
            auto_analysis_enabled: 自动分析开关（可选）

        Returns:
            是否更新成功
        """
        if self.watchlist_collection is None:
            return False

        try:
            update_data = {"updated_at": datetime.now(UTC)}

            if name is not None:
                update_data["name"] = name
            if market_type is not None:
                update_data["market_type"] = market_type
            if group_tags is not None:
                update_data["group_tags"] = group_tags
            if auto_analysis_enabled is not None:
                update_data["auto_analysis_enabled"] = auto_analysis_enabled

            result = self.watchlist_collection.update_one(
                {"symbol": symbol.upper()},
                {"$set": update_data}
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"更新股票失败: {e}")
            return False

    def update_last_analyzed(self, symbol: str, analyzed_at: datetime) -> bool:
        """
        更新股票的最后分析时间

        Args:
            symbol: 股票代码
            analyzed_at: 分析时间

        Returns:
            是否更新成功
        """
        if self.watchlist_collection is None:
            return False

        try:
            result = self.watchlist_collection.update_one(
                {"symbol": symbol.upper()},
                {"$set": {"last_analyzed_at": analyzed_at, "updated_at": datetime.now(UTC)}}
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"更新分析时间失败: {e}")
            return False

    def delete_stock(self, symbol: str) -> bool:
        """
        删除股票

        Args:
            symbol: 股票代码

        Returns:
            是否删除成功
        """
        if self.watchlist_collection is None:
            return False

        try:
            result = self.watchlist_collection.delete_one({"symbol": symbol.upper()})
            return result.deleted_count > 0
        except Exception as e:
            print(f"删除股票失败: {e}")
            return False

    def get_by_tags(
        self,
        tags: Optional[List[str]] = None,
        require_match: bool = True
    ) -> List[Dict[str, Any]]:
        """
        根据标签获取股票

        Args:
            tags: 标签列表（匹配任意一个标签）
            require_match: 是否必须匹配标签。False 表示返回所有股票（包括没有标签的）

        Returns:
            股票列表
        """
        if self.watchlist_collection is None:
            return []

        try:
            if not tags:
                return self.get_all()

            if require_match:
                # 只返回有匹配标签的股票
                query = {"group_tags": {"$in": tags}}
            else:
                # 返回所有股票（包含没有标签的股票）
                query = {}

            cursor = self.watchlist_collection.find(query).sort("created_at", ASCENDING)
            return list(cursor)
        except Exception as e:
            print(f"按标签获取股票失败: {e}")
            return []

    def get_count(self, market_type: Optional[str] = None) -> int:
        """
        获取股票数量

        Args:
            market_type: 市场类型筛选（可选）

        Returns:
            股票数量
        """
        if self.watchlist_collection is None:
            return 0

        try:
            query = {}
            if market_type:
                query["market_type"] = market_type

            return self.watchlist_collection.count_documents(query)
        except Exception as e:
            print(f"获取股票数量失败: {e}")
            return 0

    def clear_all(self) -> int:
        """
        清空所有自选股

        Returns:
            删除的股票数量
        """
        if self.watchlist_collection is None:
            return 0

        try:
            result = self.watchlist_collection.delete_many({})
            return result.deleted_count
        except Exception as e:
            print(f"清空自选股失败: {e}")
            return 0

    def close(self):
        """
        关闭 MongoDB 连接
        """
        if self.client:
            self.client.close()
            self.client = None
            self.db = None
            self.watchlist_collection = None
