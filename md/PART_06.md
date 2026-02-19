# 파트 6 (핵심 로직)

### frontend/src/app/globals.css (file:///Users/seoheun/Documents/kr_market_package/frontend/src/app/globals.css)
```css
@import "tailwindcss";

/* ========================================
   Dashboard Design System
   Korean Market AI Stock Analysis
   ======================================== */

:root {
  /* Apple Dark Mode Palette */
  --bg-page: #000000;
  --bg-surface: #1c1c1e;
  --bg-surface-hover: #2c2c2e;
  --bg-glass: rgba(28, 28, 30, 0.75);
  --border-color: rgba(255, 255, 255, 0.1);

  /* Text Colors */
  --text-primary: #f5f5f7;
  --text-secondary: #86868b;
  --text-tertiary: #6e6e73;

  /* Accents */
  --accent: #2997ff;
  --status-success: #30d158;
  --status-error: #ff453a;
  --status-warning: #ff9f0a;
}

body {
  background-color: var(--bg-page);
  color: var(--text-primary);
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", "Inter", sans-serif;
  font-size: 14px;
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* ========================================
   GLASSMORPHISM
   ======================================== */

.apple-glass {
  background-color: rgba(28, 28, 30, 0.65);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border-right: 1px solid rgba(255, 255, 255, 0.08);
}

.glass-card {
  background-color: var(--bg-surface);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 18px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  transition: transform 0.2s ease, background-color 0.2s ease;
}

.glass-card:hover {
  background-color: var(--bg-surface-hover);
  transform: scale(1.005);
}

/* ========================================
   SCROLLBARS
   ======================================== */

::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 4px;
  border: 2px solid var(--bg-page);
}

::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.3);
}

/* ========================================
   ANIMATIONS
   ======================================== */

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }

  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes pulse-glow {
  0% {
    box-shadow: 0 0 10px rgba(16, 185, 129, 0.1);
  }

  50% {
    box-shadow: 0 0 25px rgba(16, 185, 129, 0.3);
  }

  100% {
    box-shadow: 0 0 10px rgba(16, 185, 129, 0.1);
  }
}

.animate-fade-in {
  animation: fadeIn 0.3s ease both;
}

/* ========================================
   UTILITY CLASSES
   ======================================== */

.text-xxs {
  font-size: 10px !important;
  letter-spacing: 0.02em;
}```

### chatbot/core.py (file:///Users/seoheun/Documents/kr_market_package/chatbot/core.py)
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KR Stock Chatbot Core - 메인 챗봇 클래스
Gemini AI 연동 및 대화 처리 로직
"""

import os
import logging
from typing import Optional, Callable, Dict, Any
from pathlib import Path
from datetime import datetime

# .env 파일 로드(Load)
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent.parent / ".env"
    load_dotenv(env_path)
except ImportError:
    pass  # python-dotenv not installed

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

from memory import MemoryManager
from history import HistoryManager
from prompts import build_system_prompt, get_welcome_message, SYSTEM_PERSONA
from data_loader import fetch_all_data, search_stock, get_top_vcp_stocks

logger = logging.getLogger(__name__)

# 설정
GEMINI_MODEL = "gemini-3-flash-preview"
MAX_RETRIES = 3


class KRStockChatbot:
    """
    VCP 기반 한국 주식 분석 챗봇
    
    주요 기능(Features):
    - 장기 메모리: 사용자 프로필, 투자 성향 저장
    - 대화 히스토리: 최근 10개 대화 컨텍스트 유지
    - 시장 데이터 연동: 수급 점수, 섹터 점수, Market Gate
    """
    
    def __init__(
        self, 
        user_id: str,
        data_fetcher: Optional[Callable] = None,
        api_key: str = None
    ):
        """
        Args:
            user_id: 사용자 식별자
            data_fetcher: 시장 데이터 가져오는 함수 (외부 주입)
            api_key: Gemini API 키 (없으면 환경변수에서 로드)
        """
        self.user_id = user_id
        self.memory = MemoryManager(user_id)
        self.history = HistoryManager(user_id)
        self.data_fetcher = data_fetcher or fetch_all_data
        
        # Gemini 초기화
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY", "")
        self.model = None
        
        if GEMINI_AVAILABLE and self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel(GEMINI_MODEL)
                logger.info(f"Gemini initialized for user: {user_id}")
            except Exception as e:
                logger.error(f"Gemini initialization failed: {e}")
        else:
            logger.warning("Gemini not available - using fallback responses")
        
        # 데이터 캐시
        self._data_cache = None
        self._cache_timestamp = None
        self._cache_ttl = 30  # 30초 캐시
    
    def _get_cached_data(self) -> Dict[str, Any]:
        """캐시된 시장 데이터 반환 (30초 TTL)"""
        now = datetime.now()
        if (self._data_cache is None or 
            self._cache_timestamp is None or
            (now - self._cache_timestamp).seconds > self._cache_ttl):
            
            try:
                self._data_cache = self.data_fetcher()
                self._cache_timestamp = now
            except Exception as e:
                logger.error(f"Data fetch error: {e}")
                self._data_cache = {"market": {}, "vcp_stocks": [], "sector_scores": {}}
        
        return self._data_cache
    
    def chat(self, user_message: str) -> str:
        """
        메인 대화 함수
        
        Args:
            user_message: 사용자 입력
            
        Returns:
            봇 응답
        """
        # 1. 명령어 확인(Command Check)
        if user_message.startswith("/"):
            return self._handle_command(user_message)
        
        # 2. 시장 데이터 가져오기
        data = self._get_cached_data()
        market_data = data.get("market", {})
        vcp_data = data.get("vcp_stocks", [])
        sector_scores = data.get("sector_scores", {})
        
        # 3. 특정 종목 질문인지 확인
        stock_context = self._detect_stock_query(user_message)
        
        # 4. 시스템 프롬프트 구성
        system_prompt = build_system_prompt(
            memory_text=self.memory.format_for_prompt(),
            market_data=market_data,
            vcp_data=vcp_data,
            sector_scores=sector_scores
        )
        
        # 종목별 컨텍스트 추가
        if stock_context:
            system_prompt += f"\n\n## 질문 대상 종목 상세\n{stock_context}"
        
        # 5. 대화 히스토리 가져오기
        chat_history = self.history.get_recent()
        
        # 6. Gemini 호출 (또는 폴백)
        if self.model:
            bot_response = self._call_gemini(system_prompt, user_message, chat_history)
        else:
            bot_response = self._fallback_response(user_message, vcp_data)
        
        # 7. 히스토리 저장
        self.history.add("user", user_message)
        self.history.add("model", bot_response)
        
        return bot_response
    
    def _call_gemini(self, system_prompt: str, user_message: str, chat_history: list) -> str:
        """Gemini API 호출"""
        try:
            chat_session = self.model.start_chat(history=chat_history)
            
            # 시스템 프롬프트 + 사용자 메시지
            full_prompt = f"""[시스템 지시사항]
{system_prompt}

[사용자 질문]
{user_message}"""
            
            response = chat_session.send_message(full_prompt)
            return response.text
            
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return f"⚠️ AI 응답 생성 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
    
    def _fallback_response(self, user_message: str, vcp_data: list) -> str:
        """Gemini 사용 불가 시 폴백 응답"""
        lower_msg = user_message.lower()
        
        # 추천 요청
        if any(kw in lower_msg for kw in ['뭐 살', '추천', '종목', 'top']):
            if vcp_data:
                response = "📊 **오늘의 수급 상위 종목**\n\n"
                for i, stock in enumerate(vcp_data[:5], 1):
                    name = stock.get('name', 'N/A')
                    score = stock.get('supply_demand_score', 0)
                    double = " 🔥쌍끌이" if stock.get('is_double_buy') else ""
                    response += f"{i}. **{name}**: {score}점{double}\n"
                return response
            return "현재 데이터를 불러올 수 없습니다."
        
        # 특정 종목 질문
        for stock in vcp_data:
            if stock.get('name', '') in user_message:
                return self._format_stock_info(stock)
        
        return "질문을 이해하지 못했습니다. \"오늘 뭐 살까?\" 또는 \"삼성전자 어때?\"와 같이 질문해주세요."
    
    def _detect_stock_query(self, message: str) -> Optional[str]:
        """종목 관련 질문 감지 및 상세 정보 반환"""
        data = self._get_cached_data()
        vcp_stocks = data.get("vcp_stocks", [])
        
        for stock in vcp_stocks:
            name = stock.get('name', '')
            ticker = stock.get('ticker', '')
            
            if name in message or ticker in message:
                return self._format_stock_info(stock)
        
        return None
    
    def _format_stock_info(self, stock: Dict) -> str:
        """종목 정보 포맷팅"""
        name = stock.get('name', 'N/A')
        ticker = stock.get('ticker', '')
        score = stock.get('supply_demand_score', 0)
        stage = stock.get('supply_demand_stage', '')
        double = "✅ 쌍끌이" if stock.get('is_double_buy') else ""
        
        foreign_5d = stock.get('foreign_5d', 0)
        inst_5d = stock.get('inst_5d', 0)
        foreign_trend = stock.get('foreign_trend', 'N/A')
        inst_trend = stock.get('inst_trend', 'N/A')
        
        return f"""**{name}** ({ticker})
- 수급 점수: {score}점 ({stage})
- 외국인 5일: {foreign_5d:,}주 ({foreign_trend})
- 기관 5일: {inst_5d:,}주 ({inst_trend})
{double}"""
    
    def _handle_command(self, command: str) -> str:
        """명령어 처리"""
        parts = command.split(maxsplit=3)
        cmd = parts[0].lower()
        
        # /memory 명령어
        if cmd == "/memory":
            return self._handle_memory_command(parts[1:])
        
        # /clear 명령어
        elif cmd == "/clear":
            if len(parts) > 1 and parts[1] == "all":
                self.history.clear()
                self.memory.clear()
                return "✅ 모든 데이터가 초기화되었습니다."
            else:
                return self.history.clear()
        
        # /status 명령어
        elif cmd == "/status":
            return self._get_status()
        
        # 도움말(/help) 명령어
        elif cmd == "/help":
            return self._get_help()
        
        # /refresh 명령어
        elif cmd == "/refresh":
            self._data_cache = None
            return "✅ 데이터 캐시가 새로고침되었습니다."
        
        else:
            return f"❓ 알 수 없는 명령어: {cmd}\n/help로 명령어를 확인하세요."
    
    def _handle_memory_command(self, args: list) -> str:
        """메모리 명령어 처리"""
        if not args:
            args = ["view"]
        
        action = args[0].lower()
        
        if action == "view":
            memories = self.memory.view()
            if not memories:
                return "📭 저장된 메모리가 없습니다."
            
            result = "📝 **저장된 메모리**\n"
            for i, (key, data) in enumerate(memories.items(), 1):
                result += f"{i}. **{key}**: {data['value']}\n"
            return result
        
        elif action == "add" and len(args) >= 3:
            key = args[1]
            value = " ".join(args[2:])
            return self.memory.add(key, value)
        
        elif action == "remove" and len(args) >= 2:
            return self.memory.remove(args[1])
        
        elif action == "update" and len(args) >= 3:
            key = args[1]
            value = " ".join(args[2:])
            return self.memory.update(key, value)
        
        elif action == "clear":
            return self.memory.clear()
        
        else:
            return """**사용법:**
`/memory view` - 저장된 메모리 보기
`/memory add 키 값` - 메모리 추가
`/memory update 키 값` - 메모리 수정  
`/memory remove 키` - 메모리 삭제
`/memory clear` - 전체 삭제"""
    
    def _get_status(self) -> str:
        """현재 상태 확인"""
        memory_count = len(self.memory.view())
        history_count = self.history.count()
        gemini_status = "✅ 연결됨" if self.model else "❌ 미연결"
        
        data = self._get_cached_data()
        stock_count = len(data.get("vcp_stocks", []))
        
        return f"""📊 **현재 상태**
━━━━━━━━━━━━━━━━━━━━
👤 사용자: {self.user_id}
💾 저장된 메모리: {memory_count}개
💬 대화 히스토리: {history_count}개
🤖 Gemini: {gemini_status}
📈 VCP 종목: {stock_count}개
━━━━━━━━━━━━━━━━━━━━"""
    
    def _get_help(self) -> str:
        """도움말(Help) 메뉴"""
        return """🤖 **스마트머니봇 도움말**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📌 **일반 대화**
그냥 질문하면 됩니다!
• "오늘 뭐 살까?"
• "삼성전자 어때?"
• "반도체 섹터 상황은?"

📌 **명령어**
• `/memory view` - 저장된 정보 보기
• `/memory add 키 값` - 정보 저장
• `/memory remove 키` - 정보 삭제
• `/clear` - 대화 히스토리 초기화
• `/clear all` - 모든 데이터 초기화
• `/status` - 현재 상태 확인
• `/refresh` - 데이터 새로고침
• `/help` - 도움말

📌 **저장 추천 정보**
• 투자성향: 공격적/보수적/중립
• 관심섹터: 반도체, 2차전지 등
• 보유종목: 삼성전자, SK하이닉스 등

━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
    
    def get_welcome(self) -> str:
        """웰컴 메시지 반환"""
        top_stocks = get_top_vcp_stocks(3)
        return get_welcome_message(top_stocks)
    
    def to_dict(self) -> Dict[str, Any]:
        """API 응답용 상태 딕셔너리"""
        return {
            "user_id": self.user_id,
            "gemini_available": self.model is not None,
            "memory": self.memory.to_dict(),
            "history": self.history.to_dict()
        }
```

### chatbot/prompts.py (file:///Users/seoheun/Documents/kr_market_package/chatbot/prompts.py)
```python
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
```

