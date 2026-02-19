
import sys
import os
import asyncio
import pandas as pd

# Add current dir to path
sys.path.append(os.getcwd())

async def test_screener():
    print("\n[TEST] 1. SmartMoneyScreener 테스트 시작...", flush=True)
    try:
        from screener import SmartMoneyScreener
        screener = SmartMoneyScreener()
        
        # 1. 스크리닝 (종목 수 최소화)
        print("  - run_screening(max_stocks=5) 실행 중...")
        results = screener.run_screening(max_stocks=5)
        
        if results.empty:
            print("  ⚠️ 스크리닝 결과가 없습니다. (장라벨/휴장일/API문제 가능성)")
        else:
            print(f"  ✅ 스크리닝 성공: {len(results)}개 종목 발견")
            print(results[['ticker', 'name', 'change_pct', 'volume']].head().to_string())
            
            # 2. 시그널 생성
            print("\n  - generate_signals 실행 중...")
            signals = screener.generate_signals(results)
            print(f"  ✅ 시그널 생성 성공: {len(signals)}개 시그널")
            if signals:
                print(f"  --> 첫번째 시그널: {signals[0]['name']} (점수: {signals[0]['score']})")
                
    except ImportError as e:
        print(f"  ❌ Import Error: {e}")
        print("  필요한 라이브러리가 설치되었는지 확인하세요 (pandas, pykrx 등)")
    except Exception as e:
        print(f"  ❌ 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(test_screener())
