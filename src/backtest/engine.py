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
        
        # 合并数据: 信号列与策略输出的指标列一并对齐合并(供图表/分析使用)
        df = data.copy()
        for col in signals.columns:
            df[col] = signals[col]
        
        # 计算每日收益
        # A股只做多: 持仓 = 信号为1的时段; 离场日的-1仅是卖出标记,
        # 不视为空头仓位(否则卖出次日会产生一天的幻影空头收益)
        df['returns'] = df['close'].pct_change()
        df['position'] = df['signal'].shift(1).clip(lower=0)
        df['strategy_returns'] = df['position'] * df['returns']
        
        # 考虑手续费: 仅按建仓/离场事件各收一次
        # (旧实现按 signal 非零的每一天收取, 长周期持仓会被重复扣费严重失真)
        buy_day = (df['signal'] == 1) & (df['signal'].shift(1) != 1)
        trade_day = buy_day | (df['signal'] == -1)
        df['commission_cost'] = trade_day.astype(int) * self.commission
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
        """记录交易(以持仓状态变化为准)

        BUY  = 空仓时 signal 变为 1 (建仓)
        SELL = 持仓时 signal 离开 1 (信号卖出 -1 或条件失效归 0, 均视为离场)
        保证 BUY/SELL 严格交替, 供图表按序配对; 全程持仓到最后则末笔无对应卖出。
        """
        trades = []
        holding = False

        for i, row in df.iterrows():
            signal = row['signal']
            if pd.isna(signal):
                continue

            if not holding and signal == 1:
                trades.append({
                    'date': i,
                    'type': 'BUY',
                    'price': row['close'],
                    'shares': 1,
                    'value': row['close'],
                    'commission': row['close'] * self.commission
                })
                holding = True
            elif holding and signal != 1:
                trades.append({
                    'date': i,
                    'type': 'SELL',
                    'price': row['close'],
                    'shares': 1,
                    'value': row['close'],
                    'commission': row['close'] * self.commission
                })
                holding = False

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
        
        # 胜率与平均单笔收益: 按 BUY/SELL 配对的完整回合计算(卖出价高于买入价记为胜)
        win_rate = 0
        avg_return_per_trade = 0
        if len(self.trades) >= 2:
            buys = self.trades[self.trades['type'] == 'BUY']['price'].reset_index(drop=True)
            sells = self.trades[self.trades['type'] == 'SELL']['price'].reset_index(drop=True)
            n = min(len(buys), len(sells))
            if n > 0:
                round_trips = (sells.iloc[:n] - buys.iloc[:n]) / buys.iloc[:n]
                win_rate = float((round_trips > 0).mean())
                avg_return_per_trade = float(round_trips.mean())
        
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
            'avg_return_per_trade': avg_return_per_trade,
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