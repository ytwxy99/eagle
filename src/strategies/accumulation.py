from src.data.stock import get_all_a_stock_codes
from src.backtest.run import run_strategy_backtest
from src.strategies.low_point_main_force_strategy import LowPointMainForceStrategy

SUCCESS_RATE_THRESHOLD = 0.8  # 成功率达标阈值, 与"符合吸货条件"一致

def print_signal_summary(signal_stats):
    """全市场扫描时, 将今日新触发买点且成功率达标的股票汇总为按成功率排序的表格"""
    qualified = [s for s in signal_stats if s['probability'] >= SUCCESS_RATE_THRESHOLD]
    if not qualified:
        print(f"\n📊 信号汇总: 今日新触发买点共{len(signal_stats)}只, 其中成功率≥80%的 0 只")
        return

    qualified.sort(key=lambda s: (s['probability'], s['avg_gain']), reverse=True)
    print(f"\n📊 信号汇总 (今日新触发买点{len(signal_stats)}只, 达标{len(qualified)}只, 按成功率降序):")
    print("排名  股票代码  信号数  平均5日内最大涨幅  成功率")
    for i, s in enumerate(qualified, 1):
        avg = f"{s['avg_gain']:+.2%}"
        rate = f"{s['probability']:.2%}"
        print(f"{i:<6}{s['stock']:<10}{s['signals']:<8}{avg:<19}{rate}")

def run(args: any) -> any:
    print("🚀 增强版主力吸货策略回测系统启动...")
    strategy = LowPointMainForceStrategy(
            low_period=20,
            volume_ma_period=10
    )

    try:
        buy_stocks = []
        if args.stock == "all":
            stock_codes = get_all_a_stock_codes()
        else:
            stock_codes = [args.stock]

        is_scan = len(stock_codes) > 1
        signal_stats = [] if is_scan else None

        for stock_code in stock_codes:
            buy_signal = run_strategy_backtest(
                stock_code, args.start, args.end, not is_scan, strategy,
                terminal_chart=not args.save_image,
                signal_stats=signal_stats
            )

            if buy_signal:
                buy_stocks.append(stock_code)

        if is_scan:
            print_signal_summary(signal_stats)

        print(f"🎉 股票{buy_stocks}符合吸货条件")

    except Exception as e:
        print(f"❌ 回测失败: {str(e)}")
        import traceback
        traceback.print_exc()
