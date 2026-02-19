
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging
from dataclasses import dataclass

@dataclass
class Trade:
    entry_date: str
    exit_date: Optional[str]
    ticker: str
    name: str
    entry_price: float
    exit_price: Optional[float]
    quantity: int
    profit_pct: Optional[float]
    holding_days: Optional[int]
    status: str  # OPEN, CLOSED, STOP_LOSS, TAKE_PROFIT

class BacktestEngine:
    """
    간단한 이벤트 기반 백테스트 엔진
    - 일별 OHLCV 데이터를 순회하며 시그널 발생 시 매수, 조건 만족 시 매도
    """
    def __init__(self, initial_capital: float = 10_000_000):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.holdings: Dict[str, Trade] = {} # ticker -> Trade
        self.history: List[Trade] = []
        self.equity_curve: List[Dict] = []
        
    def run(self, data_feed: Dict[str, pd.DataFrame], strategy_func, start_date: str, end_date: str):
        """
        백테스트 실행
        Args:
            data_feed: 종목별 일봉 데이터 (Key: ticker, Value: DataFrame(index=date, columns=[open, high, low, close, volume]))
            strategy_func: 시그널 생성 함수 (current_date, data_feed) -> List[Dict] (매수 신호)
            start_date: 시작일 (YYYY-MM-DD)
            end_date: 종료일 (YYYY-MM-DD)
        """
        logging.info(f"백테스트 시작: {start_date} ~ {end_date}")
        
        # 날짜 범위 생성
        dates = pd.date_range(start=start_date, end=end_date, freq='B') # Business day
        
        for d in dates:
            current_date_str = d.strftime("%Y-%m-%d")
            
            # 1. 보유 종목 가격 업데이트 및 매도 조건 확인 (장 시작/장 중/장 마감)
            self._update_positions(current_date_str, data_feed)
            
            # 2. 신규 매수 시그널 확인 (전일 데이터 기반 장전/시초가 매수 가정)
            #    실제로는 당일 장 마감 후 스크리닝 -> 익일 시초가 매수 혹은 당일 종가 매수
            #    여기서는 "당일 종가 매수" 전략 가정 (종가베팅)
            
            # 전략 함수 실행
            signals = strategy_func(current_date_str, data_feed)
            
            # 3. 매수 실행
            for signal in signals:
                self._execute_buy(current_date_str, signal)
                
            # 4. 자산 가치 기록
            self._record_equity(current_date_str, data_feed)
            
        logging.info("백테스트 완료")
        
    def _update_positions(self, date_str: str, data_feed: Dict[str, pd.DataFrame]):
        """보유 종목 상태 업데이트 및 매도 처리"""
        tickers_to_close = []
        
        for ticker, trade in self.holdings.items():
            if ticker not in data_feed:
                continue
                
            df = data_feed[ticker]
            if date_str not in df.index:
                continue
                
            daily_data = df.loc[date_str]
            current_price = daily_data['close']
            low_price = daily_data['low']
            high_price = daily_data['high']
            
            # 손절/익절 로직 (간단화)
            # -3% 손절, +5% 익절
            stop_loss = trade.entry_price * 0.97
            take_profit = trade.entry_price * 1.05
            
            exit_price = None
            status = None
            
            if low_price <= stop_loss:
                exit_price = stop_loss # 갭하락 고려 없이 단순 계산
                status = "STOP_LOSS"
            elif high_price >= take_profit:
                exit_price = take_profit # 갭상승 고려 없이 단순 계산
                status = "TAKE_PROFIT"
            # 보유 기간 제한 (예: 5일)
            elif (datetime.strptime(date_str, "%Y-%m-%d") - datetime.strptime(trade.entry_date, "%Y-%m-%d")).days >= 5:
                exit_price = current_price
                status = "TIME_EXIT"
                
            if exit_price:
                trade.exit_date = date_str
                trade.exit_price = exit_price
                trade.status = status
                
                # 수익률 계산
                trade.profit_pct = (exit_price - trade.entry_price) / trade.entry_price * 100
                
                # 매도 처리
                revenue = trade.quantity * exit_price
                fee = revenue * 0.0023 # 수수료+세금 0.23%
                self.cash += (revenue - fee)
                
                self.history.append(trade)
                tickers_to_close.append(ticker)
                
        for t in tickers_to_close:
            del self.holdings[t]
            
    def _execute_buy(self, date_str: str, signal: Dict):
        """매수 실행"""
        ticker = signal['ticker']
        if ticker in self.holdings:
            return # 이미 보유 중
            
        price = signal.get('entry_price', 0)
        score = signal.get('score', 0)
        
        if price <= 0: return
        
        # 자금 관리: 가용 현금의 10% 씩 매수 (최대 10종목)
        buy_amount = self.initial_capital * 0.1
        if self.cash < buy_amount:
            buy_amount = self.cash
            
        if buy_amount < 100_000: # 최소 주문 금액
            return
            
        quantity = int(buy_amount / price)
        if quantity == 0: return
        
        cost = quantity * price
        fee = cost * 0.00015 # 매수 수수료 0.015%
        
        if self.cash >= (cost + fee):
            self.cash -= (cost + fee)
            
            trade = Trade(
                entry_date=date_str,
                exit_date=None,
                ticker=ticker,
                name=signal.get('name', ticker),
                entry_price=price,
                exit_price=None,
                quantity=quantity,
                profit_pct=None,
                holding_days=None,
                status="OPEN"
            )
            self.holdings[ticker] = trade
            
    def _record_equity(self, date_str: str, data_feed: Dict):
        """일별 자산 가치 기록"""
        stock_val = 0
        for ticker, trade in self.holdings.items():
            current_price = trade.entry_price
            if ticker in data_feed and date_str in data_feed[ticker].index:
                current_price = data_feed[ticker].loc[date_str]['close']
            stock_val += trade.quantity * current_price
            
        total_equity = self.cash + stock_val
        self.equity_curve.append({
            'date': date_str,
            'cash': self.cash,
            'stock_value': stock_val,
            'total_equity': total_equity
        })

    def get_summary(self) -> Dict:
        """결과 요약"""
        if not self.equity_curve:
            return {}
            
        final_equity = self.equity_curve[-1]['total_equity']
        total_return = (final_equity - self.initial_capital) / self.initial_capital * 100
        
        trades_count = len(self.history)
        win_trades = [t for t in self.history if t.profit_pct > 0]
        win_rate = (len(win_trades) / trades_count * 100) if trades_count > 0 else 0
        
        # MDD 계산
        equity_series = [e['total_equity'] for e in self.equity_curve]
        peak = equity_series[0]
        max_drawdown = 0
        for val in equity_series:
            if val > peak:
                peak = val
            dd = (peak - val) / peak * 100
            if dd > max_drawdown:
                max_drawdown = dd
                
        return {
            "initial_capital": self.initial_capital,
            "final_equity": final_equity,
            "total_return_pct": total_return,
            "total_trades": trades_count,
            "win_rate": win_rate,
            "mdd_pct": max_drawdown
        }
