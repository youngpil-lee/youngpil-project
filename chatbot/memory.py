import json
import os
from pathlib import Path

class MemoryManager:
    """사용자 메모리 관리자 (투자 성향, 관심 종목 등)"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        # 데이터 저장 경로 설정
        self.base_dir = Path("data/chatbot/memory")
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.file_path = self.base_dir / f"{user_id}.json"
        
        # 초기 메모리 로드
        self.memories = self._load()

    def _load(self) -> dict:
        """파일에서 메모리 로드"""
        if self.file_path.exists():
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading memory: {e}")
        return {}

    def _save(self):
        """파일에 메모리 저장"""
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.memories, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving memory: {e}")

    def add(self, key: str, value: str) -> str:
        """새로운 메모리 추가"""
        self.memories[key] = {
            "value": value,
            "created_at": os.path.getmtime(self.file_path) if self.file_path.exists() else 0 # 임시
        }
        self._save()
        return f"✅ '{key}' 정보를 기억했습니다."

    def update(self, key: str, value: str) -> str:
        """기존 메모리 업데이트"""
        if key in self.memories:
            self.memories[key]["value"] = value
            self._save()
            return f"✅ '{key}' 정보를 업데이트했습니다."
        return f"❌ '{key}' 정보가 메모리에 없습니다."

    def remove(self, key: str) -> str:
        """메모리 삭제"""
        if key in self.memories:
            del self.memories[key]
            self._save()
            return f"✅ '{key}' 정보를 삭제했습니다."
        return f"❌ '{key}' 정보가 없습니다."

    def view(self) -> dict:
        """모든 메모리 보기"""
        return self.memories

    def clear(self) -> str:
        """모든 메모리 초기화"""
        self.memories = {}
        self._save()
        return "✅ 모든 사용자 메모리가 초기화되었습니다."

    def format_for_prompt(self) -> str:
        """프롬프트 삽입용 텍스트 포맷팅"""
        if not self.memories:
            return ""
        
        text = "\n### 사용자 메모리 (중요)\n"
        for key, info in self.memories.items():
            text += f"- {key}: {info['value']}\n"
        return text

    def to_dict(self) -> dict:
        """딕셔너리 형태로 반환"""
        return self.memories
