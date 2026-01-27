"""
共享工具函数

- 股票代码转换
- 行情获取 (带缓存)
"""
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# 行情缓存
QUOTE_CACHE = {}
CACHE_TTL = 300  # 缓存 300 秒 (5分钟)

# 富途格式 -> yfinance 格式 映射
MARKET_SUFFIX_MAP = {
    'US': '',      # 美股无后缀
    'HK': '.HK',   # 港股
    'SH': '.SS',   # 上海
    'SZ': '.SZ',   # 深圳
}


def normalize_symbol(symbol: str) -> str:
    """
    统一股票代码格式 (支持富途格式)
    
    支持的输入格式:
    - yfinance: AAPL, 0700.HK, 600519.SS
    - 富途: US.AAPL, HK.0700, SH.600519, SZ.000001
    
    输出: yfinance 格式
    """
    symbol = symbol.strip().upper()
    if '.' not in symbol:
        return symbol  # 无后缀，当作美股
    
    parts = symbol.split('.', 1)
    prefix, suffix = parts[0], parts[1]
    
    # 富途格式: US.AAPL, HK.0700
    if prefix in MARKET_SUFFIX_MAP:
        return suffix + MARKET_SUFFIX_MAP[prefix]
    
    # 已经是 yfinance 格式: 0700.HK, 600519.SS
    return symbol


def get_quote(symbol: str) -> dict:
    """获取实时行情 (带缓存)"""
    symbol = normalize_symbol(symbol)
    now = time.time()
    
    # 检查缓存
    if symbol in QUOTE_CACHE:
        cached = QUOTE_CACHE[symbol]
        if now - cached['time'] < CACHE_TTL:
            return cached['data']
    
    # 获取新数据
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        # 检查是否找到有效股票
        price = info.get('regularMarketPrice') or info.get('currentPrice') or 0
        if price == 0 and not info.get('shortName'):
            # yfinance 对无效代码返回空 info
            return {'symbol': symbol, 'price': 0, 'error': f'无效代码: {symbol}', 'valid': False}
        
        data = {
            'symbol': symbol,
            'price': price,
            'change': info.get('regularMarketChange', 0),
            'change_pct': info.get('regularMarketChangePercent', 0),
            'name': info.get('shortName', symbol),
            'currency': info.get('currency', 'USD'),
            'valid': True,
        }
        
        QUOTE_CACHE[symbol] = {'data': data, 'time': now}
        return data
    except Exception as e:
        return {'symbol': symbol, 'price': 0, 'error': str(e), 'valid': False}


def get_quotes_batch(symbols: list, max_workers: int = 5) -> dict:
    """
    批量获取行情 (并行)
    
    Args:
        symbols: 股票代码列表
        max_workers: 最大并发数 (默认 5)
    
    Returns:
        {symbol: quote_data} 字典
    """
    if not symbols:
        return {}
    
    # 单个股票直接获取
    if len(symbols) == 1:
        return {symbols[0]: get_quote(symbols[0])}
    
    result = {}
    
    # 并行获取
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_symbol = {
            executor.submit(get_quote, symbol): symbol 
            for symbol in symbols
        }
        
        for future in as_completed(future_to_symbol):
            symbol = future_to_symbol[future]
            try:
                result[symbol] = future.result()
            except Exception as e:
                result[symbol] = {
                    'symbol': symbol, 
                    'price': 0, 
                    'error': str(e), 
                    'valid': False
                }
    
    return result
