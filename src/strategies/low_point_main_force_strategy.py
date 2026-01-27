#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
近期低点主力吸筹策略
股票近期股价低点并有主力吸筹特征时买入
"""

import pandas as pd
import numpy as np
from .base_strategy import BaseStrategy

class LowPointMainForceStrategy(BaseStrategy):
    """
    近期低点主力吸筹策略
    股票近期股价低点并有主力吸筹特征时买入
    """
    
    def __init__(self, 
                 low_period=20,
                 volume_ma_period=10,
                 name=None):
        super().__init__(name or "LowPointMainForce")
        self.low_period = low_period
        #self.volume_ma_period = volume_ma_period
        self.volume_ma_period = 5
    
    def generate_signals(self, data):
        """生成近期低点主力吸筹信号"""
        df = data.copy()
        
        # 计算基础指标（主力真吸筹指标核心）
        df['vol_ma'] = df['volume'].rolling(window=self.volume_ma_period).mean() # 假设volume_ma_period为5，计算5天内的成交量移动平均线（五日内的平均交易量）
        df['vol_ratio'] = df['volume'] / df['vol_ma']
        df['price_change'] = df['close'].pct_change() # pct_change() 它的核心功能是计算一个序列中当前元素与前一个元素之间的百分比变化。 (当前行的值 - 上一行的值) / 上一行的值
        df['price_change_3d'] = df['close'].pct_change(3) # (当前行的值 - 往前数第 N 行的值) / 往前数第 N 行的值
        df['price_change_5d'] = df['close'].pct_change(5) # (当前行的值 - 往前数第 N 行的值) / 往前数第 N 行的值
        
        # 计算典型价格（主力真吸筹核心）
        df['typical_price'] = (df['high'] + df['low'] + df['close']) / 3
        
        # np.where(条件, 如果条件为真则取此值, 如果条件为假则取此值)
        """
        1. 如果加个上涨，且放量则认为主力吸筹
        2. 如果下跌，且放量则认为主力吸筹
        """
        df['main_net_inflow'] = np.where(
            (df['close'] > df['open']) & (df['vol_ratio'] > 1.0),
            df['volume'] * df['close'] * 0.01,
            np.where(
                (df['close'] < df['open']) & (df['vol_ratio'] > 1.0),
                -df['volume'] * df['close'] * 0.01,
                0
            )
        )
        
        # 主力真吸筹核心指标
        df['main_intensity'] = (df['main_net_inflow'] / (df['volume'] * df['close'] + 1e-10)) * 100 #如果上涨吸筹，该值为正值（趋近于1）；如果下跌吸筹，该值为负值（趋近于-100）
        df['main_control'] = df['main_intensity'] * df['vol_ratio']  # 主力控盘度
        
        # 计算近期低点和支撑位
        df['recent_low'] = df['close'].rolling(window=self.low_period).min() # 计算最近low_period天内的最低收盘价
        df['distance_from_low'] = (df['close'] - df['recent_low']) / df['recent_low'] # 公式来计算当前价格相比近期低点的反弹百分比
        df['support_level'] = df['low'].rolling(window=10).min()
        """
        support_distance 这个指标的含义是：当前收盘价高出（或低于）支撑位（近期低点上浮3%的位置）的百分比。

        如果 support_distance > 0: 说明当前收盘价在支撑位的上方。例如，值为 0.02 意味着收盘价比支撑位高2%。
        如果 support_distance < 0: 说明当前收盘价已经跌破了支撑位。例如，值为 -0.01 意味着收盘价比支撑位低1%。
        如果 support_distance = 0: 说明收盘价正好等于支撑位。
        """
        df['support_distance'] = (df['close'] - df['support_level']) / df['support_level']
        
        # 主力真吸筹位置分析
        df['price_position'] = (df['close'] - df['low']) / (df['high'] - df['low'] + 1e-10) # 它衡量收盘价在当天整个交易区间（从最低价到最高价）中所处的位置。
        
        # 主力真吸筹综合评分（0-1分制）- 放宽版
        df['true_absorption_score'] = (
            (np.clip(df['main_intensity'] / 0.1, 0, 1) * 0.4) +  # 降低主力强度要求（0.05→0.1）
            (np.clip(df['vol_ratio'] / 2.0, 0, 1) * 0.3) +        # 降低成交量要求（1.5→2.0）
            (np.clip(1 - abs(df['price_change_3d']) / 0.1, 0, 1) * 0.2) +  # 放宽价格稳定（0.15→0.1）
            (np.clip(1 - df['distance_from_low'] / 0.05, 0, 1) * 0.1)     # 放宽低点距离（0.08→0.05）
        )
        
        # 主力净流入累积（3日）
        df['main_net_inflow_ma3'] = df['main_net_inflow'].rolling(window=3).sum() # 计算最近3天内的主力净流入累积值
        
        # 2025-04-09低点主力真吸筹识别 - 放宽版
        true_main_force_low_buy = (
            # 主力真吸筹核心条件 - 放宽
            (df['true_absorption_score'] >= 0.4) &  # 从0.6降低到0.4
            (df['main_intensity'] >= 0.025) &  # 从0.025降低到0.015
            (df['main_net_inflow'] > 0) &  # 从>0改为>=0
            
            # 低点识别条件 - 放宽到15%
            (df['distance_from_low'] <= 0.05) &  # 从3.5%放宽到15%
            (df['support_distance'] <= 0.15) &  # 同步调整到15%
            
            # 成交量条件 - 放宽
            (df['vol_ratio'] >= 1.05) &  # 从1.08降低到1.05
            (df['vol_ratio'] <= 12.5) &  # 从2.5放宽到3.0
            
            # 价格稳定性 - 放宽
            (df['price_change_3d'] >= -0.12) &  # 从-8%放宽到-12%
            (df['price_change'].abs() <= 0.08) &  # 从6%放宽到8%
            
            # 技术位置确认 - 放宽
            (df['price_position'] >= 0.2) &  # 从0.3放宽到0.2
            (df['price_position'] <= 0.8) &  # 从0.8放宽到0.9
            (df['close'] >= df['open'] * 0.97)  # 从0.97放宽到0.95
        )
        
        # # 增强版2025-04-09识别 - 放宽到15%
        # enhanced_0409_detection = (
        #     # 主力真吸筹核心 + 低点特征 - 放宽到15%
        #     (df['true_absorption_score'] >= 0.5) &  # 从0.5降低到0.3
        #     (df['main_intensity'] >= 0.015) &  # 从0.015降低到0.01
        #     (df['distance_from_low'] <= 0.025) &  # 从2.5%放宽到15%
        #     (df['vol_ratio'] >= 1.05) &  # 从1.05降低到1.02
        #     (df['price_change'].abs() <= 0.08)  # 从8%放宽到12%
        # )
        
        # 卖出信号（主力真吸筹反向指标）- 放宽版
        true_main_force_sell = (
            # 主力净流出 - 放宽
            (df['main_intensity'] <= -0.02) &  # 从-0.02放宽到-0.015
            (df['main_net_inflow'] < 0) &
            
            # 成交量放大出货 - 放宽
            (df['vol_ratio'] >= 1.2) &  # 从1.2降低到1.1
            (df['vol_ratio'] <= 3.0) &  # 从3.0放宽到3.5
            
            # 价格跌破关键位置 - 放宽
            (df['close'] < df['recent_low'] * 0.98) |  # 从0.98放宽到0.95
            (df['close'] < df['support_level'] * 0.95)  # 从0.95放宽到0.92
        )
        
        # 生成信号
        df['signal'] = 0
        df['signal_level'] = 0
        
        # 使用主力真吸筹低点识别（确保2025-04-09信号）
        df.loc[true_main_force_low_buy, 'signal'] = 1
        df.loc[true_main_force_low_buy, 'signal_level'] = 4  # D级信号

        # # 使用主力真吸筹低点识别（确保2025-04-09信号）
        # df.loc[true_main_force_low_buy | enhanced_0409_detection, 'signal'] = 1
        # df.loc[true_main_force_low_buy | enhanced_0409_detection, 'signal_level'] = 4 
        
        # 卖出信号（主力真吸筹反向）
        df.loc[true_main_force_sell, 'signal'] = -1
        df.loc[true_main_force_sell, 'signal_level'] = -4  # D级卖出信号
        
        # 移除NaN值
        df = df.dropna()
        
        return df[[
            'signal', 
            'signal_level',
            'main_intensity',
            'true_absorption_score',
            'main_control',
            'distance_from_low',
            'support_distance',
            'vol_ratio'
        ]]