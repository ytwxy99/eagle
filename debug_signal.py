#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试信号生成问题
"""

import pandas as pd
import numpy as np
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 直接导入策略
from src.strategies.main_force_strategy import EnhancedMainForceStrategy

def create_test_data():
    """创建测试数据"""
    dates = pd.date_range('2024-08-01', '2024-08-26', freq='D')
    
    # 创建有主力吸筹特征的数据
    np.random.seed(42)
    base_price = 10.0
    
    data = pd.DataFrame({
        'open': [base_price + i*0.1 + np.random.normal(0, 0.1) for i in range(len(dates))],
        'high': [base_price + i*0.12 + np.random.normal(0, 0.15) for i in range(len(dates))],
        'low': [base_price + i*0.08 + np.random.normal(0, 0.15) for i in range(len(dates))],
        'close': [base_price + i*0.11 + np.random.normal(0, 0.1) for i in range(len(dates))],
        'volume': [1000000 + np.random.randint(500000, 2000000) for i in range(len(dates))]
    }, index=dates)
    
    # 确保数据合理性
    for i in range(len(data)):
        data.loc[data.index[i], 'high'] = max(data.loc[data.index[i], 'open'], 
                                               data.loc[data.index[i], 'close'], 
                                               data.loc[data.index[i], 'high'])
        data.loc[data.index[i], 'low'] = min(data.loc[data.index[i], 'open'], 
                                              data.loc[data.index[i], 'close'], 
                                              data.loc[data.index[i], 'low'])
    
    # 创建主力吸筹特征：某天成交量放大
    data.loc[data.index[10], 'volume'] = data.loc[data.index[10], 'volume'] * 3
    data.loc[data.index[11], 'volume'] = data.loc[data.index[11], 'volume'] * 2.5
    data.loc[data.index[12], 'volume'] = data.loc[data.index[12], 'volume'] * 2
    
    return data

def debug_signal_generation():
    """调试信号生成"""
    print("🔍 开始调试信号生成...")
    
    # 创建测试数据
    data = create_test_data()
    print(f"📊 测试数据条数: {len(data)}")
    
    # 创建策略
    strategy = EnhancedMainForceStrategy(
        short_period=3,
        medium_period=5,
        long_period=10,
        volume_threshold=1.8
    )
    
    # 生成信号
    signals = strategy.generate_signals(data)
    
    print(f"📈 生成信号条数: {len(signals)}")
    print(f"🎯 买入信号: {(signals['signal'] == 1).sum()}")
    print(f"📉 卖出信号: {(signals['signal'] == -1).sum()}")
    print(f"➖ 无信号: {(signals['signal'] == 0).sum()}")
    
    # 显示详细信息
    print("\n📊 信号统计:")
    print(signals['signal'].value_counts())
    
    # 显示中间计算结果
    print("\n🔍 中间变量检查:")
    print("成交量比率范围:", signals['vol_ratio_10'].min(), "-", signals['vol_ratio_10'].max())
    print("主力指标范围:", signals['main_force_indicator'].min(), "-", signals['main_force_indicator'].max())
    
    # 显示前几行数据
    print("\n📊 前5行数据:")
    print(signals.head())
    
    # 显示有信号的行
    signal_rows = signals[signals['signal'] != 0]
    if len(signal_rows) > 0:
        print(f"\n✅ 找到 {len(signal_rows)} 个信号:")
        print(signal_rows)
    else:
        print("\n⚠️  没有找到信号，检查条件:")
        # 检查中间变量
        print("成交量比率 > 1.2 的数量:", (signals['vol_ratio_10'] > 1.2).sum())
        print("主力净流入 > 0 的数量:", (signals['main_net_indicator'] > 0).sum())
        print("主力指标 > 0 的数量:", (signals['main_force_indicator'] > 0).sum())
    
    return signals

if __name__ == "__main__":
    signals = debug_signal_generation()
    print("\n✅ 调试完成")
