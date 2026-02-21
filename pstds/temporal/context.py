# pstds/temporal/context.py
# ISD v1.0 Section 2.2: TemporalContext（时间上下文）

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Literal
from uuid import uuid4


@dataclass(frozen=True)  # 不可变，防止运行时篡改
class TemporalContext:
    """
    时间上下文 - 时间隔离层的核心数据结构

    所有数据访问方法必须接受此参数，并调用 TemporalGuard 进行时间边界校验。
    frozen=True 确保不可变性，防止运行时篡改分析日期。
    """

    analysis_date: date  # 分析基准日期（必填）

    mode: Literal["LIVE", "BACKTEST"]  # 运行模式

    created_at: datetime = field(default_factory=lambda: datetime.utcnow())

    session_id: str = field(default_factory=lambda: str(uuid4()))

    @classmethod
    def for_live(cls, analysis_date: date) -> "TemporalContext":
        """创建实时分析上下文"""
        return cls(analysis_date=analysis_date, mode="LIVE")

    @classmethod
    def for_backtest(cls, sim_date: date) -> "TemporalContext":
        """创建回测模拟上下文"""
        return cls(analysis_date=sim_date, mode="BACKTEST")

    def get_prompt_prefix(self) -> str:
        """
        返回完整中文时间锚定声明

        此声明会被注入到 LLM 提示词的最前面，强制 LLM 遵守时间隔离规则。
        """
        return (
            f"【时间隔离声明】你当前正在分析 {self.analysis_date} 这一天的市场情况。"
            f"不得引用该日期之后发生的任何事件、数据或新闻。"
            f"你的所有分析必须基于以下明确提供的数据，"
            f"不得使用训练记忆中的具体财务数字或新闻内容。"
            f"若提供数据不足以支撑结论，输出 INSUFFICIENT_DATA 标志。"
        )
