"""
VCP 및 수급 스크리너 (Smart Money Screening)
- 외국인/기관 수급 분석
- VCP (변동성 수축) 패턴 감지
- 최종 시그널 생성
"""

import asyncio
import pandas as pd
from datetime import datetime, date
from typing import List, Dict, Optional

from engine.config import SignalConfig, Grade
from engine.collectors import KRXCollector
from engine.models import StockData, Signal, SignalStatus

class SmartMoneyScreener:
    """수급 및 VCP 스크리너"""
    
    def __init__(self):
        self.config = SignalConfig()
        
    def run_screening(self, max_stocks: int = 50) -> pd.DataFrame:
        """
        1차 스크리닝: 상승률 상위 종목 + 수급 데이터 수집
        Returns: DataFrame (ticker, name, close, change, volume, foreign_buy, inst_buy)
        """
        print(f"🔍 [SmartMoneyScreener] {max_stocks}개 종목 스크리닝 시작...")
        
        # 비동기 실행을 위한 래퍼 함수
        async def _collect_data():
            collector = KRXCollector(self.config)
            
            # 1. 상승률 상위 종목 조회 (KOSPI/KOSDAQ)
            kospi_top = await collector.get_top_gainers("KOSPI", top_n=max_stocks // 2)
            kosdaq_top = await collector.get_top_gainers("KOSDAQ", top_n=max_stocks // 2)
            
            all_stocks = kospi_top + kosdaq_top
            
            # 2. 수급 데이터 병렬 수집
            tasks = [collector.get_supply_data(s.code) for s in all_stocks]
            supplies = await asyncio.gather(*tasks)
            
            # 3. 데이터 결합
            results = []
            for stock, supply in zip(all_stocks, supplies):
                if supply:
                    row = {
                        "ticker": stock.code,
                        "name": stock.name,
                        "market": stock.market,
                        "close": stock.close,
                        "change_pct": stock.change_pct,
                        "volume": stock.volume,
                        "trading_value": stock.trading_value,
                        "foreign_buy": supply.foreign_buy_5d,
                        "inst_buy": supply.inst_buy_5d,
                        "is_double_buy": supply.foreign_buy_5d > 0 and supply.inst_buy_5d > 0
                    }
                    results.append(row)
            
            return pd.DataFrame(results)

        try:
            # 기존 루프나 새 루프 사용
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 이미 실행 중인 루프가 있으면 (예: Jupyter) nest_asyncio 필요하나
                    # 여기서는 그냥 새 태스크로 실행 불가하므로 동기함수지만 await 불가
                    # 일반 파이썬 스크립트 실행 환경 가정 -> asyncio.run
                    pass
            except RuntimeError:
                pass
                
            return asyncio.run(_collect_data())
            
        except Exception as e:
            print(f"❌ 스크리닝 실패: {e}")
            return pd.DataFrame()

    def generate_signals(self, df: pd.DataFrame) -> List[Dict]:
        """
        2차 분석: VCP 패턴 및 정밀 점수 산출
        Args:
            df: run_screening 결과 DataFrame
        Returns:
            List of signal dicts
        """
        if df.empty:
            return []
            
        print(f"📊 [SmartMoneyScreener] {len(df)}개 후보군 정밀 분석(VCP)...")
        
        signals = []
        
        # 비동기 실행 (차트 데이터 조회용)
        async def _analyze_vcp(row):
            collector = KRXCollector(self.config)
            
            # 차트 데이터 조회 (60일)
            charts = await collector.get_chart_data(row['ticker'], days=60)
            if not charts:
                return None
                
            # VCP 패턴 감지
            vcp_score, contraction_ratio = self.detect_vcp_pattern(charts)
            
            # 수급 점수 계산
            supply_data = type('Supply', (), {
                'foreign_buy_5d': row['foreign_buy'], 
                'inst_buy_5d': row['inst_buy']
            })
            total_score = self._calculate_score(row, supply_data, vcp_score)
            
            # Debug log
            if total_score > 30:
                print(f"  - [{row['ticker']}] {row['name']}: {total_score}점 (VCP: {vcp_score:.1f}, Vol: {contraction_ratio:.3f})")

            # 52주 신고가 (chart max high)
            high_52w = max([c.high for c in charts]) if charts else 0
            
            # 시그널 생성 조건 (점수 50점 이상으로 완화)
            if total_score >= 50:
                signal = {
                    "ticker": row['ticker'],
                    "name": row['name'],
                    "status": "OPEN",
                    "signal_date": date.today().isoformat(),
                    "entry_price": row['close'],
                    "score": total_score,
                    "contraction_ratio": contraction_ratio,
                    "foreign_5d": row['foreign_buy'],
                    "inst_5d": row['inst_buy'],
                    "high_52w": high_52w,
                    "market": row['market']
                }
                return signal
            return None

        async def _process_all():
             tasks = []
             # DataFrame 순회
             for _, row in df.iterrows():
                 tasks.append(_analyze_vcp(row))
             
             results = await asyncio.gather(*tasks)
             return [r for r in results if r is not None]

        try:
             signals = asyncio.run(_process_all())
             # 점수순 정렬
             signals.sort(key=lambda x: x['score'], reverse=True)
             return signals
        except Exception as e:
            print(f"❌ 시그널 생성 실패: {e}")
            return []

    def detect_vcp_pattern(self, charts: List[Dict]) -> (float, float):
        """
        VCP 패턴 감지
        Returns: (score, contraction_ratio)
        """
        if len(charts) < 20:
            return 0, 1.0 # 데이터 부족
            
        # 최근 데이터부터 역순으로 분석
        # charts[-1]이 오늘
        current_close = charts[-1].close
        
        # 최근 20일 고가/저가
        recent_high = max([c.high for c in charts[-20:]])
        recent_low = min([c.low for c in charts[-20:]])
        
        if recent_high == 0: return 0, 1.0
        
        # 변동성 비율 (Contraction Ratio)
        # (고가 - 저가) / 고가
        volatility = (recent_high - recent_low) / recent_high
        
        # 축소 비율 (단순화: 변동성이 작을수록 수축된 것)
        # 0.1 (10%) 이하면 매우 좋음 -> 10점
        # 0.2 (20%) 이하면 좋음 -> 5점
        # 그 이상이면 0점
        
        score = 0
        if volatility <= 0.10:
            score = 10
        elif volatility <= 0.15: # 15%
            score = 7
        elif volatility <= 0.20:
            score = 5
        elif volatility <= 0.30:
            score = 2
            
        # 추가: 거래량 감소 확인 (최근 5일 평균 < 20일 평균)
        vol_5 = sum([c.volume for c in charts[-5:]]) / 5
        vol_20 = sum([c.volume for c in charts[-20:]]) / 20
        
        if vol_5 < vol_20:
            score += 5 # 거래량 감소 가산점
            
        # 신고가 근처인지 확인 (최근 고점이 60일 고점의 90% 이상)
        high_60 = max([c.high for c in charts])
        if recent_high >= high_60 * 0.9:
            score += 5 # 신고가 가산점
            
        return score, volatility

    def _calculate_score(self, stock_row, supply, vcp_score) -> float:
        """
        수급 + VCP 종합 점수 계산 (100점 만점)
        """
        total_score = 0
        
        # 1. 수급 점수 (50점)
        # 외국인 순매수 (25점)
        if supply.foreign_buy_5d > 5_000_000_000: # 50억 이상
            total_score += 25
        elif supply.foreign_buy_5d > 1_000_000_000: # 10억 이상
            total_score += 15
        elif supply.foreign_buy_5d > 0:
            total_score += 5
            
        # 기관 순매수 (25점)
        if supply.inst_buy_5d > 3_000_000_000: # 30억 이상
            total_score += 25
        elif supply.inst_buy_5d > 1_000_000_000: # 10억 이상
            total_score += 15
        elif supply.inst_buy_5d > 0:
            total_score += 5
            
        # 2. 거래대금/거래량 점수 (20점)
        if stock_row['trading_value'] >= 100_000_000_000: # 1천억
            total_score += 20
        elif stock_row['trading_value'] >= 50_000_000_000: # 500억
            total_score += 10
        elif stock_row['trading_value'] >= 10_000_000_000: # 100억
            total_score += 5
            
        # 3. 등락률 점수 (10점) - 너무 급등하지 않은 것 선호
        change = stock_row['change_pct']
        if 5.0 <= change <= 15.0:
            total_score += 10
        elif change < 5.0: # 너무 조금 오름
            total_score += 5
        # 15% 이상 급등은 차익실현 매물 위험으로 점수 낮게
            
        # 4. VCP 점수 (20점 만점으로 환산)
        # vcp_score는 detect_vcp_pattern에서 최대 20점 정도 나옴
        total_score += vcp_score
        
        return total_score
