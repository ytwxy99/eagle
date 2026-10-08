from abc import ABC, abstractmethod
import pandas as pd
import numpy as np


def tdx_sma(series, n, m):
    """通达信/同花顺 SMA(X,N,M): Y = (X*M + Y'*(N-M)) / N
    等价于 alpha = M/N 的指数加权平均"""
    return series.ewm(alpha=m / n, adjust=False).mean()


def main_force_indicator(df, full_scale=20.0, ratio_cap=20.0):
    """主力真吸筹指标(同花顺流传公式的日线移植, 值域约[-100, 100])

    刻度校准依据: 三只样本股(600477/000001/600519, 2023-2026)吸筹侧原始值
    p90≈8-12, p99≈17-19, max被ratio_cap截断在20; full_scale取20时
    p90映射到40-60, p99映射到85-95, ±50阈值有意义。

    吸筹侧(流传公式原样):
        VAR1 := REF((LOW+OPEN+CLOSE+HIGH)/4, 1)
        VAR2 := SMA(ABS(LOW-VAR1),13,1) / SMA(MAX(LOW-VAR1,0),13,1)
        VAR3 := EMA(VAR2,13)
        VAR4 := LLV(LOW,34)
        VAR5 := EMA(IF(LOW<=VAR4,VAR3,0),3)
        吸筹 := IF(VAR5>REF(VAR5,1), VAR5, 0)
    语义: 创34日新低且下行缺口放大时累积, 平滑后只在上行段保留 —— "低位承接"强度。

    出货侧为对称镜像(自行扩展, 非原公式): 创34日新高且上行缺口放大时累积。

    Args:
        df: 含 open/high/low/close 列的行情数据
        full_scale: 原始值映射到 ±100 的满刻度(可按个股分布校准)
        ratio_cap: 缺口放大比的上限截断(纯数值保护, 原公式无此项;
                   长期单边走势会使分母趋零, 不截断会数值爆炸)
    """
    var1 = ((df['low'] + df['open'] + df['close'] + df['high']) / 4).shift(1)

    # 吸筹侧: 新低 + 下行缺口放大
    gap_low = df['low'] - var1
    var2 = tdx_sma(gap_low.abs(), 13, 1) / (tdx_sma(gap_low.clip(lower=0), 13, 1) + 1e-10)
    var3 = var2.clip(upper=ratio_cap).ewm(span=13, adjust=False).mean()
    var4 = df['low'].rolling(window=34, min_periods=1).min()
    var5 = var3.where(df['low'] <= var4, 0.0).ewm(span=3, adjust=False).mean()
    absorption = var5.where(var5 > var5.shift(1), 0.0)

    # 出货侧: 新高 + 上行缺口放大 (镜像)
    gap_high = var1 - df['high']
    var2d = tdx_sma(gap_high.abs(), 13, 1) / (tdx_sma(gap_high.clip(lower=0), 13, 1) + 1e-10)
    var3d = var2d.clip(upper=ratio_cap).ewm(span=13, adjust=False).mean()
    var4d = df['high'].rolling(window=34, min_periods=1).max()
    var5d = var3d.where(df['high'] >= var4d, 0.0).ewm(span=3, adjust=False).mean()
    distribution = var5d.where(var5d > var5d.shift(1), 0.0)

    score = 100.0 * (absorption / full_scale).clip(upper=1.0) \
                 - 100.0 * (distribution / full_scale).clip(upper=1.0)
    return score


class BaseStrategy(ABC):
    """策略基类"""
    
    def __init__(self, name=None):
        self.name = name or self.__class__.__name__
        self.data = None
        self.signals = None
        
    @abstractmethod
    def generate_signals(self, data):
        """
        生成交易信号
        
        Args:
            data: DataFrame包含价格数据
            
        Returns:
            DataFrame包含信号列
        """
        pass
    
    def backtest(self, data, initial_capital=100000, commission=0.001):
        """
        简单回测
        
        Args:
            data: 包含价格数据的DataFrame
            initial_capital: 初始资金
            commission: 手续费率
            
        Returns:
            dict: 回测结果
        """
        self.data = data.copy()
        self.signals = self.generate_signals(data)
        
        if self.signals is None or 'signal' not in self.signals.columns:
            raise ValueError("策略必须生成包含'signal'列的信号")
        
        # 计算持仓
        self.signals['position'] = self.signals['signal'].diff()
        
        # 计算收益
        self.signals['returns'] = self.signals['close'].pct_change()
        self.signals['strategy_returns'] = self.signals['position'].shift(1) * self.signals['returns']
        
        # 计算累计收益
        self.signals['cumulative_returns'] = (1 + self.signals['strategy_returns']).cumprod()
        self.signals['portfolio_value'] = initial_capital * self.signals['cumulative_returns']
        
        # 计算指标
        total_return = (self.signals['portfolio_value'].iloc[-1] - initial_capital) / initial_capital
        sharpe_ratio = self.calculate_sharpe_ratio(self.signals['strategy_returns'])
        max_drawdown = self.calculate_max_drawdown(self.signals['portfolio_value'])
        
        return {
            'total_return': total_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'final_value': self.signals['portfolio_value'].iloc[-1],
            'trades': len(self.signals[self.signals['position'] != 0])
        }
    
    def calculate_sharpe_ratio(self, returns, risk_free_rate=0.03):
        """计算夏普比率"""
        excess_returns = returns - risk_free_rate / 252
        return excess_returns.mean() / excess_returns.std() * np.sqrt(252)
    
    def calculate_max_drawdown(self, portfolio_values):
        """计算最大回撤"""
        peak = portfolio_values.expanding().max()
        drawdown = (portfolio_values - peak) / peak
        return drawdown.min()
    
    def plot_signals(self, data, signals):
        """绘制信号图"""
        import matplotlib.pyplot as plt
        
        plt.figure(figsize=(12, 8))
        
        # 价格图
        plt.subplot(2, 1, 1)
        plt.plot(data.index, data['close'], label='Close Price')
        
        # 标记买入卖出点
        buy_signals = signals[signals['signal'] == 1]
        sell_signals = signals[signals['signal'] == -1]
        
        plt.scatter(buy_signals.index, buy_signals['close'], color='green', 
                   marker='^', label='Buy', s=100)
        plt.scatter(sell_signals.index, sell_signals['close'], color='red', 
                   marker='v', label='Sell', s=100)
        
        plt.title(f'{self.name} Strategy Signals')
        plt.legend()
        
        # 信号图
        plt.subplot(2, 1, 2)
        plt.plot(signals.index, signals['signal'], label='Position')
        plt.title('Position Over Time')
        plt.legend()
        
        plt.tight_layout()
        plt.show()