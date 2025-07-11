# API 키 관리 모듈
# 환경변수에서 API 키를 안전하게 로드하고 검증

import os
from typing import Optional
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

class APIKeyManager:
    """API 키 관리 클래스"""
    
    def __init__(self):
        self._openai_api_key: Optional[str] = None
        self._load_keys()
    
    def _load_keys(self):
        """환경변수에서 API 키 로드"""
        self._openai_api_key = os.getenv("OPENAI_API_KEY")
    
    @property
    def openai_api_key(self) -> str:
        """OpenAI API 키 반환"""
        if not self._openai_api_key:
            raise ValueError(
                "❌ OPENAI_API_KEY가 설정되지 않았습니다. "
                ".env 파일에 OPENAI_API_KEY=your_key_here 를 추가해주세요."
            )
        return self._openai_api_key
    
    def validate_keys(self) -> bool:
        """필수 API 키 검증"""
        try:
            _ = self.openai_api_key
            return True
        except ValueError:
            return False
    
    def get_openai_headers(self) -> dict:
        """OpenAI API 호출용 헤더 생성"""
        return {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json"
        }

# 싱글톤 인스턴스 생성
api_keys = APIKeyManager()

# 편의 함수들
def get_openai_key() -> str:
    """OpenAI API 키 반환"""
    return api_keys.openai_api_key

def validate_api_keys() -> bool:
    """API 키 유효성 검증"""
    return api_keys.validate_keys()

if __name__ == "__main__":
    # API 키 검증 테스트
    try:
        if validate_api_keys():
            print("✅ API 키가 올바르게 설정되었습니다.")
            print(f"OpenAI API 키: {get_openai_key()[:15]}...")
        else:
            print("❌ 필수 API 키가 설정되지 않았습니다.")
    except Exception as e:
        print(f"❌ API 키 검증 중 오류: {e}")
