# 파트 1 (핵심 로직)

### flask_app.py (file:///Users/seoheun/Documents/kr_market_package/flask_app.py)
```python
#!/usr/bin/env python3
"""
Flask 애플리케이션 진입점
기존 호환성을 위해 유지 - 내부적으로 Blueprint 기반 app 사용

원본 파일은 flask_app_backup.py 에 백업됨
"""

from app import create_app

# 팩토리(Factory) 패턴을 사용하여 Flask 웹 앱 생성
app = create_app()

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 Flask App Starting (Blueprint Version)")
    print("   Original code backed up to: flask_app_backup.py")
    print("="*60 + "\n")
    
    app.run(
        host='0.0.0.0',
        port=5001,
        debug=True,
        use_reloader=False  # 스케줄러(Scheduler) 중복 실행 방지
    )
```

### config.py (file:///Users/seoheun/Documents/kr_market_package/config.py)
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
한국 시장 설정(Configuration)
국장 분석 시스템 설정 - 외인/기관 수급 기반
"""
from dataclasses import dataclass, field
from typing import Literal, Optional, List, Tuple
from enum import Enum


class MarketRegime(Enum):
    """시장 상태"""
    KR_BULLISH = "강세장"      # KOSPI > 20MA > 60MA, 외인 순매수
    KR_NEUTRAL = "중립"        # 혼조세
    KR_BEARISH = "약세장"      # KOSPI < 20MA, 외인 순매도

class SignalType(Enum):
    """진입 시그널 유형"""
    FOREIGNER_BUY = "외인매수"     # 외국인 5일 연속 순매수
    INST_SCOOP = "기관매집"        # 기관 10일 순매수 + 거래량 급증
    DOUBLE_BUY = "쌍끌이"          # 외인 + 기관 동시 매수


@dataclass
class TrendThresholds:
    """수급 트렌드 판단 기준"""
    # 외국인 (Foreign)
    foreign_strong_buy: int = 5_000_000     # 강매수 (5백만주)
    foreign_buy: int = 2_000_000            # 매수 (2백만주)
    foreign_neutral: int = -1_000_000       # 중립
    foreign_sell: int = -2_000_000          # 매도
    foreign_strong_sell: int = -5_000_000   # 강매도
    
    # 기관 (Institutional)
    inst_strong_buy: int = 3_000_000        # 강매수 (3백만주)
    inst_buy: int = 1_000_000               # 매수 (1백만주)
    inst_neutral: int = -500_000            # 중립
    inst_sell: int = -1_000_000             # 매도
    inst_strong_sell: int = -3_000_000      # 강매도
    
    # 비율 기준
    high_ratio_foreign: float = 12.0        # 외국인 고비율
    high_ratio_inst: float = 8.0            # 기관 고비율


@dataclass 
class MarketGateConfig:
    """Market Gate 설정 - 시장 진입 조건"""
    # 환율 기준 (USD/KRW)
    usd_krw_safe: float = 1350.0            # 안전 (초록)
    usd_krw_warning: float = 1400.0         # 주의 (노랑)
    usd_krw_danger: float = 1450.0          # 위험 (빨강)
    
    # KOSPI 기준
    kospi_ma_short: int = 20                # 단기 이평
    kospi_ma_long: int = 60                 # 장기 이평
    
    # 외인 수급 기준
    foreign_net_buy_threshold: int = 500_000_000_000  # 5000억원 순매수


@dataclass
class BacktestConfig:
    """백테스트 설정"""
    # === 진입 조건(Entry Conditions) ===
    entry_trigger: Literal["FOREIGNER_BUY", "INST_SCOOP", "DOUBLE_BUY"] = "DOUBLE_BUY"
    
    # 최소 점수/등급
    min_score: int = 60                     # 최소 수급 점수 (0-100)
    min_consecutive_days: int = 3           # 최소 연속 매수일
    
    # === 청산 조건(Exit Conditions) ===
    stop_loss_pct: float = 5.0              # 손절 (%)
    take_profit_pct: float = 15.0           # 익절 (%)
    trailing_stop_pct: float = 5.0          # 트레일링 스탑 (고점 대비 %)
    max_hold_days: int = 15                 # 최대 보유 기간 (일)
    
    # RSI 기반 청산
    rsi_exit_threshold: int = 70            # RSI 70 도달 시 절반 익절
    
    # 외인 청산 조건
    exit_on_foreign_sell: bool = True       # 외인 순매도 전환 시 청산
    foreign_sell_days: int = 2              # N일 연속 순매도 시
    
    # === 시장 상태(Market Regime) ===
    allowed_regimes: List[str] = field(default_factory=lambda: ["KR_BULLISH", "KR_NEUTRAL"])
    use_usd_krw_gate: bool = True           # 환율 게이트 사용
    
    # === 자금 관리(Money Management) ===
    initial_capital: float = 100_000_000    # 초기 자본 (1억원)
    position_size_pct: float = 10.0         # 포지션 크기 (자본의 %)
    max_positions: int = 10                 # 최대 동시 보유 종목
    
    # === 수수료/슬리피지(Commission/Slippage) ===
    commission_pct: float = 0.015           # 거래 수수료 (0.015%)
    slippage_pct: float = 0.1               # 슬리피지 (0.1%)
    tax_pct: float = 0.23                   # 세금 (매도 시 0.23%)
    
    def get_total_cost_pct(self) -> float:
        """총 거래 비용 (왕복)"""
        return (self.commission_pct * 2) + self.slippage_pct + self.tax_pct
    
    def should_trade_in_regime(self, regime: str) -> bool:
        """해당 시장 상태에서 거래 가능 여부"""
        return regime in self.allowed_regimes
    
    @classmethod
    def conservative(cls) -> "BacktestConfig":
        """보수적 설정 - 안정적 수익 추구(Conservative)"""
        return cls(
            entry_trigger="DOUBLE_BUY",
            min_score=70,
            min_consecutive_days=5,
            stop_loss_pct=3.0,
            take_profit_pct=10.0,
            trailing_stop_pct=4.0,
            max_hold_days=10,
            exit_on_foreign_sell=True,
            foreign_sell_days=1,
            position_size_pct=5.0,
            max_positions=5
        )
    
    @classmethod
    def aggressive(cls) -> "BacktestConfig":
        """공격적 설정 - 고수익 추구(Aggressive)"""
        return cls(
            entry_trigger="FOREIGNER_BUY",
            min_score=50,
            min_consecutive_days=3,
            stop_loss_pct=7.0,
            take_profit_pct=25.0,
            trailing_stop_pct=6.0,
            max_hold_days=20,
            exit_on_foreign_sell=False,
            position_size_pct=15.0,
            max_positions=15
        )


@dataclass
class ScreenerConfig:
    """스크리너 설정"""
    # 데이터 소스
    data_source: Literal["naver", "krx", "both"] = "naver"
    
    # 분석 기간
    lookback_days: int = 60                 # 분석 기간 (일)
    
    # 점수 가중치
    weight_foreign: float = 0.40            # 외국인 수급 (40%)
    weight_inst: float = 0.30               # 기관 수급 (30%)
    weight_technical: float = 0.20          # 기술적 분석 (20%)
    weight_fundamental: float = 0.10        # 펀더멘털 (10%)
    
    # Top N
    top_n: int = 20                         # 상위 N개 종목 선정
    
    # 필터
    min_market_cap: int = 100_000_000_000   # 최소 시총 (1000억)
    min_avg_volume: int = 100_000           # 최소 평균 거래량
    exclude_admin: bool = True              # 관리종목 제외
    exclude_etf: bool = True                # ETF 제외


# === 상수 정의 ===
KOSPI_TICKER = "^KS11"
KOSDAQ_TICKER = "^KQ11"
USD_KRW_TICKER = "KRW=X"

# 섹터 분류 (GICS 기준)
SECTORS = {
    "반도체": ["005930", "000660", "042700"],
    "2차전지": ["373220", "006400", "003670"],
    "자동차": ["005380", "000270", "012330"],
    "조선": ["329180", "009540", "010140"],
    "금융": ["105560", "055550", "086790"],
    "바이오": ["207940", "068270", "326030"],
    "인터넷": ["035420", "035720", "377300"],
    "에너지": ["096770", "010950", "034020"],
}
```

### run.py (file:///Users/seoheun/Documents/kr_market_package/run.py)
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KR Market - 빠른 시작 엔트리 포인트(Entry Point)
바로 실행 가능한 메인 스크립트(Script)
"""

import os
import sys

# 현재 디렉토리를 패키지 루트로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
os.chdir(BASE_DIR)

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
    
    choice = input("\n실행할 기능 번호를 입력하세요 (1-6): ").strip()
    
    if choice == "1":
        print("\n🔍 수급 스크리닝 시작...")
        from screener import SmartMoneyScreener
        screener = SmartMoneyScreener()
        results = screener.run_screening(max_stocks=50)
        print(f"\n✅ 스크리닝 완료! {len(results)}개 종목 분석됨")
        print(results.head(10).to_string())
        
    elif choice == "2":
        print("\n📊 VCP 시그널 생성...")
        from screener import SmartMoneyScreener
        screener = SmartMoneyScreener()
        results = screener.run_screening(max_stocks=30)
        signals = screener.generate_signals(results)
        print(f"\n✅ {len(signals)}개 시그널 생성됨")
        
    elif choice == "3":
        print("\n🎯 종가베팅 V2 실행...")
        from engine.generator import run_screener
        results = run_screener()
        print(f"\n✅ 완료!")
        
    elif choice == "4":
        print("\n🤖 AI 분석 시작...")
        from kr_ai_analyzer import KrAiAnalyzer
        analyzer = KrAiAnalyzer()
        # 샘플 종목 분석
        result = analyzer.analyze_stock("005930")  # 삼성전자
        print(result)
        
    elif choice == "5":
        print("\n📈 백테스트 실행...")
        from run_backtest import main as run_backtest_main
        run_backtest_main()
        
    elif choice == "6":
        print("\n⏰ 스케줄러 실행...")
        from scheduler import main as scheduler_main
        scheduler_main()
        
    else:
        print("잘못된 선택입니다.")
        
    input("\n아무 키나 눌러 종료...")

if __name__ == "__main__":
    main()
```

### models.py (file:///Users/seoheun/Documents/kr_market_package/models.py)
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KR Market - Data Models
국장 분석 시스템 데이터 모델
"""
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict
from datetime import datetime


@dataclass
class StockInfo:
    """종목 기본 정보"""
    ticker: str
    name: str
    market: str                         # KOSPI / KOSDAQ
    sector: Optional[str] = None
    market_cap: Optional[int] = None    # 시가총액
    is_etf: bool = False
    is_admin: bool = False              # 관리종목


@dataclass
class InstitutionalFlow:
    """기관/외국인 수급 데이터"""
    ticker: str
    date: str
    
    # 외국인 순매매
    foreign_net_buy: int = 0            # 주수
    foreign_net_buy_amount: int = 0     # 금액 (원)
    foreign_holding_pct: float = 0.0    # 보유 비율 (%)
    
    # 기관 순매매  
    inst_net_buy: int = 0
    inst_net_buy_amount: int = 0
    
    # 개인 순매매
    retail_net_buy: int = 0
    retail_net_buy_amount: int = 0
    
    # 거래량
    volume: int = 0
    close_price: float = 0.0


@dataclass
class TrendAnalysis:
    """수급 트렌드 분석 결과"""
    ticker: str
    analysis_date: str
    
    # 기간별 외국인 순매매
    foreign_net_60d: int = 0
    foreign_net_20d: int = 0
    foreign_net_10d: int = 0
    foreign_net_5d: int = 0
    
    # 기간별 기관 순매매
    inst_net_60d: int = 0
    inst_net_20d: int = 0
    inst_net_10d: int = 0
    inst_net_5d: int = 0
    
    # 거래량 대비 비율
    foreign_ratio_20d: float = 0.0
    inst_ratio_20d: float = 0.0
    
    # 연속 매수일
    foreign_consecutive_buy_days: int = 0
    inst_consecutive_buy_days: int = 0
    
    # 트렌드 판단
    foreign_trend: str = "neutral"      # strong_buying, buying, neutral, selling, strong_selling
    inst_trend: str = "neutral"
    
    # 종합 점수 (0-100)
    supply_demand_score: float = 50.0
    supply_demand_stage: str = "중립"   # 강한매집, 매집, 약매집, 중립, 약분산, 분산, 강한분산
    
    # 매집 신호
    is_double_buy: bool = False         # 쌍끌이
    accumulation_intensity: str = "보통"
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class Signal:
    """매수/매도 시그널"""
    ticker: str
    name: str
    signal_type: str                    # FOREIGNER_BUY, INST_SCOOP, DOUBLE_BUY
    signal_time: int                    # Unix timestamp
    
    # 시그널 강도
    score: int                          # 0-100
    grade: str                          # A, B, C, D
    
    # 가격 정보
    price: float
    pivot_high: Optional[float] = None  # 돌파 기준점
    
    # 수급 정보
    foreign_net_5d: int = 0
    inst_net_5d: int = 0
    consecutive_days: int = 0
    
    # 시장 상태
    market_regime: str = "KR_NEUTRAL"
    usd_krw: float = 0.0
    
    # 기술적 지표
    rsi: Optional[float] = None
    ma_alignment: Optional[str] = None  # 정배열, 역배열, 혼조
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class Trade:
    """개별 거래 기록"""
    ticker: str
    name: str
    
    # 진입
    entry_time: int                     # Unix timestamp
    entry_price: float
    entry_type: str                     # FOREIGNER_BUY, INST_SCOOP, DOUBLE_BUY
    entry_score: int
    
    # 청산 (진행 중이면 None)
    exit_time: Optional[int] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None   # STOP_LOSS, TAKE_PROFIT, TRAILING_STOP, TIME_EXIT, FOREIGN_SELL, RSI_EXIT
    
    # 포지션 정보
    quantity: int = 0
    position_value: float = 0.0
    stop_loss: float = 0.0
    take_profit: Optional[float] = None
    
    # 수급 정보 (진입 시점)
    foreign_net_5d: int = 0
    inst_net_5d: int = 0
    
    # 시장 상태
    market_regime: str = "KR_NEUTRAL"
    
    @property
    def is_closed(self) -> bool:
        return self.exit_price is not None
    
    @property
    def return_pct(self) -> float:
        if not self.is_closed:
            return 0.0
        return ((self.exit_price - self.entry_price) / self.entry_price) * 100
    
    @property
    def pnl(self) -> float:
        """손익 금액"""
        if not self.is_closed:
            return 0.0
        return (self.exit_price - self.entry_price) * self.quantity
    
    @property
    def r_multiple(self) -> float:
        """리스크 대비 수익 (R-Multiple)"""
        if not self.is_closed or self.stop_loss == 0:
            return 0.0
        risk = self.entry_price - self.stop_loss
        if risk <= 0:
            return 0.0
        reward = self.exit_price - self.entry_price
        return reward / risk
    
    @property
    def is_winner(self) -> bool:
        return self.return_pct > 0
    
    @property
    def holding_days(self) -> int:
        if not self.is_closed:
            return 0
        return (self.exit_time - self.entry_time) // 86400
    
    def to_dict(self) -> Dict:
        d = asdict(self)
        d['is_closed'] = self.is_closed
        d['return_pct'] = self.return_pct
        d['pnl'] = self.pnl
        d['r_multiple'] = self.r_multiple
        d['is_winner'] = self.is_winner
        d['holding_days'] = self.holding_days
        return d


@dataclass
class BacktestResult:
    """백테스트 결과"""
    # 설정
    config_name: str
    start_date: str
    end_date: str
    
    # 거래 통계
    total_trades: int = 0
    winners: int = 0
    losers: int = 0
    
    # 수익률
    win_rate: float = 0.0
    avg_return_pct: float = 0.0
    avg_winner_pct: float = 0.0
    avg_loser_pct: float = 0.0
    
    # R-Multiple
    avg_r_multiple: float = 0.0
    total_r: float = 0.0
    
    # 리스크 지표
    total_return_pct: float = 0.0
    max_drawdown_pct: float = 0.0
    sharpe_ratio: float = 0.0
    
    # 벤치마크 비교
    kospi_return_pct: float = 0.0
    kosdaq_return_pct: float = 0.0
    alpha: float = 0.0                  # KOSPI 대비 초과수익
    
    # 자금
    initial_capital: float = 0.0
    final_capital: float = 0.0
    
    # 기간 통계
    avg_holding_days: float = 0.0
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0
    
    # 시그널별 통계
    signal_stats: Dict = field(default_factory=dict)
    
    # 상세 데이터
    trades: List[Trade] = field(default_factory=list)
    equity_curve: List[tuple] = field(default_factory=list)  # [(timestamp, equity), ...]
    
    def to_dict(self) -> Dict:
        d = asdict(self)
        d['trades'] = [t.to_dict() if hasattr(t, 'to_dict') else t for t in self.trades]
        return d


@dataclass
class MarketStatus:
    """현재 시장 상태"""
    timestamp: int
    
    # 지수
    kospi: float = 0.0
    kospi_change_pct: float = 0.0
    kosdaq: float = 0.0
    kosdaq_change_pct: float = 0.0
    
    # 환율
    usd_krw: float = 0.0
    usd_krw_change_pct: float = 0.0
    
    # 외인/기관 당일 순매매 (전체)
    foreign_net_total: int = 0          # 금액 (억원)
    inst_net_total: int = 0
    retail_net_total: int = 0
    
    # 시장 상태
    regime: str = "KR_NEUTRAL"
    regime_score: float = 50.0          # 0-100 (100이면 매우 강세)
    
    # 게이트 상태
    is_gate_open: bool = True
    gate_reason: str = ""
    
    def to_dict(self) -> Dict:
        return asdict(self)
```

