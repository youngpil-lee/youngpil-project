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
    # 프로젝트 루트의 .env 파일을 찾기 위해 경로 설정
    env_path = Path(__file__).parent.parent / ".env"
    load_dotenv(env_path)
except ImportError:
    pass  # python-dotenv not installed

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# 로컬 모듈 임포트 (패키지 구조에 따라 상대 임포트 사용)
try:
    from .memory import MemoryManager
    from .history import HistoryManager
    from .prompts import build_system_prompt, get_welcome_message, SYSTEM_PERSONA
    from .data_loader import fetch_all_data, search_stock, get_top_vcp_stocks
except ImportError:
    # 직접 실행 시를 위한 폴백
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
                    # 데이터 필드명 확인 (score 또는 supply_demand_score)
                    score = stock.get('score') or stock.get('supply_demand_score', 0)
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
            
            if name in message or (ticker and ticker in message):
                return self._format_stock_info(stock)
        
        return None
    
    def _format_stock_info(self, stock: Dict) -> str:
        """종목 정보 포맷팅"""
        name = stock.get('name', 'N/A')
        ticker = stock.get('ticker', '')
        score = stock.get('score') or stock.get('supply_demand_score', 0)
        grade = stock.get('grade', '')
        double = "✅ 쌍끌이" if stock.get('is_double_buy') else ""
        
        foreign_5d = stock.get('foreign_5d', 0)
        inst_5d = stock.get('inst_5d', 0)
        
        return f"""**{name}** ({ticker})
- 종합 점수: {score}점 (등급: {grade})
- 외국인 5일 순매수: {foreign_5d:,}
- 기관 5일 순매수: {inst_5d:,}
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
            return self.get_status()
        
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

    # --- API 호환용 메서드들 ---

    def get_memory(self) -> dict:
        """현재 메모리 반환"""
        return self.memory.view()

    def update_memory(self, data: dict) -> str:
        """메모리 업데이트"""
        for k, v in data.items():
            self.memory.add(k, v)
        return "✅ 메모리가 업데이트되었습니다."

    def clear_memory(self) -> str:
        """메모리 초기화"""
        return self.memory.clear()

    def get_history(self) -> list:
        """대화 히스토리 반환"""
        return self.history.get_recent()

    def clear_history(self) -> str:
        """히스토리 초기화"""
        return self.history.clear()

    def get_status(self) -> dict:
        """현재 상태 확인 (API 응답용)"""
        memory_count = len(self.memory.view())
        history_count = self.history.count()
        gemini_status = "✅ 연결됨" if self.model else "❌ 미연결"
        
        data = self._get_cached_data()
        stock_count = len(data.get("vcp_stocks", []))
        
        return {
            "user_id": self.user_id,
            "memory_count": memory_count,
            "history_count": history_count,
            "gemini_status": gemini_status,
            "vcp_stock_count": stock_count,
            "timestamp": datetime.now().isoformat()
        }

    def _get_status_text(self) -> str:
        """현재 상태 확인 (텍스트 응답용)"""
        st = self.get_status()
        
        return f"""📊 **현재 상태**
━━━━━━━━━━━━━━━━━━━━
👤 사용자: {st['user_id']}
💾 저장된 메모리: {st['memory_count']}개
💬 대화 히스토리: {st['history_count']}개
🤖 Gemini: {st['gemini_status']}
📈 VCP 종목: {st['vcp_stock_count']}개
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
    
    def get_welcome_message(self) -> str:
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
