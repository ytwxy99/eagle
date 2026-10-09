from src.data.stock import get_stock_data
from src.backtest.engine import BacktestEngine
from src.utils.chart import create_enhanced_trading_chart
from src.utils.term_chart import create_terminal_trading_chart


def run_strategy_backtest(stock_code, start_date, end_date=None, backtest=False, strategy=None, terminal_chart=False, signal_stats=None):
    """运行策略回测

    terminal_chart=True 时直接在终端控制台绘制图表（不生成 PNG 文件）
    signal_stats 传入 list 时收集信号统计供调用方汇总（全市场扫描模式），None 时保持原有单股输出
    """
    data = None
    try:
        data = get_stock_data(stock_code, start_date, end_date)
    except ValueError as e:
        print(f"⚠️ {e}")
        return False
    
    # 生成信号
    signals = strategy.generate_signals(data[['open', 'high', 'low', 'close', 'volume']])
    try:
        if backtest:
            # 运行回测
            engine = BacktestEngine(initial_capital=100000, commission=0.001, slippage=0.001)
            results, detailed_data = engine.run_backtest(data, signals)
    
            # 获取交易记录
            trades = engine.get_trade_log()
            if terminal_chart:
                create_terminal_trading_chart(
                    data, trades, detailed_data, stock_code, results, start_date, end_date
                )
            else:
                chart_path = create_enhanced_trading_chart(
                    data, trades, detailed_data, stock_code, results, start_date, end_date
                )
                print(f"\n🎉 回测完成！图表已保存到: {chart_path}")
                
        # 今日新触发买点: 今日建仓(signal==1)且昨日非持仓
        # (区别于过去买入后一直持仓中的股票, 后者不参与"符合吸货条件"筛选)
        last_two = signals.tail(2)['signal'].values
        if len(last_two) == 2 and last_two[-1] == 1 and last_two[-2] != 1:

            #TODO(shawn), 这里可以添加回测结果，用于评估回测概率
            probability_gt_5_percent, total_signals, average_max_gain = analyze_signal_performance(signals, stock_code, data, start_date, end_date)

            # 全市场扫描时收集统计(由调用方汇总成表), 单股模式保持原有输出
            if signal_stats is not None:
                signal_stats.append({
                    'stock': stock_code,
                    'signals': total_signals,
                    'avg_gain': average_max_gain,
                    'probability': probability_gt_5_percent,
                })

            if probability_gt_5_percent >= 0.8:
                if signal_stats is None:
                    print(f"----------------------------------------------------------")
                    print(f"股票{stock_code}在 {start_date} 到 {end_date} 之间的回测概率超过80%")
                    print(f"历史买入信号总数: {total_signals}")
                    print(f"信号后 5 日内平均最大涨幅: {average_max_gain:.2%}")
                    print(f"信号后 5 日内涨幅大于5%的概率: {probability_gt_5_percent:.2%}")
                    print(f"----------------------------------------------------------")

                return True
            
    except IndexError:
        print(f"⚠️ 股票{stock_code}信号生成失败")

    return False


def analyze_signal_performance(signals, stock_code, stock_data, start_date, end_date, forward_days = 5):
    """
    分析策略在单个股票上的历史信号表现。
    """    
    buy_signals = signals[signals['signal'] == 1]

    if buy_signals.empty:
        return 0.0, 0, 0.0
    gains = []
    success_count = 0  # 涨幅超过5%的次数

    for signal_date in buy_signals.index:
        try:
            signal_idx = stock_data.index.get_loc(signal_date)
        except KeyError:
            continue

        # 定义信号日之后5个交易日的窗口
        window_end_idx = min(signal_idx + 1 + forward_days, len(stock_data))
        future_window = stock_data.iloc[signal_idx + 1 : window_end_idx]

        if future_window.empty:
            continue

        signal_day_close = stock_data.loc[signal_date]['close']
        max_high_in_window = future_window['high'].max()
        max_gain = (max_high_in_window - signal_day_close) / signal_day_close
        gains.append(max_gain)

        if max_gain > 0.02:
            success_count += 1
            
    if not gains:
        return 0.0, 0, 0.0

    total_signals = len(gains)
    average_max_gain = sum(gains) / total_signals
    probability_gt_5_percent = success_count / total_signals

    return probability_gt_5_percent, total_signals, average_max_gain
    
    
    
