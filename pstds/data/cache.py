# pstds/data/cache.py
# SQLite 缓存管理器 - DDD v2.0 Section 3.3

import sqlite3
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import date, datetime, timedelta
import json
import hashlib

from pstds.temporal.context import TemporalContext


class CacheManager:
    """
    SQLite 缓存管理器

    按 DDD v2.0 第 3.3 节创建 5 张缓存表：
    - ohlcv_cache (24h TTL，永久用于回测)
    - fundamentals_cache (24h TTL)
    - news_cache (6h TTL)
    - technical_cache (24h TTL)
    - decision_hash_cache (7天 TTL)

    读取缓存时 WHERE 条件包含时间隔离校验。
    行情数据同时追加写入 Parquet 文件（原始数据不可篡改）。
    """

    def __init__(
        self,
        db_path: str = "./data/cache.db",
        parquet_dir: str = "./data/raw/prices",
        news_dir: str = "./data/raw/news",
    ):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.parquet_dir = Path(parquet_dir)
        self.parquet_dir.mkdir(parents=True, exist_ok=True)

        self.news_dir = Path(news_dir)
        self.news_dir.mkdir(parents=True, exist_ok=True)

        self._init_db()

    def _init_db(self) -> None:
        """初始化数据库表结构"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # ohlcv_cache 表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ohlcv_cache (
                    symbol TEXT,
                    date TEXT,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    volume INTEGER,
                    adj_close REAL,
                    data_source TEXT,
                    fetched_at TEXT,
                    ttl_hours INTEGER DEFAULT 24,
                    PRIMARY KEY (symbol, date)
                )
            """)

            # fundamentals_cache 表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fundamentals_cache (
                    symbol TEXT,
                    as_of_date TEXT,
                    data_json TEXT,
                    fetched_at TEXT,
                    ttl_hours INTEGER DEFAULT 24,
                    PRIMARY KEY (symbol, as_of_date)
                )
            """)

            # news_cache 表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS news_cache (
                    symbol TEXT,
                    published_at TEXT,
                    title_hash TEXT,
                    news_json TEXT,
                    fetched_at TEXT,
                    ttl_hours INTEGER DEFAULT 6,
                    PRIMARY KEY (symbol, title_hash)
                )
            """)

            # technical_cache 表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS technical_cache (
                    symbol TEXT,
                    date TEXT,
                    indicator TEXT,
                    value REAL,
                    fetched_at TEXT,
                    ttl_hours INTEGER DEFAULT 24,
                    PRIMARY KEY (symbol, date, indicator)
                )
            """)

            # decision_hash_cache 表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS decision_hash_cache (
                    input_hash TEXT PRIMARY KEY,
                    result_json TEXT,
                    created_at TEXT,
                    ttl_days INTEGER DEFAULT 7
                )
            """)

            conn.commit()

    def _is_expired(self, fetched_at: str, ttl_hours: int) -> bool:
        """检查缓存是否过期"""
        fetched = datetime.fromisoformat(fetched_at)
        expiry = fetched + timedelta(hours=ttl_hours)
        return datetime.utcnow() > expiry

    def get_ohlcv(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        ctx: TemporalContext,
    ) -> Optional[pd.DataFrame]:
        """
        获取 OHLCV 缓存

        WHERE 条件包含 date <= ctx.analysis_date（时间隔离）
        """
        with sqlite3.connect(self.db_path) as conn:
            query = """
                SELECT symbol, date, open, high, low, close, volume, adj_close, data_source
                FROM ohlcv_cache
                WHERE symbol = ?
                AND date(date) >= ?
                AND date(date) <= ?
                AND date(date) <= ?
                ORDER BY date
            """
            df = pd.read_sql_query(
                query,
                conn,
                params=(symbol, start_date, end_date, ctx.analysis_date)
            )

            # 检查过期
            if not df.empty:
                df["date"] = pd.to_datetime(df["date"])
                return df

        return None

    def set_ohlcv(
        self,
        symbol: str,
        df: pd.DataFrame,
        ctx: TemporalContext,
        ttl_hours: int = 24,
    ) -> None:
        """
        设置 OHLCV 缓存

        同时追加写入 Parquet 文件（原始数据不可篡改）
        """
        # 写入 SQLite 缓存
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            for _, row in df.iterrows():
                date_str = row["date"].isoformat() if pd.notna(row["date"]) else None
                fetched_at = datetime.utcnow().isoformat()

                cursor.execute("""
                    INSERT OR REPLACE INTO ohlcv_cache
                    (symbol, date, open, high, low, close, volume, adj_close, data_source, fetched_at, ttl_hours)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    symbol, date_str, row["open"], row["high"], row["low"],
                    row["close"], row["volume"], row["adj_close"],
                    row.get("data_source", "unknown"), fetched_at, ttl_hours
                ))
            conn.commit()

        # 追加写入 Parquet 文件（原始数据不可篡改）
        self._append_parquet(symbol, df)

    def _append_parquet(self, symbol: str, df: pd.DataFrame) -> None:
        """
        追加写入 Parquet 文件

        只追加不修改，确保回测数据不可篡改
        """
        parquet_path = self.parquet_dir / f"{symbol}.parquet"

        try:
            if parquet_path.exists():
                # 读取现有数据并追加
                existing_df = pq.read_table(parquet_path).to_pandas()
                df = pd.concat([existing_df, df], ignore_index=True)

            # 写入 Parquet
            table = pa.Table.from_pandas(df)
            pq.write_table(table, parquet_path)
        except Exception as e:
            print(f"Error appending to Parquet: {e}")

    def get_fundamentals(
        self,
        symbol: str,
        as_of_date: date,
        ctx: TemporalContext,
    ) -> Optional[Dict]:
        """
        获取基本面缓存

        WHERE 条件包含 as_of_date <= ctx.analysis_date
        """
        with sqlite3.connect(self.db_path) as conn:
            query = """
                SELECT data_json, fetched_at, ttl_hours
                FROM fundamentals_cache
                WHERE symbol = ?
                AND date(as_of_date) <= ?
                ORDER BY as_of_date DESC
                LIMIT 1
            """
            cursor = conn.cursor()
            cursor.execute(query, (symbol, ctx.analysis_date))
            result = cursor.fetchone()

            if result:
                data_json, fetched_at, ttl_hours = result
                if not self._is_expired(fetched_at, ttl_hours):
                    return json.loads(data_json)

        return None

    def set_fundamentals(
        self,
        symbol: str,
        as_of_date: date,
        data: Dict,
        ttl_hours: int = 24,
    ) -> None:
        """设置基本面缓存"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            fetched_at = datetime.utcnow().isoformat()

            cursor.execute("""
                INSERT OR REPLACE INTO fundamentals_cache
                (symbol, as_of_date, data_json, fetched_at, ttl_hours)
                VALUES (?, ?, ?, ?, ?)
            """, (
                symbol, as_of_date.isoformat(), json.dumps(data),
                fetched_at, ttl_hours
            ))
            conn.commit()

    def get_news(
        self,
        symbol: str,
        ctx: TemporalContext,
    ) -> Optional[List[Dict]]:
        """
        获取新闻缓存

        WHERE 条件包含 published_at <= ctx.analysis_date
        """
        with sqlite3.connect(self.db_path) as conn:
            query = """
                SELECT news_json, fetched_at, ttl_hours
                FROM news_cache
                WHERE symbol = ?
                AND date(published_at) <= ?
                ORDER BY published_at DESC
            """
            df = pd.read_sql_query(
                query,
                conn,
                params=(symbol, ctx.analysis_date)
            )

            # 过滤过期数据
            valid_news = []
            for _, row in df.iterrows():
                if not self._is_expired(row["fetched_at"], row["ttl_hours"]):
                    valid_news.append(json.loads(row["news_json"]))

            return valid_news if valid_news else None

    def set_news(
        self,
        symbol: str,
        news_list: List,
        ttl_hours: int = 6,
    ) -> None:
        """
        设置新闻缓存

        同时追加写入 JSON 文件
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            fetched_at = datetime.utcnow().isoformat()

            for news in news_list:
                title = news.get("title", "")
                title_hash = hashlib.md5(title.encode()).hexdigest()

                cursor.execute("""
                    INSERT OR REPLACE INTO news_cache
                    (symbol, published_at, title_hash, news_json, fetched_at, ttl_hours)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    symbol,
                    news.get("published_at", datetime.utcnow().isoformat()),
                    title_hash,
                    json.dumps(news),
                    fetched_at,
                    ttl_hours
                ))
            conn.commit()

        # 追加写入 JSON 文件
        self._append_news_json(symbol, news_list)

    def _append_news_json(self, symbol: str, news_list: List) -> None:
        """追加写入新闻 JSON 文件"""
        today_str = date.today().isoformat()
        symbol_news_dir = self.news_dir / symbol
        symbol_news_dir.mkdir(parents=True, exist_ok=True)

        json_path = symbol_news_dir / f"{today_str}.json"
        with open(json_path, "a", encoding="utf-8") as f:
            for news in news_list:
                f.write(json.dumps(news, ensure_ascii=False) + "\n")

    def get_decision(
        self,
        input_hash: str,
    ) -> Optional[Dict]:
        """获取决策哈希缓存"""
        with sqlite3.connect(self.db_path) as conn:
            query = """
                SELECT result_json, created_at, ttl_days
                FROM decision_hash_cache
                WHERE input_hash = ?
            """
            cursor = conn.cursor()
            cursor.execute(query, (input_hash,))
            result = cursor.fetchone()

            if result:
                result_json, created_at, ttl_days = result
                created = datetime.fromisoformat(created_at)
                expiry = created + timedelta(days=ttl_days)
                if datetime.utcnow() <= expiry:
                    return json.loads(result_json)

        return None

    def set_decision(
        self,
        input_hash: str,
        result: Dict,
        ttl_days: int = 7,
    ) -> None:
        """设置决策哈希缓存"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            created_at = datetime.utcnow().isoformat()

            cursor.execute("""
                INSERT OR REPLACE INTO decision_hash_cache
                (input_hash, result_json, created_at, ttl_days)
                VALUES (?, ?, ?, ?)
            """, (
                input_hash,
                json.dumps(result),
                created_at,
                ttl_days
            ))
            conn.commit()

    def clear_expired(self) -> int:
        """清除过期缓存，返回清除的行数"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            total_cleared = 0

            # 清理各表的过期数据
            tables = [
                ("ohlcv_cache", "fetched_at", "ttl_hours"),
                ("fundamentals_cache", "fetched_at", "ttl_hours"),
                ("news_cache", "fetched_at", "ttl_hours"),
                ("technical_cache", "fetched_at", "ttl_hours"),
                ("decision_hash_cache", "created_at", "ttl_days"),
            ]

            for table, time_col, ttl_col in tables:
                cursor.execute(f"""
                    DELETE FROM {table}
                    WHERE datetime({time_col}) < datetime('now', '-' || {ttl_col} || ' hours')
                """)
                total_cleared += cursor.rowcount

            conn.commit()
            return total_cleared
