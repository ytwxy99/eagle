import argparse
import importlib

def parse_args() -> any: 
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='主力吸货策略回测系统')
    parser.add_argument('--mode', choices=['accumulation', 'monitor'], required=True, help='运行模式: accumulation(主力吸货策略)')
    parser.add_argument('--stock', default="sh.600477", help='股票代码')
    parser.add_argument('--start', default="2024-07-26", help='开始日期')
    parser.add_argument('--end', default="2026-01-20", help='结束日期')
    parser.add_argument('--date', help='扫描日期(默认为今天)')
    
    args = parser.parse_args()
    return args


def parse_dispatch(args: any) -> any:
    """根据参数模式分发处理"""
    getattr(importlib.import_module(f"src.strategies.{args.mode}"), f"run")(args)
