import asyncio
from datetime import datetime, timedelta
import pandas as pd
from pykrx import stock as krx_stock
from engine.config import SignalConfig

async def debug_get_top_gainers():
    config = SignalConfig()
    today = "20260221"
    market = "KOSPI"
    top_n = 5
    
    loop = asyncio.get_event_loop()
    df = pd.DataFrame()
    for i in range(10):
        target_date = (datetime.strptime(today, "%Y%m%d") - timedelta(days=i)).strftime("%Y%m%d")
        print(f"Trying date: {target_date}")
        _df = await loop.run_in_executor(None, lambda d=target_date: krx_stock.get_market_ohlcv(d, market=market))
        if not _df.empty and len(_df) > 50:
            print(f"Found data! Length: {len(_df)}")
            df = _df
            break

    if df.empty:
        print("Empty DF after loop.")
        return []

    print("Pre-filters length:", len(df))
    df = df[df['등락률'] >= config.min_change_pct]
    print("After min_change_pct:", len(df))
    df = df[df['등락률'] <= config.max_change_pct]
    print("After max_change_pct:", len(df))
    df = df[df['거래대금'] >= config.min_trading_value]
    print("After min_trading_value:", len(df))
    df = df[df['종가'] >= config.min_price]
    print("After min_price:", len(df))
    df = df[df['종가'] <= config.max_price]
    print("After max_price:", len(df))
    
    df = df.sort_values(by='등락률', ascending=False).head(top_n)
    
    stock_list = []
    print("Columns:", df.columns.tolist())
    for code, row in df.iterrows():
        name = krx_stock.get_market_ticker_name(code)
        if any(keyword in name for keyword in config.exclude_keywords):
            print("Excluded by keyword:", name)
            continue
        
        stock_list.append(name)
    print("returning:", stock_list)

asyncio.run(debug_get_top_gainers())
