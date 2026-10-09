"""终端控制台图表渲染（plotext）

替代 matplotlib 生成 PNG 的方式，直接在终端（iTerm2 等）中用字符绘制图表。
"""

import pandas as pd
import plotext as plt

INITIAL_CAPITAL = 100000


def _new_figure(width, height, title):
    """开始一个新图表"""
    plt.clf()
    plt.limit_size(False)  # 允许图表超出终端窗口高度（可滚动查看）
    try:
        plt.theme('clear')
    except Exception:
        pass
    plt.plot_size(width, height)
    if title:
        plt.title(title)


def _plot_series(series, color, label):
    """按整数 x 坐标绘制序列，自动跳过 NaN（braille 点阵线型）"""
    valid = series.notna()
    xs = [i for i, v in enumerate(valid) if v]
    plt.plot(xs, series[valid].tolist(), marker='braille', color=color, label=label)


def _date_positions(dates_index, trade_dates):
    """将交易日期映射到整数 x 坐标"""
    date_to_idx = {pd.Timestamp(ts): i for i, ts in enumerate(pd.to_datetime(dates_index))}
    positions = []
    for d in trade_dates:
        ts = pd.Timestamp(d)
        if ts in date_to_idx:
            positions.append(date_to_idx[ts])
    return positions


def _pair_trades(trades):
    """将 BUY/SELL 顺序配对，返回 [(买入日, 买价, 卖出日, 卖价, 收益率%)]"""
    pairs = []
    if trades is None or trades.empty:
        return pairs
    buy = None
    for _, t in trades.sort_values('date').iterrows():
        if t['type'] == 'BUY':
            buy = t
        elif t['type'] == 'SELL' and buy is not None:
            pnl_pct = (t['price'] - buy['price']) / buy['price'] * 100
            pairs.append((buy['date'], buy['price'], t['date'], t['price'], pnl_pct))
            buy = None
    return pairs


def create_terminal_trading_chart(data, trades, detailed_data, stock_code, results, start_date, end_date):
    """在终端直接绘制交易分析图：价格+MA20+买卖点 / 成交量 / 主力真吸货指标 / 策略资产曲线"""
    data = data.copy()
    data['ma20'] = data['close'].rolling(window=20).mean()

    dates = pd.to_datetime(data.index)
    x = list(range(len(data)))
    date_labels = [ts.strftime('%m-%d') for ts in dates]
    step = max(1, len(x) // 8)
    tick_pos = x[::step]
    tick_lab = date_labels[::step]

    width = plt.terminal_width() or 100
    width = min(width - 2, 120)
    has_indicator = 'main_force_indicator' in detailed_data.columns
    title = f"{stock_code} 交易分析 ({start_date} ~ {end_date or '至今'})"

    # 1. 价格 + MA20 + 买卖点
    _new_figure(width, 18, title)
    _plot_series(data['close'], 'white', '收盘价')
    _plot_series(data['ma20'], 'orange', 'MA20')

    if trades is not None and not trades.empty:
        buy_trades = trades[trades['type'] == 'BUY']
        sell_trades = trades[trades['type'] == 'SELL']
        buy_pos = _date_positions(dates, buy_trades['date'])
        sell_pos = _date_positions(dates, sell_trades['date'])
        if buy_pos:
            plt.scatter(buy_pos, buy_trades['price'].tolist()[:len(buy_pos)],
                        marker='▲', color='red', label='买入')
        if sell_pos:
            plt.scatter(sell_pos, sell_trades['price'].tolist()[:len(sell_pos)],
                        marker='▼', color='green', label='卖出')
    plt.ylabel('股价(¥)')
    plt.xticks(tick_pos, tick_lab)
    plt.show()

    # 2. 成交量
    _new_figure(width, 10, '成交量')
    plt.bar(x, data['volume'].tolist(), color='cyan', label='成交量')
    plt.xticks(tick_pos, tick_lab)
    plt.show()

    # 3. 同花顺主力真吸货指标
    if has_indicator:
        _new_figure(width, 10, '主力真吸货指标')
        _plot_series(detailed_data['main_force_indicator'], 'purple', '主力真吸货')
        plt.hline(50, color='red')
        plt.hline(0, color='gray')
        plt.hline(-50, color='green')
        plt.xticks(tick_pos, tick_lab)
        plt.show()

    # 4. 策略资产曲线
    _new_figure(width, 10, '策略资产曲线')
    _plot_series(detailed_data['portfolio_value'], 'blue', '策略资产')
    plt.hline(INITIAL_CAPITAL, color='gray')
    plt.xticks(tick_pos, tick_lab)
    plt.show()

    # ---- 文本形式的交易记录与回测统计 ----
    pairs = _pair_trades(trades)
    if pairs:
        print("\n📊 交易记录:")
        for i, (bd, bp, sd, sp, pct) in enumerate(pairs, 1):
            bd_s = pd.Timestamp(bd).strftime('%Y-%m-%d')
            sd_s = pd.Timestamp(sd).strftime('%Y-%m-%d')
            print(f"   T{i:<3} 买入 {bd_s} @¥{bp:.2f}  卖出 {sd_s} @¥{sp:.2f}  收益率 {pct:+.2f}%")

    final_value = detailed_data['portfolio_value'].iloc[-1]
    total_return = (final_value - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
    total_trades = len(trades) // 2 if trades is not None else 0
    print("\n📈 回测统计:")
    print(f"   股票代码: {stock_code}   回测期间: {start_date} ~ {end_date or '至今'}")
    print(f"   初始资金: ¥{INITIAL_CAPITAL:,}   最终资产: ¥{final_value:,.0f}   总收益率: {total_return:+.2f}%")
    print(f"   交易次数: {total_trades}   胜率: {results['win_rate']:.1%}   平均单笔收益: {results['avg_return_per_trade']:+.2%}")
    print(f"   夏普比率: {results['sharpe_ratio']:.2f}   最大回撤: {results['max_drawdown']:.2%}")
