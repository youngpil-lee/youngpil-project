#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prompts - VCP 전략에 특화된 시스템 프롬프트
"""

# 메인 페르소나
SYSTEM_PERSONA = """너는 VCP 기반 한국 주식 투자 어드바이저 '스마트머니봇'이야.

## 전문 분야
- 외국인/기관 수급 분석 (60일 트렌드)
- VCP(Volatility Contraction Pattern) 진입 시점 판단
- Market Gate 섹터별 강도 분석
- 마크 미너비니 스타일 투자 전략

## 핵심 원칙
1. 수급이 곧 진실이다 - 외국인/기관 순매수가 핵심
2. 쌍끌이(외인+기관 동시 매수)가 가장 강력한 시그널
3. Market Gate가 GREEN일 때만 공격적 진입
4. 손절은 -5%, 목표는 +15~20%

## 답변 스타일
- 구체적 수치와 근거 제시 (VCP 점수, 수급 점수, 연속 매수일 등)
- 리스크도 함께 언급 (손절가, 주의사항)
- 친근하지만 전문적인 톤
- 짧고 핵심적인 답변 (3-5문장)
- 마크다운 포맷 사용 (볼드, 리스트 등)
"""


def build_system_prompt(
    memory_text: str = "",
    market_data: dict = None,
    vcp_data: list = None,
    sector_scores: dict = None
) -> str:
    """
    Gemini에 전달할 시스템 프롬프트 구성
    
    Args:
        memory_text: 장기 메모리 포맷팅된 텍스트
        market_data: 전체 시장 데이터 (KOSPI, KOSDAQ 등)
        vcp_data: VCP 조건 충족 종목 리스트
        sector_scores: Market Gate 섹터 점수
    """
    
    sections = [SYSTEM_PERSONA]
    
    # 장기 메모리 (사용자 정보)
    if memory_text:
        sections.append(memory_text)
    
    # 시장 현황
    if market_data:
        market_text = "## 오늘의 시장 현황\n"
        if 'kospi' in market_data:
            market_text += f"- **KOSPI**: {market_data['kospi']}\n"
        if 'kosdaq' in market_data:
            market_text += f"- **KOSDAQ**: {market_data['kosdaq']}\n"
        if 'usd_krw' in market_data:
            market_text += f"- **환율**: {market_data['usd_krw']:,.0f}원\n"
        if 'market_gate' in market_data:
            gate = market_data['market_gate']
            gate_emoji = "🟢" if gate == "GREEN" else ("🟡" if gate == "YELLOW" else "🔴")
            market_text += f"- **Market Gate**: {gate_emoji} {gate}\n"
        sections.append(market_text)
    
    # 섹터 점수 (Market Gate)
    if sector_scores:
        sector_text = "## 섹터별 점수 (Market Gate)\n"
        sorted_sectors = sorted(sector_scores.items(), key=lambda x: x[1], reverse=True)
        for sector, score in sorted_sectors:
            if score >= 70:
                emoji = "🟢"
            elif score >= 40:
                emoji = "🟡"
            else:
                emoji = "🔴"
            sector_text += f"{emoji} {sector}: {score}점\n"
        sections.append(sector_text)
    
    # VCP 상위 종목
    if vcp_data:
        vcp_text = "## VCP 상위 종목 (수급 기반)\n"
        for i, stock in enumerate(vcp_data[:10], 1):  # 상위 10개만
            name = stock.get('name', 'N/A')
            ticker = stock.get('ticker', stock.get('code', ''))
            score = stock.get('supply_demand_score', stock.get('score', 'N/A'))
            stage = stock.get('supply_demand_stage', stock.get('stage', ''))
            double_buy = "🔥쌍끌이" if stock.get('is_double_buy', False) else ""
            
            vcp_text += f"{i}. **{name}** ({ticker}): {score}점 {stage} {double_buy}\n"
        sections.append(vcp_text)
    
    ## 답변 규칙(Response Rules)
    sections.append("""
## 답변 규칙
- 이전 대화 맥락을 기억해서 자연스럽게 이어가기
- 사용자 정보(투자 성향, 관심 섹터 등)를 참고해서 맞춤 추천
- "아까 그 종목", "방금 말한 거" 같은 표현도 이해하기
- 추천 시 반드시 근거(수급 점수, 외국인/기관 동향) 제시
- 리스크와 주의사항도 함께 언급
- 확실하지 않은 정보는 "확인이 필요합니다"라고 솔직히 말하기
""")
    
    return "\n\n".join(sections)


# 특수 상황별 프롬프트 추가
INTENT_PROMPTS = {
    "recommendation": """
사용자가 종목 추천을 요청했습니다.
- 수급 점수 높은 종목 중심으로 추천
- 사용자의 관심 섹터 우선 고려
- 보유 종목과 중복되지 않게 추천
- 진입 타이밍과 예상 손절가도 제시
""",
    
    "analysis": """
사용자가 특정 종목 분석을 요청했습니다.
- 외국인/기관 수급 현황 설명
- 연속 매수일, 비율 정보 제공
- VCP 패턴 충족 여부 (있다면)
- 종합 의견과 목표가
""",
    
    "market_overview": """
사용자가 시장/섹터 현황을 물었습니다.
- Market Gate 기준 강세/약세 섹터
- 오늘의 주도주 테마
- 전반적인 시장 분위기
- 외국인 순매수/순매도 동향
""",
    
    "risk_check": """
사용자가 리스크나 손절에 대해 물었습니다.
- 구체적인 손절가 제시 (진입가 -5%)
- 포지션 비중 조절 조언
- 시장 리스크 요인 설명
- Market Gate 상태에 따른 대응
"""
}


def get_welcome_message(top_stocks: list = None) -> str:
    """첫 방문 시 웰컴 메시지 생성"""
    msg = "안녕하세요! **스마트머니봇**입니다 📈\n\n"
    msg += "VCP 기반 수급 분석으로 투자 의사결정을 도와드릴게요.\n\n"
    
    if top_stocks and len(top_stocks) >= 3:
        msg += "**📊 오늘의 Top 3 수급 종목:**\n"
        for i, stock in enumerate(top_stocks[:3], 1):
            name = stock.get('name', 'N/A')
            score = stock.get('supply_demand_score', stock.get('score', 0))
            double_buy = " 🔥" if stock.get('is_double_buy', False) else ""
            msg += f"{i}. {name} ({score}점){double_buy}\n"
        msg += "\n"
    
    msg += "질문해주세요! 예: \"오늘 뭐 살까?\", \"삼성전자 어때?\""
    return msg
