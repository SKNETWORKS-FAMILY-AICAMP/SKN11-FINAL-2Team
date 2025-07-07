#!/usr/bin/env python3

import sys
import os
import asyncio
sys.path.append('/Users/hwangjunho/Desktop/date-course-agent/src')

from database.qdrant_client import get_qdrant_client
from core.embedding_service import EmbeddingService

async def test_vector_search():
    """벡터 검색 직접 테스트"""
    try:
        print("🔍 벡터 검색 직접 테스트...")
        
        # 클라이언트 초기화
        qdrant_client = get_qdrant_client()
        embedding_service = EmbeddingService()
        
        # 컬렉션 정보 확인
        info = qdrant_client.get_collection_info()
        print(f"📊 컬렉션 정보: {info}")
        
        # 테스트 쿼리 (용산구 맞춤)
        test_query = "이태원에서 로맨틱한 레스토랑"
        print(f"🔍 검색 쿼리: '{test_query}'")
        
        # 임베딩 생성
        embedding = await embedding_service.create_single_embedding(test_query)
        print(f"✅ 임베딩 생성 완료 - 차원: {len(embedding)}")
        
        # 지리적 필터 검색 (이태원 중심)
        results = await qdrant_client.search_with_geo_filter(
            query_vector=embedding,
            center_lat=37.5339,  # 이태원
            center_lon=126.9956,
            radius_meters=2000,
            category="음식점",
            limit=5
        )
        
        print(f"✅ 검색 결과: {len(results)}개")
        for i, result in enumerate(results, 1):
            print(f"  {i}. {result['place_name']} (유사도: {result['similarity_score']:.3f})")
            print(f"     카테고리: {result['category']}")
            print(f"     위치: ({result['latitude']:.4f}, {result['longitude']:.4f})")
            print()
        
        if not results:
            print("❌ 검색 결과가 없습니다!")
            
            # 전체 검색 (필터 없이)
            print("🔍 전체 검색 시도...")
            all_results = await qdrant_client.search_vectors(
                query_vector=embedding,
                limit=10
            )
            print(f"전체 검색 결과: {len(all_results)}개")
            for i, result in enumerate(all_results[:3], 1):
                print(f"  {i}. {result['place_name']} - {result['category']}")
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_vector_search())
