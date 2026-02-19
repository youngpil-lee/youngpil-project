#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KR Market - 빠른 시작 엔트리 포인트(Entry Point)
바로 실행 가능한 메인 스크립트(Script)
"""

import os
import sys
import logging

# 현재 디렉토리를 패키지 루트로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
os.chdir(BASE_DIR)

# 로깅 설정
logging.basicConfig(
    filename='run_log.txt',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8' # Python 3.9+
)

def log_print(msg):
    print(msg, flush=True)
    logging.info(msg)

def main():
    print("""
╔══════════════════════════════════════════════════════════════╗
║               KR Market - Smart Money Screener               ║
║                   외인/기관 수급 분석 시스템                   ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    print("사용 가능한 기능:")
    print("-" * 60)
    print("1. 수급 스크리닝      - 외인/기관 매집 종목 탐지")
    print("2. VCP 시그널 생성    - 변동성 수축 패턴 종목 발굴")
    print("3. 종가베팅 V2        - 고급 시그널 생성")
    print("4. AI 분석            - Gemini 기반 종목 분석")
    print("5. 백테스트           - 전략 성과 검증")
    print("6. 스케줄러 실행      - 자동 데이터 업데이트")
    print("-" * 60)
    
    print(f"\n[Arguments] {sys.argv}")
    if len(sys.argv) > 1:
        choice = sys.argv[1]
        log_print(f"선택된 메뉴: {choice} (자동 실행)")
    else:
        choice = input("\n실행할 기능 번호를 입력하세요 (1-6): ").strip()
    
    if choice == "1":
        log_print("\n🔍 수급 스크리닝 시작...")
        try:
            from screener import SmartMoneyScreener
            screener = SmartMoneyScreener()
            results = screener.run_screening(max_stocks=50)
            
            if results is not None and not results.empty:
                log_print(f"\n✅ 스크리닝 완료! {len(results)}개 종목 분석됨")
                log_print("\n[상위 10개 종목]")
                columns_to_show = ['ticker', 'name', 'close', 'change_pct', 'foreign_buy', 'inst_buy']
                valid_columns = [c for c in columns_to_show if c in results.columns]
                log_print(results[valid_columns].head(10).to_string(index=False))
            else:
                log_print("\n⚠️ 검색된 종목이 없거나 데이터를 가져오지 못했습니다.")
                
        except Exception as e:
            log_print(f"Error: 스크리닝 중 오류 발생 ({e})")
        
    elif choice == "2":
        log_print("\n📊 VCP 시그널 생성...")
        try:
            from screener import SmartMoneyScreener
            screener = SmartMoneyScreener()
            # 1단계: 스크리닝
            df = screener.run_screening(max_stocks=30)
            
            if df is not None and not df.empty:
                log_print(f"✅ 1차 스크리닝: {len(df)}개 종목 추출")
                # 2단계: 시그널 생성 (VCP 등)
                signals = screener.generate_signals(df)
                
                log_print(f"\n✅ {len(signals)}개 시그널 생성됨")
                for s in signals[:5]: # 상위 5개만 출력
                    log_print(f"- [{s['ticker']}] {s['name']}: {s['score']}점")
            else:
                log_print("⚠️ 스크리닝된 종목이 없습니다.")

        except Exception as e:
            log_print(f"Error: 시그널 생성 중 오류 발생 ({e})")
        
    elif choice == "3":
        log_print("\n🎯 종가베팅 V2 실행...")
        try:
            from engine.generator import run_screener
            # asyncio.run 필요 (engine/generator.py는 async 함수)
            import asyncio
            
            # 이미 루프가 도는 경우 처리 (Jupyter 등)
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                log_print("⚠️ 비동기 루프가 이미 실행 중입니다. (Nest Asyncio 필요)")
            else:
                result = asyncio.run(run_screener())
                log_print(f"\n✅ V2 스크리닝 완료! {result.filtered_count}개 시그널")
                if result.signals:
                    for s in result.signals[:5]:
                        log_print(f"- {s.stock_name} ({s.grade.value}급): {s.score.total}점")
        except Exception as e:
            log_print(f"Error running screener v2: {e}")
        
    elif choice == "4":
        log_print("\n🤖 AI 분석 시작...")
        try:
            from kr_ai_analyzer import KrAiAnalyzer
            analyzer = KrAiAnalyzer()
            
            # 메뉴 서브 선택
            sub_choice = "2" # 기본값
            if len(sys.argv) > 2:
                sub_choice = sys.argv[2]
            else:
                print("  1. 종목 분석 (삼성전자)")
                print("  2. 시장 전망 (Market Outlook)")
                print("  3. 포트폴리오 진단")
                sub_choice = input("  선택 (기본: 2): ").strip() or "2"
            
            if sub_choice == "1":
                result = analyzer.analyze_stock("005930")
                log_print(result)
            elif sub_choice == "3":
                pf = [
                    {"ticker": "005930", "name": "삼성전자", "profit_pct": -2.5, "weight": 40},
                    {"ticker": "000660", "name": "SK하이닉스", "profit_pct": 15.2, "weight": 30},
                    {"ticker": "035420", "name": "NAVER", "profit_pct": -10.5, "weight": 30}
                ]
                result = analyzer.analyze_user_portfolio(pf)
                log_print(result)
            else:
                result = analyzer.analyze_market_outlook()
                log_print(result)
                
        except ImportError:
            log_print("Error: kr_ai_analyzer.py missing.")
        except Exception as e:
            import traceback
            traceback.print_exc()
            log_print(f"Error: {e}")
        
    elif choice == "5":
        log_print("\n📈 백테스트 실행...")
        try:
            import run_backtest
            run_backtest.main()
        except ImportError:
            log_print("Error: run_backtest.py missing.")
        except Exception as e:
            log_print(f"Error running backtest: {e}")
        
    elif choice == "6":
        log_print("\n⏰ 스케줄러 실행...")
        try:
            import scheduler
            scheduler.main()
        except ImportError:
             log_print("Error: scheduler.py missing.")
        except Exception as e:
            log_print(f"Error running scheduler: {e}")
            
    else:
        log_print("잘못된 선택입니다.")
        
    if len(sys.argv) == 1:
        input("\n아무 키나 눌러 종료...")

if __name__ == "__main__":
    import asyncio
    # if sys.platform.startswith('win'):
    #    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    main()
