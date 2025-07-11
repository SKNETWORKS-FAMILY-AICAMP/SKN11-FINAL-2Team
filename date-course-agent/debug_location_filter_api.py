#!/usr/bin/env python3
"""
위도경도 필터링 버그 긴급 분석 스크립트 (API 호출 버전)
"1,2번은 이촌동, 3번은 이태원" 시나리오 재현
"""

import requests
import json
import math
from typing import Dict, Any, List

class LocationFilterDebugger:
    """위도경도 필터링 버그 디버깅 클래스 (API 호출 버전)"""
    
    def __init__(self):
        self.base_url = "http://localhost:8003"
        
        # 실제 이촌동, 이태원 좌표 (Google Maps 기준)
        self.locations = {
            "이촌동": {"latitude": 37.5227, "longitude": 126.9755},
            "이태원": {"latitude": 37.5344, "longitude": 126.9943}
        }
        
        # 두 지역 간 거리 계산
        distance = self._calculate_distance(
            self.locations["이촌동"]["latitude"], self.locations["이촌동"]["longitude"],
            self.locations["이태원"]["latitude"], self.locations["이태원"]["longitude"]
        )
        
        print(f"🗺️ 이촌동 ↔ 이태원 거리: {distance:.0f}m ({distance/1000:.1f}km)")
    
    def debug_location_filtering(self):
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
        
        # 2. API 호출 및 결과 분석
        print(f"\n🤖 API 호출 및 결과 분석:")
        try:
            response = requests.post(
                f"{self.base_url}/recommend-course",
                json=test_request,
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                self._analyze_api_result(result)
                
                # 결과를 JSON 파일로 저장
                with open('/Users/hwangjunho/Desktop/아카이브/agents/date-course-agent/debug_result.json', 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                
                print(f"\n💾 결과가 debug_result.json에 저장되었습니다.")
                return result
            else:
                print(f"❌ API 호출 실패: HTTP {response.status_code}")
                print(f"   응답: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ API 호출 예외: {e}")
            return None
    
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
    
    def _analyze_api_result(self, result: Dict[str, Any]):
        """API 결과 분석"""
        print(f"   처리 시간: {result.get('processing_time', 'Unknown')}")
        print(f"   상태: {result.get('status', 'Unknown')}")
        
        # 제약 조건 분석
        constraints = result.get('constraints_applied', {})
        print(f"\n🔧 적용된 제약 조건:")
        
        sunny_constraints = constraints.get('sunny_weather', {})
        rainy_constraints = constraints.get('rainy_weather', {})
        
        print(f"   맑은 날:")
        print(f"     시도: {sunny_constraints.get('attempt', 'Unknown')}")
        print(f"     반경: {sunny_constraints.get('radius_used', 'Unknown')}m")
        
        print(f"   비오는 날:")
        print(f"     시도: {rainy_constraints.get('attempt', 'Unknown')}")
        print(f"     반경: {rainy_constraints.get('radius_used', 'Unknown')}m")
        
        results_data = result.get('results', {})
        
        # 맑은 날 결과 분석
        print(f"\n🌞 맑은 날 결과 분석:")
        sunny_courses = results_data.get('sunny_weather', [])
        self._analyze_courses(sunny_courses, "맑은 날")
        
        # 비오는 날 결과 분석
        print(f"\n🌧️ 비오는 날 결과 분석:")
        rainy_courses = results_data.get('rainy_weather', [])
        self._analyze_courses(rainy_courses, "비오는 날")
        
        # 지역별 분포 분석
        print(f"\n🏢 지역별 분포 분석:")
        self._analyze_regional_distribution(sunny_courses, rainy_courses)
    
    def _analyze_courses(self, courses: List[Dict[str, Any]], weather_type: str):
        """코스 분석"""
        print(f"   {weather_type} 코스 수: {len(courses)}개")
        
        for i, course in enumerate(courses, 1):
            places = course.get('places', [])
            print(f"\n   코스 {i} ({len(places)}개 장소):")
            
            for j, place in enumerate(places, 1):
                place_info = place.get('place_info', {})
                name = place_info.get('name', 'Unknown')
                category = place_info.get('category', 'Unknown')
                coords = place_info.get('coordinates', {})
                similarity = place_info.get('similarity_score', 0)
                
                if coords.get('latitude') and coords.get('longitude'):
                    lat, lon = coords['latitude'], coords['longitude']
                    
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
                    
                    print(f"     {j}. {name} ({category})")
                    print(f"        위치: {region} ({distance:.0f}m)")
                    print(f"        좌표: ({lat:.4f}, {lon:.4f})")
                    print(f"        유사도: {similarity:.3f}")
                else:
                    print(f"     {j}. {name} ({category}) - 좌표 없음")
    
    def _analyze_regional_distribution(self, sunny_courses: List[Dict[str, Any]], rainy_courses: List[Dict[str, Any]]):
        """지역별 분포 분석"""
        
        def count_places_by_region(courses):
            ichon_count = 0
            itaewon_count = 0
            no_coords_count = 0
            
            for course in courses:
                for place in course.get('places', []):
                    place_info = place.get('place_info', {})
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
                        
                        if distance_to_ichon < distance_to_itaewon:
                            ichon_count += 1
                        else:
                            itaewon_count += 1
                    else:
                        no_coords_count += 1
            
            return ichon_count, itaewon_count, no_coords_count
        
        sunny_ichon, sunny_itaewon, sunny_no_coords = count_places_by_region(sunny_courses)
        rainy_ichon, rainy_itaewon, rainy_no_coords = count_places_by_region(rainy_courses)
        
        print(f"   맑은 날 지역 분포:")
        print(f"     이촌동: {sunny_ichon}개")
        print(f"     이태원: {sunny_itaewon}개")
        print(f"     좌표 없음: {sunny_no_coords}개")
        
        print(f"\n   비오는 날 지역 분포:")
        print(f"     이촌동: {rainy_ichon}개")
        print(f"     이태원: {rainy_itaewon}개")
        print(f"     좌표 없음: {rainy_no_coords}개")
        
        # 문제 진단
        print(f"\n🔍 문제 진단:")
        
        # 요청: 1,2번은 이촌동, 3번은 이태원
        # 예상: 이촌동 2개, 이태원 1개 (최소)
        
        total_ichon = sunny_ichon + rainy_ichon
        total_itaewon = sunny_itaewon + rainy_itaewon
        
        if total_itaewon > total_ichon:
            print(f"   ❌ 문제 발견: 이태원 장소가 너무 많음 (이촌동 {total_ichon}개 vs 이태원 {total_itaewon}개)")
            print(f"   예상: 이촌동이 더 많아야 함 (1,2번이 이촌동 요청)")
        else:
            print(f"   ✅ 지역 분포 양호: 이촌동 {total_ichon}개, 이태원 {total_itaewon}개")
        
        if total_ichon == 0:
            print(f"   ❌ 심각한 문제: 이촌동 장소가 전혀 없음 (1,2번 요청 무시됨)")
        
        if total_itaewon == 0:
            print(f"   ❌ 심각한 문제: 이태원 장소가 전혀 없음 (3번 요청 무시됨)")
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """두 좌표 간 거리 계산 (미터)"""
        R = 6371000  # 지구 반지름 (미터)
        lat1_rad, lon1_rad, lat2_rad, lon2_rad = map(math.radians, [lat1, lon1, lat2, lon2])
        dlat, dlon = lat2_rad - lat1_rad, lon2_rad - lon1_rad
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c

def main():
    """메인 실행 함수"""
    debugger = LocationFilterDebugger()
    result = debugger.debug_location_filtering()
    
    if result:
        print(f"\n🎯 분석 완료!")
    else:
        print(f"\n❌ 분석 실패!")

if __name__ == "__main__":
    main()