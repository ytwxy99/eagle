#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
akshare 数据客户端
替代 baostock: 走 HTTPS(443) 接口, 无需登录, 公司网络可用。

支持市场:
- A股: 'sh.600477' / 'sz.000001' / '600477'
- 港股: 'hk.01810' / '01810' (小米集团)

K线数据源优先级:
1. 东财 stock_zh_a_hist / stock_hk_hist  (部分公司网络会拦截 push2his.eastmoney.com)
2. 新浪 stock_zh_a_daily / stock_hk_daily (回退源, 仅日线, 港股为全量历史本地过滤)

对外接口与原 baostock_client 保持一致:
- get_all_stocks()      -> DataFrame[code, code_name], code 为 'sh.600477' 格式 (仅A股)
- get_historical_data() -> DataFrame[date, open, high, low, close,
                            volume(单位:股), amount, turn, pctChg]
"""

import logging
import time

import pandas as pd
import akshare as ak

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 内部列名顺序 (date, OHLC, volume 为下游必需列)
_HIST_COLUMN_ORDER = ['date', 'open', 'high', 'low', 'close',
                      'volume', 'amount', 'turn', 'pctChg']

# 东财日线列名 -> 项目内部列名
_EM_COLUMNS = {
    '日期': 'date',
    '开盘': 'open',
    '收盘': 'close',
    '最高': 'high',
    '最低': 'low',
    '成交量': 'volume',   # 东财单位为"手", 取数后 x100 换算为"股"
    '成交额': 'amount',
    '换手率': 'turn',
    '涨跌幅': 'pctChg',
}

# 新浪日线列名 -> 项目内部列名
_SINA_COLUMNS = {
    'date': 'date',
    'open': 'open',
    'high': 'high',
    'low': 'low',
    'close': 'close',
    'volume': 'volume',     # 新浪单位已是"股"
    'amount': 'amount',
    'turnover': 'turn',     # 新浪为小数(0.0149=1.49%), 取数后 x100 对齐百分比口径
}

# 复权映射: 与原 baostock adjustflag 口径一致 ('3'=不复权)
_ADJUST_MAP = {'1': 'qfq', '2': 'hfq', '3': ''}
_PERIOD_MAP = {'d': 'daily', 'w': 'weekly', 'm': 'monthly'}


def _retry(func, attempts=3, delay=1.0):
    """简单重试: akshare 接口偶发超时/限流"""
    last_err = None
    for i in range(attempts):
        try:
            return func()
        except Exception as e:
            last_err = e
            if i < attempts - 1:
                time.sleep(delay * (i + 1))
    raise last_err


# 东财源熔断器: 连续失败达到阈值后本进程内不再尝试(公司网拦截场景,
# 避免 --stock all 全市场扫描时每只股票都白等东财超时)
# A股与港股共用同一个东财域名, 熔断状态共享
_em_fail_streak = 0
_EM_FAIL_STREAK_MAX = 3


def _em_call(fetch):
    """带熔断器的东财请求: 连续失败达到阈值后直接跳过"""
    global _em_fail_streak
    if _em_fail_streak >= _EM_FAIL_STREAK_MAX:
        raise ConnectionError("东财源已被熔断跳过(此前连续失败)")
    try:
        result = fetch()
        _em_fail_streak = 0
        return result
    except Exception:
        _em_fail_streak += 1
        raise


def _to_bare_code(stock_code) -> str:
    """'sh.600477' / '600477' -> '600477'"""
    code = str(stock_code).strip()
    return code.split('.')[-1] if '.' in code else code


def _to_prefixed_code(code: str) -> str:
    """6位代码 -> 'sh.600477' 格式 (北交所加 bj 前缀, 由上层过滤掉)"""
    if code.startswith('6'):
        return f"sh.{code}"
    if code.startswith(('0', '3')):
        return f"sz.{code}"
    return f"bj.{code}"


def _finalize_hist(df: pd.DataFrame) -> pd.DataFrame:
    """统一类型/列顺序, 补齐缺失的涨跌幅"""
    if df.empty:
        return df
    if 'pctChg' not in df.columns and 'close' in df.columns:
        df['pctChg'] = (df['close'].pct_change() * 100).round(4)
    if 'turn' in df.columns:
        df['turn'] = pd.to_numeric(df['turn'], errors='coerce')
    df['date'] = pd.to_datetime(df['date'])
    for col in ('open', 'high', 'low', 'close', 'volume', 'amount'):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    cols = [c for c in _HIST_COLUMN_ORDER if c in df.columns]
    return df[cols].reset_index(drop=True)


def _normalize_volume_unit(df: pd.DataFrame) -> pd.DataFrame:
    """按成交额反推成交量单位: amount/(volume*close)≈100 视为"手"则x100, ≈1 为"股"不处理。
    用于东财等接口成交量单位随市场不同的情况(不可离线确认时以数据自证)"""
    if not {'volume', 'amount', 'close'}.issubset(df.columns) or df.empty:
        return df
    v = pd.to_numeric(df['volume'], errors='coerce')
    a = pd.to_numeric(df['amount'], errors='coerce')
    valid = (v > 0) & (a > 0) & df['close'].notna()
    if not valid.any():
        return df
    ratio = (a[valid] / (v[valid] * df['close'][valid])).median()
    if 50 <= ratio <= 200:  # "手"口径
        df = df.copy()
        df['volume'] = v * 100
    return df


def _fetch_eastmoney(symbol, period, start, end, adjust) -> pd.DataFrame:
    raw = _em_call(lambda: ak.stock_zh_a_hist(
        symbol=symbol, period=period, start_date=start, end_date=end, adjust=adjust))
    if raw is None or raw.empty:
        return pd.DataFrame()
    df = raw.rename(columns=_EM_COLUMNS)
    return _normalize_volume_unit(df)


def _fetch_hk_eastmoney(symbol, period, start, end, adjust) -> pd.DataFrame:
    raw = _em_call(lambda: ak.stock_hk_hist(
        symbol=symbol, period=period, start_date=start, end_date=end, adjust=adjust))
    if raw is None or raw.empty:
        return pd.DataFrame()
    df = raw.rename(columns=_EM_COLUMNS)
    return _normalize_volume_unit(df)


def _fetch_hk_sina(symbol, start, end, adjust) -> pd.DataFrame:
    """新浪港股日线: 接口无日期参数, 返回全量历史后本地过滤"""
    raw = _retry(lambda: ak.stock_hk_daily(symbol=symbol.zfill(5), adjust=adjust))
    if raw is None or raw.empty:
        return pd.DataFrame()
    df = raw.copy()
    df['date'] = pd.to_datetime(df['date'])
    mask = (df['date'] >= pd.Timestamp(start)) & (df['date'] <= pd.Timestamp(end))
    return df[mask]


def _fetch_sina(prefixed_code, start, end, adjust) -> pd.DataFrame:
    raw = _retry(lambda: ak.stock_zh_a_daily(
        symbol=prefixed_code.replace('.', ''), start_date=start,
        end_date=end, adjust=adjust))
    if raw is None or raw.empty:
        return pd.DataFrame()
    df = raw.rename(columns=_SINA_COLUMNS)
    if 'turn' in df.columns:
        # 新浪换手率为小数, x100 对齐东财百分比口径
        df['turn'] = pd.to_numeric(df['turn'], errors='coerce') * 100
    return df


def get_all_stocks() -> pd.DataFrame:
    """获取全部A股列表, 返回 DataFrame[code, code_name]"""
    try:
        df = _retry(ak.stock_info_a_code_name)
    except Exception as e:
        logger.warning(f"交易所接口获取股票列表失败: {e}, 改用东财全市场快照")
        try:
            df = _retry(lambda: ak.stock_zh_a_spot_em()[['代码', '名称']])
        except Exception as e2:
            logger.error(f"获取股票列表失败: {e2}")
            return pd.DataFrame(columns=['code', 'code_name'])

    df = df.rename(columns={'代码': 'code', '名称': 'code_name', 'name': 'code_name'})
    df = df[df['code'].astype(str).str.fullmatch(r'\d{6}')].copy()
    df['code'] = df['code'].astype(str).map(_to_prefixed_code)
    return df[['code', 'code_name']].reset_index(drop=True)


def get_historical_data(stock_code, start_date, end_date=None,
                        frequency='d', adjustflag='3'):
    """获取历史K线数据(字段口径与原 baostock 客户端一致)

    Args:
        stock_code: 股票代码, A股如 'sz.000001'/'000001', 港股如 'hk.01810'/'01810'
        start_date: 开始日期, 格式 '2023-01-01'
        end_date: 结束日期, 默认为今天
        frequency: 数据频率, 'd'=日线, 'w'=周线, 'm'=月线 (新浪回退源仅支持日线)
        adjustflag: 复权类型, '3'=不复权
    """
    if end_date is None:
        end_date = pd.Timestamp.now().strftime('%Y-%m-%d')

    bare = _to_bare_code(stock_code)
    start = str(start_date).replace('-', '')
    end = str(end_date).replace('-', '')
    adjust = _ADJUST_MAP.get(str(adjustflag), '')
    period = _PERIOD_MAP.get(str(frequency), 'daily')

    is_hk = bare.isdigit() and len(bare) <= 5

    if is_hk:
        # ---------- 港股: 东财 -> 新浪 ----------
        symbol = bare.zfill(5)
        try:
            df = _fetch_hk_eastmoney(symbol, period, start, end, adjust)
        except Exception as e_em:
            logger.warning(f"东财接口获取 {stock_code} 失败: {e_em}")
            df = pd.DataFrame()
        if (df is None or df.empty) and frequency == 'd':
            logger.info(f"回退新浪源获取 {stock_code}")
            try:
                df = _fetch_hk_sina(symbol, start, end, adjust)
            except Exception as e_sina:
                logger.warning(f"新浪源获取 {stock_code} 失败: {e_sina}")
                return pd.DataFrame()
    else:
        # ---------- A股: 东财 -> 新浪 ----------
        prefixed = _to_prefixed_code(bare)
        try:
            df = _fetch_eastmoney(bare, period, start, end, adjust)
        except Exception as e_em:
            logger.warning(f"东财接口获取 {stock_code} 失败: {e_em}")
            df = pd.DataFrame()
        if (df is None or df.empty) and frequency == 'd':
            logger.info(f"回退新浪源获取 {stock_code}")
            try:
                df = _fetch_sina(prefixed, start, end, adjust)
            except Exception as e_sina:
                logger.warning(f"新浪源获取 {stock_code} 失败: {e_sina}")
                return pd.DataFrame()

    if df is None or df.empty:
        return pd.DataFrame()

    return _finalize_hist(df)
