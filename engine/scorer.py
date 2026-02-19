"""
점수 계산기 (Scorer)
- 다양한 요소(뉴스, 수급, 차트 등)를 종합하여 점수 산출
- 최종 등급 결정
"""

from engine.config import SignalConfig, Grade
from engine.models import StockData, ScoreDetail, ChecklistDetail

class Scorer:
    """종가베팅 점수 계산기"""
    
    def __init__(self, config: SignalConfig):
        self.config = config
        
    def calculate(self, stock: StockData, charts: list, news_list: list, supply: any, llm_result: dict = None):
        """
        종합 점수 계산
        Returns: (ScoreDetail, ChecklistDetail)
        """
        score = ScoreDetail()
        checklist = ChecklistDetail()
        
        # 1. 뉴스 점수 (최대 3점)
        if llm_result:
            score.news = float(llm_result.get('score', 0))
        else:
            # LLM 결과 없으면 키워드 기반 간이 점수 (여기서는 생략, 기본 0)
            score.news = 0
            
        # 2. 거래대금 점수 (최대 3점)
        # 1조 이상: 3점, 5천억 이상: 2점, 1천억 이상: 1점
        if stock.trading_value >= 1_000_000_000_000:
            score.volume = 3
        elif stock.trading_value >= 500_000_000_000:
            score.volume = 2
        elif stock.trading_value >= 100_000_000_000:
            score.volume = 1
        else:
            score.volume = 0
            
        # 3. 수급 점수 (최대 2점)
        # 외인/기관 동시 순매수: 2점, 하나만: 1점
        if supply:
            is_foreign_buy = supply.foreign_buy_5d > 0
            is_inst_buy = supply.inst_buy_5d > 0
            
            if is_foreign_buy and is_inst_buy:
                score.supply = 2
                checklist.is_supply_good = True
            elif is_foreign_buy or is_inst_buy:
                score.supply = 1
            else:
                score.supply = 0
        
        # 4. 차트/캔들/기간조정 점수 (간이 로직)
        # 실제로는 이동평균선, 볼린저밴드 등 기술적 분석 필요
        # 여기서는 등락률과 신고가 여부 등으로 대체
        
        # 차트 (2점): 신고가 근처 (52주 고가의 90% 이상)
        if stock.high_52w > 0 and stock.close >= stock.high_52w * 0.9:
            score.chart = 2
            checklist.is_vcp = True # 신고가 근처를 VCP 후보로 간주
        elif stock.high_52w > 0 and stock.close >= stock.high_52w * 0.8:
            score.chart = 1
            
        # 캔들 (1점): 장대양봉 (5% 이상 상승)
        if stock.change_pct >= 5.0:
            # 윗꼬리 계산 필요하나 데이터 부족으로 생략
            score.chart += 0.5 # 캔들 점수를 chart에 합산하거나 별도 필드 사용
            
        # 총점 계산
        score.total = score.news + score.volume + score.supply + score.chart
        
        return score, checklist
        
    def determine_grade(self, stock: StockData, score: ScoreDetail) -> Grade:
        """점수와 기타 조건으로 등급 결정"""
        total_score = score.total
        
        # S급 조건
        s_config = self.config.grade_configs[Grade.S]
        if (total_score >= s_config.min_score and 
            stock.trading_value >= s_config.min_trading_value):
            return Grade.S
            
        # A급 조건
        a_config = self.config.grade_configs[Grade.A]
        if (total_score >= a_config.min_score and 
            stock.trading_value >= a_config.min_trading_value):
            return Grade.A
            
        # B급 조건
        b_config = self.config.grade_configs[Grade.B]
        if (total_score >= b_config.min_score and 
            stock.trading_value >= b_config.min_trading_value):
            return Grade.B
            
        return Grade.C
