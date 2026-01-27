import pandas as pd
import numpy as np
from .base_strategy import BaseStrategy

class MovingAverageStrategy(BaseStrategy):
    """移动平均线策略"""
    
    def __init__(self, short_window=20, long_window=50, name=None):
        super().__init__(name or f"MA_{short_window}_{long_window}")
        self.short_window = short_window
        self.long_window = long_window
    
    def generate_signals(self, data):
        """
        生成移动平均线交易信号
        
        Args:
            data: DataFrame包含价格数据，必须有'close'列
            
        Returns:
            DataFrame包含信号列
        """
        if 'close' not in data.columns:
            raise ValueError("数据必须包含'close'列")
        
        df = data.copy()
        
        # 计算移动平均线
        df['short_ma'] = df['close'].rolling(window=self.short_window).mean()
        df['long_ma'] = df['close'].rolling(window=self.long_window).mean()
        
        # 生成信号
        df['signal'] = 0
        df.loc[df['short_ma'] > df['long_ma'], 'signal'] = 1
        df.loc[df['short_ma'] < df['long_ma'], 'signal'] = -1
        
        # 移除NaN值
        df = df.dropna()
        
        return df[['signal', 'short_ma', 'long_ma']]

class DualThrustStrategy(BaseStrategy):
    """Dual Thrust策略"""
    
    def __init__(self, k1=0.5, k2=0.5, n=4, name=None):
        super().__init__(name or f"DualThrust_{k1}_{k2}_{n}")
        self.k1 = k1
        self.k2 = k2
        self.n = n
    
    def generate_signals(self, data):
        """
        生成Dual Thrust交易信号
        
        Args:
            data: DataFrame包含价格数据，必须有'high', 'low', 'close', 'open'列
        """
        required_cols = ['high', 'low', 'close', 'open']
        if not all(col in data.columns for col in required_cols):
            raise ValueError(f"数据必须包含{required_cols}列")
        
        df = data.copy()
        
        # 计算前n天的范围
        df['hh'] = df['high'].rolling(window=self.n).max()
        df['ll'] = df['low'].rolling(window=self.n).min()
        df['hc'] = df['close'].rolling(window=self.n).max()
        df['lc'] = df['close'].rolling(window=self.n).min()
        
        # 计算范围
        df['range'] = np.maximum(df['hh'] - df['lc'], df['hc'] - df['ll'])
        
        # 计算买入和卖出线
        df['buy_line'] = df['open'] + self.k1 * df['range'].shift(1)
        df['sell_line'] = df['open'] - self.k2 * df['range'].shift(1)
        
        # 生成信号
        df['signal'] = 0
        df.loc[df['close'] > df['buy_line'], 'signal'] = 1
        df.loc[df['close'] < df['sell_line'], 'signal'] = -1
        
        # 移除NaN值
        df = df.dropna()
        
        return df[['signal', 'buy_line', 'sell_line']]

class RSIStrategy(BaseStrategy):
    """RSI策略"""
    
    def __init__(self, rsi_period=14, oversold=30, overbought=70, name=None):
        super().__init__(name or f"RSI_{rsi_period}_{oversold}_{overbought}")
        self.rsi_period = rsi_period
        self.oversold = oversold
        self.overbought = overbought
    
    def calculate_rsi(self, prices, period=14):
        """计算RSI指标"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def generate_signals(self, data):
        """
        生成RSI交易信号
        
        Args:
            data: DataFrame包含价格数据，必须有'close'列
        """
        if 'close' not in data.columns:
            raise ValueError("数据必须包含'close'列")
        
        df = data.copy()
        
        # 计算RSI
        df['rsi'] = self.calculate_rsi(df['close'], self.rsi_period)
        
        # 生成信号
        df['signal'] = 0
        
        # 超卖买入
        df.loc[df['rsi'] < self.oversold, 'signal'] = 1
        
        # 超买卖出
        df.loc[df['rsi'] > self.overbought, 'signal'] = -1
        
        # 移除NaN值
        df = df.dropna()
        
        return df[['signal', 'rsi']]

class MACDStrategy(BaseStrategy):
    """MACD策略"""
    
    def __init__(self, fast=12, slow=26, signal=9, name=None):
        super().__init__(name or f"MACD_{fast}_{slow}_{signal}")
        self.fast = fast
        self.slow = slow
        self.signal = signal
    
    def calculate_macd(self, prices):
        """计算MACD指标"""
        ema_fast = prices.ewm(span=self.fast).mean()
        ema_slow = prices.ewm(span=self.slow).mean()
        macd = ema_fast - ema_slow
        signal_line = macd.ewm(span=self.signal).mean()
        histogram = macd - signal_line
        
        return macd, signal_line, histogram
    
    def generate_signals(self, data):
        """
        生成MACD交易信号
        
        Args:
            data: DataFrame包含价格数据，必须有'close'列
        """
        if 'close' not in data.columns:
            raise ValueError("数据必须包含'close'列")
        
        df = data.copy()
        
        # 计算MACD
        df['macd'], df['macd_signal'], df['macd_histogram'] = self.calculate_macd(df['close'])
        
        # 生成信号
        df['signal'] = 0
        
        # MACD金叉买入
        df.loc[(df['macd'] > df['macd_signal']) & (df['macd'].shift(1) <= df['macd_signal'].shift(1)), 'signal'] = 1
        
        # MACD死叉卖出
        df.loc[(df['macd'] < df['macd_signal']) & (df['macd'].shift(1) >= df['macd_signal'].shift(1)), 'signal'] = -1
        
        # 移除NaN值
        df = df.dropna()
        
        return df[['signal', 'macd', 'macd_signal', 'macd_histogram']]