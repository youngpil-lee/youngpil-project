from pykrx import stock as krx_stock
from datetime import datetime, timedelta
import pandas as pd

def test_supply():
    ticker = "005930" # Samsung
    today = "20240419" # Fixed date just to check column names first
    # Let's use real recent dates
    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=10)).strftime("%Y%m%d")
    
    print(f"Fetching from {start_date} to {end_date} for {ticker}")
    df = krx_stock.get_market_trading_value_by_date(start_date, end_date, ticker)
    
    if df.empty:
        print("DataFrame is empty!")
        return
        
    print("Columns in DataFrame:", df.columns.tolist())
    print("Head of DataFrame:")
    print(df.head())
    
    # Check current logic in collectors.py
    target_foreign = '외국인합계' if '외국인합계' in df.columns else '외국인'
    target_inst = '기관합계' if '기관합계' in df.columns else '기관'
    
    f_sum = int(df[target_foreign].sum())
    i_sum = int(df[target_inst].sum())
    
    print(f"\nForeign Sum: {f_sum}")
    print(f"Inst Sum: {i_sum}")

if __name__ == "__main__":
    test_supply()
