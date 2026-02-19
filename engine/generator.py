"""
시그널 생성기 (Main Engine)
- Collector로부터 데이터 수집
- Scorer로 점수 계산
- PositionSizer로 자금 관리
- 최종 Signal 생성 (PART_04.md 기반)
"""

import asyncio
from datetime import date, datetime, timedelta
import time
import sys
import os
from typing import List, Optional, Dict

# sys.path modification removed to prevent conflicts with run.py

from engine.config import SignalConfig, Grade
from engine.models import (
    StockData, Signal, SignalStatus, 
    ScoreDetail, ChecklistDetail, ScreenerResult, ChartData
)
from engine.collectors import KRXCollector, EnhancedNewsCollector
from engine.scorer import Scorer
from engine.position_sizer import PositionSizer
from engine.llm_analyzer import LLMAnalyzer


class SignalGenerator:
    """종가베팅 시그널 생성기 (v2)"""
    
    def __init__(
        self,
        config: SignalConfig = None,
        capital: float = 10_000_000,
    ):
        """
        Args:
            capital: 총 자본금 (기본 5천만원)
            config: 설정 (기본 설정 사용)
        """
        self.config = config or SignalConfig()
        self.capital = capital
        
        self.scorer = Scorer(self.config)
        self.position_sizer = PositionSizer(capital, self.config)
        self.llm_analyzer = LLMAnalyzer() # API Key from env
        
        self._collector: Optional[KRXCollector] = None
        self._news: Optional[EnhancedNewsCollector] = None
    
    async def __aenter__(self):
        self._collector = KRXCollector(self.config)
        await self._collector.__aenter__()
        
        self._news = EnhancedNewsCollector(self.config)
        await self._news.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._collector:
            await self._collector.__aexit__(exc_type, exc_val, exc_tb)
        if self._news:
            await self._news.__aexit__(exc_type, exc_val, exc_tb)
    
    async def generate(
        self,
        target_date: date = None,
        markets: List[str] = None,
        top_n: int = 30,
    ) -> List[Signal]:
        """
        시그널 생성
        
        Args:
            target_date: 대상 날짜 (기본: 오늘)
            markets: 대상 시장 (기본: KOSPI, KOSDAQ)
            top_n: 상승률 상위 N개 종목
        
        Returns:
            Signal 리스트 (등급순 정렬)
        """
        target_date = target_date or date.today()
        # markets = markets or ["KOSPI", "KOSDAQ"]
        markets = markets or ["KOSPI", "KOSDAQ"] 
        
        all_signals = []
        
        for market in markets:
            print(f"\n[{market}] 상승률 상위 종목 스크리닝...")
            
            # 1. 상승률 상위 종목 조회
            candidates = await self._collector.get_top_gainers(market, top_n)
            print(f"  - 1차 필터 통과: {len(candidates)}개")
            
            # 2. 각 종목 분석
            for i, stock in enumerate(candidates):
                print(f"  [{i+1}/{len(candidates)}] {stock.name}({stock.code}) 분석 중...", end='\r')
                
                signal = await self._analyze_stock(stock, target_date)
                
                if signal and signal.grade != Grade.C:
                    all_signals.append(signal)
                    print(f"\n    ✅ {stock.name}: {signal.grade.value}급 시그널 생성! (점수: {signal.score.total})")
                
                # Rate limiting
                # await asyncio.sleep(0.1) # 너무 느려지면 제거
        
        # 3. 등급순 정렬 (S > A > B)
        grade_order = {Grade.S: 0, Grade.A: 1, Grade.B: 2, Grade.C: 3}
        all_signals.sort(key=lambda s: (grade_order[s.grade], -s.score.total))
        
        # 4. 최대 포지션 수 제한
        if len(all_signals) > self.config.max_positions:
            all_signals = all_signals[:self.config.max_positions]
        
        print(f"\n총 {len(all_signals)}개 시그널 생성 완료")
        return all_signals
    
    async def _analyze_stock(
        self,
        stock: StockData,
        target_date: date
    ) -> Optional[Signal]:
        """개별 종목 분석"""
        try:
            # 1. 상세 정보 조회 (이미 top_gainers에서 대부분 가져왔으나 52주 고가 등 보완)
            detail = await self._collector.get_stock_detail(stock.code)
            if detail:
                # 병합 로직 (필요한 정보만 업데이트)
                stock.high_52w = detail.high_52w or stock.high_52w # detail에 값이 있으면 덮어씀
                if detail.marcap: stock.marcap = detail.marcap # 시가총액 업데이트
            
            # 2. 차트 데이터 조회
            charts = await self._collector.get_chart_data(stock.code, 60)
            
            # 3. 뉴스 조회 (본문 포함, 종목명 전달)
            # EnhancedNewsCollector: get_stock_news(code, limit, name)
            news_list = await self._news.get_stock_news(stock.code, 3, stock.name)
            
            # 4. LLM 뉴스 분석 (Rate Limit 방지 Sleep)
            llm_result = None
            if news_list and self.llm_analyzer.model:
                # Gemini Rate Limit 방지 (3.0 유료 모델 테스트: 2초)
                await asyncio.sleep(2)
                
                print(f"    [LLM] {stock.name} 뉴스 분석 중(Analyzing)...")
                news_dicts = [{"title": n.title, "summary": n.summary} for n in news_list]
                llm_result = await self.llm_analyzer.analyze_news_sentiment(stock.name, news_dicts)
                if llm_result:
                   print(f"      -> 점수(Score): {llm_result.get('score')}, 사유(Reason): {llm_result.get('reason')}")

            # 5. 수급 데이터 조회 (CSV에서 로드, 5일 누적)
            supply = await self._collector.get_supply_data(stock.code)
            if supply:
                # print(f"      -> 5일 수급(Supply 5d): 외인 {supply.foreign_buy_5d}, 기관 {supply.inst_buy_5d}")
                pass
            
            # 6. 점수 계산 (LLM 결과 반영)
            score, checklist = self.scorer.calculate(stock, charts, news_list, supply, llm_result)
            
            # 7. 등급 결정
            grade = self.scorer.determine_grade(stock, score)
            
            # C등급은 제외
            if grade == Grade.C:
                # print(f"    ❌ 탈락 {stock.name}: 점수 {score.total}")
                return None
            
            # 7. 포지션 계산
            position = self.position_sizer.calculate(stock.close, grade)
            
            # 8. 시그널 생성
            signal = Signal(
                stock_code=stock.code,
                stock_name=stock.name,
                market=stock.market,
                sector=stock.sector,
                signal_date=target_date,
                signal_time=datetime.now(),
                grade=grade,
                score=score,
                checklist=checklist,
                news_items=[{
                    "title": n.title,
                    "source": n.source,
                    "published_at": n.published_at.isoformat() if n.published_at else "",
                    "url": n.url
                } for n in news_list[:5]], # 상위 5개 뉴스 저장
                current_price=stock.close,
                entry_price=position.entry_price,
                stop_price=position.stop_price,
                target_price=position.target_price,
                r_value=position.r_value,
                position_size=position.position_size,
                quantity=position.quantity,
                r_multiplier=position.r_multiplier,
                trading_value=stock.trading_value,
                change_pct=stock.change_pct,
                status=SignalStatus.PENDING,
                created_at=datetime.now(),
            )
            
            return signal
            
        except Exception as e:
            # print(f"    분석 실패: {e}")
            return None
    
    def get_summary(self, signals: List[Signal]) -> Dict:
        """시그널 요약 정보"""
        summary = {
            "total": len(signals),
            "by_grade": {g.value: 0 for g in Grade},
            "by_market": {},
            "total_position": 0,
            "total_risk": 0,
        }
        
        for s in signals:
            summary["by_grade"][s.grade.value] += 1
            summary["by_market"][s.market] = summary["by_market"].get(s.market, 0) + 1
            summary["total_position"] += s.position_size
            summary["total_risk"] += s.r_value * s.r_multiplier
        
        return summary


async def run_screener(
    capital: float = 50_000_000,
    markets: List[str] = None,
) -> ScreenerResult:
    """
    스크리너 실행 (간편 함수)
    """
    start_time = time.time()
    
    async with SignalGenerator(capital=capital) as generator:
        signals = await generator.generate(markets=markets)
        summary = generator.get_summary(signals)
    
    processing_time = (time.time() - start_time) * 1000
    
    result = ScreenerResult(
        date=date.today(),
        total_candidates=summary["total"],
        filtered_count=len(signals),
        signals=signals,
        by_grade=summary["by_grade"],
        by_market=summary["by_market"],
        processing_time_ms=processing_time,
    )
    
    # 결과 저장 (파일명 충돌 우려로 save_result_to_json은 일단 생략하거나 여기서 구현)
    # save_result_to_json(result) # PART_04.md에 있던 함수인데 여기선 생략
    
    return result

# save_result_to_json 함수도 PART_04.md에 있었으므로 복사
def save_result_to_json(result: ScreenerResult):
    """결과 JSON 저장 (Daily + Latest)"""
    import json
    import shutil
    
    data = {
        "date": result.date.isoformat(),
        "total_candidates": result.total_candidates,
        "filtered_count": result.filtered_count,
        "signals": [s.to_dict() for s in result.signals],
        "by_grade": result.by_grade,
        "by_market": result.by_market,
        "processing_time_ms": result.processing_time_ms,
        "updated_at": datetime.now().isoformat()
    }
    
    # 1. 날짜별 파일 저장
    date_str = result.date.strftime("%Y%m%d")
    filename = f"jongga_v2_results_{date_str}.json"
    
    base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    os.makedirs(base_dir, exist_ok=True)
    
    save_path = os.path.join(base_dir, filename)
    
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"\n[저장 완료] 일간 데이터(Daily): {save_path}")
    
    # 2. Latest 파일 업데이트 (덮어쓰기)
    latest_path = os.path.join(base_dir, "jongga_v2_latest.json")
    with open(latest_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        
    print(f"[저장 완료] 최신 데이터(Latest): {latest_path}")
