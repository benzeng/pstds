# pstds/notify/desktop.py
# 桌面通知 - Phase 6 Task 4 (P6-T4)

from typing import Optional

try:
    from plyer import notification
    PLYER_AVAILABLE = True
except ImportError:
    PLYER_AVAILABLE = False
    notification = None


class DesktopNotifier:
    """
    桌面通知管理器

    使用 plyer 发送系统通知。
    """

    def __init__(self, enabled: bool = True):
        """
        初始化桌面通知管理器

        Args:
            enabled: 是否启用桌面通知
        """
        self.enabled = enabled

    def notify(self, title: str, message: str, timeout: int = 10) -> bool:
        """
        发送桌面通知

        Args:
            title: 通知标题
            message: 通知消息
            timeout: 显示时长（秒）

        Returns:
            是否发送成功
        """
        if not self.enabled or not PLYER_AVAILABLE:
            return False

        try:
            notification.notify(
                title=title,
                message=message,
                app_name="PSTDS",
                timeout=timeout,
            )
            return True
        except Exception as e:
            print(f"发送桌面通知失败: {e}")
            return False

    def notify_analysis_complete(self, symbol: str, action: str) -> bool:
        """
        通知分析完成

        Args:
            symbol: 股票代码
            action: 决策类型

        Returns:
            是否发送成功
        """
        title = f"{symbol} 分析完成"
        message = f"决策: {action}"
        return self.notify(title, message)

    def notify_cost_alert(self, estimated_cost: float, monthly_cost: float) -> bool:
        """
        通知费用告警

        Args:
            estimated_cost: 本次估算成本
            monthly_cost: 本月累计成本

        Returns:
            是否发送成功
        """
        if monthly_cost >= 10.0:  # 告警阈值
            title = "费用告警"
            message = f"本月累计成本已达 ${monthly_cost:.2f}"
            return self.notify(title, message)

        return False


# 全局通知器实例
_global_notifier: Optional[DesktopNotifier] = None


def get_notifier() -> Optional[DesktopNotifier]:
    """
    获取全局通知器实例（单例）

    Returns:
        DesktopNotifier 实例
    """
    global _global_notifier
    if _global_notifier is None:
        _global_notifier = DesktopNotifier()
    return _global_notifier
