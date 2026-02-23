# pstds/agents/temporal_injection.py
# TemporalContext 注入工具函数 - BUG-002 修复接口
# ISD v1.0 Section 5 约束 C-02

import tradingagents.dataflows.interface as _iface
from pstds.temporal.context import TemporalContext

_original_route = None


def inject_temporal_context(ctx: TemporalContext) -> None:
    """
    将 TemporalContext 注入 tradingagents 数据获取层。

    通过 monkey-patch tradingagents.dataflows.interface.route_to_vendor，
    确保所有数据请求的日期参数不超过 ctx.analysis_date。

    Args:
        ctx: 时间上下文
    """
    global _original_route

    _original_route = _iface.route_to_vendor
    analysis_date_str = ctx.analysis_date.strftime("%Y-%m-%d")

    DATE_CAP_POSITIONS = {
        "get_stock_data": 2,
        "get_indicators": 2,
        "get_fundamentals": 1,
        "get_balance_sheet": 2,
        "get_cashflow": 2,
        "get_income_statement": 2,
        "get_news": 2,
        "get_global_news": 0,
    }

    def _guarded_route(method, *args, **kwargs):
        args = list(args)
        if method in DATE_CAP_POSITIONS:
            idx = DATE_CAP_POSITIONS[method]
            if idx < len(args) and args[idx] is not None:
                date_arg = str(args[idx])
                if date_arg > analysis_date_str:
                    args[idx] = analysis_date_str
        return _original_route(method, *args, **kwargs)

    _iface.route_to_vendor = _guarded_route


def restore_original_router() -> None:
    """
    恢复原版 route_to_vendor（monkey-patch 反向还原）。

    必须在 finally 块中调用，确保即使分析抛异常也能恢复。
    """
    global _original_route
    if _original_route is not None:
        _iface.route_to_vendor = _original_route
        _original_route = None
