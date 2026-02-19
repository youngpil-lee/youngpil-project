import json
from pathlib import Path
from typing import List, Dict

class HistoryManager:
    """대화 기록 관리자 (Gemini API 형식 호환)"""
    
    def __init__(self, user_id: str, max_history: int = 20):
        self.user_id = user_id
        self.max_history = max_history
        self.base_dir = Path("data/chatbot/history")
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.file_path = self.base_dir / f"{user_id}.json"
        
        # 초기 대화 기록 로드
        self.history = self._load()

    def _load(self) -> List[Dict]:
        """파일에서 대화 기록 로드"""
        if self.file_path.exists():
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading history: {e}")
        return []

    def _save(self):
        """파일에 대화 기록 저장"""
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving history: {e}")

    def add(self, role: str, text: str):
        """대화 추가 (role: 'user' 또는 'model')"""
        # Gemini API 형식: {"role": role, "parts": [{"text": text}]}
        entry = {
            "role": "user" if role == "user" else "model",
            "parts": [{"text": text}]
        }
        self.history.append(entry)
        
        # 최대 기록 유지 (사용자+모델 페어 고려)
        if len(self.history) > self.max_history * 2:
            self.history = self.history[-(self.max_history * 2):]
            
        self._save()

    def get_recent(self) -> List[Dict]:
        """최근 대화 기록 반환"""
        return self.history

    def clear(self) -> str:
        """대화 기록 초기화"""
        self.history = []
        self._save()
        return "✅ 대화 기록이 모두 삭제되었습니다."

    def count(self) -> int:
        """대화 기록 개수"""
        return len(self.history)

    def to_dict(self) -> List[Dict]:
        """리스트 형태로 반환"""
        return self.history
