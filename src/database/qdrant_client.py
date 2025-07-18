# Qdrant 로컬 파일 기반 클라이언트
# - 별도 서버 없이 파일로 벡터 DB 관리
# - 프로젝트 내 data/ 폴더에 저장

from qdrant_client import QdrantClient
from qdrant_client.http import models
from typing import List, Dict, Any, Optional
import os
import sys
from loguru import logger

# 상위 디렉토리의 config 모듈 import를 위한 경로 설정
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from config.settings import Settings

class QdrantClientManager:
    """Qdrant 로컬 파일 기반 벡터 DB 연결 및 기본 operations 관리"""
    
    def __init__(self, storage_path: str = None, collection_name: str = None):
        """
        로컬 파일 기반 Qdrant 클라이언트 초기화
        
        Args:
            storage_path: 벡터 DB 파일이 저장될 경로
            collection_name: 컬렉션 이름
        """
        # 설정 로드
        settings = Settings()
        self.storage_path = storage_path or settings.QDRANT_STORAGE_PATH
        self.collection_name = collection_name or settings.QDRANT_COLLECTION_NAME
        
        # 저장 경로 생성
        os.makedirs(self.storage_path, exist_ok=True)
        logger.info(f"📁 Qdrant 저장 경로: {self.storage_path}")
        
        # 로컬 파일 기반 클라이언트 생성
        self.client = QdrantClient(path=self.storage_path)
        logger.info("✅ Qdrant 로컬 클라이언트 생성 완료")
        
        # 컬렉션 초기화
        self._initialize_collection()
    
    def _initialize_collection(self):
        """컬렉션 초기화"""
        try:
            # 컬렉션이 있는지 확인
            collections = self.client.get_collections().collections
            collection_exists = any(col.name == self.collection_name for col in collections)
            
            if not collection_exists:
                # 컬렉션 생성 (OpenAI embedding 차원: 3072 for Large model)
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=3072,  # OpenAI text-embedding-3-large 차원
                        distance=models.Distance.COSINE
                    )
                )
                logger.info(f"✅ 컬렉션 '{self.collection_name}' 생성 완료")
            else:
                logger.info(f"✅ 기존 컬렉션 '{self.collection_name}' 로드 완료")
                
        except Exception as e:
            logger.error(f"❌ 컬렉션 초기화 오류: {e}")
            raise
    
    async def search_vectors(
        self, 
        query_vector: List[float], 
        limit: int, 
        filters: Optional[models.Filter] = None
    ) -> List[Dict]:
        """벡터 유사도 검색"""
        try:
            logger.debug(f"🔍 벡터 검색 시작 - limit: {limit}")
            
            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                query_filter=filters,
                limit=limit,
                with_payload=True,
                with_vectors=False
            )
            
            # 결과 변환
            results = []
            for point in search_result:
                result = {
                    'place_id': point.payload.get('place_id'),
                    'place_name': point.payload.get('place_name'),
                    'latitude': point.payload.get('latitude'),
                    'longitude': point.payload.get('longitude'),
                    'description': point.payload.get('description'),
                    'category': point.payload.get('category'),
                    'similarity_score': point.score,
                    'kakao_url': point.payload.get('kakao_url', '')
                }
                results.append(result)
            
            logger.info(f"✅ 벡터 검색 완료 - {len(results)}개 결과")
            return results
            
        except Exception as e:
            logger.error(f"❌ 벡터 검색 오류: {e}")
            return []
    
    async def search_with_geo_filter(
        self, 
        query_vector: List[float], 
        center_lat: float, 
        center_lon: float, 
        radius_meters: int, 
        category: str, 
        limit: int
    ) -> List[Dict]:
        """지리적 위치와 카테고리 필터링을 포함한 벡터 검색"""
        
        logger.info(f"🌍 지리적 필터 검색 - 중심: ({center_lat}, {center_lon}), 반경: {radius_meters}m, 카테고리: {category}")
        
        # 지리적 필터 생성 (간단한 박스 필터 사용)
        geo_filter = self.create_geo_filter(center_lat, center_lon, radius_meters, category)
        
        return await self.search_vectors(query_vector, limit, geo_filter)
    
    def add_places(self, places_data: List[Dict]):
        """장소 데이터 벡터 DB에 추가"""
        try:
            logger.info(f"📝 장소 데이터 추가 시작 - {len(places_data)}개")
            
            points = []
            for i, place in enumerate(places_data):
                # UUID 대신 정수 ID 사용 (Qdrant 호환)
                point_id = hash(place.get('place_id', f"place_{i}")) % (2**63 - 1)  # 64비트 정수로 변환
                if point_id < 0:
                    point_id = -point_id  # 음수면 양수로 변환
                    
                point = models.PointStruct(
                    id=point_id,  # 정수 ID 사용
                    vector=place['embedding_vector'],
                    payload={
                        'place_id': place['place_id'],
                        'place_name': place['place_name'],
                        'latitude': place['latitude'],
                        'longitude': place['longitude'],
                        'description': place['description'],
                        'category': place['category'],
                        # 추가 메타데이터
                        'price': place.get('price', []),
                        'address': place.get('address', ''),
                        'kakao_url': place.get('kakao_url', ''),
                        'summary': place.get('summary', '')
                    }
                )
                points.append(point)
            
            # 배치로 데이터 추가
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            
            logger.info(f"✅ {len(places_data)}개 장소 데이터 추가 완료")
            
        except Exception as e:
            logger.error(f"❌ 데이터 추가 오류: {e}")
            raise
    
    def get_collection_info(self) -> Dict:
        """컬렉션 정보 조회"""
        try:
            info = self.client.get_collection(self.collection_name)
            collection_info = {
                'collection_name': self.collection_name,
                'points_count': info.points_count,
                'status': info.status.value if hasattr(info.status, 'value') else str(info.status),
                'vectors_count': info.vectors_count if hasattr(info, 'vectors_count') else info.points_count
            }
            logger.info(f"📊 컬렉션 정보: {collection_info}")
            return collection_info
            
        except Exception as e:
            logger.error(f"❌ 컬렉션 정보 조회 오류: {e}")
            return {}
    
    def create_geo_filter(self, lat: float, lon: float, radius_meters: int, category: str) -> models.Filter:
        """지리적 위치 및 카테고리 필터 생성"""
        # 반경을 위도/경도 차이로 근사 변환 (1도 ≈ 111km)
        import math
        lat_diff = radius_meters / 111000  # 미터를 위도 차이로 변환
        lon_diff = radius_meters / (111000 * math.cos(math.radians(lat)))
        
        logger.debug(f"🔧 지리적 필터 생성 - 위도차: {lat_diff:.6f}, 경도차: {lon_diff:.6f}")
        
        return models.Filter(
            must=[
                # 카테고리 필터
                models.FieldCondition(
                    key="category",
                    match=models.MatchValue(value=category)
                ),
                # 위도 범위 필터
                models.FieldCondition(
                    key="latitude",
                    range=models.Range(
                        gte=lat - lat_diff,
                        lte=lat + lat_diff
                    )
                ),
                # 경도 범위 필터  
                models.FieldCondition(
                    key="longitude",
                    range=models.Range(
                        gte=lon - lon_diff,
                        lte=lon + lon_diff
                    )
                )
            ]
        )
    
    def create_category_filter(self, category: str) -> models.Filter:
        """카테고리 필터만 생성"""
        return models.Filter(
            must=[
                models.FieldCondition(
                    key="category",
                    match=models.MatchValue(value=category)
                )
            ]
        )
    
    def clear_collection(self):
        """컬렉션의 모든 데이터 삭제"""
        try:
            self.client.delete_collection(self.collection_name)
            self._initialize_collection()
            logger.info(f"🗑️ 컬렉션 '{self.collection_name}' 초기화 완료")
        except Exception as e:
            logger.error(f"❌ 컬렉션 초기화 오류: {e}")
            raise

# 전역 클라이언트 인스턴스 (싱글톤 패턴)
_qdrant_client = None

def get_qdrant_client() -> QdrantClientManager:
    """Qdrant 클라이언트 싱글톤 인스턴스 반환"""
    global _qdrant_client
    if _qdrant_client is None:
        _qdrant_client = QdrantClientManager()
    return _qdrant_client

def reset_qdrant_client():
    """클라이언트 인스턴스 리셋 (테스트용)"""
    global _qdrant_client
    _qdrant_client = None

if __name__ == "__main__":
    # 테스트 실행
    try:
        client = get_qdrant_client()
        info = client.get_collection_info()
        print("✅ Qdrant 클라이언트 테스트 성공")
        print(f"컬렉션 정보: {info}")
    except Exception as e:
        print(f"❌ Qdrant 클라이언트 테스트 실패: {e}")
