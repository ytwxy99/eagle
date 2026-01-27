# 股票交易策略系统

基于Baostock的A股量化交易策略开发框架。

## 功能特性

- **数据获取**: 使用Baostock获取A股历史数据
- **策略开发**: 支持多种技术指标策略
- **回测引擎**: 完整的回测和绩效评估系统
- **可视化**: 策略信号和回测结果可视化

## 安装

1. 安装依赖：
```bash
pip install -r requirements.txt
```

2. 注册Baostock账号：
访问 [Baostock官网](http://baostock.com) 注册账号

## 快速开始

### 1. 获取股票数据

```python
from src.data.baostock_client import BaostockClient

with BaostockClient() as client:
    # 获取平安银行2023年数据
    data = client.get_historical_data("sz.000001", "2023-01-01", "2023-12-31")
    print(data.head())
```

### 2. 运行策略

```python
from src.strategies.moving_average_strategy import MovingAverageStrategy
from src.backtest.backtest_engine import BacktestEngine

# 创建策略
strategy = MovingAverageStrategy(short_window=20, long_window=50)

# 生成信号
signals = strategy.generate_signals(data)

# 回测
engine = BacktestEngine(initial_capital=100000)
results, detailed_data = engine.run_backtest(data, signals)

print(f"总收益率: {results['total_return']:.2%}")
print(f"夏普比率: {results['sharpe_ratio']:.2f}")
```

### 3. 运行示例

```bash
python examples/simple_strategy_example.py
```

## 内置策略

### 1. 移动平均线策略 (MovingAverageStrategy)
- 短期均线上穿长期均线：买入
- 短期均线下穿长期均线：卖出

### 2. RSI策略 (RSIStrategy)
- RSI < 30：超卖，买入
- RSI > 70：超买，卖出

### 3. MACD策略 (MACDStrategy)
- MACD金叉：买入
- MACD死叉：卖出

### 4. Dual Thrust策略
- 基于价格波动的突破策略

## 项目结构

```
├── src/
│   ├── data/                 # 数据获取模块
│   │   └── baostock_client.py
│   ├── strategies/           # 策略模块
│   │   ├── base_strategy.py
│   │   └── moving_average_strategy.py
│   └── backtest/            # 回测引擎
│       └── backtest_engine.py
├── examples/                # 示例代码
├── tests/                   # 测试文件
├── data/                    # 数据存储
└── requirements.txt         # 依赖列表
```

## 扩展策略

要创建自定义策略，继承`BaseStrategy`类：

```python
from src.strategies.base_strategy import BaseStrategy

class MyStrategy(BaseStrategy):
    def generate_signals(self, data):
        df = data.copy()
        
        # 计算指标
        df['my_indicator'] = ...
        
        # 生成信号
        df['signal'] = 0
        df.loc[condition, 'signal'] = 1
        df.loc[condition, 'signal'] = -1
        
        return df
```

## 注意事项

1. Baostock需要注册账号才能使用
2. 免费用户有数据获取频率限制
3. 回测结果仅供参考，实际交易存在风险
4. 建议先在模拟盘测试策略