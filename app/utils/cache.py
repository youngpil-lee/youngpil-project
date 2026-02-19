# app/utils/cache.py
"""캐시 및 유틸리티 함수"""

from config import SECTORS

# 섹터 매핑 역방향 생성 (Ticker -> Sector)
SECTOR_MAP = {}
for sector, tickers in SECTORS.items():
    for ticker in tickers:
        SECTOR_MAP[ticker] = sector

def get_sector(ticker):
    """티커에 해당하는 섹터 반환"""
    return SECTOR_MAP.get(ticker, "기타")
