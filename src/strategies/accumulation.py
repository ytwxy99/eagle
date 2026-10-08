from src.data.stock import get_all_a_stock_codes
from src.backtest.run import run_strategy_backtest
from src.strategies.low_point_main_force_strategy import LowPointMainForceStrategy

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
        
        for stock_code in stock_codes:
            buy_signal = run_strategy_backtest(
                stock_code, args.start, args.end, len(stock_codes) == 1, strategy,
                terminal_chart=not args.save_image
            )

            if buy_signal:
                buy_stocks.append(stock_code)

        print(f"🎉 股票{buy_stocks}符合吸货条件")
            
    except Exception as e:
        print(f"❌ 回测失败: {str(e)}")
        import traceback
        traceback.print_exc()