from dataclasses import dataclass, field, asdict
from datetime import datetime, date
from typing import List, Dict, Optional, Any
from enum import Enum

class SignalStatus(Enum):
    PENDING = "대기"
    OPEN = "진입"
    CLOSED = "종료"
    CANCELLED = "취소"

@dataclass
class ScoreDetail:
    news: float = 0
    supply: float = 0
    volume: float = 0
    chart: float = 0
    total: float = 0
    
    def to_dict(self):
        return asdict(self)

@dataclass
class ChecklistDetail:
    is_vcp: bool = False
    is_golden_cross: bool = False
    is_supply_good: bool = False
    is_news_hot: bool = False
    
    def to_dict(self):
        return asdict(self)

@dataclass
class StockData:
    code: str
    name: str
    market: str
    sector: str = ""
    close: float = 0
    change_pct: float = 0
    trading_value: float = 0
    volume: int = 0
    marcap: float = 0
    high_52w: float = 0
    
    def to_dict(self):
        return asdict(self)

@dataclass
class Signal:
    stock_code: str
    stock_name: str
    market: str
    sector: str
    signal_date: date
    signal_time: datetime
    grade: Any  # Grade Enum (import from config to avoid circular import)
    score: ScoreDetail
    checklist: ChecklistDetail
    news_items: List[Dict] = field(default_factory=list)
    current_price: float = 0
    entry_price: float = 0
    stop_price: float = 0
    target_price: float = 0
    r_value: float = 0
    position_size: float = 0
    quantity: int = 0
    r_multiplier: float = 0
    trading_value: float = 0
    change_pct: float = 0
    status: SignalStatus = SignalStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self):
        d = asdict(self)
        d['signal_date'] = self.signal_date.isoformat() if hasattr(self.signal_date, 'isoformat') else str(self.signal_date)
        d['signal_time'] = self.signal_time.isoformat() if hasattr(self.signal_time, 'isoformat') else str(self.signal_time)
        d['created_at'] = self.created_at.isoformat() if hasattr(self.created_at, 'isoformat') else str(self.created_at)
        d['status'] = self.status.value
        if hasattr(self.grade, 'value'):
            d['grade'] = self.grade.value
        return d

@dataclass
class ScreenerResult:
    date: date
    total_candidates: int
    filtered_count: int
    signals: List[Signal]
    by_grade: Dict[str, int]
    by_market: Dict[str, int]
    processing_time_ms: float
    
    def to_dict(self):
        d = asdict(self)
        d['date'] = self.date.isoformat() if hasattr(self.date, 'isoformat') else str(self.date)
        d['signals'] = [s.to_dict() for s in self.signals]
        return d

@dataclass
class ChartData:
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int
