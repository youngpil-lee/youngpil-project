
import sys
import os
import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta

# 패키지 경로 설정
sys.path.append(os.getcwd())

from engine.backtester import BacktestEngine

def generate_mock_data(tickers, start_date, end_date):
    """가상의 주가 데이터 생성 (테스트용)"""
    dates = pd.date_range(start=start_date, end=end_date, freq='B')
    data_feed = {}
    
    for ticker in tickers:
        prices = []
        price = 10000
        for _ in dates:
            change = np.random.normal(0, 0.02) # 평균 0, 표준편차 2%
            price = price * (1 + change)
            prices.append(price)
            
        df = pd.DataFrame({
            'open': prices,
            'high': [p * 1.02 for p in prices],
            'low': [p * 0.98 for p in prices],
            'close': prices,
            'volume': [random.randint(100000, 1000000) for _ in prices]
        }, index=dates.strftime("%Y-%m-%d"))
        data_feed[ticker] = df
        
    return data_feed

def mock_strategy(current_date, data_feed):
    """가상의 전략: 랜덤 매수"""
    signals = []
    available_tickers = list(data_feed.keys())
    
    # 10% 확률로 매수 시그널 발생
    if random.random() < 0.3:
        target = random.choice(available_tickers)
        if current_date in data_feed[target].index:
            row = data_feed[target].loc[current_date]
            signals.append({
                "ticker": target,
                "name": f"Stock_{target}",
                "entry_price": row['close'],
                "score": 80
            })
    return signals

def main():
    print("""
╔══════════════════════════════════════════════════════════════╗
║                    KR Market - Backtester                    ║
║                   (Mock Simulation Mode)                     ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    start_date = "2023-01-01"
    end_date = "2023-12-31"
    
    print(f"기간: {start_date} ~ {end_date}")
    print("데이터 생성 중...")
    
    tickers = ["A005930", "A000660", "A035420", "A005380", "A051910"]
    data_feed = generate_mock_data(tickers, start_date, end_date)
    
    engine = BacktestEngine(initial_capital=10_000_000)
    
    print("백테스트 실행 중...")
    engine.run(data_feed, mock_strategy, start_date, end_date)
    
    summary = engine.get_summary()
    
    print("\n[백테스트 결과]")
    print(f"초기 자본: {summary['initial_capital']:,.0f}원")
    print(f"최종 자본: {summary['final_equity']:,.0f}원")
    print(f"수익률: {summary['total_return_pct']:.2f}%")
    print(f"총 매매 횟수: {summary['total_trades']}회")
    print(f"승률: {summary['win_rate']:.2f}%")
    print(f"MDD: {summary['mdd_pct']:.2f}%")
    
    print("\n[매매 기록 (최근 5건)]")
    for t in engine.history[-5:]:
        profit_color = "🔴" if t.profit_pct > 0 else "🔵"
        print(f"{t.exit_date} {profit_color} {t.name} ({t.ticker}): {t.profit_pct:.2f}% ({t.status})")

if __name__ == "__main__":
    main()
