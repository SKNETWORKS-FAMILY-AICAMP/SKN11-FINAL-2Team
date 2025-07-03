# Place Agent 설정 관리
# - 환경 변수 및 시스템 설정

import os
from typing import Optional
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

class Settings:
    """Place Agent 시스템 설정 클래스"""
    
    # OpenAI API 설정
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    
    # 서버 설정
    SERVER_HOST: str = os.getenv("SERVER_HOST", "0.0.0.0")
    SERVER_PORT: int = int(os.getenv("SERVER_PORT", "8001"))
    
    # Place Agent 설정
    DEFAULT_PLACE_COUNT: int = 3
    MAX_PLACE_COUNT: int = 10
    COORDINATE_PRECISION: int = 6  # 소수점 자리수
    
    # LLM 설정
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 500
    LLM_TIMEOUT: float = 30.0
    
    @classmethod
    def validate_settings(cls) -> bool:
        """필수 설정값 검증"""
        if not cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
        return True
    
    @classmethod
    def print_config(cls):
        """현재 설정 출력 (디버깅용)"""
        print("📋 Place Agent 설정:")
        print(f"  OpenAI API Key: {'✅ 설정됨' if cls.OPENAI_API_KEY else '❌ 미설정'}")
        print(f"  서버 주소: {cls.SERVER_HOST}:{cls.SERVER_PORT}")
        print(f"  기본 장소 개수: {cls.DEFAULT_PLACE_COUNT}")
        print(f"  LLM 모델: {cls.OPENAI_MODEL}")

# 설정 인스턴스
settings = Settings()

if __name__ == "__main__":
    # 설정 테스트
    try:
        settings.validate_settings()
        settings.print_config()
        print("✅ 모든 설정이 올바르게 구성되었습니다!")
    except Exception as e:
        print(f"❌ 설정 오류: {e}")