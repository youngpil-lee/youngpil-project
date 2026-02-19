import json
import pandas as pd
from pathlib import Path
from typing import List, Dict, Optional, Any

def fetch_all_data() -> Dict[str, Any]:
    """
    chatbot에 필요한 모든 시장 및 종목 데이터를 로드합니다.
    """
    data = {
        "market": {
            "kospi": {"value": 0, "change_pct": 0},
            "kosdaq": {"value": 0, "change_pct": 0},
            "status": "알 수 없음"
        },
        "vcp_stocks": [],
        "sector_scores": {}
    }
    
    # 1. AI 분석 결과 로드 (가장 최신 시장 요약 포함)
    ai_path = Path("data/kr_ai_analysis.json")
    if not ai_path.exists():
        # 폴백 경로 확인
        fallback = Path("kr_market/data/kr_ai_analysis.json")
        if fallback.exists():
            ai_path = fallback

    if ai_path.exists():
        try:
            with open(ai_path, "r", encoding="utf-8") as f:
                ai_data = json.load(f)
                data["market"] = ai_data.get("market_indices", data["market"])
                data["vcp_stocks"] = ai_data.get("signals", [])
        except Exception as e:
            print(f"Error loading AI analysis: {e}")

    # 2. 종가베팅 V2 결과 로드 (점수 기반 데이터)
    v2_path = Path("data/jongga_v2_latest.json")
    if v2_path.exists():
        try:
            with open(v2_path, "r", encoding="utf-8") as f:
                v2_data = json.load(f)
                # 필요한 경우 병합
        except Exception as e:
            print(f"Error loading Jongga V2 data: {e}")

    return data

def get_top_vcp_stocks(n: int = 5) -> List[Dict]:
    """VCP 점수가 높은 상단 N개 종목 반환"""
    all_data = fetch_all_data()
    stocks = all_data.get("vcp_stocks", [])
    
    # 점수(score) 필드 기준으로 내림차순 정렬
    sorted_stocks = sorted(
        stocks, 
        key=lambda x: x.get("score", 0), 
        reverse=True
    )
    return sorted_stocks[:n]

def search_stock(query: str) -> Optional[Dict]:
    """종목명 또는 티커로 종목 정보 검색"""
    all_data = fetch_all_data()
    stocks = all_data.get("vcp_stocks", [])
    
    query = query.strip().lower()
    for stock in stocks:
        if (query == stock.get("ticker", "").lower() or 
            query == stock.get("name", "").lower()):
            return stock
            
    return None

def get_market_summary() -> str:
    """프롬프트용 시장 요약 텍스트 생성"""
    data = fetch_all_data()
    market = data["market"]
    
    summary = f"현재 시장 지수: KOSPI {market['kospi']['value']} ({market['kospi']['change_pct']}%), "
    summary += f"KOSDAQ {market['kosdaq']['value']} ({market['kosdaq']['change_pct']}%)"
    return summary
