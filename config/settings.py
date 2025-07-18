# 설정 관리 (로컬 파일 기반 Qdrant 버전)
# - 환경 변수 및 시스템 설정

import os
from typing import Optional

# 환경변수 로드 (가장 먼저 실행)
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ .env 파일 로드 완료")
except ImportError:
    print("⚠️  python-dotenv가 설치되지 않음. pip install python-dotenv")
except Exception as e:
    print(f"⚠️  .env 파일 로드 실패: {e}")

class Settings:
    """시스템 설정 클래스"""
    
    # OpenAI API 설정
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_EMBEDDING_MODEL: str = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-large")
    OPENAI_GPT_MODEL: str = os.getenv("OPENAI_GPT_MODEL", "gpt-4o-mini")
    
    # Qdrant 로컬 파일 설정 (서버 불필요!)
    QDRANT_STORAGE_PATH: str = os.getenv("QDRANT_STORAGE_PATH", "./data/qdrant_storage")
    QDRANT_COLLECTION_NAME: str = os.getenv("QDRANT_COLLECTION_NAME", "date_course_places")
    
    # 검색 설정 (거리 제한 강화!)
    DEFAULT_SEARCH_RADIUS: int = int(os.getenv("DEFAULT_SEARCH_RADIUS", "1000"))  # 2000 → 1000m (1km)
    RADIUS_EXPANSION_FACTOR: float = float(os.getenv("RADIUS_EXPANSION_FACTOR", "1.3"))  # 1.5 → 1.3 (확장 범위 축소)
    MAX_SEARCH_ATTEMPTS: int = int(os.getenv("MAX_SEARCH_ATTEMPTS", "3"))
    
    # 거리 제한 설정 (새로 추가)
    MAX_TOTAL_DISTANCE: int = int(os.getenv("MAX_TOTAL_DISTANCE", "3000"))  # 총 이동거리 3km 제한
    MAX_SINGLE_SEGMENT_DISTANCE: int = int(os.getenv("MAX_SINGLE_SEGMENT_DISTANCE", "1500"))  # 구간별 1.5km 제한
    
    # 조합 설정
    FIRST_ATTEMPT_TOP_K: int = int(os.getenv("FIRST_ATTEMPT_TOP_K", "5"))
    SECOND_ATTEMPT_TOP_K: int = int(os.getenv("SECOND_ATTEMPT_TOP_K", "8"))
    MAX_COMBINATIONS_PER_ATTEMPT: int = 100
    
    # 성능 설정
    MAX_WORKERS: int = int(os.getenv("MAX_WORKERS", "10"))
    REQUEST_TIMEOUT: float = float(os.getenv("REQUEST_TIMEOUT", "120.0"))
    EMBEDDING_BATCH_SIZE: int = 10
    
    # 로깅 설정
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # 서버 설정
    SERVER_HOST: str = os.getenv("SERVER_HOST", "0.0.0.0")
    SERVER_PORT: int = int(os.getenv("SERVER_PORT", "8000"))
    
    # 카테고리 매핑 (비올 때 야외활동 변환)
    RAINY_WEATHER_CATEGORY_MAPPING = {
        "야외활동": ["문화시설", "휴식시설"]
    }
    
    # GPT 프롬프트 설정
    GPT_MAX_TOKENS: int = int(os.getenv("OPENAI_MAX_TOKENS", "1500"))
    GPT_TEMPERATURE: float = float(os.getenv("OPENAI_TEMPERATURE", "0.3"))
    
    @classmethod
    def validate_settings(cls) -> bool:
        """필수 설정값 검증"""
        if not cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
        return True
    
    @classmethod
    def get_qdrant_storage_path(cls) -> str:
        """Qdrant 저장 경로 반환"""
        # 상대경로를 절대경로로 변환
        if cls.QDRANT_STORAGE_PATH.startswith('./'):
            import os
            return os.path.abspath(cls.QDRANT_STORAGE_PATH)
        return cls.QDRANT_STORAGE_PATH
    
    @classmethod
    def print_config(cls):
        """현재 설정 출력 (디버깅용)"""
        print("📋 현재 설정:")
        print(f"  OpenAI API Key: {'✅ 설정됨' if cls.OPENAI_API_KEY else '❌ 미설정'}")
        print(f"  Qdrant 저장 경로: {cls.get_qdrant_storage_path()}")
        print(f"  컬렉션 이름: {cls.QDRANT_COLLECTION_NAME}")
        print(f"  검색 반경: {cls.DEFAULT_SEARCH_RADIUS}m")
        print(f"  서버 주소: {cls.SERVER_HOST}:{cls.SERVER_PORT}")

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
