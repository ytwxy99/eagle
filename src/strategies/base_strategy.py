from abc import ABC, abstractmethod
import pandas as pd
import numpy as np

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