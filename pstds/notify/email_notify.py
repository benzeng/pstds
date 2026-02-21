# pstds/notify/email_notify.py
# 邮件通知 - Phase 6 Task 4 (P6-T4)

from typing import Optional, List
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
import os


class EmailNotifier:
    """
    邮件通知管理器

    发送邮件通知（分析完成、费用告警等）。
    """

    def __init__(
        self,
        smtp_server: str = "smtp.gmail.com",
        smtp_port: int = 587,
        smtp_username: Optional[str] = None,
        smtp_password: Optional[str] = None,
        from_email: Optional[str] = None,
        enabled: bool = False,
    ):
        """
        初始化邮件通知管理器

        Args:
            smtp_server: SMTP 服务器
            smtp_port: SMTP 端口
            smtp_username: SMTP 用户名
            smtp_password: SMTP 密码
            from_email: 发件人邮箱
            enabled: 是否启用邮件通知
        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.smtp_username = smtp_username or os.getenv("SMTP_USERNAME")
        self.smtp_password = smtp_password or os.getenv("SMTP_PASSWORD")
        self.from_email = from_email or os.getenv("FROM_EMAIL")
        self.enabled = enabled

        if not self.smtp_username or not self.smtp_password or not self.from_email:
            print("邮件通知未配置，请设置 SMTP_USERNAME、SMTP_PASSWORD、FROM_EMAIL 环境变量")
            self.enabled = False

    def send_email(
        self,
        to_emails: List[str],
        subject: str,
        body: str,
        html: bool = False,
    ) -> bool:
        """
        发送邮件

        Args:
            to_emails: 收件人邮箱列表
            subject: 邮件主题
            body: 邮件正文
            html: 是否为 HTML 格式

        Returns:
            是否发送成功
        """
        if not self.enabled:
            print("邮件通知未启用")
            return False

        try:
            # 创建邮件消息
            if html:
                msg = MIMEMultipart('alternative')
                msg.attach(MIMEText(body, 'plain', 'utf-8'))
                msg.attach(MIMEText(body, 'html', 'utf-8'))
            else:
                msg = MIMEMultipart('mixed')
                msg.attach(MIMEText(body, 'plain', 'utf-8'))

            # 设置邮件头
            msg['From'] = formataddr(('PSTDS', self.from_email))
            msg['Subject'] = subject
            msg['Date'] = datetime.now().strftime("%a, %d %b %Y %H:%M:%S")

            # 设置收件人
            for to_email in to_emails:
                msg['To'] = to_email
                msg.set_recipients([to_email])

            # 连接 SMTP 服务器并发送
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
                server.quit()

            print(f"邮件已发送至: {', '.join(to_emails)}")
            return True

        except Exception as e:
            print(f"发送邮件失败: {e}")
            return False

    def notify_analysis_complete(self, to_emails: List[str], symbol: str, action: str) -> bool:
        """
        通知分析完成

        Args:
            to_emails: 收件人邮箱列表
            symbol: 股票代码
            action: 决策类型

        Returns:
            是否发送成功
        """
        subject = f"[PSTDS] {symbol} 分析完成"
        body = f"""
股票代码: {symbol}
决策类型: {action}
完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

这是 PSTDS 系统自动生成的通知邮件。

重要提示：
- 投资有风险，入市须谨慎
- 本系统不构成任何形式的投资建议
- 开发者对投资损失不承担任何责任
"""

        return self.send_email(to_emails, subject, body)

    def notify_cost_alert(self, to_emails: List[str], monthly_cost: float) -> bool:
        """
        通知费用告警

        Args:
            to_emails: 收件人邮箱列表
            monthly_cost: 本月累计成本

        Returns:
            是否发送成功
        """
        if monthly_cost < 10.0:  # 告警阈值
            return False

        subject = f"[PSTDS] 费用告警"
        body = f"""
本月累计成本: ${monthly_cost:.2f}
阈值: $10.00

您的月度 API 成本已接近或超过阈值，请注意控制使用。

这是 PSTDS 系统自动生成的通知邮件。
"""

        return self.send_email(to_emails, subject, body)


# 全局邮件通知器实例
_global_email_notifier: Optional[EmailNotifier] = None


def get_email_notifier() -> Optional[EmailNotifier]:
    """
    获取全局邮件通知器实例（单例）

    Returns:
        EmailNotifier 实例
    """
    global _global_email_notifier
    if _global_email_notifier is None:
        _global_email_notifier = EmailNotifier()
    return _global_email_notifier
