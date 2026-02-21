"""
KR Market AI 분석기 (Wrapper)
- run.py와의 호환성을 위한 래퍼 클래스
- engine.llm_analyzer를 사용
"""

import asyncio
from typing import Dict, Any, List
import logging

try:
    from engine.llm_analyzer import LLMAnalyzer
    from engine.collectors import EnhancedNewsCollector
    from engine.config import SignalConfig
    from engine.config import SignalConfig
    # from pykrx import stock # 여기서 에러 발생 가능
    
    # pykrx import try
    try:
        from pykrx import stock
    except ImportError:
        stock = None
        
except (ImportError, ModuleNotFoundError):
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from engine.llm_analyzer import LLMAnalyzer
    from engine.collectors import EnhancedNewsCollector
    from engine.config import SignalConfig
    stock = None

# Fallback Class if pykrx is missing
class NaverFallbackStock:
    @staticmethod
    def get_market_ticker_name(code):
        try:
            import requests
            from bs4 import BeautifulSoup
            url = f"https://finance.naver.com/item/main.naver?code={code}"
            headers = {'User-Agent': 'Mozilla/5.0'}
            resp = requests.get(url, headers=headers)
            soup = BeautifulSoup(resp.content, "html.parser")
            name = soup.select_one(".wrap_company h2 a").text.strip()
            return name
        except:
            return f"Code({code})"

if stock is None:
    stock = NaverFallbackStock()

class KrAiAnalyzer:
    """AI 분석기 (run.py 호환)"""
    
    def __init__(self):
        self.config = SignalConfig()
        self.llm = LLMAnalyzer()
        
    def analyze_stock(self, code: str) -> Dict[str, Any]:
        """
        단일 종목 AI 분석 (동기 메서드)
        """
        print(f"🤖 [{code}] 종목 AI 분석을 시작합니다...")
        
        async def _process():
            # 1. 종목명 조회
            try:
                name = stock.get_market_ticker_name(code)
                if not name:
                    name = f"Code({code})"
            except Exception as e:
                print(f"⚠️ 종목명 조회 실패: {e}")
                name = f"Code({code})"
            
            print(f"   대상 종목: {name}")
            
            # 2. 뉴스 데이터 수집
            news_collector = EnhancedNewsCollector(self.config)
            # await news_collector.__aenter__() # Explicit context enter if needed, but ContextManager handles it
            # async with logic is better
            
            # Use async with normally
            news_list = await news_collector.get_stock_news(code, limit=5, stock_name=name)
            
            if not news_list:
                print("   ⚠️ 최근 뉴스가 없습니다.")
                # 뉴스가 없어도 계속 진행
            
            # 뉴스 dict 변환
            news_dicts = []
            if news_list:
                news_dicts = [{"title": n.title, "summary": n.summary} for n in news_list]
            
            # 3. LLM 분석
            print("   🧠 Gemini AI가 분석 중입니다...")
            result = await self.llm.analyze_news_sentiment(name, news_dicts)
            return result
                
        try:
            return asyncio.run(_process())
        except Exception as e:
            return {"error": f"분석 중 오류 발생: {str(e)}"}

    def analyze_market_outlook(self) -> Dict:
        """
        시장 전망 분석 (동기 메서드)
        """
        print("🤖 [Market] 시장 데이터 분석 중...")
        
        async def _process():
            # 실제 데이터 수집 (네이버 금융 크롤링)
            import requests
            from bs4 import BeautifulSoup
            
            market_data = {}
            try:
                # KOSPI
                resp = requests.get("https://finance.naver.com/sise/sise_index.naver?code=KOSPI")
                soup = BeautifulSoup(resp.content, "html.parser")
                kospi_now = soup.select_one("#now_value").text
                kospi_change = soup.select_one("#change_value_and_rate").text.strip()
                market_data["kospi"] = f"{kospi_now} ({kospi_change})"
                
                # KOSDAQ
                resp = requests.get("https://finance.naver.com/sise/sise_index.naver?code=KOSDAQ")
                soup = BeautifulSoup(resp.content, "html.parser")
                kosdaq_now = soup.select_one("#now_value").text
                kosdaq_change = soup.select_one("#change_value_and_rate").text.strip()
                market_data["kosdaq"] = f"{kosdaq_now} ({kosdaq_change})"
                
                # Exchange Rate using main page or market index page
                resp = requests.get("https://finance.naver.com/marketindex/")
                soup = BeautifulSoup(resp.content, "html.parser")
                usd_krw = soup.select_one("#exchangeList .head_info.point_dn .value, #exchangeList .head_info.point_up .value").text
                market_data["usd_krw"] = f"{usd_krw} KRW"
                
                # Market Issues (Headlines)
                headlines = [h.text for h in soup.select(".section_news .tit")][:3]
                market_data["issues"] = ", ".join(headlines) if headlines else "주요 시장 뉴스 수집 중..."
                
            except Exception as e:
                 print(f"⚠️ 시장 데이터 수집 실패: {e}")
                 # Fallback
                 market_data = {
                    "kospi": "2650.00 (Mock)", 
                    "kosdaq": "870.00 (Mock)", 
                    "usd_krw": "1330.0", 
                    "issues": "데이터 수집 실패, 일반적 시장 상황 가정"
                 }
            
            return await self.llm.analyze_market(market_data)

        try:
            return asyncio.run(_process())
        except Exception as e:
            return {"error": f"시장 분석 오류: {str(e)}"}

    def analyze_user_portfolio(self, portfolio: List[Dict]) -> Dict:
        """
        포트폴리오 분석 (동기 메서드)
        Args:
            portfolio: [{"ticker": "005930", "name": "삼성전자", "profit_pct": 5.2, "weight": 20}, ...]
        """
        print(f"🤖 [Portfolio] 보유 {len(portfolio)}종목 포트폴리오 진단 중...")
        
        async def _process():
            return await self.llm.analyze_portfolio(portfolio)

        try:
            return asyncio.run(_process())
        except Exception as e:
            return {"error": f"포트폴리오 분석 오류: {str(e)}"}

if __name__ == "__main__":
    analyzer = KrAiAnalyzer()
    
    # 1. 삼성전자 테스트
    # print(analyzer.analyze_stock("005930"))
    
    # 2. 시장 분석 테스트
    print("\n=== 시장 전망 ===")
    print(analyzer.analyze_market_outlook())
    
    # 3. 포트폴리오 테스트
    print("\n=== 포트폴리오 진단 ===")
    pf = [
        {"ticker": "005930", "name": "삼성전자", "profit_pct": -2.5, "weight": 40},
        {"ticker": "000660", "name": "SK하이닉스", "profit_pct": 15.2, "weight": 30},
        {"ticker": "035420", "name": "NAVER", "profit_pct": -10.5, "weight": 30}
    ]
    print(analyzer.analyze_user_portfolio(pf))
