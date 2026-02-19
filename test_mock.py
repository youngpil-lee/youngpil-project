
import sys
import os
import asyncio
from unittest.mock import MagicMock
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

# 1. Mock dependencies
sys.modules["pykrx"] = MagicMock()
sys.modules["pykrx.stock"] = MagicMock()
sys.modules["google"] = MagicMock()
sys.modules["google.generativeai"] = MagicMock()

# Try to use real pandas, if fails use mock
try:
    import pandas as pd
except ImportError:
    sys.modules["pandas"] = MagicMock()
    pd = MagicMock()

# Re-mock pykrx components that might be imported specifically
sys.modules["pykrx.stock"] = MagicMock()

# 2. Import modules
sys.path.append(os.getcwd())
try:
    from engine.models import StockData, ChartData
    from engine.config import SignalConfig
    from engine.collectors import KRXCollector, EnhancedNewsCollector
    from screener import SmartMoneyScreener
except ImportError as e:
    print(f"Import failed: {e}")
    sys.exit(1)

# 3. Mock KRXCollector methods (Monkey Patching)
async def mock_get_top_gainers(self, market, top_n):
    print(f"  [Mock] get_top_gainers({market}) called")
    return [
        StockData(code="005930", name="삼성전자", market="KOSPI", close=70000, change_pct=3.5, trading_value=100000000000, volume=1000000, high_52w=80000),
        StockData(code="000660", name="SK하이닉스", market="KOSPI", close=120000, change_pct=4.2, trading_value=500000000000, volume=500000, high_52w=140000),
    ]

async def mock_get_supply_data(self, code):
    # print(f"  [Mock] get_supply_data({code}) called")
    class Supply:
        foreign_buy_5d = 10000000000
        inst_buy_5d = 5000000000
    return Supply()

async def mock_get_chart_data(self, code, days):
    # print(f"  [Mock] get_chart_data({code}) called")
    charts = []
    import datetime
    base = datetime.datetime.today()
    for i in range(days):
        d = (base - datetime.timedelta(days=days-i)).strftime("%Y-%m-%d")
        # Generate dummy data
        charts.append(ChartData(date=d, open=100, high=110, low=90, close=105, volume=1000))
    # Make last one match VCP (low volatility)
    charts[-1].close = 108
    charts[-1].high = 109 
    charts[-1].low = 107
    return charts

async def mock_get_stock_detail(self, code):
    return StockData(code=code, name="MockStock", market="KOSPI", marcap=5000000000000)
    
async def mock_get_stock_news(self, code, limit=3, stock_name=""):
    return [] # Empty news

# Patch
KRXCollector.get_top_gainers = mock_get_top_gainers
KRXCollector.get_supply_data = mock_get_supply_data
KRXCollector.get_chart_data = mock_get_chart_data
KRXCollector.get_stock_detail = mock_get_stock_detail
EnhancedNewsCollector.get_stock_news = mock_get_stock_news


# 4. Run Test (Sync wrapper because screener uses asyncio.run internally)
def run_test():
    print(">>> Starting Mock Test (Logic Verification)")
    screener = SmartMoneyScreener()
    
    print("\n1. Testing run_screening...")
    # ... (rest of logic same)
    df = screener.run_screening(max_stocks=2)
    
    if isinstance(df, pd.DataFrame):
        print(f"Screening Results (DataFrame): Shape={df.shape}")
        if not df.empty:
            print(df.to_string())
        else:
            print("DataFrame is empty")
    else:
        print("Screening Results:", df)
    
    print("\n2. Testing generate_signals...")
    # This calls detect_vcp_pattern
    signals = screener.generate_signals(df)
    
    print(f"Generated {len(signals)} signals")
    if signals:
        s = signals[0]
        print(f"First Signal: {s['name']} (Score: {s['score']})")
        print(f"  - Status: {s['status']}")
        print(f"  - Entry: {s['entry_price']}")
        
if __name__ == "__main__":
    # Remove asyncio.set_event_loop_policy if not using explicit loop here
    # but screener might need it? 
    # Usually asyncio.run handles policy if not set.
    # But on Windows, specific policy is often needed.
    if sys.platform.startswith('win'):
        # For python 3.8+ on Windows
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    run_test()
