# 벡터 DB 초기화 및 관리 스크립트
# 샘플 데이터를 로드하고 Qdrant에 저장

import json
import asyncio
import os
from pathlib import Path

# 상위 디렉토리의 src 모듈 import를 위한 경로 설정
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from database.qdrant_client import get_qdrant_client
from core.embedding_service import EmbeddingService
from config.api_keys import api_keys

async def initialize_vector_db():
    """벡터 DB 초기화 및 샘플 데이터 로드"""
    print("🚀 벡터 DB 초기화 시작...")
    
    try:
        # Qdrant 클라이언트 생성
        qdrant_client = get_qdrant_client()
        print("✅ Qdrant 클라이언트 생성 완료")
        
        # 샘플 장소 데이터 로드
        data_path = Path(__file__).parent / "sample_places.json"
        with open(data_path, 'r', encoding='utf-8') as f:
            places_data = json.load(f)
        print(f"✅ 샘플 데이터 로드 완료: {len(places_data)}개 장소")
        
        # 임베딩 서비스 초기화
        embedding_service = EmbeddingService(api_keys.openai_api_key)
        print("✅ 임베딩 서비스 초기화 완료")
        
        # 각 장소의 설명문을 임베딩으로 변환
        descriptions = [place['description'] for place in places_data]
        embeddings = await embedding_service.create_embeddings(descriptions)
        print("✅ 임베딩 생성 완료")
        
        # 임베딩을 장소 데이터에 추가
        for i, place in enumerate(places_data):
            place['embedding_vector'] = embeddings[i]
        
        # 벡터 DB에 데이터 추가
        qdrant_client.add_places(places_data)
        print("✅ 벡터 DB에 데이터 추가 완료")
        
        # 컬렉션 정보 출력
        info = qdrant_client.get_collection_info()
        print(f"✅ 컬렉션 정보: {info}")
        
        print("🎉 벡터 DB 초기화 완료!")
        
    except Exception as e:
        print(f"❌ 벡터 DB 초기화 실패: {e}")
        raise

async def test_vector_search():
    """벡터 검색 테스트"""
    print("\n🔍 벡터 검색 테스트 시작...")
    
    try:
        qdrant_client = get_qdrant_client()
        embedding_service = EmbeddingService(api_keys.openai_api_key)
        
        # 테스트 쿼리
        test_query = "로맨틱한 분위기의 파인다이닝 레스토랑"
        query_embedding = await embedding_service.create_single_embedding(test_query)
        
        # 검색 수행
        results = await qdrant_client.search_vectors(
            query_vector=query_embedding,
            limit=3
        )
        
        print(f"✅ 검색 결과 ({len(results)}개):")
        for i, result in enumerate(results, 1):
            print(f"  {i}. {result['place_name']} (유사도: {result['similarity_score']:.3f})")
            print(f"     카테고리: {result['category']}")
            print(f"     설명: {result['description'][:50]}...")
            print()
        
        print("🎉 벡터 검색 테스트 완료!")
        
    except Exception as e:
        print(f"❌ 벡터 검색 테스트 실패: {e}")

async def main():
    """메인 실행 함수"""
    print("📊 Qdrant 로컬 파일 기반 벡터 DB 설정")
    print("=" * 50)
    
    # API 키 확인
    try:
        api_key = api_keys.openai_api_key
        print(f"✅ OpenAI API 키 확인: {api_key[:10]}...")
    except Exception as e:
        print(f"❌ OpenAI API 키 오류: {e}")
        print("💡 .env 파일에 OPENAI_API_KEY를 설정해주세요.")
        return
    
    # 벡터 DB 초기화
    await initialize_vector_db()
    
    # 검색 테스트
    await test_vector_search()
    
    print("\n🎯 다음 단계:")
    print("1. 실제 장소 데이터를 더 많이 수집하여 추가")
    print("2. 웹 크롤링 또는 API로 실시간 데이터 수집")
    print("3. 정기적인 데이터 업데이트 스케줄링")

if __name__ == "__main__":
    asyncio.run(main())