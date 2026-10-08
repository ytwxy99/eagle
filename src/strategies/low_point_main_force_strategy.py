#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主力吸筹突破策略(原"近期低点主力吸筹策略")

买卖点规则:
- 买点: 主力真吸筹指标(main_force_indicator, 同花顺流传公式日线移植,
  值域约[-100,100]) 上穿 +50 的当日收盘买入。
  指标吸筹侧仅在"创34日新低 + 下行缺口放大"时累积, 因此买点天然出现在
  低位恐慌/压盘承接段。
- 卖点(三个, 满足其一即离场):
  1) 指标下穿 -50: 出货强度突破阈值, 与买点对称;
  2) 支撑止损: 收盘 < 前10日最低价 x 0.97。
     必须保留: 出货侧指标只在创34日新高时累积, 慢阴跌永远不会触发它,
     无止损会导致买后阴跌深套;
  3) 最大亏损止损: 收盘 < 买入价 x (1-8%) 强制离场。
     支撑位随价格下移, 连续阴跌永远到不了固定比例的支撑线(结构性盲区),
     锚定成本价的止损不受此影响。
- 持仓规则: 买入后持续持有(signal=1)直到离场日(signal=-1, 仅当日标记)。
  持仓期间指标回落到0不算离场——该指标在VAR5停止上行时天然归零,
  频繁归零是其固有特性, 不能作为离场依据。

信息列(不参与买卖判定): main_intensity(20日CMF)、main_intensity_3d(3日CMF)、
vol_ratio、distance_from_low、true_absorption_score 等, 供图表/分析使用。
"""

import pandas as pd
import numpy as np
from .base_strategy import BaseStrategy, main_force_indicator

class LowPointMainForceStrategy(BaseStrategy):
    """
    主力吸筹突破策略
    吸筹指标上穿50买入; 出货下穿-50 / 跌破支撑 / 成本亏损超8% 任一即离场
    """

    # 信号阈值集中定义, 便于回测调参
    BUY_INDICATOR_CROSS = 50.0    # 主力吸筹指标上穿该值 -> 买入
    SELL_INDICATOR_CROSS = -50.0  # 主力出货指标下穿该值 -> 离场
    SELL_SUPPORT_BREAK = 0.97     # 收盘跌破前10日最低价的97% -> 止损离场
    SELL_MAX_LOSS_PCT = 0.08      # 收盘较买入价亏损超8% -> 强制离场(锚定成本价)

    def __init__(self,
                 low_period=20,
                 volume_ma_period=10,
                 name=None):
        super().__init__(name or "LowPointMainForce")
        self.low_period = low_period              # CMF周期(信息列)
        self.volume_ma_period = volume_ma_period  # 量比基准均量窗口(信息列)

    def generate_signals(self, data):
        """生成主力吸筹突破信号"""
        df = data.copy()

        # ---------- 成交量指标(信息列) ----------
        # 量比 = 当日成交量 / 前volume_ma_period日均量, shift(1)剔除当日
        df['vol_ma'] = df['volume'].rolling(window=self.volume_ma_period).mean().shift(1)
        df['vol_ratio'] = df['volume'] / (df['vol_ma'] + 1e-10)

        df['price_change'] = df['close'].pct_change()
        df['price_change_3d'] = df['close'].pct_change(3)

        # ---------- 主力资金流指标(信息列) ----------
        clv = ((df['close'] - df['low']) - (df['high'] - df['close'])) / \
              (df['high'] - df['low'] + 1e-10)
        df['main_net_inflow'] = clv * df['volume']

        vol_sum_20d = df['volume'].rolling(window=self.low_period).sum() + 1e-10
        vol_sum_3d = df['volume'].rolling(window=3).sum() + 1e-10
        df['main_intensity'] = df['main_net_inflow'].rolling(window=self.low_period).sum() / vol_sum_20d
        df['main_intensity_3d'] = df['main_net_inflow'].rolling(window=3).sum() / vol_sum_3d
        df['main_control'] = df['main_intensity_3d'] * df['vol_ratio']

        # ---------- 位置指标(信息列, support_level同时用于止损) ----------
        df['recent_low'] = df['close'].rolling(window=self.low_period).min()
        df['distance_from_low'] = (df['close'] - df['recent_low']) / (df['recent_low'] + 1e-10)
        # 前10日最低价支撑位(shift(1)剔除当日)
        df['support_level'] = df['low'].rolling(window=10).min().shift(1)
        df['price_position'] = (df['close'] - df['low']) / (df['high'] - df['low'] + 1e-10)

        # 吸筹综合评分(0-1, 信息列)
        df['true_absorption_score'] = (
            (np.clip(df['main_intensity_3d'] / 0.15, 0, 1) * 0.4) +
            (np.clip(df['vol_ratio'] / 2.0, 0, 1) * 0.3) +
            (np.clip(1 - df['price_change_3d'].abs() / 0.1, 0, 1) * 0.2) +
            (np.clip(1 - df['distance_from_low'] / 0.05, 0, 1) * 0.1)
        )

        # 主力真吸筹指标(同花顺流传公式日线移植, 值域约[-100,100])
        df['main_force_indicator'] = main_force_indicator(df)

        # 移除指标预热期产生的NaN(先清理再判信号, 避免预热期产生幽灵买卖点)
        df = df.dropna()

        # ---------- 买点: 吸筹强度上穿 +50 ----------
        ind = df['main_force_indicator']
        prev_ind = ind.shift(1)
        cross_buy = (ind > self.BUY_INDICATOR_CROSS) & (prev_ind <= self.BUY_INDICATOR_CROSS)

        # ---------- 离场候选(无条件项): 出货下穿-50 或 跌破支撑止损 ----------
        exit_base = (
            ((ind < self.SELL_INDICATOR_CROSS) & (prev_ind >= self.SELL_INDICATOR_CROSS)) |
            (df['close'] < df['support_level'] * self.SELL_SUPPORT_BREAK)
        )

        # ---------- 持仓状态机: 逐日循环 ----------
        # 最大亏损止损锚定入场价, 而入场价由持仓状态决定, 无法向量化,
        # 用逐日循环保证严格正确(数据量为日线级别, 性能无压力)
        closes = df['close'].values
        cross_buy_arr = cross_buy.values
        exit_base_arr = exit_base.values
        signal_arr = np.zeros(len(df), dtype=int)

        holding = False
        entry_price = np.nan
        for i in range(len(df)):
            if not holding:
                if cross_buy_arr[i]:
                    if exit_base_arr[i]:
                        continue  # 买入当日即破位/出货, 不建仓
                    holding = True
                    entry_price = closes[i]
                    signal_arr[i] = 1
            else:
                max_loss_hit = closes[i] < entry_price * (1 - self.SELL_MAX_LOSS_PCT)
                if exit_base_arr[i] or max_loss_hit:
                    holding = False
                    entry_price = np.nan
                    signal_arr[i] = -1
                else:
                    signal_arr[i] = 1

        signal = pd.Series(signal_arr, index=df.index)

        df['signal'] = signal
        df['signal_level'] = 0
        df.loc[cross_buy & (signal == 1), 'signal_level'] = 4   # 买入标记日
        df.loc[signal == -1, 'signal_level'] = -4               # 离场标记日

        return df[[
            'signal',
            'signal_level',
            'main_intensity',
            'main_intensity_3d',
            'main_net_inflow',
            'true_absorption_score',
            'main_force_indicator',
            'main_control',
            'distance_from_low',
            'vol_ratio'
        ]]
