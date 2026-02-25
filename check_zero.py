import asyncio
import pandas as pd
from screener import SmartMoneyScreener

async def test():
    screener = SmartMoneyScreener()
    print("Running screening...")
    df = screener.run_screening(max_stocks=3)
    if df.empty:
        print("Empty DataFrame")
        return
    
    print("Screening Results:")
    print(df[['ticker', 'name', 'foreign_buy', 'inst_buy']])
    
    print("\nGenerating signals...")
    signals = screener.generate_signals(df)
    print(f"Signals found: {len(signals)}")
    for s in signals:
        print(f"- {s['name']}: Score={s['score']}, Foreign={s['foreign_5d']}, Inst={s['inst_5d']}")

if __name__ == "__main__":
    asyncio.run(test())
