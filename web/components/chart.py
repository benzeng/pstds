# web/components/chart.py
# K 线图组件 - Phase 4 Task 5 (P4-T5)
# Plotly 4 层布局（K线+均线、成交量、MACD、RSI）

from typing import Optional
import pandas as pd
import numpy as np

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    go = None
    make_subplots = None

try:
    import pandas_ta as ta
    PANDAS_TA_AVAILABLE = True
except ImportError:
    PANDAS_TA_AVAILABLE = False
    ta = None


def create_candlestick_chart(
    df: pd.DataFrame,
    symbol: str,
    show_volume: bool = True,
    show_ma: bool = True,
    show_macd: bool = True,
    show_rsi: bool = True,
    ma_periods: list = [5, 10, 20, 60],
) -> Optional[object]:
    """
    创建 K 线图

    4 层布局：
    1. K 线 + 均线
    2. 成交量
    3. MACD
    4. RSI

    Args:
        df: OHLCV 数据 DataFrame，包含 ['date', 'open', 'high', 'low', 'close', 'volume'] 列
        symbol: 股票代码
        show_volume: 是否显示成交量
        show_ma: 是否显示均线
        show_macd: 是否显示 MACD
        show_rsi: 是否显示 RSI
        ma_periods: 均线周期列表

    Returns:
        Plotly Figure 对象
    """
    if not PLOTLY_AVAILABLE:
        print("Plotly 未安装，无法创建图表")
        return None

    if df is None or df.empty:
        print("数据为空，无法创建图表")
        return None

    # 确保数据按日期排序
    df = df.sort_values('date').reset_index(drop=True)

    # 添加技术指标
    df = _add_technical_indicators(df, ma_periods)

    # 创建子图
    if show_macd and show_rsi:
        # 4 个子图：K线、成交量、MACD、RSI
        fig = make_subplots(
            rows=4, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.02,
            row_heights=[0.45, 0.15, 0.20, 0.20],
            subplot_titles=("K线图", "成交量", "MACD", "RSI"),
        )
    elif show_macd:
        fig = make_subplots(
            rows=3, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=[0.55, 0.20, 0.25],
            subplot_titles=("K线图", "成交量", "MACD"),
        )
    elif show_rsi:
        fig = make_subplots(
            rows=3, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=[0.55, 0.20, 0.25],
            subplot_titles=("K线图", "成交量", "RSI"),
        )
    else:
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            row_heights=[0.80, 0.20],
            subplot_titles=("K线图", "成交量"),
        )

    # --- 第 1 层：K 线 + 均线 ---
    fig.add_trace(
        go.Candlestick(
            x=df['date'],
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name=symbol,
            increasing_line_color='#26a69a',
            decreasing_line_color='#ef5350',
            showlegend=False,
        ),
        row=1, col=1,
    )

    # 添加均线
    if show_ma and PANDAS_TA_AVAILABLE:
        ma_colors = ['#ff9800', '#2196f3', '#4caf50', '#9c27b0']
        for i, period in enumerate(ma_periods):
            ma_col = f'MA{period}'
            if ma_col in df.columns:
                fig.add_trace(
                    go.Scatter(
                        x=df['date'],
                        y=df[ma_col],
                        mode='lines',
                        name=f'MA{period}',
                        line=dict(color=ma_colors[i % len(ma_colors)], width=1),
                        showlegend=True,
                    ),
                    row=1, col=1,
                )

    # --- 第 2 层：成交量 ---
    if show_volume:
        colors = np.where(
            df['close'] >= df['open'],
            '#26a69a',  # 上涨
            '#ef5350',  # 下跌
        )
        fig.add_trace(
            go.Bar(
                x=df['date'],
                y=df['volume'],
                name='成交量',
                marker_color=colors,
                showlegend=False,
            ),
            row=2 if show_macd or show_rsi else 2, col=1,
        )

    # --- 第 3 层：MACD ---
    if show_macd and 'MACD' in df.columns:
        macd_row = 3  # MACD is always on row 3 when shown
        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=df['MACD'],
                mode='lines',
                name='MACD',
                line=dict(color='#2196f3', width=1),
                showlegend=True,
            ),
            row=macd_row, col=1,
        )

        if 'MACD_signal' in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df['date'],
                    y=df['MACD_signal'],
                    mode='lines',
                    name='Signal',
                    line=dict(color='#ff9800', width=1),
                    showlegend=True,
                ),
                row=macd_row, col=1,
            )

        if 'MACD_hist' in df.columns:
            hist_colors = np.where(df['MACD_hist'] >= 0, '#26a69a', '#ef5350')
            fig.add_trace(
                go.Bar(
                    x=df['date'],
                    y=df['MACD_hist'],
                    name='Histogram',
                    marker_color=hist_colors,
                    showlegend=False,
                ),
                row=macd_row, col=1,
            )

    # --- 第 4 层：RSI ---
    if show_rsi and 'RSI' in df.columns:
        # RSI is on row 3 when MACD not shown, row 4 when MACD is shown
        rsi_row = 4 if show_macd else 3
        # RSI 超买超卖区域
        rsi_70 = [70] * len(df)
        rsi_30 = [30] * len(df)

        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=df['RSI'],
                mode='lines',
                name='RSI',
                line=dict(color='#9c27b0', width=1.5),
                showlegend=True,
            ),
            row=rsi_row, col=1,
        )

        # 添加超买超卖线
        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=rsi_70,
                mode='lines',
                name='Overbought (70)',
                line=dict(color='rgba(239, 83, 80, 0.3)', width=1, dash='dash'),
                showlegend=True,
            ),
            row=rsi_row, col=1,
        )

        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=rsi_30,
                mode='lines',
                name='Oversold (30)',
                line=dict(color='rgba(38, 166, 154, 0.3)', width=1, dash='dash'),
                showlegend=True,
            ),
            row=rsi_row, col=1,
        )

    # 更新布局 - 根据子图数量动态设置
    layout_updates = {
        'title': f'{symbol} K线图',
        'height': 800,
        'showlegend': True,
        'legend': dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
        'hovermode': 'x unified',
    }
    # 只禁用存在的 xaxis 的 rangeslider
    num_rows = 4 if show_macd and show_rsi else (3 if show_macd or show_rsi else 2)
    for i in range(1, num_rows + 1):
        layout_updates[f'xaxis{i}_rangeslider_visible'] = False

    fig.update_layout(**layout_updates)

    # 设置 Y 轴范围
    fig.update_yaxes(title_text="价格", row=1, col=1)
    fig.update_yaxes(title_text="成交量", row=2, col=1)

    if show_macd:
        fig.update_yaxes(title_text="MACD", row=3, col=1)

    if show_rsi:
        rsi_row = 4 if show_macd else 3
        fig.update_yaxes(title_text="RSI", row=rsi_row, col=1)
        fig.update_yaxes(range=[0, 100], row=rsi_row, col=1)

    return fig


def _add_technical_indicators(df: pd.DataFrame, ma_periods: list) -> pd.DataFrame:
    """
    添加技术指标

    Args:
        df: 原始 OHLCV 数据
        ma_periods: 均线周期列表

    Returns:
        添加了技术指标的 DataFrame
    """
    df = df.copy()

    if PANDAS_TA_AVAILABLE:
        # 计算均线
        for period in ma_periods:
            ma_col = f'MA{period}'
            if len(df) >= period:
                df[ma_col] = ta.sma(df['close'], length=period)

        # 计算 MACD
        if len(df) >= 26:
            macd_df = ta.macd(df['close'], fast=12, slow=26, signal=9)
            if macd_df is not None and not macd_df.empty:
                # 获取实际的列名（pandas_ta 返回: MACD_12_26_9, MACDs_12_26_9, MACDh_12_26_9）
                macd_cols = [c for c in macd_df.columns if c == 'MACD_12_26_9' or (c.startswith('MACD') and 'h' not in c and 's' not in c)]
                if macd_cols:
                    df['MACD'] = macd_df[macd_cols[0]]
                signal_cols = [c for c in macd_df.columns if 'MACDs' in c or 'signal' in c.lower()]
                if signal_cols:
                    df['MACD_signal'] = macd_df[signal_cols[0]]
                hist_cols = [c for c in macd_df.columns if 'MACDh' in c or 'hist' in c.lower()]
                if hist_cols:
                    df['MACD_hist'] = macd_df[hist_cols[0]]

        # 计算 RSI
        if len(df) >= 14:
            rsi_series = ta.rsi(df['close'], length=14)
            if rsi_series is not None:
                df['RSI'] = rsi_series
    else:
        # 如果 pandas-ta 不可用，使用简化计算
        for period in ma_periods:
            ma_col = f'MA{period}'
            if len(df) >= period:
                df[ma_col] = df['close'].rolling(window=period).mean()

        if len(df) >= 26:
            ema_fast = df['close'].ewm(span=12).mean()
            ema_slow = df['close'].ewm(span=26).mean()
            df['MACD'] = ema_fast - ema_slow
            df['MACD_signal'] = df['MACD'].ewm(span=9).mean()
            df['MACD_hist'] = df['MACD'] - df['MACD_signal']

        if len(df) >= 15:
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))

    return df


def create_simple_line_chart(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: str = "",
    color: str = "#2196f3",
) -> Optional[object]:
    """
    创建简单折线图

    Args:
        df: 数据 DataFrame
        x_col: X 轴列名
        y_col: Y 轴列名
        title: 图表标题
        color: 线条颜色

    Returns:
        Plotly Figure 对象
    """
    if not PLOTLY_AVAILABLE:
        return None

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df[x_col],
            y=df[y_col],
            mode='lines',
            name=y_col,
            line=dict(color=color, width=2),
        )
    )

    fig.update_layout(
        title=title,
        xaxis_title=x_col,
        yaxis_title=y_col,
        height=400,
    )

    return fig
