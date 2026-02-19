"""
LLM 기반 뉴스 분석기 (Gemini)
"""

import os
import google.generativeai as genai
from typing import List, Dict
import asyncio
from datetime import datetime
from dotenv import load_dotenv

# 환경변수 로드 (.env)
load_dotenv()

class LLMAnalyzer:
    """Gemini를 이용한 뉴스 분석 및 점수 산출"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            print("경고(Warning): GOOGLE_API_KEY를 찾을 수 없습니다. LLM 분석을 건너뜁니다.")
            self.model = None
        else:
            genai.configure(api_key=self.api_key)
            # 모델명 환경변수에서 로드 (기본값: gemini-2.0-flash-exp)
            model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
            self.model = genai.GenerativeModel(model_name)
    
    async def analyze_news_sentiment(self, stock_name: str, news_items: List[Dict]) -> Dict:
        """
        뉴스 목록을 분석하여 호재 점수(0~3)와 요약 반환
        """
        if not self.model or not news_items:
            return {"score": 0, "reason": "LLM 설정 미비 또는 뉴스 데이터 없음"}
            
        # 프롬프트 구성
        news_text = ""
        for i, news in enumerate(news_items, 1):
            title = news.get("title", "")
            summary = news.get("summary", "")[:200]  # 너무 길면 자름
            news_text += f"[{i}] 제목: {title}\n내용: {summary}\n\n"
            
        prompt = f"""
            당신은 주식 투자 전문가입니다. 다음은 '{stock_name}' 종목에 대한 최신 뉴스들입니다.
            이 뉴스들을 **종합적으로 분석**하여 현재 시점에서의 호재 강도를 0~3점으로 평가하세요.
            
            [뉴스 목록]
            {news_text}
            
            [점수 기준]
            3점: 확실한 호재 (대규모 수주, 상한가 재료, 어닝 서프라이즈, 경영권 분쟁 등)
            2점: 긍정적 호재 (실적 개선, 기대감, 테마 상승)
            1점: 단순/중립적 소식
            0점: 악재 또는 별다른 호재 없음
            
            [출력 형식]
            뉴스 3개를 따로 평가하지 말고, **종목 전체에 대한 하나의 평가**를 내리세요.
            반드시 아래 포맷의 **단일 JSON 객체**로만 답하세요. (Markdown code block 없이)
            
            Format: {{"score": 2, "reason": "종합적인 요약 이유"}}
            """
        
        try:
            # 비동기 실행
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            
            import json
            import re
            
            text = response.text.strip()
            
            # JSON 추출 (Markdown 코드블록 제거 및 정규식)
            if "```" in text:
                text = re.sub(r"```json|```", "", text).strip()
            
            # 중괄호로 시작하고 끝나는지 확인, 아니면 정규식으로 추출
            if not (text.startswith("{") and text.endswith("}")):
                match = re.search(r"\{.*\}", text, re.DOTALL)
                if match:
                    text = match.group()
            
            try:
                result = json.loads(text)
                return result
            except json.JSONDecodeError:
                print(f"[LLM Error] JSON Decode Failed. Raw text: {text[:100]}...")
                return {"score": 0, "reason": "JSON 파싱 실패(Parsing Failed)"}
            
        except Exception as e:
            print(f"[LLM Error] API 호출 실패(Call Failed): {e}")
            return {"score": 0, "reason": f"Error: {str(e)}"}

    async def analyze_market(self, market_data: Dict) -> Dict:
        """
        시장 데이터를 바탕으로 금일/익일 시장 전망 분석
        """
        if not self.model:
            return {"outlook": "Neutral", "reason": "LLM 미설정"}
            
        prompt = f"""
        당신은 베테랑 주식 시황 분석가입니다. 다음 시장 데이터를 바탕으로 시장의 분위기와 향후 전망을 분석해주세요.
        
        [시장 데이터]
        KOSPI: {market_data.get('kospi', 'N/A')}
        KOSDAQ: {market_data.get('kosdaq', 'N/A')}
        환율(USD/KRW): {market_data.get('usd_krw', 'N/A')}
        주요 뉴스/이슈: {market_data.get('issues', '없음')}
        
        [요청사항]
        1. 현재 시장의 강세/약세 여부 판별
        2. 주요 상승/하락 원인 분석
        3. 투자자들을 위한 대응 전략 제안 (현금 비중 확대, 저점 매수 등)
        
        [출력 형식]
        반드시 JSON 형식으로만 응답하세요.
        {{
            "outlook": "Bullish" | "Bearish" | "Neutral",
            "summary": "시장 상황 요약 (한글)",
            "strategy": "대응 전략 제안 (한글)"
        }}
        """
        
        try:
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            return self._parse_json_response(response.text)
        except Exception as e:
            print(f"[LLM Error] Market Analysis Failed: {e}")
            return {"outlook": "Error", "reason": str(e)}

    async def analyze_portfolio(self, portfolio: List[Dict]) -> Dict:
        """
        포트폴리오 종목들을 분석하여 리밸런싱 제안
        """
        if not self.model:
            return {"action": "Hold", "reason": "LLM 미설정"}
            
        items_str = "\n".join([f"- {item['name']} ({item['ticker']}): 수익률 {item.get('profit_pct', 0)}%, 비중 {item.get('weight', 0)}%" for item in portfolio])
        
        prompt = f"""
        당신은 자산 운용 전문가(PM)입니다. 현재 고객의 포트폴리오 상태가 다음과 같습니다.
        종목별 상태를 점검하고, 포트폴리오 리밸런싱 의견을 주세요.
        
        [보유 종목 목록]
        {items_str}
        
        [요청사항]
        1. 포트폴리오의 안정성과 위험도 평가
        2. 특정 종목의 매도/비중 축소 필요성 (수익 실현 또는 손절)
        3. 전체적인 운용 조언
        
        [출력 형식]
        반드시 JSON 형식으로만 응답하세요.
        {{
            "risk_level": "High" | "Medium" | "Low",
            "evaluation": "포트폴리오 총평 (한글)",
            "suggestions": [
                {{"ticker": "종목코드", "action": "BUY" | "SELL" | "HOLD", "reason": "이유"}}
            ]
        }}
        """
        
        try:
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            return self._parse_json_response(response.text)
        except Exception as e:
            print(f"[LLM Error] Portfolio Analysis Failed: {e}")
            return {"evaluation": "Error", "reason": str(e)}

    def _parse_json_response(self, text: str) -> Dict:
        """LLM 응답 텍스트에서 JSON 파싱"""
        import json
        import re
        
        text = text.strip()
        if "```" in text:
            text = re.sub(r"```json|```", "", text).strip()
        
        if not (text.startswith("{") and text.endswith("}")):
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                text = match.group()
        
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"error": "JSON Parsing Failed", "raw": text}
