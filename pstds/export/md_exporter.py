# pstds/export/md_exporter.py
# Markdown 导出器 - Phase 6 Task 1 (P6-T1)

from typing import Dict, Any, Optional
from datetime import date, datetime, UTC
import json


class MarkdownExporter:
    """
    Markdown 导出器

    将回测结果和分析记录导出为 Markdown 格式。
    """

    def export_backtest_result(self, result: Dict[str, Any]) -> str:
        """
        导出回测结果为 Markdown

        Args:
            result: 回测结果字典（来自 BacktestRunner）

        Returns:
            Markdown 格式字符串
        """
        md_lines = []

        # 标题
        md_lines.append("# 回测报告")
        md_lines.append("")
        md_lines.append(f"**股票代码**: {result.get('symbol', 'N/A')}")
        md_lines.append(f"**市场类型**: {result.get('market_type', 'N/A')}")
        md_lines.append(f"**回测期间**: {result.get('start_date', 'N/A')} 至 {result.get('end_date', 'N/A')}")
        md_lines.append(f"**交易天数**: {result.get('trading_days_count', 0)} 天")
        md_lines.append(f"**生成时间**: {datetime.now(UTC).isoformat()}")
        md_lines.append("")

        # 绩效摘要
        md_lines.append("## 绩效摘要")
        md_lines.append("")

        metrics = result.get('nav_series', {})

        if 'total_return' in result:
            md_lines.append(f"- **总收益率**: {result['total_return']:.2f}%")
        if 'annualized_return' in result:
            md_lines.append(f"- **年化收益率**: {result['annualized_return']:.2f}%")
        if 'max_drawdown' in result:
            md_lines.append(f"- **最大回撤**: {result['max_drawdown']:.2f}%")
        if 'sharpe_ratio' in result:
            md_lines.append(f"- **夏普比率**: {result['sharpe_ratio']:.2f}")
        if 'calmar_ratio' in result:
            md_lines.append(f"- **卡尔马比率**: {result['calmar_ratio']:.2f}")
        if 'win_rate' in result:
            md_lines.append(f"- **胜率**: {result['win_rate']:.2f}%")
        if 'prediction_accuracy' in result:
            md_lines.append(f"- **预测准确率**: {result['prediction_accuracy']:.2f}%")

        md_lines.append("")

        # 资金变化
        md_lines.append("## 资金变化")
        md_lines.append("")
        md_lines.append(f"- **初始资金**: ${result.get('initial_capital', 0):.2f}")
        md_lines.append(f"- **最终净值**: ${result.get('final_nav', 0):.2f}")
        md_lines.append("")

        # 交易统计
        md_lines.append("## 交易统计")
        md_lines.append("")
        md_lines.append(f"- **交易次数**: {result.get('trade_count', 0)}")
        md_lines.append("")

        # 每日快照（可选）
        if result.get('include_daily_snapshots', False):
            md_lines.append("## 每日净值快照")
            md_lines.append("")
            md_lines.append("| 日期 | 净值 | 现金 | 持仓数 | 决策 |")
            md_lines.append("| --- | --- | --- | --- | --- |")

            for snapshot in result.get('daily_snapshots', [])[:30]:  # 限制显示30天
                md_lines.append(
                    f"| {snapshot.get('date', 'N/A')} | "
                    f"${snapshot.get('nav', 0):.2f} | "
                    f"${snapshot.get('cash', 0):.2f} | "
                    f"{snapshot.get('positions_count', 0)} | "
                    f"{snapshot.get('decision', {}).get('action', 'N/A')} |"
                )

            md_lines.append("")
            md_lines.append("*注：仅显示前30天数据*")
            md_lines.append("")

        # 免责声明
        md_lines.append("---")
        md_lines.append("")
        md_lines.append("## 免责声明")
        md_lines.append("")
        md_lines.append("> 本报告由 PSTDS（个人专用股票交易决策系统）自动生成。")
        md_lines.append("> ")
        md_lines.append("> **重要提示：**")
        md_lines.append("> - 投资有风险，入市须谨慎")
        md_lines.append("> - 本系统不构成任何形式的投资建议")
        md_lines.append("> - 开发者对投资损失不承担任何责任")
        md_lines.append("> - 请在充分理解风险的前提下使用本系统")
        md_lines.append("> ")
        md_lines.append("> 本报告的任何内容仅供研究参考，不作为投资决策的唯一依据。")
        md_lines.append("")
        md_lines.append("---")
        md_lines.append("*© 2026 PSTDS - 个人专用股票交易决策系统*")

        return "\n".join(md_lines)

    def export_analysis(self, decision: Dict[str, Any]) -> str:
        """
        导出分析结果为 Markdown

        Args:
            decision: 分析决策字典（TradeDecision）

        Returns:
            Markdown 格式字符串
        """
        md_lines = []

        # 标题
        md_lines.append("# 分析报告")
        md_lines.append("")
        md_lines.append(f"**股票代码**: {decision.get('symbol', 'N/A')}")
        md_lines.append(f"**市场类型**: {decision.get('market_type', 'N/A')}")
        md_lines.append(f"**分析日期**: {decision.get('analysis_date', 'N/A')}")
        md_lines.append(f"**生成时间**: {datetime.now(UTC).isoformat()}")
        md_lines.append("")

        # 决策信息
        md_lines.append("## 决策信息")
        md_lines.append("")
        md_lines.append(f"- **决策**: {decision.get('action', 'N/A')}")
        md_lines.append(f"- **置信度**: {decision.get('confidence', 0):.2f}")
        md_lines.append(f"- **信心度**: {decision.get('conviction', 'N/A')}")
        md_lines.append(f"- **主要理由**: {decision.get('primary_reason', 'N/A')}")
        md_lines.append("")

        # 价格目标
        if decision.get('target_price_low') or decision.get('target_price_high'):
            md_lines.append("## 价格目标")
            md_lines.append("")
            if decision.get('target_price_low'):
                md_lines.append(f"- **目标价下限**: ${decision.get('target_price_low', 0):.2f}")
            if decision.get('target_price_high'):
                md_lines.append(f"- **目标价上限**: ${decision.get('target_price_high', 0):.2f}")
            md_lines.append(f"- **时间框架**: {decision.get('time_horizon', 'N/A')}")
            md_lines.append("")

        # 风险因素
        md_lines.append("## 风险因素")
        md_lines.append("")
        for risk in decision.get('risk_factors', []):
            md_lines.append(f"- {risk}")
        md_lines.append("")

        # 数据来源
        md_lines.append("## 数据来源")
        md_lines.append("")
        for source in decision.get('data_sources', []):
            name = source.get('name', 'N/A')
            md_lines.append(f"- {name}")
        md_lines.append("")

        # 元数据
        md_lines.append("## 元数据")
        md_lines.append("")
        md_lines.append(f"- **波动率调整**: {decision.get('volatility_adjustment', 1.0):.2f}")
        md_lines.append(f"- **辩论质量分**: {decision.get('debate_quality_score', 0):.2f}/10.0")
        md_lines.append("")

        # 免责声明
        md_lines.append("---")
        md_lines.append("")
        md_lines.append("## 免责声明")
        md_lines.append("")
        md_lines.append("> 本报告由 PSTDS（个人专用股票交易决策系统）自动生成。")
        md_lines.append("> ")
        md_lines.append("> **重要提示：**")
        md_lines.append("> - 投资有风险，入市须谨慎")
        md_lines.append("> - 本系统不构成任何形式的投资建议")
        md_lines.append("> - 开发者对投资损失不承担任何责任")
        md_lines.append("> - 请在充分理解风险的前提下使用本系统")
        md_lines.append("> ")
        md_lines.append("> 本报告的任何内容仅供研究参考，不作为投资决策的唯一依据。")
        md_lines.append("")
        md_lines.append("---")
        md_lines.append("*© 2026 PSTDS - 个人专用股票交易决策系统*")

        return "\n".join(md_lines)

    def save_to_file(self, content: str, filepath: str) -> bool:
        """
        保存 Markdown 内容到文件

        Args:
            content: Markdown 内容
            filepath: 文件路径

        Returns:
            是否保存成功
        """
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            print(f"保存 Markdown 文件失败: {e}")
            return False

    def get_disclaimer(self) -> str:
        """
        获取标准免责声明

        Returns:
            免责声明 Markdown 字符串
        """
        return """---
## 免责声明

本报告由 PSTDS（个人专用股票交易决策系统）自动生成。

**重要提示：**
- 投资有风险，入市须谨慎
- 本系统不构成任何形式的投资建议
- 开发者对投资损失不承担任何责任
- 请在充分理解风险的前提下使用本系统

本报告的任何内容仅供研究参考，不作为投资决策的唯一依据。

---
*© 2026 PSTDS - 个人专用股票交易决策系统*
"""
