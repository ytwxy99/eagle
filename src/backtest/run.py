from src.data.stock import get_stock_data
from src.strategies.low_point_main_force_strategy import LowPointMainForceStrategy
from src.backtest.engine import BacktestEngine


def run_strategy_backtest(stock_code, start_date, end_date=None, strategy_params=None):
    """运行策略回测"""
    data = None
    try:
        data = get_stock_data(stock_code, start_date, end_date)
    except ValueError as e:
        return False
        
    # 创建策略 - 使用近期低点主力吸筹策略
    strategy = LowPointMainForceStrategy(
        low_period=20,
        volume_ma_period=10
    )
    
    # 生成信号
    signals = strategy.generate_signals(data[['open', 'high', 'low', 'close', 'volume']])
    try:
        if signals.tail(1)['signal'].values[0] == 1:
            #signals.to_csv('/Users/bytedance/Desktop/dessignals_output.csv', index=True)
            # # 运行回测
            # engine = BacktestEngine(initial_capital=100000, commission=0.001, slippage=0.001)
            # results, detailed_data = engine.run_backtest(data, signals)
    
            # # 获取交易记录
            # trades = engine.get_trade_log()
            # return results, detailed_data, trades

            # chart_path = create_enhanced_trading_chart(
            #    data, trades, detailed_data, stock_code, results, start_date, end_date
            # )
            # print(f"\n🎉 回测完成！图表已保存到: {chart_path}")

            #TODO(shawn), 这里可以添加回测结果，用于评估回测概率
            probability_gt_5_percent, total_signals, average_max_gain = analyze_signal_performance(signals, stock_code, data, start_date, end_date)
            if probability_gt_5_percent >= 0.8:
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
        return
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
            
    if gains:
        total_signals = len(gains)
        average_max_gain = sum(gains) / total_signals
        probability_gt_5_percent = success_count / total_signals
        
    return probability_gt_5_percent, total_signals, average_max_gain
    
    
    