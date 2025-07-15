# 벡터 검색 로직 및 재시도 전략 (Top-K 순차 확대) - 최종 개선안
# - '단일 지역' 검색 시, location_analyzer가 결정한 동적 검색 반경을 사용
# - 조합이 부족할 경우, Top-K를 순차적으로 늘려가며 재시도
# - 반경 확대는 모든 Top-K 시도 후, 최후의 보루로만 사용

import asyncio
from typing import List, Dict, Any
from loguru import logger
import os
import sys

# 상위 디렉토리의 모듈들 import
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from src.database.qdrant_client import get_qdrant_client

class VectorSearchResult:
    """벡터 검색 결과 래퍼"""
    def __init__(self, places: List[Dict], attempt: str, radius_used: int, top_k_used: int):
        self.places = places
        self.attempt = attempt
        self.radius_used = radius_used
        self.top_k_used = top_k_used

class SmartVectorSearchEngine:
    """스마트 벡터 검색 엔진 (Top-K 순차 확대 전략)"""

    def __init__(self):
        """초기화"""
        self.qdrant_client = get_qdrant_client()
        self.top_k_steps = [5, 8, 12] # 재시도 시 사용할 Top-K 값들 (더 점진적이고 효율적)
        self.radius_expansion_factor = 1.5
        logger.info("✅ 스마트 벡터 검색 엔진 초기화 완료 (Top-K 순차 확대 전략)")

    async def search_with_retry_logic(
        self,
        search_targets: List[Dict[str, Any]],
        embeddings: List[List[float]],
        location_analysis: Dict[str, Any]
    ) -> VectorSearchResult:
        """
        상황에 맞는 동적 검색 반경을 사용하고,
        결과가 부족하면 Top-K를 순차적으로 늘려 재시도한다.
        """
        try:
            # 1. Top-K 순차적 재시도
            for i, top_k in enumerate(self.top_k_steps):
                attempt_name = f"{i+1}차 (Top-K={top_k})"
                logger.info(f"▶️  {attempt_name} 검색 시작")

                # location_analysis에서 결정된 동적 검색 반경을 사용
                search_results = await self._execute_search(search_targets, embeddings, location_analysis, top_k)

                if self._is_search_successful(search_results, len(search_targets)):
                    logger.info(f"✅ {attempt_name} 검색 성공 - 충분한 장소 확보")
                    # 클러스터별 반경이 다를 수 있으므로, 첫번째 클러스터의 반경을 대표로 사용
                    radius_used = location_analysis['clusters'][0].search_radius
                    return VectorSearchResult(search_results, attempt_name, radius_used, top_k)
                else:
                    logger.warning(f"⚠️ {attempt_name} 검색 불충분, 다음 단계 시도")

            # 2. 최후의 보루: 반경 확대 재시도
            logger.warning(f"🚨 모든 Top-K 시도 실패. 최후의 보루 (반경 확대) 시도")
            
            # 기존 분석 결과의 반경을 1.5배 확대하여 새로운 분석 결과 생성
            expanded_location_analysis = self._expand_search_radius(location_analysis)
            final_top_k = self.top_k_steps[1] # 반경 확대 시에는 Top-K=5로 고정
            attempt_name = f"최후 (반경 확대, Top-K={final_top_k})"

            final_results = await self._execute_search(search_targets, embeddings, expanded_location_analysis, final_top_k)
            
            radius_used = expanded_location_analysis['clusters'][0].search_radius
            logger.info(f"✅ {attempt_name} 검색 완료")
            return VectorSearchResult(final_results, attempt_name, radius_used, final_top_k)

        except Exception as e:
            logger.error(f"❌ 스마트 벡터 검색 실패: {e}")
            return VectorSearchResult([], "실패", 0, 0)

    async def _execute_search(
        self,
        search_targets: List[Dict[str, Any]],
        embeddings: List[List[float]],
        location_analysis: Dict[str, Any],
        top_k: int
    ) -> List[Dict]:
        """실제 DB 검색을 수행하는 내부 함수"""
        all_places = []
        clusters = location_analysis['clusters']

        # 각 클러스터별로 검색 수행
        for cluster in clusters:
            # 클러스터에 속한 타겟들만 필터링
            cluster_target_indices = [i for i, t in enumerate(search_targets) if self._is_target_in_cluster(t, cluster)]

            for i in cluster_target_indices:
                target = search_targets[i]
                embedding = embeddings[i]
                
                # location_analyzer가 결정한 동적 검색 반경을 사용!
                radius = cluster.search_radius

                search_results = await self.qdrant_client.search_with_geo_filter(
                    query_vector=embedding,
                    center_lat=cluster.center_lat,
                    center_lon=cluster.center_lon,
                    radius_meters=radius,
                    category=self._get_target_info(target, 'category'),
                    limit=top_k
                )

                for result in search_results:
                    result['search_sequence'] = self._get_target_info(target, 'sequence')
                    result['target_category'] = self._get_target_info(target, 'category')
                all_places.extend(search_results)
        
        logger.debug(f"   검색 완료 (Top-K={top_k}) - 총 {len(all_places)}개 장소 발견")
        return all_places

    def _is_search_successful(self, places: List[Dict], target_count: int) -> bool:
        """검색 성공 여부 판단 (각 카테고리별로 최소 2개 이상 결과 확보)"""
        if not places:
            return False
        
        places_by_seq = {}
        for p in places:
            seq = p.get('search_sequence')
            if seq not in places_by_seq:
                places_by_seq[seq] = []
            places_by_seq[seq].append(p)
        
        # 모든 요청 타겟에 대해 결과가 있는지, 그리고 각 결과가 최소 2개 이상인지 확인
        if len(places_by_seq) < target_count:
            return False
        
        return all(len(p_list) >= 2 for p_list in places_by_seq.values())

    def _expand_search_radius(self, location_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """기존 분석 결과의 검색 반경을 1.5배 확대"""
        expanded_analysis = location_analysis.copy()
        for cluster in expanded_analysis['clusters']:
            cluster.search_radius = int(cluster.search_radius * self.radius_expansion_factor)
        logger.info(f"반경 확대: {location_analysis['clusters'][0].search_radius}m -> {expanded_analysis['clusters'][0].search_radius}m")
        return expanded_analysis

    # --- Helper Functions ---
    def _get_target_info(self, target: Any, key: str) -> Any:
        if hasattr(target, key):
            return getattr(target, key)
        return target.get(key)

    def _is_target_in_cluster(self, target: Any, cluster: Any) -> bool:
        target_seq = self._get_target_info(target, 'sequence')
        for cluster_target in cluster.targets:
            if self._get_target_info(cluster_target, 'sequence') == target_seq:
                return True
        return False

# 하위 호환성을 위한 별칭
VectorSearchEngine = SmartVectorSearchEngine
