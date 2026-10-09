# Eagle 股票交易策略系统

基于 akshare 的 A 股量化策略回测与全市场扫描框架。

## 功能特性

- **数据获取**: akshare 接口，东财优先、新浪回退、连续失败自动熔断（无需注册账号）
- **策略扫描**: 全市场 A 股扫描，筛选"今日新触发买点且历史信号成功率达标"的股票
- **回测引擎**: 手续费/滑点模拟，输出总收益、胜率、夏普比率、最大回撤等指标
- **可视化**: 默认直接在终端控制台绘图（plotext），可选保存 PNG 图片（matplotlib）

## 安装

```bash
pip install -r requirements.txt
```

## 使用方法

### 单只股票回测（默认在终端直接绘图，不生成文件）

```bash
python main.py --mode accumulation --stock sh.600000
```

输出：价格+MA20+买卖点、成交量、主力真吸货指标、策略资产曲线四幅终端图表，
以及交易记录与回测统计（最终资产、收益率、胜率、夏普、最大回撤）。

### 保存 PNG 图片

```bash
# 需要图片文件时加 --save-image，保存到桌面
python main.py --mode accumulation --stock sh.600000 --save-image
```

### 全市场扫描

```bash
python main.py --mode accumulation --stock all
```

对全部 A 股逐只计算信号，筛选"今日新触发买点"（指标当日上穿 +50，区别于过去买入后仍持仓中的股票），
并输出成功率达标的股票汇总表，按成功率降序排列：

```
📊 信号汇总 (今日新触发买点3只, 达标2只, 按成功率降序):
排名  股票代码  信号数  平均5日内最大涨幅  成功率
1     sh.600000 11      +3.00%             90.91%
2     sh.600519 5       +5.00%             85.00%
🎉 股票['sh.600000', 'sh.600519']符合吸货条件
```

- 汇总表只显示成功率 ≥ 80% 的达标股票，数量与"符合吸货条件"一致
- 成功率 = 该股历史 signal==1 的交易日后 5 个交易日内最大涨幅超过 2% 的比例
- 首次触发买点的股票（无历史信号可评估）成功率为 0，不会达标

### 调试日志

```bash
# 默认只输出 ERROR；加 --debug 输出 INFO/WARNING（如数据源回退提示）
python main.py --mode accumulation --stock sh.600000 --debug
```

### 全部参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--mode` | 运行模式：`accumulation`（主力吸货）/ `breakthrough`（箱体突破） | 必填 |
| `--stock` | 股票代码（如 `sh.600000`），或 `all` 全市场扫描 | `sh.600477` |
| `--start` | 回测开始日期 | `2024-07-26` |
| `--end` | 回测结束日期 | 今天 |
| `--date` | 扫描日期 | 今天 |
| `--save-image` | 回测图表保存为 PNG 到桌面（默认终端绘制） | 关闭 |
| `--debug` | 输出 INFO/WARNING 日志（默认只输出 ERROR） | 关闭 |

## 内置策略

### accumulation 主力吸货突破策略 (LowPointMainForceStrategy)

- **买点**: 主力真吸货指标（同花顺流传公式日线移植，值域约 ±100）上穿 +50
- **卖点**（满足其一即离场）:
  1. 指标下穿 -50（出货强度突破阈值）
  2. 支撑止损：收盘 < 前 10 日最低价 × 0.97
  3. 最大亏损止损：收盘 < 买入价 × (1 - 8%)
- 持仓期间持续持有（signal=1），直到任一离场条件触发

### breakthrough 箱体突破策略 (BoxBreakthroughStrategy)

- 箱体震荡（30 日振幅 < 5%）后放量突破（涨幅 > 3%、成交量放大 1.5 倍以上）

## 全市场扫描机制

- **股票池**: `src/data/all_stock_codes.txt` 缓存（仅 sh.60 / sz.00 / sz.30 / sh.68，剔除北交所）。
  缓存无过期机制，需更新时手动删除该文件
- **数据源**: 东财接口优先（连续失败 3 次后熔断跳过，避免逐股等待超时），失败自动回退新浪日线
- **扫描模式**（`--stock all`）下不运行回测引擎、不输出图表，仅做信号与历史成功率筛选

## 项目结构

```
├── main.py                      # 命令行入口
├── src/
│   ├── data/
│   │   ├── akshare_client.py    # akshare 数据客户端（东财/新浪双源+熔断）
│   │   ├── baostock_client.py   # 旧版 baostock 客户端（遗留）
│   │   ├── stock.py             # 数据获取与股票池缓存
│   │   └── all_stock_codes.txt  # A股股票池缓存
│   ├── strategies/
│   │   ├── base_strategy.py     # 策略基类 + 主力真吸货指标公式
│   │   ├── low_point_main_force_strategy.py  # 主力吸货突破策略
│   │   ├── breakthrough.py      # 箱体突破策略
│   │   ├── accumulation.py      # accumulation 模式入口（全市场汇总表）
│   │   └── moving_average_strategy.py        # 移动平均线策略（示例）
│   ├── backtest/
│   │   ├── engine.py            # 回测引擎（资金曲线/绩效指标）
│   │   └── run.py               # 回测执行器 + 信号成功率分析
│   └── utils/
│       ├── parser.py            # 命令行参数解析与模式分发
│       ├── term_chart.py        # 终端图表（plotext）
│       └── chart.py             # PNG 图表（matplotlib）
├── examples/                    # 示例代码
├── tests/                       # 测试文件
└── requirements.txt             # 依赖列表
```

## 注意事项

1. 全市场扫描约 5000+ 只股票，逐只网络取数，耗时较长属正常现象
2. 终端绘图使用 Unicode 特殊字符（六分块/三角标记），需 iTerm2 等支持 UTF-8 的终端
3. 回测结果仅供参考，实际交易存在风险
