
import sys
import os
import asyncio
import traceback

sys.path.append(os.getcwd())

LOG_FILE = "test_log.txt"

def log(msg):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(str(msg) + "\n")
    print(msg)

def test_screener():
    log("\n[TEST] 1. SmartMoneyScreener 테스트 시작...")
    try:
        from screener import SmartMoneyScreener
        screener = SmartMoneyScreener()
        
        log("  - run_screening(max_stocks=3) 실행 중...")
        results = screener.run_screening(max_stocks=3)
        
        if results.empty:
            log("  ⚠️ 스크리닝 결과가 없습니다.")
        else:
            log(f"  ✅ 스크리닝 성공: {len(results)}개 종목 발견")
            # Convert to string and log
            if 'ticker' in results.columns:
                 log(results[['ticker', 'name']].head().to_string())
            else:
                 log(results.head().to_string())
            
            log("\n  - generate_signals 실행 중...")
            signals = screener.generate_signals(results)
            log(f"  ✅ 시그널 생성 성공: {len(signals)}개 시그널")
            if signals:
                log(f"  --> 첫번째 시그널: {signals[0]['name']} (점수: {signals[0]['score']})")
                
    except ImportError as e:
        log(f"  ❌ Import Error: {e}")
    except Exception as e:
        log(f"  ❌ 테스트 중 오류 발생: {e}")
        log(traceback.format_exc())

if __name__ == "__main__":
    # Clear log file
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("Test Started\n")
        
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    try:
        test_screener()
    except Exception as e:
         log(f"Fatal Error: {e}")
         log(traceback.format_exc())
    finally:
        log("Test Complete.")
