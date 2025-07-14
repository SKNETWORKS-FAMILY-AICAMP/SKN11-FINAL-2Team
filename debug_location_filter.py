#!/usr/bin/env python3
"""
위도경도 필터링 버그 긴급 분석 스크립트
"1,2번은 이촌동, 3번은 이태원" 시나리오 재현
"""

import json
import sys
import os
import asyncio
from typing import Dict, Any, List

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '.'))

from src.main import DateCourseAgent
from src.utils.location_analyzer import location_analyzer
from src.database.qdrant_client import get_qdrant_client

class LocationFilterDebugger:
    """위도경도 필터링 버그 디버깅 클래스"""
    
    def __init__(self):
        self.agent = DateCourseAgent()
        self.location_analyzer = location_analyzer
        self.qdrant_client = get_qdrant_client()
        
        # 실제 이촌동, 이태원 좌표 (Google Maps 기준)
        self.locations = {
            "이촌동": {"latitude": 37.5227, "longitude": 126.9755},
            "이태원": {"latitude": 37.5344, "longitude": 126.9943}
        }
    
    async def debug_location_filtering(self):
        """위도경도 필터링 버그 디버깅"""
        print("🔍 위도경도 필터링 버그 긴급 분석 시작")
        print("=" * 80)
        
        # 1. 문제 상황 재현을 위한 테스트 데이터 생성
        test_request = self._create_test_request()
        
        print("\n📋 테스트 요청 데이터:")
        print(f"   1번 (음식점): {test_request['search_targets'][0]['location']['area_name']} - "
              f"({test_request['search_targets'][0]['location']['coordinates']['latitude']}, "
              f"{test_request['search_targets'][0]['location']['coordinates']['longitude']})")
        print(f"   2번 (카페): {test_request['search_targets'][1]['location']['area_name']} - "
              f"({test_request['search_targets'][1]['location']['coordinates']['latitude']}, "
              f"{test_request['search_targets'][1]['location']['coordinates']['longitude']})")
        print(f"   3번 (문화시설): {test_request['search_targets'][2]['location']['area_name']} - "
              f"({test_request['search_targets'][2]['location']['coordinates']['latitude']}, "
              f"{test_request['search_targets'][2]['location']['coordinates']['longitude']})")
        
        # 2. Location Analyzer 분석 결과 확인
        print(f"\n🗺️ Location Analyzer 분석 결과:")
        search_targets = test_request['search_targets']
        location_analysis = self.location_analyzer.analyze_search_targets(search_targets, "sunny")
        
        print(f"   분석 타입: {location_analysis['analysis_type']}")
        print(f"   클러스터 개수: {len(location_analysis['clusters'])}")
        print(f"   분석 요약: {location_analysis['analysis_summary']}")
        
        for i, cluster in enumerate(location_analysis['clusters']):
            print(f"\n   클러스터 {i+1}:")
            print(f"     중심 좌표: ({cluster.center_lat:.4f}, {cluster.center_lon:.4f})")
            print(f"     검색 반경: {cluster.search_radius}m")
            print(f"     포함 타겟 수: {len(cluster.targets)}")
            
            for target in cluster.targets:
                area_name = target['location']['area_name']
                coords = target['location']['coordinates']
                print(f"       - {target['sequence']}번 ({target['category']}): {area_name} "
                      f"({coords['latitude']}, {coords['longitude']})")
        
        # 3. 각 클러스터별 벡터 검색 시뮬레이션
        print(f"\n🔍 벡터 검색 시뮬레이션:")
        await self._simulate_vector_search(location_analysis)
        
        # 4. 실제 에이전트 처리 결과 확인
        print(f"\n🤖 실제 에이전트 처리 결과:")
        result = await self.agent.process_request(test_request)
        
        self._analyze_agent_result(result)
        
        # 5. 벡터 DB에서 각 지역별 실제 장소 수 확인
        print(f"\n📊 벡터 DB 내 지역별 장소 분포:")
        await self._check_db_place_distribution()
        
        print(f"\n🎯 분석 완료!")
        return result
    
    def _create_test_request(self) -> Dict[str, Any]:
        """문제 상황을 재현하기 위한 테스트 요청 생성"""
        return {
            "request_id": "location-filter-debug-001",
            "timestamp": "2025-07-07T16:30:00Z",
            "search_targets": [
                {
                    "sequence": 1,
                    "category": "음식점",
                    "location": {
                        "area_name": "이촌동",
                        "coordinates": self.locations["이촌동"]
                    },
                    "semantic_query": "이촌동에서 커플이 가기 좋은 로맨틱한 레스토랑. 점심 또는 저녁 시간에 분위기가 좋고 데이트하기 적절한 곳."
                },
                {
                    "sequence": 2,
                    "category": "카페",
                    "location": {
                        "area_name": "이촌동",
                        "coordinates": self.locations["이촌동"]
                    },
                    "semantic_query": "이촌동에서 디저트와 커피를 즐길 수 있는 아늑한 카페. 커플이 대화하기 좋은 조용한 분위기."
                },
                {
                    "sequence": 3,
                    "category": "문화시설",
                    "location": {
                        "area_name": "이태원",
                        "coordinates": self.locations["이태원"]
                    },
                    "semantic_query": "이태원에서 커플이 함께 즐길 수 있는 박물관이나 전시관. 문화적 체험을 할 수 있는 곳."
                }
            ],
            "user_context": {
                "demographics": {
                    "age": 26,
                    "mbti": "ENFP",
                    "relationship_stage": "연인"
                },
                "preferences": ["로맨틱한 분위기", "문화적 체험", "저녁 데이트"],
                "requirements": {
                    "budget_range": "커플 기준 15-20만원",
                    "time_preference": "저녁",
                    "party_size": 2,
                    "transportation": "대중교통"
                }
            },
            "course_planning": {
                "optimization_goals": ["로맨틱한 저녁 데이트 경험 극대화", "문화적 체험과 맛있는 음식 조화"],
                "route_constraints": {
                    "max_travel_time_between": 30,
                    "total_course_duration": 300,
                    "flexibility": "medium"
                },
                "sequence_optimization": {
                    "allow_reordering": True,
                    "prioritize_given_sequence": False
                }
            }
        }
    
    async def _simulate_vector_search(self, location_analysis: Dict[str, Any]):
        """각 클러스터별 벡터 검색 시뮬레이션"""
        from src.core.embedding_service import EmbeddingService
        from src.database.vector_search import SmartVectorSearchEngine
        
        embedding_service = EmbeddingService()
        vector_search = SmartVectorSearchEngine()
        
        # 임베딩 생성 (실제 semantic_query 사용)
        search_targets = []
        for cluster in location_analysis['clusters']:
            search_targets.extend(cluster.targets)
        
        semantic_queries = [target['semantic_query'] for target in search_targets]
        embeddings = await embedding_service.create_semantic_embeddings(semantic_queries)
        
        # 검색 수행
        search_result = await vector_search.search_with_retry_logic(
            search_targets=search_targets,
            embeddings=embeddings,
            location_analysis=location_analysis
        )
        
        print(f"   검색 결과: {len(search_result.places)}개 장소")
        print(f"   검색 시도: {search_result.attempt}")
        print(f"   사용된 반경: {search_result.radius_used}m")
        
        # 검색 결과를 지역별로 분류
        places_by_region = {}
        for place in search_result.places:
            lat, lon = place['latitude'], place['longitude']
            
            # 이촌동과 이태원 중 어느 지역에 가까운지 계산
            distance_to_ichon = self._calculate_distance(
                lat, lon, 
                self.locations["이촌동"]["latitude"], 
                self.locations["이촌동"]["longitude"]
            )
            distance_to_itaewon = self._calculate_distance(
                lat, lon,
                self.locations["이태원"]["latitude"],
                self.locations["이태원"]["longitude"]
            )
            
            if distance_to_ichon < distance_to_itaewon:
                region = "이촌동"
                distance = distance_to_ichon
            else:
                region = "이태원"
                distance = distance_to_itaewon
            
            if region not in places_by_region:
                places_by_region[region] = []
            
            places_by_region[region].append({
                'name': place['place_name'],
                'category': place['category'],
                'sequence': place.get('search_sequence', 'Unknown'),
                'distance': distance,
                'coordinates': (lat, lon)
            })
        
        print(f"\n   🏢 지역별 검색 결과:")
        for region, places in places_by_region.items():
            print(f"     {region}: {len(places)}개 장소")
            for place in places[:3]:  # 상위 3개만 표시
                print(f"       - {place['name']} ({place['category']}) "
                      f"[{place['sequence']}번 대상, {place['distance']:.0f}m]")
    
    def _analyze_agent_result(self, result: Dict[str, Any]):
        """에이전트 처리 결과 분석"""
        print(f"   처리 시간: {result.get('processing_time', 'Unknown')}")
        print(f"   상태: {result.get('status', 'Unknown')}")
        
        results_data = result.get('results', {})
        
        # 맑은 날 결과 분석
        sunny_courses = results_data.get('sunny_weather', [])
        print(f"\n   🌞 맑은 날 코스 ({len(sunny_courses)}개):")
        
        for i, course in enumerate(sunny_courses, 1):
            places = course.get('places', [])
            print(f"     코스 {i}: {len(places)}개 장소")
            
            for place in places:
                place_info = place.get('place_info', {})
                name = place_info.get('name', 'Unknown')
                coords = place_info.get('coordinates', {})
                
                if coords.get('latitude') and coords.get('longitude'):
                    # 이 장소가 어느 지역에 속하는지 확인
                    lat, lon = coords['latitude'], coords['longitude']
                    distance_to_ichon = self._calculate_distance(
                        lat, lon,
                        self.locations["이촌동"]["latitude"],
                        self.locations["이촌동"]["longitude"]
                    )
                    distance_to_itaewon = self._calculate_distance(
                        lat, lon,
                        self.locations["이태원"]["latitude"],
                        self.locations["이태원"]["longitude"]
                    )
                    
                    region = "이촌동" if distance_to_ichon < distance_to_itaewon else "이태원"
                    distance = min(distance_to_ichon, distance_to_itaewon)
                    
                    print(f"       - {name} → {region} ({distance:.0f}m)")
                else:
                    print(f"       - {name} → 좌표 정보 없음")
        
        # 비오는 날 결과도 동일하게 분석
        rainy_courses = results_data.get('rainy_weather', [])
        print(f"\n   🌧️ 비오는 날 코스 ({len(rainy_courses)}개):")
        
        for i, course in enumerate(rainy_courses, 1):
            places = course.get('places', [])
            print(f"     코스 {i}: {len(places)}개 장소")
            
            for place in places:
                place_info = place.get('place_info', {})
                name = place_info.get('name', 'Unknown')
                coords = place_info.get('coordinates', {})
                
                if coords.get('latitude') and coords.get('longitude'):
                    lat, lon = coords['latitude'], coords['longitude']
                    distance_to_ichon = self._calculate_distance(
                        lat, lon,
                        self.locations["이촌동"]["latitude"],
                        self.locations["이촌동"]["longitude"]
                    )
                    distance_to_itaewon = self._calculate_distance(
                        lat, lon,
                        self.locations["이태원"]["latitude"],
                        self.locations["이태원"]["longitude"]
                    )
                    
                    region = "이촌동" if distance_to_ichon < distance_to_itaewon else "이태원"
                    distance = min(distance_to_ichon, distance_to_itaewon)
                    
                    print(f"       - {name} → {region} ({distance:.0f}m)")
                else:
                    print(f"       - {name} → 좌표 정보 없음")
    
    async def _check_db_place_distribution(self):
        """벡터 DB에서 각 지역별 장소 분포 확인"""
        try:
            # 이촌동 주변 장소 수 확인
            ichon_places = await self.qdrant_client.search_with_geo_filter(
                query_vector=[0.0] * 3072,  # 더미 벡터
                center_lat=self.locations["이촌동"]["latitude"],
                center_lon=self.locations["이촌동"]["longitude"],
                radius_meters=2000,
                category="음식점",
                limit=100
            )
            
            # 이태원 주변 장소 수 확인
            itaewon_places = await self.qdrant_client.search_with_geo_filter(
                query_vector=[0.0] * 3072,  # 더미 벡터
                center_lat=self.locations["이태원"]["latitude"],
                center_lon=self.locations["이태원"]["longitude"],
                radius_meters=2000,
                category="문화시설",
                limit=100
            )
            
            print(f"   이촌동 주변 음식점: {len(ichon_places)}개")
            print(f"   이태원 주변 문화시설: {len(itaewon_places)}개")
            
            # 실제 장소 이름 몇 개 출력
            if ichon_places:
                print(f"   이촌동 음식점 예시:")
                for place in ichon_places[:5]:
                    print(f"     - {place['place_name']}")
            
            if itaewon_places:
                print(f"   이태원 문화시설 예시:")
                for place in itaewon_places[:5]:
                    print(f"     - {place['place_name']}")
        
        except Exception as e:
            print(f"   ❌ DB 분포 확인 실패: {e}")
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """두 좌표 간 거리 계산 (미터)"""
        import math
        R = 6371000  # 지구 반지름 (미터)
        lat1_rad, lon1_rad, lat2_rad, lon2_rad = map(math.radians, [lat1, lon1, lat2, lon2])
        dlat, dlon = lat2_rad - lat1_rad, lon2_rad - lon1_rad
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c

async def main():
    """메인 실행 함수"""
    debugger = LocationFilterDebugger()
    result = await debugger.debug_location_filtering()
    
    # 결과를 JSON 파일로 저장
    with open('/Users/hwangjunho/Desktop/아카이브/agents/date-course-agent/debug_result.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 결과가 debug_result.json에 저장되었습니다.")

if __name__ == "__main__":
    asyncio.run(main())