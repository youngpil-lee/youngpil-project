"""
자동 실행 스케줄러
- 매일 장 마감 후 스크리닝 실행
- AI 분석 수행
"""

import time
import asyncio
from datetime import datetime

try:
    import schedule
    from engine.generator import run_screener
except ImportError as e:
    print(f"필요한 라이브러리가 없습니다: {e}")
    print("pip install schedule")
    schedule = None

def daily_job():
    print(f"\n[Scheduler] {datetime.now()} 스크리닝 시작...")
    try:
        if asyncio.get_event_loop().is_running():
            # 이미 루프 실행 중이면 (드물겠지만)
            asyncio.create_task(run_screener())
        else:
            asyncio.run(run_screener())
        print(f"[Scheduler] 스크리닝 완료")
    except Exception as e:
        print(f"[Scheduler] 오류 발생: {e}")

def main():
    if not schedule:
        return

    print("⏰ 스케줄러가 시작되었습니다.")
    print("매일 15:40에 실행됩니다. (Ctrl+C로 종료)")
    
    # 장 마감 후 15:40 실행
    schedule.every().day.at("15:40").do(daily_job)
    
    # 테스트용: 1분마다 실행 (주석 처리)
    # schedule.every(1).minutes.do(daily_job)
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n스케줄러 종료")

if __name__ == "__main__":
    main()
