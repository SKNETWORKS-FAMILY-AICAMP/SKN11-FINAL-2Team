import asyncio
import time
from typing import Dict, Any, List, Optional
from loguru import logger

from src.core.embedding_service import EmbeddingService
from src.database.vector_search import SmartVectorSearchEngine


class PlaceSearchAgent:
    """장소 설명 기반 검색을 담당하는 에이전트"""
    
    def __init__(self):
        """기존 서비스들 재사용"""
        self.embedding_service = EmbeddingService()
        self.vector_search = SmartVectorSearchEngine()
        logger.info("✅ PlaceSearchAgent 초기화 완료")
    
    async def process_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """메인 처리 로직"""
        start_time = time.time()
        
        try:
            description = request_data["description"]
            district = request_data["district"] 
            category = request_data.get("category")
            
            logger.info(f"🔍 장소 검색 시작: 설명='{description}', 구='{district}', 카테고리='{category}'")
            
            # 병렬 처리: 임베딩 생성 + 필터 조건 생성
            embedding_task = asyncio.create_task(
                self.embedding_service.create_single_embedding(description)
            )
            filter_task = asyncio.create_task(
                self._build_filters(district, category)
            )
            
            embedding, filters = await asyncio.gather(embedding_task, filter_task)
            
            # Qdrant 벡터 검색 실행
            search_results = await self._execute_vector_search(embedding, filters)
            
            # place_id만 추출
            place_ids = self._extract_place_ids(search_results)
            
            processing_time = time.time() - start_time
            logger.info(f"✅ 검색 완료: {len(place_ids)}개 장소 발견 ({processing_time:.2f}초)")
            
            return {
                "status": "success",
                "place_ids": place_ids,
                "total_results": len(place_ids),
                "processing_time": processing_time
            }
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"❌ 장소 검색 실패: {str(e)} ({processing_time:.2f}초)")
            
            return {
                "status": "error", 
                "place_ids": [],
                "error_message": str(e),
                "processing_time": processing_time
            }

    async def _build_filters(self, district: str, category: Optional[str] = None) -> Dict[str, Any]:
        """구와 카테고리 필터 조건 생성"""
        filters = {
            "must": []
        }
        
        # 1. 구 필터 (필수) - place_id에서 구 정보 추출
        if district:
            filters["must"].append({
                "match": {
                    "place_id": {
                        "text": district
                    }
                }
            })
        
        # 2. 카테고리 필터 (선택적)
        if category and category != "전체":
            filters["must"].append({
                "match": {
                    "category": category
                }
            })
        
        logger.debug(f"🔧 필터 조건 생성: {filters}")
        return filters
    
    async def _execute_vector_search(self, embedding: List[float], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Qdrant 벡터 검색 실행"""
        try:
            # Qdrant 클라이언트 직접 사용하여 검색
            from qdrant_client.models import Filter, FieldCondition, MatchText, MatchValue
            
            # 필터 조건을 Qdrant 형식으로 변환
            qdrant_filter = None
            if filters and filters.get("must"):
                conditions = []
                for condition in filters["must"]:
                    if "match" in condition:
                        for field, value in condition["match"].items():
                            if isinstance(value, dict) and "text" in value:
                                # place_id에서 구 정보 매칭
                                conditions.append(
                                    FieldCondition(
                                        key=field,
                                        match=MatchText(text=value["text"])
                                    )
                                )
                            else:
                                # 일반 필드 매칭 - MatchValue 객체로 감싸기
                                conditions.append(
                                    FieldCondition(
                                        key=field,
                                        match=MatchValue(value=str(value))
                                    )
                                )
                
                if conditions:
                    qdrant_filter = Filter(must=conditions)
            
            # Qdrant 검색 실행 (올바른 메서드 사용)
            search_results = await self.vector_search.qdrant_client.search_vectors(
                query_vector=embedding,
                limit=20,
                filters=qdrant_filter
            )
            
            # 결과는 이미 딕셔너리 형태로 반환됨
            formatted_results = search_results
            
            logger.info(f"🎯 벡터 검색 완료: {len(formatted_results)}개 결과")
            return formatted_results
            
        except Exception as e:
            logger.error(f"❌ 벡터 검색 실패: {str(e)}")
            raise
    
    def _extract_place_ids(self, search_results: List[Dict[str, Any]]) -> List[str]:
        """검색 결과에서 place_id만 추출"""
        place_ids = []
        
        for result in search_results:
            try:
                # 결과 구조에 따라 place_id 추출
                place_id = None
                
                # payload에서 place_id 찾기
                if 'payload' in result:
                    place_id = result['payload'].get('place_id')
                
                # 직접 place_id 필드에서 찾기  
                if not place_id:
                    place_id = result.get('place_id')
                
                # metadata에서 찾기
                if not place_id and 'metadata' in result:
                    place_id = result['metadata'].get('place_id')
                
                if place_id:
                    place_ids.append(place_id)
                    logger.debug(f"✅ place_id 추출: {place_id} (유사도: {result.get('score', 0):.3f})")
                else:
                    logger.warning(f"⚠️ place_id 누락: {result}")
                    
            except Exception as e:
                logger.warning(f"⚠️ place_id 추출 실패: {result}, error: {e}")
                continue
        
        return place_ids
    
    def _extract_district_from_place_id(self, place_id: str) -> str:
        """place_id에서 구 정보 추출"""
        try:
            # place_id 형태: "kakao_레스토랑_용산구_000014"
            parts = place_id.split('_')
            if len(parts) >= 3:
                district = parts[2]  # "용산구"
                if district.endswith('구'):
                    return district
        except Exception as e:
            logger.warning(f"⚠️ place_id 파싱 실패: {place_id}, error: {e}")
        
        return ""
    
    def _validate_district(self, district: str) -> bool:
        """25개구 유효성 검증"""
        seoul_districts = [
            "강남구", "강동구", "강북구", "강서구", "관악구", "광진구", "구로구", "금천구", 
            "노원구", "도봉구", "동대문구", "동작구", "마포구", "서대문구", "서초구", 
            "성동구", "성북구", "송파구", "양천구", "영등포구", "용산구", "은평구", 
            "종로구", "중구", "중랑구"
        ]
        return district in seoul_districts