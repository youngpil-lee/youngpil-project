"""
자금 관리 (Position Sizing)
- 리스크 관리
- 진입/손절/목표가 계산
- 포지션 크기 및 수량 결정
"""

from engine.config import SignalConfig, Grade


class PositionSizer:
    """종가베팅 포지션 사이징"""
    
    def __init__(self, capital: float, config: SignalConfig):
        self.capital = capital
        self.config = config
        
    def calculate(self, current_price: float, grade: Grade):
        """
        포지션 정보 계산
        Returns: Position (object or simple class)
        """
        class Position:
            entry_price: float
            stop_price: float
            target_price: float
            r_value: float
            position_size: float
            quantity: int
            r_multiplier: float
            
        position = Position()
        
        # 1. 진입가 (현재가 기준)
        position.entry_price = current_price
        
        # 2. 손절가 (설정된 % 적용)
        # 3% 손절이면: entry * (1 - 0.03)
        position.stop_price = int(current_price * (1 - self.config.stop_loss_pct))
        # 틱단위 보정은 생략 (간단히 정수형)
        
        # 3. 목표가 (설정된 % 적용 or R배수)
        # 5% 익절이면: entry * (1 + 0.05)
        position.target_price = int(current_price * (1 + self.config.take_profit_pct))
        
        # 4. R값 (Risk per share)
        risk_per_share = position.entry_price - position.stop_price
        position.r_value = risk_per_share
        
        # 5. R 배수 (Grade별 차등)
        grade_config = self.config.grade_configs.get(grade)
        position.r_multiplier = grade_config.r_multiplier if grade_config else 1.0
        
        # 6. 포지션 크기 (리스크 기반 or 고정 비율)
        # 여기서는 간단히 자본금 대비 일정 비율 + 등급 가중치
        # 예: 자본금 10% * r_multiplier
        base_pct = 0.1 # 기본 10%
        position_size = self.capital * base_pct * position.r_multiplier
        
        # 최대 포지션 크기 제한 (자본금의 50% 등)
        max_size = self.capital * 0.5
        position.position_size = min(position_size, max_size)
        
        # 7. 수량 계산
        if current_price > 0:
            position.quantity = int(position.position_size // current_price)
        else:
             position.quantity = 0
             
        return position
