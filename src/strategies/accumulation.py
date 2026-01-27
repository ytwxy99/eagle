from src.data.stock import get_all_a_stock_codes
from src.backtest.run import run_strategy_backtest

def run(args: any) -> any:
    print("🚀 增强版主力吸货策略回测系统启动...")
        
    # 策略参数
    strategy_params = {
        'low_period': 20,
        'volume_ma_period': 10
    }   

    try:
        buy_stocks = []
        if args.stock == "all":
            stock_codes = get_all_a_stock_codes()
        else:
            stock_codes = [args.stock]
        
        for stock_code in stock_codes:
            buy_signal = run_strategy_backtest(
                stock_code, args.start, args.end, strategy_params
            )

            if buy_signal:
                buy_stocks.append(stock_code)

        print(f"🎉 股票{buy_stocks}符合吸货条件")
            
    except Exception as e:
        print(f"❌ 回测失败: {str(e)}")
        import traceback
        traceback.print_exc()