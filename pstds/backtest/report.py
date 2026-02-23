# pstds/backtest/report.py
# 回测报告生成器 - ISD v2.0 Section 4.4 / DDD v3.0 Section 2.4
# Phase 1 Task 4 (P1-T4)

import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class BacktestReportGenerator:
    """
    回测报告生成器 - DDD v3.0 Section 2.4

    接收 BacktestRunner 已完成的结果，生成各种格式的报告。
    不负责回测计算，仅负责报告生成。
    """

    def __init__(self, backtest_result: Dict[str, Any], daily_records: List[Dict]):
        """
        初始化报告生成器

        Args:
            backtest_result: BacktestRunner.run() 返回的结果字典，包含绩效指标
            daily_records: 逐日决策记录列表，每条含 date/action/price/nav 等字段
        """
        self.result = backtest_result
        self.records = daily_records

    def nav_series(self) -> Dict[str, float]:
        """
        日度净值序列 - DDD v3.0 Section 2.4

        Returns:
            {日期字符串: NAV值} 字典，日期格式 YYYY-MM-DD
        """
        series: Dict[str, float] = {}
        for record in self.records:
            date_key = str(record.get("date", ""))
            nav = record.get("nav", record.get("portfolio_nav", None))
            if date_key and nav is not None:
                series[date_key] = float(nav)
        return series

    def attribution_analysis(self) -> Dict[str, Dict[str, Any]]:
        """
        决策归因分析 - DDD v3.0 Section 2.4

        按 action 类型统计准确率，HOLD 不计入统计。

        Returns:
            {
                "BUY":  {"count": int, "correct": int, "accuracy_pct": float},
                "SELL": {"count": int, "correct": int, "accuracy_pct": float},
            }
        """
        attribution: Dict[str, Dict[str, Any]] = {}

        for record in self.records:
            action = record.get("action", "HOLD")
            if action == "HOLD":
                continue

            if action not in attribution:
                attribution[action] = {"count": 0, "correct": 0, "accuracy_pct": 0.0}

            attribution[action]["count"] += 1
            if record.get("correct", False):
                attribution[action]["correct"] += 1

        # 计算准确率
        for action_data in attribution.values():
            count = action_data["count"]
            if count > 0:
                action_data["accuracy_pct"] = round(
                    action_data["correct"] / count * 100, 2
                )

        return attribution

    def to_markdown(self) -> str:
        """
        生成 Markdown 格式回测报告 - DDD v3.0 Section 2.4

        报告包含：
        - 回测概况
        - 绩效指标表格
        - 净值走势描述
        - 归因分析
        - 逐日决策摘要（最近 10 条）

        Returns:
            Markdown 格式字符串
        """
        r = self.result
        symbol = r.get("symbol", "N/A")
        start_date = r.get("start_date", "N/A")
        end_date = r.get("end_date", "N/A")
        initial_capital = r.get("initial_capital", 0.0)
        final_nav = r.get("final_nav", 0.0)
        total_return = r.get("total_return", 0.0)
        annualized_return = r.get("annualized_return", 0.0)
        max_drawdown = r.get("max_drawdown", 0.0)
        sharpe_ratio = r.get("sharpe_ratio", 0.0)
        calmar_ratio = r.get("calmar_ratio", 0.0)
        win_rate = r.get("win_rate", 0.0)
        prediction_accuracy = r.get("prediction_accuracy", 0.0)
        trade_count = r.get("trade_count", 0)
        trading_days = r.get("trading_days_count", 0)

        lines = []

        # 回测概况
        lines.append(f"# 回测报告：{symbol}")
        lines.append("")
        lines.append("## 回测概况")
        lines.append("")
        lines.append(f"| 参数 | 值 |")
        lines.append(f"|------|-----|")
        lines.append(f"| 标的 | {symbol} |")
        lines.append(f"| 回测区间 | {start_date} ~ {end_date} |")
        lines.append(f"| 初始资金 | ¥{initial_capital:,.2f} |")
        lines.append(f"| 期末净值 | ¥{final_nav:,.2f} |")
        lines.append(f"| 交易天数 | {trading_days} 天 |")
        lines.append(f"| 交易次数 | {trade_count} 次 |")
        lines.append("")

        # 绩效指标
        lines.append("## 绩效指标")
        lines.append("")
        lines.append(f"| 指标 | 值 |")
        lines.append(f"|------|-----|")
        lines.append(f"| 总收益率 | {total_return * 100:.2f}% |")
        lines.append(f"| 年化收益率 | {annualized_return * 100:.2f}% |")
        lines.append(f"| 最大回撤 | {max_drawdown * 100:.2f}% |")
        lines.append(f"| 夏普比率 | {sharpe_ratio:.4f} |")
        lines.append(f"| 卡玛比率 | {calmar_ratio:.4f} |")
        lines.append(f"| 胜率 | {win_rate * 100:.2f}% |")
        lines.append(f"| 预测准确率 | {prediction_accuracy * 100:.2f}% |")
        lines.append("")

        # 净值走势描述
        lines.append("## 净值走势")
        lines.append("")
        nav_data = self.nav_series()
        if nav_data:
            min_nav = min(nav_data.values())
            max_nav = max(nav_data.values())
            lines.append(f"- 区间最低净值：¥{min_nav:,.2f}")
            lines.append(f"- 区间最高净值：¥{max_nav:,.2f}")
            lines.append(f"- 净值记录条数：{len(nav_data)} 条")
        else:
            lines.append("暂无净值数据。")
        lines.append("")

        # 归因分析
        lines.append("## 归因分析")
        lines.append("")
        attribution = self.attribution_analysis()
        if attribution:
            lines.append("| 操作类型 | 总次数 | 正确次数 | 准确率 |")
            lines.append("|----------|--------|----------|--------|")
            for action, data in attribution.items():
                lines.append(
                    f"| {action} | {data['count']} | {data['correct']} | {data['accuracy_pct']:.1f}% |"
                )
        else:
            lines.append("暂无归因数据（无 BUY/SELL 操作）。")
        lines.append("")

        # 逐日决策摘要（最近 10 条）
        lines.append("## 逐日决策摘要（最近 10 条）")
        lines.append("")
        recent_records = self.records[-10:] if len(self.records) > 10 else self.records
        if recent_records:
            lines.append("| 日期 | 操作 | 置信度 | 净值 |")
            lines.append("|------|------|--------|------|")
            for rec in recent_records:
                d = rec.get("date", "N/A")
                a = rec.get("action", "N/A")
                c = rec.get("confidence", 0.0)
                n = rec.get("nav", rec.get("portfolio_nav", 0.0))
                lines.append(f"| {d} | {a} | {c:.2f} | ¥{n:,.2f} |")
        else:
            lines.append("暂无逐日记录。")
        lines.append("")

        return "\n".join(lines)

    def to_docx(self, output_path: str) -> None:
        """
        生成 DOCX 格式报告 - DDD v3.0 Section 2.4

        Args:
            output_path: 输出文件路径
        """
        try:
            from pstds.export.docx_exporter import DocxExporter
            exporter = DocxExporter()
            md_content = self.to_markdown()
            exporter.export(md_content, output_path)
        except ImportError:
            logger.warning("[BacktestReportGenerator] docx_exporter 未安装，跳过 DOCX 导出")
        except Exception as e:
            logger.warning(f"[BacktestReportGenerator] DOCX 导出失败: {e}")

    def save_to_mongo(self, store) -> str:
        """
        序列化写入 MongoDB - DDD v3.0 Section 2.4

        Args:
            store: MongoStore 实例

        Returns:
            插入文档的 ID 字符串
        """
        from datetime import datetime, UTC
        doc = {
            "symbol": self.result.get("symbol", ""),
            "start_date": self.result.get("start_date", ""),
            "end_date": self.result.get("end_date", ""),
            "report_text": self.to_markdown(),
            "backtest_result": self.result,
            "nav_series": self.nav_series(),
            "attribution": self.attribution_analysis(),
            "generated_at": datetime.now(UTC).isoformat(),
        }
        doc_id = store.insert_one("backtest_results", doc)
        return str(doc_id)
