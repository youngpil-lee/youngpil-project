# chatbot/__init__.py
from .core import KRStockChatbot

# 단일 세션용 전역 인스턴스 (필요 시 사용자별 관리 가능)
_chatbot_instance = None

def get_chatbot(user_id: str = "default_user") -> KRStockChatbot:
    """
    챗봇 인스턴스를 반환하는 팩토리 함수.
    싱글톤 패턴을 사용하여 리소스를 절약합니다.
    """
    global _chatbot_instance
    if _chatbot_instance is None:
        _chatbot_instance = KRStockChatbot(user_id=user_id)
    return _chatbot_instance
