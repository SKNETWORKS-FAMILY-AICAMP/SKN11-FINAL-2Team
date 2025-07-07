#!/usr/bin/env python3
"""
간단한 벡터 DB 확인 스크립트
"""

import sys
import os
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def check_vector_db():
    """벡터 DB 상태 확인"""
    
    print("🔍 벡터 DB 상태 확인 중...")
    print("=" * 50)
    
    try:
        # 설정 확인
        from config.settings import Settings
        settings = Settings()
        
        print(f"📁 저장 경로: {settings.QDRANT_STORAGE_PATH}")
        print(f"📊 컬렉션: {settings.QDRANT_COLLECTION_NAME}")
        
        # 클라이언트 연결
        from src.database.qdrant_client import get_qdrant_client
        qdrant_client = get_qdrant_client()
        
        # 컬렉션 정보
        collection_info = qdrant_client.client.get_collection(settings.QDRANT_COLLECTION_NAME)
        print(f"\n✅ 컬렉션 연결 성공!")
        print(f"   - 총 데이터 수: {collection_info.points_count}")
        print(f"   - 벡터 차원: {collection_info.config.params.vectors.size}")
        
        # 샘플 데이터 몇 개 확인
        print(f"\n📋 샘플 데이터 (최대 5개):")
        
        results = qdrant_client.client.scroll(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            limit=5,
            with_payload=True,
            with_vectors=False
        )
        
        for i, point in enumerate(results[0], 1):
            payload = point.payload
            print(f"\n   {i}. {payload.get('place_name', 'Unknown')}")
            print(f"      카테고리: {payload.get('category', 'Unknown')}")
            print(f"      위치: ({payload.get('latitude', 0):.4f}, {payload.get('longitude', 0):.4f})")
            description = payload.get('description', '')
            if description:
                print(f"      설명: {description[:100]}...")
        
        # 카테고리별 개수 확인
        print(f"\n📊 카테고리별 데이터 수:")
        categories = ["음식점", "카페", "술집", "문화시설", "휴식시설", "야외활동", "쇼핑", "엔터테인먼트"]
        
        for category in categories:
            try:
                count_result = qdrant_client.client.count(
                    collection_name=settings.QDRANT_COLLECTION_NAME,
                    count_filter={
                        "must": [
                            {
                                "key": "category",
                                "match": {"value": category}
                            }
                        ]
                    }
                )
                print(f"   - {category}: {count_result.count}개")
            except Exception as e:
                print(f"   - {category}: 확인 실패 ({str(e)})")
        
    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_vector_db()
