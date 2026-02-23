# pstds/data/news_filter.py
# NewsFilter 三级过滤器 - ISD v2.0 Section 4.1
# Phase 1 Task 1 (P1-T1)

import logging
from dataclasses import dataclass
from typing import List, Tuple

from pstds.data.models import NewsItem
from pstds.temporal.context import TemporalContext
from pstds.temporal.guard import TemporalGuard

logger = logging.getLogger(__name__)


@dataclass
class NewsFilterStats:
    """
    过滤统计数据 - ISD v2.0 Section 4.1

    字段：
      raw_count        原始新闻总数
      after_temporal   L1 时间过滤后数量
      after_relevance  L2 相关性过滤后数量
      after_dedup      L3 去重后数量

    属性：
      temporal_filtered   L1 过滤掉的数量
      relevance_filtered  L2 过滤掉的数量
    """

    raw_count: int = 0
    after_temporal: int = 0
    after_relevance: int = 0
    after_dedup: int = 0

    @property
    def temporal_filtered(self) -> int:
        """L1 时间过滤掉的数量"""
        return self.raw_count - self.after_temporal

    @property
    def relevance_filtered(self) -> int:
        """L2 相关性过滤掉的数量"""
        return self.after_temporal - self.after_relevance


class NewsFilter:
    """
    新闻三级过滤器 - ISD v2.0 Section 4.1

    L1: 时间过滤（直接调用 TemporalGuard.filter_news()，不重复实现）
    L2: 相关性过滤（TF-IDF 余弦相似度，method 参数支持切换为 embedding）
    L3: 余弦去重（相似度 > dedup_threshold 的对中保留 published_at 最早的）

    约束 C-08：纯函数设计，不修改输入列表，每次调用返回新对象
    """

    def __init__(
        self,
        relevance_threshold: float = 0.05,
        dedup_threshold: float = 0.85,
        method: str = "tfidf",
    ):
        """
        Args:
            relevance_threshold: L2 相关性阈值（低于此值被过滤）
            dedup_threshold: L3 去重阈值（高于此值视为重复）
            method: 相关性计算方法 ("tfidf" 或 "embedding")
        """
        self.relevance_threshold = relevance_threshold
        self.dedup_threshold = dedup_threshold
        self.method = method

    def filter(
        self,
        news_list: List[NewsItem],
        symbol: str,
        ctx: TemporalContext,
        company_name: str = "",
    ) -> Tuple[List[NewsItem], NewsFilterStats]:
        """
        三级过滤新闻列表 - ISD v2.0 Section 4.1

        纯函数：不修改输入列表，每次调用返回新对象（C-08 约束）。
        任何内部错误静默降级，记录 logger.warning，不传播异常。

        Args:
            news_list: 原始新闻列表（不被修改）
            symbol: 股票代码
            ctx: 时间上下文
            company_name: 公司名称（可选，用于 L2 查询词增强）

        Returns:
            (过滤后新闻列表, NewsFilterStats)
        """
        stats = NewsFilterStats(raw_count=len(news_list))

        # ─── L1: 时间过滤 ───────────────────────────────────────────
        try:
            # 直接调用 TemporalGuard.filter_news()，不重复实现
            temporal_filtered = TemporalGuard.filter_news(list(news_list), ctx)
        except Exception as e:
            logger.warning(f"[NewsFilter] L1 时间过滤异常，降级返回原列表: {e}")
            temporal_filtered = list(news_list)

        stats.after_temporal = len(temporal_filtered)

        # ─── L2: 相关性过滤 ─────────────────────────────────────────
        try:
            relevance_filtered = self._filter_by_relevance(
                temporal_filtered, symbol, company_name
            )
        except Exception as e:
            logger.warning(f"[NewsFilter] L2 相关性过滤异常，降级返回 L1 结果: {e}")
            relevance_filtered = temporal_filtered

        stats.after_relevance = len(relevance_filtered)

        # ─── L3: 余弦去重 ───────────────────────────────────────────
        try:
            deduped = self._dedup_by_cosine(relevance_filtered)
        except Exception as e:
            logger.warning(f"[NewsFilter] L3 去重异常，降级返回 L2 结果: {e}")
            deduped = relevance_filtered

        stats.after_dedup = len(deduped)

        return deduped, stats

    def _filter_by_relevance(
        self,
        news_list: List[NewsItem],
        symbol: str,
        company_name: str,
    ) -> List[NewsItem]:
        """
        L2 相关性过滤 - 默认使用 sklearn TF-IDF

        corpus 为空时静默返回原列表。
        """
        if not news_list:
            return []

        texts = [f"{n.title} {n.content}" for n in news_list]
        if not any(t.strip() for t in texts):
            # corpus 为空时静默返回原列表
            return list(news_list)

        query = f"{symbol} {company_name}".strip()

        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity

            all_texts = [query] + texts
            vectorizer = TfidfVectorizer(min_df=1)
            tfidf_matrix = vectorizer.fit_transform(all_texts)

            query_vec = tfidf_matrix[0]
            doc_vecs = tfidf_matrix[1:]
            similarities = cosine_similarity(query_vec, doc_vecs)[0]

            result = [
                news
                for news, score in zip(news_list, similarities)
                if score >= self.relevance_threshold
            ]

            # 全部低相关时降级（不丢弃所有新闻）
            if not result:
                logger.warning(
                    f"[NewsFilter] L2 所有新闻相关性不足（threshold={self.relevance_threshold}），降级返回原列表"
                )
                return list(news_list)

            return result

        except ImportError:
            logger.warning("[NewsFilter] sklearn 未安装，跳过 L2 相关性过滤")
            return list(news_list)

    def _dedup_by_cosine(
        self,
        news_list: List[NewsItem],
    ) -> List[NewsItem]:
        """
        L3 余弦去重

        相似度 > dedup_threshold 的对中保留 published_at 最早的。
        """
        if len(news_list) <= 1:
            return list(news_list)

        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity

            texts = [f"{n.title} {n.content}" for n in news_list]
            vectorizer = TfidfVectorizer(min_df=1)
            tfidf_matrix = vectorizer.fit_transform(texts)
            sim_matrix = cosine_similarity(tfidf_matrix)

            # 按 published_at 升序排列（最早的优先保留）
            indexed = sorted(enumerate(news_list), key=lambda x: x[1].published_at)

            kept_orig_indices: set = set()
            for orig_i, _news in indexed:
                is_dup = any(
                    sim_matrix[orig_i, kept_j] > self.dedup_threshold
                    for kept_j in kept_orig_indices
                )
                if not is_dup:
                    kept_orig_indices.add(orig_i)

            # 按原始顺序返回
            return [news for i, news in enumerate(news_list) if i in kept_orig_indices]

        except ImportError:
            logger.warning("[NewsFilter] sklearn 未安装，跳过 L3 去重")
            return list(news_list)
