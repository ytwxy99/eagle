import logging
import pandas as pd
from functools import wraps
from datetime import datetime, timedelta

import baostock as bs


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def bs_init() -> any:
    try:
        lg = bs.login()
        if lg.error_code == '0':
            return lg
        else:
            logger.error(f"Baostock登录失败: {lg.error_msg}")
            return False
    except Exception as e:
        logger.error(f"登录异常: {e}")
        return False


def ensure_login(func):
    """
    装饰器：确保在执行方法前客户端已登录。
    如果检测到未登录或会话过期，则自动重新登录并重试。
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        result, rs = func(*args, **kwargs)
        
        # 检查结果是否为 DataFrame 或 Baostock 的结果对象
        if rs.error_code != "0" and "you don't login." in rs.error_msg:
            print("Baostock session expired or not logged in. Re-logging in...")
            bs_init()
            result = func(*args, **kwargs)
        
        return result
        
    return wrapper

@ensure_login
def get_all_stocks(bs_client: any):
    """获取所有股票列表"""
    rs = bs.query_stock_basic(code_name="", code="")
    stocks = []
    while rs.error_code == '0' and rs.next():
        stocks.append(rs.get_row_data())
        
    df = pd.DataFrame(stocks, columns=rs.fields)
    return df, rs
    
    
@ensure_login
def get_historical_data(stock_code, start_date, end_date=None, 
                          frequency='d', adjustflag='3'):
    """
    获取历史K线数据
        
    Args:
        stock_code: 股票代码，如'sz.000001'
        start_date: 开始日期，格式'2023-01-01'
        end_date: 结束日期，默认为今天
        frequency: 数据频率，'d'=日线，'w'=周线，'m'=月线
        adjustflag: 复权类型，'3'=不复权
    """     
    if end_date is None:
        end_date = datetime.now().strftime('%Y-%m-%d')
            
    rs = bs.query_history_k_data_plus(
        stock_code,
        "date,code,open,high,low,close,preclose,volume,amount,adjustflag,turn,tradestatus,pctChg,isST",
        start_date=start_date,
        end_date=end_date,
        frequency=frequency,
        adjustflag=adjustflag
    )
        
    data = []
    while rs.error_code == '0' and rs.next():
        data.append(rs.get_row_data())
        
    if not data:
        return pd.DataFrame(), rs
            
    df = pd.DataFrame(data, columns=rs.fields)
    df['date'] = pd.to_datetime(df['date'])
        
    # 转换数值类型
    numeric_cols = ['open', 'high', 'low', 'close', 'preclose', 'volume', 'amount', 'turn', 'pctChg']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
    return df, rs

bs_init()