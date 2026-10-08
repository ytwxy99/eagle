#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主力吸货策略回测主程序
使用EnhancedMainForceStrategy进行回测并生成交易图表
"""
import logging
import os
import sys

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.parser import parse_args, parse_dispatch


def main():
    args = parse_args()
    # 默认只输出ERROR; --debug 时输出INFO/WARNING日志
    logging.basicConfig(level=logging.INFO if args.debug else logging.ERROR)
    parse_dispatch(args)


if __name__ == "__main__":
    main()
