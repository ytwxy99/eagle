
import datetime
import os

from src.data.akshare_client import get_all_stocks, get_historical_data


def get_stock_data(stock_code, start_date, end_date=None):
    """获取股票数据"""
    data = get_historical_data(
        stock_code=stock_code,
        start_date=start_date,
        end_date=end_date,
        frequency='d',
        adjustflag='3'  # 不复权
    )
        
    if data.empty:
        raise ValueError(f"无法获取股票{stock_code}的数据")
        
    # 设置日期为索引
    data.set_index('date', inplace=True)
    data.sort_index(inplace=True)
        
    return data
    

def get_all_a_stock_codes():
    cache_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'all_stock_codes.txt')    
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                codes = [line.strip() for line in f if line.strip()]
            if codes:
                print(f"📁 从缓存读取股票代码: {len(codes)} 只")
                return codes
        except Exception as e:
            print(f"⚠️ 读取缓存失败: {e}")
    
    # 实时获取股票代码
    print("📡 正在实时获取A股股票代码列表...")
    
    try:
        stock_df = get_all_stocks()
            
        if stock_df.empty:
            return list()
            
        # 过滤A股股票
        a_stock_codes = []
        for code in stock_df['code']:
            if isinstance(code, str):
                code = str(code).strip()
                if (code.startswith('sh.60') or  # 上海主板
                    code.startswith('sz.00') or   # 深圳主板
                    code.startswith('sz.30') or   # 创业板
                    code.startswith('sh.68')):    # 科创板
                    a_stock_codes.append(code)
            
        # 保存到缓存文件
        os.makedirs(os.path.dirname(cache_file), exist_ok=True)
        with open(cache_file, 'w', encoding='utf-8') as f:
            for code in a_stock_codes:
                f.write(f"{code}\n")
            
        print(f"✅ 成功获取并缓存 {len(a_stock_codes)} 只A股股票")
        return a_stock_codes
            
    except Exception as e:
        print(f"⚠️ 获取股票代码失败: {e}")
        # 尝试从缓存读取（如果存在）
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    codes = [line.strip() for line in f if line.strip()]
                if codes:
                    print(f"📁 从缓存恢复股票代码: {len(codes)} 只")
                    return codes
            except:
                pass
        
        return list()

