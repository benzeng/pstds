# pstds/export/pdf_exporter.py
# PDF 导出器 - Phase 6 Task 3 (P6-T3)

from typing import Dict, Any, Optional
from datetime import date, datetime
import os

try:
    from weasyprint import HTML
    from weasyprint import CSS
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False
    HTML = None
    CSS = None


class PDFExporter:
    """
    PDF 导出器

    使用 WeasyPrint 导出为 PDF，包含图表和格式化报告。
    """

    def __init__(self, output_dir: str = "./data/reports"):
        """
        初始化 PDF 导出器

        Args:
            output_dir: 输出目录
        """
        self.output_dir = os.path.abspath(output_dir)
        os.makedirs(self.output_dir, exist_ok=True)

    def export_backtest_result(self, result: Dict[str, Any]) -> Optional[str]:
        """
        导出回测结果为 PDF

        Args:
            result: 回测结果字典

        Returns:
            PDF 文件路径，失败返回 None
        """
        if not WEASYPRINT_AVAILABLE:
            print("WeasyPrint 未安装，无法导出 PDF 文档")
            return None

        try:
            # 构建 HTML 内容
            html_content = self._build_backtest_html(result)

            # CSS 样式
            css = self._get_backtest_css()

            # 生成 PDF
            filename = f"backtest_{result.get('symbol', 'N/A')}_{datetime.now().strftime('%Y%m%d')}.pdf"
            filepath = os.path.join(self.output_dir, filename)

            HTML(string=html_content).write_pdf(
                filepath,
                stylesheets=[CSS(css)],
            )

            print(f"PDF 文档已保存: {filepath}")
            return filepath

        except Exception as e:
            print(f"导出 PDF 文档失败: {e}")
            return None

    def export_analysis(self, decision: Dict[str, Any]) -> Optional[str]:
        """
        导出分析结果为 PDF

        Args:
            decision: 分析决策字典

        Returns:
            PDF 文件路径，失败返回 None
        """
        if not WEASYPRINT_AVAILABLE:
            print("WeasyPrint 未安装，无法导出 PDF 文档")
            return None

        try:
            # 构建 HTML 内容
            html_content = self._build_analysis_html(decision)

            # CSS 样式
            css = self._get_analysis_css()

            # 生成 PDF
            filename = f"analysis_{decision.get('symbol', 'N/A')}_{datetime.now().strftime('%Y%m%d')}.pdf"
            filepath = os.path.join(self.output_dir, filename)

            HTML(string=html_content).write_pdf(
                filepath,
                stylesheets=[CSS(css)],
            )

            print(f"PDF 文档已保存: {filepath}")
            return filepath

        except Exception as e:
            print(f"导出 PDF 文档失败: {e}")
            return None

    def _build_backtest_html(self, result: Dict[str, Any]) -> str:
        """构建回测结果的 HTML 内容"""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>回测报告 - {result.get('symbol', 'N/A')}</title>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>回测报告</h1>
            <div class="meta">
                <p><strong>股票代码:</strong> {result.get('symbol', 'N/A')}</p>
                <p><strong>市场类型:</strong> {result.get('market_type', 'N/A')}</p>
                <p><strong>回测期间:</strong> {result.get('start_date', 'N/A')} 至 {result.get('end_date', 'N/A')}</p>
                <p><strong>生成时间:</strong> {datetime.now().strftime('%Y年%m月%d日 %H:%M')}</p>
            </div>
        </div>

        <div class="section">
            <h2>1. 绩效摘要</h2>
            <table class="metrics-table">
                <tr>
                    <th>指标</th>
                    <th>数值</th>
                </tr>
                <tr>
                    <td>初始资金</td>
                    <td>${result.get('initial_capital', 0):.2f}</td>
                </tr>
                <tr>
                    <td>最终净值</td>
                    <td>${result.get('final_nav', 0):.2f}</td>
                </tr>
"""

        # 添加绩效指标
        if 'total_return' in result:
            html += f"""
                <tr>
                    <td>总收益率</td>
                    <td>{result['total_return']:.2f}%</td>
                </tr>
"""
        if 'annualized_return' in result:
            html += f"""
                <tr>
                    <td>年化收益率</td>
                    <td>{result['annualized_return']:.2f}%</td>
                </tr>
"""
        if 'max_drawdown' in result:
            html += f"""
                <tr>
                    <td>最大回撤</td>
                    <td>{result['max_drawdown']:.2f}%</td>
                </tr>
"""
        if 'sharpe_ratio' in result:
            html += f"""
                <tr>
                    <td>夏普比率</td>
                    <td>{result['sharpe_ratio']:.2f}</td>
                </tr>
"""
        if 'calmar_ratio' in result:
            html += f"""
                <tr>
                    <td>卡尔马比率</td>
                    <td>{result['calmar_ratio']:.2f}</td>
                </tr>
"""
        html += """
            </table>
        </div>

        <div class="section">
            <h2>2. 资金变化</h2>
            <table class="metrics-table">
                <tr>
                    <th>指标</th>
                    <th>数值</th>
                </tr>
                <tr>
                    <td>交易次数</td>
                    <td>{result.get('trade_count', 0)}</td>
                </tr>
            </table>
        </div>

        <div class="disclaimer">
            <h3>免责声明</h3>
            <p>本报告由 PSTDS（个人专用股票交易决策系统）自动生成。</p>
            <p><strong>重要提示：</strong></p>
            <ul>
                <li>投资有风险，入市须谨慎</li>
                <li>本系统不构成任何形式的投资建议</li>
                <li>开发者对投资损失不承担任何责任</li>
                <li>请在充分理解风险的前提下使用本系统</li>
                <li>本报告的任何内容仅供研究参考，不作为投资决策的唯一依据</li>
            </ul>
            <p class="copyright">&copy; 2026 PSTDS - 个人专用股票交易决策系统</p>
        </div>
    </div>
</body>
</html>
"""
        return html

    def _build_analysis_html(self, decision: Dict[str, Any]) -> str:
        """构建分析结果的 HTML 内容"""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>分析报告 - {decision.get('symbol', 'N/A')}</title>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>分析报告</h1>
            <div class="meta">
                <p><strong>股票代码:</strong> {decision.get('symbol', 'N/A')}</p>
                <p><strong>市场类型:</strong> {decision.get('market_type', 'N/A')}</p>
                <p><strong>分析日期:</strong> {decision.get('analysis_date', 'N/A')}</p>
                <p><strong>生成时间:</strong> {datetime.now().strftime('%Y年%m月%d日 %H:%M')}</p>
            </div>
        </div>

        <div class="section">
            <h2>1. 决策信息</h2>
            <table class="metrics-table">
                <tr>
                    <th>字段</th>
                    <th>数值</th>
                </tr>
                <tr>
                    <td>决策</td>
                    <td><strong>{decision.get('action', 'N/A')}</strong></td>
                </tr>
                <tr>
                    <td>置信度</td>
                    <td>{decision.get('confidence', 0):.2f}</td>
                </tr>
                <tr>
                    <td>信心度</td>
                    <td>{decision.get('conviction', 'N/A')}</td>
                </tr>
                <tr>
                    <td>主要理由</td>
                    <td>{decision.get('primary_reason', 'N/A')}</td>
                </tr>
            </table>
        </div>
"""

        # 价格目标
        if decision.get('target_price_low') or decision.get('target_price_high'):
            html += """
        <div class="section">
            <h2>2. 价格目标</h2>
            <table class="metrics-table">
                <tr>
                    <th>字段</th>
                    <th>数值</th>
                </tr>
"""
            if decision.get('target_price_low'):
                html += f"""
                <tr>
                    <td>目标价下限</td>
                    <td>${decision.get('target_price_low', 0):.2f}</td>
                </tr>
"""
            if decision.get('target_price_high'):
                html += f"""
                <tr>
                    <td>目标价上限</td>
                    <td>${decision.get('target_price_high', 0):.2f}</td>
                </tr>
"""
            html += """
            </table>
        </div>
"""

        # 风险因素
        if decision.get('risk_factors'):
            html += """
        <div class="section">
            <h2>3. 风险因素</h2>
            <ul class="risk-list">
"""
            for risk in decision.get('risk_factors', []):
                html += f"<li>{risk}</li>"

            html += """
            </ul>
        </div>
"""

        # 免责声明
        html += """
        <div class="disclaimer">
            <h3>免责声明</h3>
            <p>本报告由 PSTDS（个人专用股票交易决策系统）自动生成。</p>
            <p><strong>重要提示：</strong></p>
            <ul>
                <li>投资有风险，入市须谨慎</li>
                <li>本系统不构成任何形式的投资建议</li>
                <li>开发者对投资损失不承担任何责任</li>
                <li>请在充分理解风险的前提下使用本系统</li>
                <li>本报告的任何内容仅供研究参考，不作为投资决策的唯一依据</li>
            </ul>
            <p class="copyright">&copy; 2026 PSTDS - 个人专用股票交易决策系统</p>
        </div>
    </div>
</body>
</html>
"""
        return html

    def _get_backtest_css(self) -> str:
        """获取回测报告的 CSS 样式"""
        return """
        @page {
            size: A4;
            margin: 2cm;
            font-family: Arial, sans-serif;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
        }
        .header {
            background-color: #f5f5f5;
            padding: 20px;
            border-bottom: 2px solid #ddd;
        }
        .section {
            margin: 30px 0;
        }
        h1 {
            color: #333;
            margin-bottom: 10px;
        }
        h2 {
            color: #555;
            border-bottom: 1px solid #eee;
            padding-bottom: 10px;
        }
        .metrics-table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }
        .metrics-table th,
        .metrics-table td {
            border: 1px solid #ddd;
            padding: 10px;
            text-align: left;
        }
        .metrics-table th {
            background-color: #f0f0f0;
            font-weight: bold;
        }
        .metrics-table tr:nth-child(even) {
            background-color: #f9f9f9;
        }
        .disclaimer {
            background-color: #fff3e0;
            color: white;
            padding: 20px;
            margin: 30px 0;
            border-radius: 5px;
        }
        .disclaimer h3 {
            margin-top: 0;
        }
        .disclaimer ul {
            margin: 10px 0;
        }
        .copyright {
            margin-top: 20px;
            text-align: center;
            font-size: 12px;
        }
        """

    def _get_analysis_css(self) -> str:
        """获取分析报告的 CSS 样式"""
        return """
        @page {
            size: A4;
            margin: 2cm;
            font-family: Arial, sans-serif;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
        }
        .header {
            background-color: #f5f5f5;
            padding: 20px;
            border-bottom: 2px solid #ddd;
        }
        .section {
            margin: 30px 0;
        }
        h1 {
            color: #333;
            margin-bottom: 10px;
        }
        h2 {
            color: #555;
            border-bottom: 1px solid #eee;
            padding-bottom: 10px;
        }
        .metrics-table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }
        .metrics-table th,
        .metrics-table td {
            border: 1px solid #ddd;
            padding: 10px;
            text-align: left;
        }
        .metrics-table th {
            background-color: #f0f0f0;
            font-weight: bold;
        }
        .metrics-table tr:nth-child(even) {
            background-color: #f9f9f9;
        }
        .risk-list {
            list-style-type: square;
            margin-left: 20px;
        }
        .risk-list li {
            margin: 10px 0;
            color: #d32f2f;
        }
        .disclaimer {
            background-color: #fff3e0;
            color: white;
            padding: 20px;
            margin: 30px 0;
            border-radius: 5px;
        }
        .disclaimer h3 {
            margin-top: 0;
        }
        .disclaimer ul {
            margin: 10px 0;
        }
        .copyright {
            margin-top: 20px;
            text-align: center;
            font-size: 12px;
        }
        """
