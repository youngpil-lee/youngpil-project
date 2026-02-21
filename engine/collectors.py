"""
데이터 수집기 (Collectors)
- KRXCollector: pykrx를 이용한 주가/수급 데이터 수집
- EnhancedNewsCollector: 뉴스 데이터 수집
"""

import asyncio
import pandas as pd
from datetime import datetime, timedelta, date
from typing import List, Dict, Optional, Any
try:
    from pykrx import stock as krx_stock
except ImportError:
    krx_stock = None
    print("[Alert] pykrx 모듈이 없습니다. Mock 모드로 동작합니다.")

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import ssl
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

import logging
import random # Mock data generation

from engine.config import SignalConfig
from engine.models import StockData, ChartData

# 로깅 설정
logger = logging.getLogger(__name__)

class KRXCollector:
    """KRX 데이터 수집기 (비동기 래퍼)"""
    
    def __init__(self, config: SignalConfig):
        self.config = config
        self.today = date.today().strftime("%Y%m%d")
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
        
    async def get_top_gainers(self, market: str = "KOSPI", top_n: int = 50) -> List[StockData]:
        """
        상승률 상위 종목 조회 (pykrx -> Naver Finance 크롤링 -> Mock)
        """
        try:
            # 1. Try pykrx
            if krx_stock:
                return await self._get_top_gainers_pykrx(market, top_n)
            
            # 2. Try Naver Finance Crawling
            try:
                import requests
                from bs4 import BeautifulSoup
                return await self._get_top_gainers_naver(market, top_n)
            except Exception as e:
                logger.error(f"Naver 크롤링 실패: {e}")
                
            # 3. Mock Data (Fallback)
            return self._get_top_gainers_mock(market, top_n)
            
        except Exception as e:
            logger.error(f"상승률 상위 종목 조회 실패: {e}")
            return []

    async def _get_top_gainers_pykrx(self, market: str, top_n: int) -> List[StockData]:
        loop = asyncio.get_event_loop()
        df = pd.DataFrame()
        for i in range(10):
            target_date = (datetime.strptime(self.today, "%Y%m%d") - timedelta(days=i)).strftime("%Y%m%d")
            _df = await loop.run_in_executor(None, lambda d=target_date: krx_stock.get_market_ohlcv(d, market=market))
            if not _df.empty and len(_df) > 50 and _df['거래대금'].sum() > 0:
                self.today = target_date  # 기준일 업데이트
                df = _df
                break
        
        if df.empty:
            return []

        
        # 필터링 로직 (기존 코드 재사용)
        df = df[df['등락률'] >= self.config.min_change_pct]
        df = df[df['등락률'] <= self.config.max_change_pct]
        df = df[df['거래대금'] >= self.config.min_trading_value]
        df = df[df['종가'] >= self.config.min_price]
        df = df[df['종가'] <= self.config.max_price]
        df = df.sort_values(by='등락률', ascending=False).head(top_n)
        
        stock_list = []
        for code, row in df.iterrows():
            name = krx_stock.get_market_ticker_name(code)
            if any(keyword in name for keyword in self.config.exclude_keywords):
                continue
            
            stock_list.append(StockData(
                code=str(code),
                name=name,
                market=market,
                close=int(row['종가']),
                change_pct=float(row['등락률']),
                trading_value=float(row['거래대금']),
                volume=int(row['거래량'])
            ))
        return stock_list

    async def _get_top_gainers_naver(self, market: str, top_n: int) -> List[StockData]:
        """네이버 금융 '상승율 상위' 페이지 크롤링"""
        import requests
        from bs4 import BeautifulSoup
        
        loop = asyncio.get_event_loop()
        
        def crawl():
            # sosok: 0=KOSPI, 1=KOSDAQ
            sosok = 0 if market == "KOSPI" else 1
            url = f"https://finance.naver.com/sise/sise_rise.naver?sosok={sosok}"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
            resp = requests.get(url, headers=headers, verify=False)
            soup = BeautifulSoup(resp.content, "html.parser")
            
            items = []
            # 테이블 파싱
            rows = soup.select("table.type_2 tr")
            for row in rows:
                cols = row.select("td")
                if len(cols) < 10: continue
                
                try:
                    # 종목명/코드
                    title_tag = cols[1].select_one("a")
                    if not title_tag: continue
                    
                    name = title_tag.text.strip()
                    href = title_tag['href']
                    code = href.split("code=")[1]
                    
                    # 현재가, 등락률, 거래량
                    close = int(cols[2].text.replace(",", ""))
                    change_pct = float(cols[4].text.strip().replace("+", "").replace("%", ""))
                    volume = int(cols[6].text.replace(",", ""))
                    
                    # 거래대금 정보가 없으므로 대략 추산 (종가 * 거래량)
                    # 정확한 거래대금은 상세페이지 가야 함
                    trading_value = close * volume 
                    
                    # 필터링
                    if self.config.min_change_pct <= change_pct <= self.config.max_change_pct and \
                       trading_value >= self.config.min_trading_value and \
                       self.config.min_price <= close <= self.config.max_price:
                           
                        if not any(k in name for k in self.config.exclude_keywords):
                            items.append(StockData(
                                code=code, name=name, market=market,
                                close=close, change_pct=change_pct,
                                trading_value=trading_value, volume=volume
                            ))
                except:
                    continue
                    
            return items[:top_n]
            
        return await loop.run_in_executor(None, crawl)

    def _get_top_gainers_mock(self, market: str, top_n: int) -> List[StockData]:
        logging.info(f"Mock Data Generating for {market}")
        # ... (기존 Mock 로직)
        data = [
            ("A005930", "삼성전자", 70000, 2.5, 1000000000000),
            ("A000660", "SK하이닉스", 140000, 3.2, 500000000000),
            ("A035420", "NAVER", 200000, 1.5, 100000000000)
        ]
        items = []
        for code, name, close, pct, val in data:
            items.append(StockData(code=code, name=name, market=market, close=close, change_pct=pct, trading_value=val, volume=int(val/close)))
        return items

    async def get_stock_detail(self, code: str) -> Optional[StockData]:
        """종목 상세 정보 (pykrx -> Naver -> Mock)"""
        try:
            loop = asyncio.get_event_loop()
            
            if krx_stock:
                return await self._get_stock_detail_pykrx(code)
            
            # Naver Crawling Fallback
            try:
                return await self._get_stock_detail_naver(code)
            except Exception as e:
                logger.error(f"Naver 상세 조회 실패: {e}")
                
            return self._get_stock_detail_mock(code)
            
        except Exception as e:
            logger.error(f"종목 상세 조회 실패 ({code}): {e}")
            return None

    async def _get_stock_detail_pykrx(self, code: str):
        loop = asyncio.get_event_loop()
        fund_df = await loop.run_in_executor(None, lambda: krx_stock.get_market_fundamental_by_ticker(self.today, market="ALL"))
        if code not in fund_df.index: return None
        marcap_df = await loop.run_in_executor(None, lambda: krx_stock.get_market_cap_by_ticker(self.today))
        marcap = marcap_df.loc[code]['시가총액'] if code in marcap_df.index else 0
        name = krx_stock.get_market_ticker_name(code)
        return StockData(code=code, name=name, market="Unknown", marcap=float(marcap))

    async def _get_stock_detail_naver(self, code: str):
        import requests
        from bs4 import BeautifulSoup
        loop = asyncio.get_event_loop()
        
        def crawl():
            url = f"https://finance.naver.com/item/main.naver?code={code}"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
            resp = requests.get(url, headers=headers, verify=False)
            soup = BeautifulSoup(resp.content, "html.parser")
            
            # 시가총액
            marcap_txt = soup.select_one("#_market_sum").text.strip().replace(",", "").replace("조", "").strip()
            # 1조 2345억 -> 12345 (단위 확인 필요, 여기서는 단순 억단위 파싱 가정)
            # 네이버는 'X조 Y억' 형태로 줌. 단순화를 위해 대략적 파싱
            if "조" in marcap_txt:
                parts = marcap_txt.split("조")
                trillion = int(parts[0])
                billion = int(parts[1].replace("억", "").strip() or 0)
                marcap = (trillion * 10000 + billion) * 100000000
            else:
                marcap = int(marcap_txt.replace("억", "")) * 100000000
            
            name = soup.select_one(".wrap_company h2 a").text.strip()
            return StockData(code=code, name=name, market="Unknown", marcap=float(marcap))
            
        return await loop.run_in_executor(None, crawl)

    def _get_stock_detail_mock(self, code: str):
        return StockData(code=code, name=f"MockStock_{code}", market="Unknown", marcap=1000000000000)

    async def get_chart_data(self, code: str, days: int = 60) -> List[ChartData]:
        """차트 데이터 조회 (pykrx -> YFinance -> Mock)"""
        try:
            loop = asyncio.get_event_loop()
            
            # 1. pykrx
            if krx_stock:
                charts = await self._get_chart_data_pykrx(code, days)
                if charts: return charts
            
            # 2. Yfinance Fallback
            try:
                import yfinance as yf
                charts = await self._get_chart_data_yfinance(code, days)
                if charts: return charts
            except Exception as e:
                logger.error(f"YFinance 조회 실패: {e}")
                
            # 3. Mock Data
            return self._get_chart_data_mock(code, days)
            
        except Exception as e:
            logger.error(f"차트 데이터 조회 실패 ({code}): {e}")
            return []

    async def _get_chart_data_pykrx(self, code: str, days: int):
        loop = asyncio.get_event_loop()
        end_date = self.today
        start_date = (datetime.now() - timedelta(days=days + 20)).strftime("%Y%m%d")
        df = await loop.run_in_executor(None, lambda: krx_stock.get_market_ohlcv(start_date, end_date, code))
        charts = []
        for date_idx, row in df.iterrows():
            charts.append(ChartData(
                date=date_idx.strftime("%Y-%m-%d"),
                open=int(row['시가']), high=int(row['고가']), low=int(row['저가']), close=int(row['종가']), volume=int(row['거래량'])
            ))
        return charts

    async def _get_chart_data_yfinance(self, code: str, days: int):
        import yfinance as yf
        loop = asyncio.get_event_loop()
        
        def fetch():
            # Remove 'A' prefix if present (common in KRX data)
            ticker_code = code[1:] if code.startswith('A') else code
            
            # Try appending .KS (KOSPI) first, if empty try .KQ (KOSDAQ)
            # Default to .KS
            ticker = f"{ticker_code}.KS"
            # yfinance 0.2.x uses auto_adjust=True by default? no.
            data = yf.download(ticker, period=f"{days+20}d", progress=False)
            
            if data.empty:
                ticker = f"{ticker_code}.KQ"
                data = yf.download(ticker, period=f"{days+20}d", progress=False)
            
            charts = []
            if not data.empty:
                # yfinance returns MultiIndex columns sometimes, handling simple case
                for idx, row in data.iterrows():
                    # Check if scalar or series (yfinance bug workaround)
                    close = row['Close']
                    open_p = row['Open']
                    high = row['High']
                    low = row['Low']
                    vol = row['Volume']
                    
                    if hasattr(close, 'iloc'): close = close.iloc[0]
                    if hasattr(open_p, 'iloc'): open_p = open_p.iloc[0]
                    if hasattr(high, 'iloc'): high = high.iloc[0]
                    if hasattr(low, 'iloc'): low = low.iloc[0]
                    if hasattr(vol, 'iloc'): vol = vol.iloc[0]
                    
                    try:
                        charts.append(ChartData(
                            date=idx.strftime("%Y-%m-%d"),
                            open=int(float(open_p)), 
                            high=int(float(high)), 
                            low=int(float(low)),
                            close=int(float(close)), 
                            volume=int(float(vol))
                        ))
                    except (ValueError, TypeError):
                         continue
                         
            return charts
        return await loop.run_in_executor(None, fetch)

    def _get_chart_data_mock(self, code: str, days: int) -> List[ChartData]:
        # 가짜 데이터 생성 (상승 추세 + 눌림목)
        import random
        # Base price around 10000
        base_price = 10000
        charts = []
        
        # Simulate an uptrend with some volatility
        for i in range(days + 20): # Generate extra for VCP lookback
            # Trend component
            trend = i * 50 
            # Random component (volatility)
            noise = random.randint(-200, 200)
            
            close = base_price + trend + noise
            open_p = close + random.randint(-100, 100)
            high = max(close, open_p) + random.randint(0, 150)
            low = min(close, open_p) - random.randint(0, 150)
            volume = random.randint(50000, 500000)
            
            # Ensure VCP-like patterns occasionally (low volatility near end)
            if i > days + 10: 
                # Reduce volatility for recent days (Contraction)
                noise = random.randint(-50, 50)
                close = base_price + trend + noise
                high = close + random.randint(0, 50)
                low = close - random.randint(0, 50)

            charts.append(ChartData(
                date=(datetime.today() - timedelta(days=days+20-i)).strftime("%Y-%m-%d"),
                open=int(open_p), high=int(high), low=int(low), close=int(close), volume=int(volume)
            ))
            
        return charts[-days:] # Return requested days

    async def get_supply_data(self, code: str) -> Any:
        """수급 데이터 조회 (pykrx -> Naver -> Mock)"""
        try:
            loop = asyncio.get_event_loop()
            
            if krx_stock:
                return await self._get_supply_data_pykrx(code)
            
            # Naver Fallback
            try:
                return await self._get_supply_data_naver(code)
            except Exception as e:
                logger.error(f"Naver 수급 조회 실패: {e}")
                
            return self._get_supply_data_mock(code)
            
        except Exception as e:
            logger.error(f"수급 데이터 조회 실패 ({code}): {e}")
            return None

    async def _get_supply_data_pykrx(self, code: str):
        loop = asyncio.get_event_loop()
        end_date = self.today
        start_date = (datetime.now() - timedelta(days=7)).strftime("%Y%m%d")
        df = await loop.run_in_executor(None, lambda: krx_stock.get_market_investor_net_purchase_by_date_by_ticker(start_date, end_date, code))
        df = df.tail(5)
        
        if df is None or df.empty:
            return None
            
        class SupplyInfo: pass
        supply = SupplyInfo()
        try:
            supply.foreign_buy_5d = int(df['외국인'].sum())
            supply.inst_buy_5d = int(df['기관합계'].sum())
            return supply
        except Exception as e:
            logger.error(f"수급 데이터 파싱 실패 ({code}): {e}")
            return None

    async def _get_supply_data_naver(self, code: str):
        import requests
        from bs4 import BeautifulSoup
        loop = asyncio.get_event_loop()
        
        def crawl():
            url = f"https://finance.naver.com/item/frgn_man.naver?code={code}"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
            resp = requests.get(url, headers=headers, verify=False)
            soup = BeautifulSoup(resp.content, "html.parser")
            
            # 테이블 파싱 (일별매매동향 중 상단 5개 행)
            # 순매수량임. 금액 아님. -> 금액 추정 필요 (종가 * 수량)
            # 정확도는 떨어지지만 없는 것보단 낫음
            rows = soup.select("table.type2 tr")
            f_sum = 0
            i_sum = 0
            count = 0
            
            # rows[3]부터 데이터 시작 (헤더 무시)
            for row in rows:
                if count >= 5: break
                cols = row.select("td")
                if len(cols) < 9: continue # 날짜 포함 행 아니면 스킵
                
                try:
                    close = int(cols[1].text.replace(",", ""))
                    # 기관 순매수량 (+6)
                    inst_vol = int(cols[5].text.replace(",", ""))
                    # 외국인 순매수량 (+7)
                    frgn_vol = int(cols[6].text.replace(",", ""))
                    
                    f_sum += frgn_vol * close
                    i_sum += inst_vol * close
                    count += 1
                except:
                    continue
            
            class SupplyInfo: pass
            supply = SupplyInfo()
            supply.foreign_buy_5d = f_sum
            supply.inst_buy_5d = i_sum
            return supply
            
        return await loop.run_in_executor(None, crawl)

    def _get_supply_data_mock(self, code: str):
        class SupplyInfo: pass
        supply = SupplyInfo()
        supply.foreign_buy_5d = 5_000_000_000
        supply.inst_buy_5d = 2_000_000_000
        return supply


class EnhancedNewsCollector:
    """뉴스 수집기 (네이버 금융 등)"""
    
    def __init__(self, config: SignalConfig):
        self.config = config
        
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
        
    async def get_stock_news(self, code: str, limit: int = 5, stock_name: str = ""):
        """
        종목 뉴스 수집 (네이버 금융 크롤링)
        """
        try:
            import requests
            from bs4 import BeautifulSoup
            
            loop = asyncio.get_event_loop()
            
            def fetch_news():
                url = f"https://finance.naver.com/item/news_news.naver?code={code}&page=&sm=&clusterId="
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Referer': f'https://finance.naver.com/item/news.naver?code={code}'
                }
                response = requests.get(url, headers=headers, verify=False)
                soup = BeautifulSoup(response.content, 'html.parser')
                
                news_items = []
                # 네이버 금융 뉴스 목록 파싱
                articles = soup.select('.type5 tbody tr')
                
                for article in articles:
                    if len(news_items) >= limit:
                        break
                        
                    title_tag = article.select_one('.title a')
                    if not title_tag:
                         continue
                         
                    title = title_tag.text.strip()
                    link = "https://finance.naver.com" + title_tag['href']
                    source_tag = article.select_one('.info')
                    source = source_tag.text.strip() if source_tag else "Unknown"
                    date_tag = article.select_one('.date')
                    published_at = date_tag.text.strip() if date_tag else ""
                    
                    # 뉴스 본문 요약 (선택 사항 - 링크 들어가서 가져오면 더 정확하지만 속도 저하)
                    # 여기서는 제목만 사용하거나 간단히 처리
                    
                    news_items.append(type('NewsItem', (), {
                        'title': title,
                        'summary': title, # 요약 대신 제목 사용 (상세 크롤링은 비용 문제로 생략)
                        'url': link,
                        'source': source,
                        'published_at': None # datetime 파싱 필요하나 일단 생략
                    }))
                    
                return news_items

            return await loop.run_in_executor(None, fetch_news)
            
        except Exception as e:
            logger.error(f"뉴스 수집 실패 ({code}): {e}")
            return []
