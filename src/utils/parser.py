import argparse
import importlib
from datetime import datetime

def parse_args() -> any: 
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='主力吸货策略回测系统')
    parser.add_argument('--mode', choices=['accumulation', 'breakthrough'], required=True, help='运行模式: accumulation')
    parser.add_argument('--stock', default="sh.600477", help='股票代码')
    parser.add_argument('--start', default="2024-07-26", help='开始日期')
    parser.add_argument('--end', default=datetime.now().strftime('%Y-%m-%d'), help='结束日期')
    parser.add_argument('--date', help='扫描日期(默认为今天)')
    parser.add_argument('--save-image', action='store_true', help='回测图表保存为PNG图片(默认直接在终端控制台绘制)')
    parser.add_argument('--debug', action='store_true', help='输出INFO/WARNING等日志(默认只输出ERROR)')
    
    args = parser.parse_args()
    return args


def parse_dispatch(args: any) -> any:
    """根据参数模式分发处理"""
    getattr(importlib.import_module(f"src.strategies.{args.mode}"), f"run")(args)
