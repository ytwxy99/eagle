import pandas as pd
import numpy as np
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class BacktestEngine:
    """回测引擎"""
    
    def __init__(self, initial_capital=100000, commission=0.001, slippage=0.001):
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        self.trades = []
        self.equity_curve = []
        
    def run_backtest(self, data, signals):
        """
        运行回测
        
        Args:
            data: DataFrame包含价格数据
            signals: DataFrame包含交易信号
            
        Returns:
            dict: 回测结果
        """
        if 'signal' not in signals.columns:
            raise ValueError("信号数据必须包含'signal'列")
        
        # 合并数据
        df = data.copy()
        df['signal'] = signals['signal']
        
        # 计算持仓
        #df['position'] = df['signal'].diff()
        """
        | 信号变化 (当前-前值) | position值 | 交易行为 | |---------------------|------------|-------------------| | 1 → 0 | -1 | 平仓（多头离场） | | 0 → 1 | +1 | 开仓（建立多头） | | 1 → 1 | 0 | 持仓不变 | | -1 → 0 | +1 | 平仓（空头离场） | | 0 → -1 | -1 | 开仓（建立空头） |
        """
        
        # 计算每日收益
        df['returns'] = df['close'].pct_change()
        df['strategy_returns'] = df['signal'].shift(1) * df['returns']
        
        # 考虑手续费
        df['commission_cost'] = abs(df['signal']) * self.commission
        df['strategy_returns'] = df['strategy_returns'] - df['commission_cost']
        
        # 计算累计收益
        df['cumulative_returns'] = (1 + df['strategy_returns']).cumprod()
        df['portfolio_value'] = self.initial_capital * df['cumulative_returns']
        
        # 记录交易
        self._record_trades(df)
        
        # 计算绩效指标
        results = self._calculate_performance_metrics(df)
        
        return results, df
    
    def _record_trades(self, df):
        """记录交易"""
        first_trade = 0
        trades = []
        
        for i, row in df.iterrows():
            if row['signal'] > 0:
                first_trade = first_trade + 1

            if row['signal'] > 0:
                if first_trade ==0:
                    continue

                trade = {
                    'date': i,
                    'type': 'BUY' if row['signal'] > 0 else 'SELL',
                    'price': row['close'],
                    'shares': abs(row['signal']),
                    'value': abs(row['signal']) * row['close'],
                    'commission': abs(row['signal']) * row['close'] * self.commission
                }
                trades.append(trade)
        
        self.trades = pd.DataFrame(trades)
    
    def _calculate_performance_metrics(self, df):
        """计算绩效指标"""
        strategy_returns = df['strategy_returns'].dropna()
        
        # 基本指标
        total_return = (df['portfolio_value'].iloc[-1] - self.initial_capital) / self.initial_capital
        annual_return = (1 + total_return) ** (252 / len(df)) - 1
        
        # 波动率和夏普比率
        volatility = strategy_returns.std() * np.sqrt(252)
        sharpe_ratio = (annual_return - 0.03) / volatility if volatility != 0 else 0
        
        # 最大回撤
        cumulative = df['portfolio_value']
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min()
        
        # 胜率
        if len(self.trades) > 1:
            # 简化的胜率计算
            non_zero_returns = strategy_returns[strategy_returns != 0]
            if len(non_zero_returns) > 0:
                profitable_trades = len(non_zero_returns[non_zero_returns > 0])
                win_rate = profitable_trades / len(non_zero_returns)
            else:
                win_rate = 0
        else:
            win_rate = 0
        
        # 交易统计
        total_trades = len(self.trades)
        
        return {
            'total_return': total_return,
            'annual_return': annual_return,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'total_trades': total_trades,
            'final_value': df['portfolio_value'].iloc[-1],
            'avg_return_per_trade': strategy_returns.mean() * 252,
            'profit_factor': abs(strategy_returns[strategy_returns > 0].sum() / 
                               strategy_returns[strategy_returns < 0].sum()) if len(strategy_returns[strategy_returns < 0]) > 0 else 0
        }
    
    def get_trade_log(self):
        """获取交易日志"""
        return self.trades
    
    def get_equity_curve(self, df):
        """获取权益曲线"""
        return df[['portfolio_value', 'cumulative_returns']]
    
    def plot_results(self, df):
        """绘制回测结果"""
        import matplotlib.pyplot as plt
        
        fig, axes = plt.subplots(3, 1, figsize=(15, 12))
        
        # 价格图
        axes[0].plot(df.index, df['close'], label='Close Price', alpha=0.7)
        
        # 标记交易点
        buy_signals = df[df['signal'] > 0]
        sell_signals = df[df['signal'] < 0]
        
        axes[0].scatter(buy_signals.index, buy_signals['close'], 
                       color='green', marker='^', label='Buy', s=100)
        axes[0].scatter(sell_signals.index, sell_signals['close'], 
                       color='red', marker='v', label='Sell', s=100)
        
        axes[0].set_title('Price and Trading Signals')
        axes[0].legend()
        
        # 权益曲线
        axes[1].plot(df.index, df['portfolio_value'], label='Portfolio Value', color='blue')
        axes[1].axhline(y=self.initial_capital, color='red', linestyle='--', label='Initial Capital')
        axes[1].set_title('Portfolio Value Over Time')
        axes[1].legend()
        
        # 回撤
        cumulative = df['portfolio_value']
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max * 100
        
        axes[2].fill_between(df.index, drawdown, 0, color='red', alpha=0.3)
        axes[2].set_title('Drawdown (%)')
        axes[2].set_ylabel('Drawdown %')
        
        plt.tight_layout()
        plt.show()