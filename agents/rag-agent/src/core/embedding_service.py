# OpenAI 임베딩 처리 서비스
# - semantic_query를 벡터로 변환
# - 배치 처리로 여러 쿼리 동시 임베딩

import openai
import asyncio
from typing import List
from loguru import logger
import os
import sys

# 상위 디렉토리의 config 모듈 import를 위한 경로 설정
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from config.settings import Settings

class EmbeddingService:
    """OpenAI 임베딩 API를 사용한 벡터 변환 서비스"""
    
    def __init__(self, api_key: str = None):
        """초기화"""
        if api_key:
            self.api_key = api_key
        else:
            settings = Settings()
            self.api_key = settings.OPENAI_API_KEY
            
        self.client = openai.OpenAI(api_key=self.api_key)
        self.model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-large")
        logger.info(f"✅ 임베딩 서비스 초기화 완료 - 모델: {self.model}")
    
    async def create_embeddings(self, texts: List[str]) -> List[List[float]]:
        """텍스트 리스트를 임베딩 벡터로 변환 (배치 처리)"""
        try:
            logger.info(f"🔄 임베딩 생성 시작 - {len(texts)}개 텍스트")
            
            # OpenAI API는 동기 호출이므로 executor에서 실행
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                self._create_embeddings_sync, 
                texts
            )
            
            embeddings = [data.embedding for data in response.data]
            logger.info(f"✅ 임베딩 생성 완료 - {len(embeddings)}개 벡터")
            return embeddings
            
        except Exception as e:
            logger.error(f"❌ 임베딩 생성 실패: {e}")
            raise
    
    def _create_embeddings_sync(self, texts: List[str]):
        """동기 임베딩 생성 (내부 메서드)"""
        return self.client.embeddings.create(
            input=texts,
            model=self.model
        )
    
    async def create_single_embedding(self, text: str) -> List[float]:
        """단일 텍스트를 임베딩 벡터로 변환"""
        try:
            logger.debug(f"🔄 단일 임베딩 생성: {text[:50]}...")
            
            embeddings = await self.create_embeddings([text])
            return embeddings[0]
            
        except Exception as e:
            logger.error(f"❌ 단일 임베딩 생성 실패: {e}")
            raise
    
    async def create_semantic_embeddings(self, semantic_queries: List[str]) -> List[List[float]]:
        """의미적 쿼리들을 임베딩으로 변환 (데이트 코스 특화)"""
        try:
            logger.info(f"🎯 의미적 쿼리 임베딩 생성 - {len(semantic_queries)}개")
            
            # 쿼리 전처리 (필요시)
            processed_queries = [self._preprocess_query(query) for query in semantic_queries]
            
            return await self.create_embeddings(processed_queries)
            
        except Exception as e:
            logger.error(f"❌ 의미적 임베딩 생성 실패: {e}")
            raise
    
    def _preprocess_query(self, query: str) -> str:
        """쿼리 전처리 (데이트 코스 맥락 추가)"""
        # 필요시 데이트 코스 관련 컨텍스트를 추가할 수 있음
        return query.strip()
    
    def get_embedding_dimension(self) -> int:
        """임베딩 벡터 차원 반환"""
        if self.model == "text-embedding-3-small":
            return 1536
        elif self.model == "text-embedding-3-large":
            return 3072  # Large 모델 차원
        elif self.model == "text-embedding-ada-002":
            return 1536
        else:
            return 3072  # 기본값을 Large로 변경
    
    async def test_connection(self) -> bool:
        """OpenAI API 연결 테스트"""
        try:
            test_embedding = await self.create_single_embedding("테스트")
            logger.info("✅ OpenAI 임베딩 API 연결 테스트 성공")
            return True
        except Exception as e:
            logger.error(f"❌ OpenAI 임베딩 API 연결 실패: {e}")
            return False

# 편의 함수
async def create_embedding_service() -> EmbeddingService:
    """임베딩 서비스 팩토리 함수"""
    service = EmbeddingService()
    
    # 연결 테스트
    if not await service.test_connection():
        raise RuntimeError("임베딩 서비스 연결 실패")
    
    return service

if __name__ == "__main__":
    # 테스트 실행
    async def test_embedding_service():
        try:
            service = EmbeddingService()
            
            # 단일 임베딩 테스트
            test_text = "홍대에서 커플이 가기 좋은 로맨틱한 파인다이닝 레스토랑"
            embedding = await service.create_single_embedding(test_text)
            print(f"✅ 단일 임베딩 성공 - 차원: {len(embedding)}")
            
            # 배치 임베딩 테스트
            test_texts = [
                "로맨틱한 분위기의 레스토랑",
                "조용한 와인바",
                "커플이 즐길 수 있는 문화시설"
            ]
            embeddings = await service.create_embeddings(test_texts)
            print(f"✅ 배치 임베딩 성공 - {len(embeddings)}개 벡터")
            
        except Exception as e:
            print(f"❌ 테스트 실패: {e}")
    
    asyncio.run(test_embedding_service())
