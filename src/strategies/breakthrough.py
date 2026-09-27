#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
箱体震荡后突破策略
股票在箱体震荡后突破上涨，关注突破后的量价关系
"""

import pandas as pd
import numpy as np
from src.strategies.base_strategy import BaseStrategy
from src.data.stock import get_all_a_stock_codes
from src.backtest.run import run_strategy_backtest

class BoxBreakthroughStrategy(BaseStrategy):
    """
    箱体震荡突破策略
    关注箱体震荡后的突破，以及突破后的量价配合关系
    """

    def __init__(self,
                 box_period=30,           # 箱体计算周期
                 breakout_threshold=0.03, # 突破阈值（3%）
                 volume_threshold=1.5,    # 成交量放大阈值
                 consolidation_threshold=0.05, # 箱体震荡幅度阈值（5%）
                 follow_days=5,           # 突破后观察天数
                 name=None):
        """
        Args:
            box_period: 箱体周期（天）
            breakout_threshold: 突破阈值（价格突破箱体的最小幅度）
            volume_threshold: 突破时成交量放大倍数
            consolidation_threshold: 箱体震荡幅度阈值
            follow_days: 突破后观察量价关系的天数
        """
        super().__init__(name or "BoxBreakthrough")
        self.box_period = box_period
        self.breakout_threshold = breakout_threshold
        self.volume_threshold = volume_threshold
        self.consolidation_threshold = consolidation_threshold
        self.follow_days = follow_days

    def generate_signals(self, data):
        """生成交易信号"""
        df = data.copy()

        # 1. 计算箱体指标
        # 箱体上沿（过去N日最高价，不包含当日）
        df['box_high'] = df['high'].rolling(window=self.box_period).max().shift(1)
        # 箱体下沿（过去N日最低价，不包含当日）
        df['box_low'] = df['low'].rolling(window=self.box_period).min().shift(1)
        # 箱体中轴
        df['box_mid'] = (df['box_high'] + df['box_low']) / 2
        # 箱体幅度
        df['box_range'] = (df['box_high'] - df['box_low']) / df['box_low']

        # 2. 计算价格动量和位置
        # 当前价格相对于箱体的位置
        df['price_position'] = (df['close'] - df['box_low']) / (df['box_high'] - df['box_low'] + 1e-10)
        # 突破强度（相对于箱体上沿）
        df['breakout_strength'] = (df['close'] - df['box_high']) / df['box_high']

        # 3. 计算成交量指标
        # 成交量移动平均
        df['vol_ma_short'] = df['volume'].rolling(window=5).mean()
        df['vol_ma_long'] = df['volume'].rolling(window=10).mean()
        # 成交量比率
        df['vol_ratio_short'] = df['volume'] / df['vol_ma_short']
        df['vol_ratio_long'] = df['volume'] / df['vol_ma_long']

        # 4. 计算价格动量
        df['price_change'] = df['close'].pct_change()
        df['price_change_3d'] = df['close'].pct_change(3)
        df['price_change_5d'] = df['close'].pct_change(5)

        # 6. 计算箱体震荡时间
        # 连续在箱体内运行的天数
        df['in_box'] = (df['close'] <= df['box_high']) & (df['close'] >= df['box_low'])
        df['box_days'] = self._count_consecutive_days(df['in_box'])

        # 7. 突破后的量价关系分析
        # 计算突破后N天的平均成交量比率
        df['post_breakout_vol_avg'] = df['vol_ratio_short'].rolling(window=self.follow_days).mean().shift(-self.follow_days)
        # 计算突破后N天的价格涨幅
        df['post_breakout_return'] = df['close'].pct_change(self.follow_days).shift(-self.follow_days)

        # 8. 主要突破买入信号
        breakthrough_buy = (
            # 价格有效突破箱体上沿
            #(df['breakout_strength'] >= self.breakout_threshold) &
            (df['breakout_strength'] >= 0.01) &


            # 成交量放大确认突破
            #(df['vol_ratio_short'] >= self.volume_threshold) &

            # 箱体震荡充分（幅度适中，时间足够）
            (df['box_range'] >= 0.01) &
            (df['box_range'] <= 0.25) &  # 箱体幅度5%-25%
            # (df['box_days'] >= 10) &  # 箱体震荡至少10天

            # 突破时价格动量良好
            (df['price_change'] > 0) &
            (df['price_change_3d'] > -0.03) &  # 3日跌幅不超过3%

            # 技术位置合理
            (df['price_position'] >= 0.01)  # 突破时价格在箱体上部80%以上
        )

        # 9. 增强版突破信号（更严格的量价配合）
        enhanced_breakthrough = (
            breakthrough_buy &
            # 突破时成交量创近期新高
            (df['volume'] >= df['volume'].rolling(window=20).max().shift(1) * 0.8) &
            # 突破后预期量价配合良好（通过历史数据验证）
            (df['post_breakout_vol_avg'].shift(self.follow_days) >= 1.2) &
            (df['post_breakout_return'].shift(self.follow_days) >= 0.02)
        )

        # 10. 卖出信号
        breakthrough_sell = (
            # 价格跌破箱体下沿（突破失败）
            (df['close'] < df['box_low'] * 0.97) |

            # 突破后快速回落到箱体内（假突破）
            ((df['breakout_strength'].shift(1) > 0) &
             (df['close'] < df['box_high'].shift(1)) &
             (df['vol_ratio_short'] < 1.0)) |

            # 放量下跌（主力出货）
            ((df['vol_ratio_short'] >= 1.5) &
             (df['price_change'] < -0.03)) |
            #  (df['main_intensity'] < -0.02)) |

            # 跌破重要均线
            (df['close'] < df['close'].rolling(window=20).mean() * 0.95)
        )

        # 11. 生成信号
        df['signal'] = 0
        df['signal_level'] = 0

        # 基础突破信号（C级）
        df.loc[breakthrough_buy, 'signal'] = 1
        df.loc[breakthrough_buy, 'signal_level'] = 3

        # 增强突破信号（B级）
        df.loc[enhanced_breakthrough, 'signal'] = 1
        df.loc[enhanced_breakthrough, 'signal_level'] = 2

        # 卖出信号
        df.loc[breakthrough_sell, 'signal'] = -1
        df.loc[breakthrough_sell, 'signal_level'] = -3

        # 移除NaN值
        df = df.dropna()

        return df[[
            'signal',
            'signal_level',
            'breakout_strength',
            'vol_ratio_short',
            'vol_ratio_long',
            'box_range',
            'box_days',
            'price_position',
            'post_breakout_vol_avg',
            'post_breakout_return'
        ]]

    def _count_consecutive_days(self, condition):
        """计算连续满足条件的天数"""
        result = pd.Series(0, index=condition.index)
        count = 0

        for i in range(len(condition)):
            if condition.iloc[i]:
                count += 1
                result.iloc[i] = count
            else:
                count = 0
                result.iloc[i] = 0

        return result

def run(args: any) -> any:
    print("🚀 箱体突破策略回测系统启动...")
    
    # 策略参数
    strategy = BoxBreakthroughStrategy(
        box_period=30,           # 30天箱体
        consolidation_threshold=0.25, # 放宽到25%震荡幅度
        volume_threshold=1.5     # 1.5倍放量
    )

    try:
        buy_stocks = []
        if hasattr(args, 'stock') and args.stock == "all":
            stock_codes = get_all_a_stock_codes()
        elif hasattr(args, 'stock'):
            stock_codes = [args.stock]
        else:
            # 默认 fallback
            stock_codes = ["sh.600000"] 
        
        for stock_code in stock_codes:
            # 调用回测，传入自定义策略
            buy_signal = run_strategy_backtest(
                stock_code, args.start, args.end, len(stock_codes) == 1,
                strategy=strategy
            )

            if buy_signal:
                buy_stocks.append(stock_code)

        print(f"🎉 股票{buy_stocks}符合突破条件")
            
    except Exception as e:
        print(f"❌ 回测失败: {str(e)}")
        import traceback
        traceback.print_exc()
