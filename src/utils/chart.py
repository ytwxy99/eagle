import os
from datetime import datetime

from matplotlib import pyplot as plt
import pandas as pd

def create_enhanced_trading_chart(data, trades, detailed_data, stock_code, results, start_date, end_date):
    """创建增强版交易分析图"""
    
    # 设置中文字体
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False
    
    # 创建大图
    fig = plt.figure(figsize=(20, 16))
    
    # 创建网格布局
    gs = fig.add_gridspec(5, 2, height_ratios=[3, 1, 1, 1, 1], width_ratios=[3, 1], hspace=0.3)
    
    # 1. 主图：价格走势与买卖点
    ax1 = fig.add_subplot(gs[0, :])
    
    # 价格线
    ax1.plot(data.index, data['close'], color='black', linewidth=1.5, label='收盘价', alpha=0.8)
    
    # 移动平均线
    data['ma20'] = data['close'].rolling(window=20).mean()
    ax1.plot(data.index, data['ma20'], color='orange', linewidth=1, label='MA20', alpha=0.7)
    
    # 买卖点标注
    if not trades.empty:
        buy_trades = trades[trades['type'] == 'BUY']
        sell_trades = trades[trades['type'] == 'SELL']
        
        # 买入点
        if not buy_trades.empty:
            ax1.scatter(buy_trades['date'], buy_trades['price'], 
                       color='red', marker='^', s=150, zorder=5, label='买入信号')
            
            # 添加买入标注
            for idx, trade in buy_trades.iterrows():
                date_str = trade['date'].strftime('%m-%d')
                ax1.annotate(f'买入\n¥{trade["price"]:.2f}\n{date_str}', 
                            (trade['date'], trade['price']), 
                            xytext=(15, 15), textcoords='offset points',
                            fontsize=9, color='red', fontweight='bold',
                            bbox=dict(boxstyle="round,pad=0.3", facecolor="lightyellow", alpha=0.8))
        
        # 卖出点
        if not sell_trades.empty:
            ax1.scatter(sell_trades['date'], sell_trades['price'], 
                       color='green', marker='v', s=150, zorder=5, label='卖出信号')
            
            # 添加卖出标注
            for idx, trade in sell_trades.iterrows():
                date_str = trade['date'].strftime('%m-%d')
                ax1.annotate(f'卖出\n¥{trade["price"]:.2f}\n{date_str}', 
                            (trade['date'], trade['price']), 
                            xytext=(15, -25), textcoords='offset points',
                            fontsize=9, color='green', fontweight='bold',
                            bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgreen", alpha=0.8))
    
    # 盈利曲线
    ax1_twin = ax1.twinx()
    ax1_twin.plot(detailed_data.index, detailed_data['portfolio_value'], 
                 color='blue', linewidth=2.5, label='策略资产', alpha=0.8)
    ax1_twin.axhline(y=100000, color='gray', linestyle='--', alpha=0.7, label='初始资金')
    
    # 设置标题和标签
    ax1.set_title(f'{stock_code} 交易分析图', fontsize=18, fontweight='bold', pad=20)
    ax1.set_ylabel('股价 (¥)', fontsize=12)
    ax1_twin.set_ylabel('资产价值 (¥)', fontsize=12)
    ax1.legend(loc='upper left')
    ax1_twin.legend(loc='upper right')
    ax1.grid(True, alpha=0.3)
    
    # 2. 成交量图
    ax2 = fig.add_subplot(gs[1, :])
    colors = ['red' if close > open_price else 'green' 
             for close, open_price in zip(data['close'], data['open'])]
    ax2.bar(data.index, data['volume'], color=colors, alpha=0.6, width=0.8)
    ax2.set_ylabel('成交量', fontsize=12)
    ax2.grid(True, alpha=0.3)
    
    # 3. 同花顺主力真吸货指标
    ax3 = fig.add_subplot(gs[2, :])
    if 'main_force_indicator' in detailed_data.columns:
        ax3.plot(detailed_data.index, detailed_data['main_force_indicator'], 
                color='purple', linewidth=1.5, label='主力真吸货指标')
        ax3.axhline(y=50, color='red', linestyle='--', alpha=0.7, label='强吸货阈值')
        ax3.axhline(y=0, color='gray', linestyle='-', alpha=0.5, label='零轴')
        ax3.axhline(y=-50, color='green', linestyle='--', alpha=0.7, label='强出货阈值')
        ax3.set_ylabel('主力真吸货', fontsize=12)
        ax3.legend()
        ax3.grid(True, alpha=0.3)
    
    # 4. 交易记录表格
    ax4 = fig.add_subplot(gs[3, :])
    ax4.axis('off')
    
    if not trades.empty:
        # 创建交易表格数据
        table_data = []
        trade_pairs = []
        
        # 配对买卖交易
        temp_trades = trades.copy()
        temp_trades['date'] = pd.to_datetime(temp_trades['date'])
        temp_trades = temp_trades.sort_values('date')
        
        buy_trades_list = temp_trades[temp_trades['type'] == 'BUY'].values.tolist()
        sell_trades_list = temp_trades[temp_trades['type'] == 'SELL'].values.tolist()
        
        min_len = min(len(buy_trades_list), len(sell_trades_list))
        
        for i in range(min_len):
            buy_trade = buy_trades_list[i]
            sell_trade = sell_trades_list[i]
            
            buy_price = buy_trade[2]  # price column
            sell_price = sell_trade[2]
            profit_pct = ((sell_price - buy_price) / buy_price) * 100
            profit = (sell_price - buy_price) * min(buy_trade[3], sell_trade[3])  # shares column
            
            table_data.append([
                f"T{i+1}",
                buy_trade[0].strftime('%m-%d'),
                f"¥{buy_price:.2f}",
                sell_trade[0].strftime('%m-%d'),
                f"¥{sell_price:.2f}",
                f"{profit_pct:.1f}%",
                f"¥{profit:.0f}"
            ])
        
        if table_data:
            table = ax4.table(cellText=table_data,
                            colLabels=['交易', '买入日', '买入价', '卖出日', '卖出价', '收益率', '收益'],
                            cellLoc='center',
                            loc='center',
                            bbox=[0, 0.2, 1, 0.8])
            table.auto_set_font_size(False)
            table.set_fontsize(9)
            table.scale(1, 1.8)
            
            # 设置表格样式
            for i, key in enumerate(table.get_celld().keys()):
                cell = table.get_celld()[key]
                if key[0] == 0:  # 表头
                    cell.set_facecolor('#4CAF50')
                    cell.set_text_props(weight='bold', color='white')
                else:
                    if key[1] == 5:  # 收益率列
                        value = float(table_data[key[0]-1][5].rstrip('%'))
                        cell.set_facecolor('#90EE90' if value > 0 else '#FFB6C1')
    
    ax4.set_title('交易记录详情', fontsize=14, pad=20)
    
    # 5. 统计信息
    ax5 = fig.add_subplot(gs[4, :])
    ax5.axis('off')
    
    # 计算统计数据
    total_return = ((detailed_data['portfolio_value'].iloc[-1] - 100000) / 100000 * 100)
    total_trades = len(trades) // 2
    
    # 创建统计文本
    stats_text = f"""
    📈 增强版主力吸货策略回测统计
    
    📊 股票代码: {stock_code}
    📅 回测期间: {start_date} 至 {end_date}
    💰 初始资金: ¥100,000
    💵 最终资产: ¥{detailed_data['portfolio_value'].iloc[-1]:,.0f}
    📈 总收益率: {total_return:.2f}%
    📊 夏普比率: {results['sharpe_ratio']:.2f}
    📉 最大回撤: {results['max_drawdown']:.2f}%
    🔄 交易次数: {total_trades}
    🎯 胜率: {results['win_rate']:.1%}
    💱 平均单笔收益: {results['avg_return_per_trade']:.2f}%
    """
    
    ax5.text(0.5, 0.5, stats_text, ha='center', va='center', fontsize=11,
            bbox=dict(boxstyle="round,pad=1", facecolor="lightblue", alpha=0.8))
    
    # 添加时间日期标注
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    fig.text(0.99, 0.01, f'生成时间: {current_time}', ha='right', va='bottom', 
             fontsize=9, color='gray', alpha=0.7)
    
    # 调整布局
    plt.tight_layout()
    plt.subplots_adjust(top=0.95, bottom=0.05)
    
    # 保存到桌面
    desktop = os.path.expanduser("~/Desktop")
    filename = f"main_force_strategy_{stock_code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    filepath = os.path.join(desktop, filename)
    plt.savefig(filepath, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    
    print(f"✅ 交易分析图已保存到桌面: {filepath}")
    print(f"📅 生成时间: {current_time}")
    
    # 打印交易摘要
    if not trades.empty:
        print(f"\n📊 交易摘要:")
        print(f"   总交易对数: {total_trades}")
        print(f"   总收益率: {total_return:.2f}%")
        print(f"   最终资产: ¥{detailed_data['portfolio_value'].iloc[-1]:,.0f}")
        print(f"   夏普比率: {results['sharpe_ratio']:.2f}")
        print(f"   最大回撤: {results['max_drawdown']:.2f}%")
    
    return filepath