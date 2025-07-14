#!/usr/bin/env python3
"""
용산 데이트 코스 종합 테스트
- 카테고리 1개~5개까지 다양한 조합
- 용산 내 동일 장소 ~ 먼 장소 고루 섞어서 테스트
- 전체 시스템 기능 검증
"""

import requests
import json
import time
from typing import List, Dict, Any

class YongsanComprehensiveTest:
    """용산 종합 테스트 클래스"""
    
    def __init__(self):
        self.base_url = "http://localhost:8000"
        
        # 용산 내 다양한 위치 정의 (실제 용산 지역별 좌표)
        self.yongsan_locations = {
            "용산역": {"latitude": 37.5326, "longitude": 126.9904},
            "용산전자상가": {"latitude": 37.5326, "longitude": 126.9904},
            "해방촌": {"latitude": 37.5460, "longitude": 126.9851},
            "이태원": {"latitude": 37.5344, "longitude": 126.9943},
            "한강진역": {"latitude": 37.5314, "longitude": 126.9775},
            "국립중앙박물관": {"latitude": 37.5238, "longitude": 126.9818},
            "용산공원": {"latitude": 37.5302, "longitude": 126.9829},
            "남산": {"latitude": 37.5507, "longitude": 126.9882},
            "한남동": {"latitude": 37.5341, "longitude": 126.9999}
        }
        
        self.categories = ["음식점", "카페", "문화시설", "휴식시설", "야외활동"]
        
        # 테스트 케이스별 사용자 프로필
        self.user_profiles = {
            "커플": {
                "age": 26,
                "mbti": "ENFP", 
                "relationship_stage": "연인",
                "preferences": ["로맨틱한 분위기", "특별한 경험"],
                "budget": "커플 기준 10-15만원"
            },
            "썸": {
                "age": 24,
                "mbti": "ISFP",
                "relationship_stage": "썸타는 사이", 
                "preferences": ["캐주얼한 분위기", "대화하기 좋은 공간"],
                "budget": "커플 기준 8-12만원"
            }
        }
    
    def run_all_tests(self):
        """모든 테스트 실행"""
        print("🚀 용산 종합 테스트 시작!")
        print("=" * 80)
        
        test_results = []
        
        # 1. 카테고리별 테스트 (1개~5개)
        for i in range(1, 6):
            print(f"\n📂 {i}개 카테고리 테스트")
            print("-" * 40)
            
            result = self._test_category_count(i)
            test_results.append(result)
            
            time.sleep(2)  # 서버 부하 방지
        
        # 2. 거리 다양성 테스트 
        print(f"\n📏 거리 다양성 테스트")
        print("-" * 40)
        
        distance_result = self._test_distance_variety()
        test_results.append(distance_result)
        
        # 3. 사용자 프로필별 테스트
        print(f"\n👥 사용자 프로필별 테스트")
        print("-" * 40)
        
        for profile_name in self.user_profiles.keys():
            profile_result = self._test_user_profile(profile_name)
            test_results.append(profile_result)
            time.sleep(2)
        
        # 4. 전체 결과 요약
        self._print_summary(test_results)
    
    def _test_category_count(self, category_count: int) -> Dict[str, Any]:
        """카테고리 개수별 테스트"""
        print(f"  🔢 {category_count}개 카테고리 조합 테스트")
        
        # 카테고리 선택 (순서대로)
        selected_categories = self.categories[:category_count]
        
        # 위치 다양화 (근거리 + 원거리 섞어서)
        locations = self._get_varied_locations(category_count)
        
        # 요청 데이터 생성
        request_data = self._create_request_data(
            f"category-{category_count}-test",
            selected_categories,
            locations,
            "커플"
        )
        
        # API 호출 및 결과 분석
        start_time = time.time()
        response = self._call_api(request_data)
        elapsed_time = time.time() - start_time
        
        result = self._analyze_response(
            response, 
            f"{category_count}개 카테고리",
            elapsed_time
        )
        
        return result
    
    def _test_distance_variety(self) -> Dict[str, Any]:
        """거리 다양성 테스트 - 의도적으로 멀리 떨어진 장소들"""
        print("  📍 극단적 거리 차이 테스트")
        
        # 용산 내에서 최대한 멀리 떨어진 3곳
        extreme_locations = [
            ("용산역", self.yongsan_locations["용산역"]),      # 남쪽
            ("남산", self.yongsan_locations["남산"]),          # 북쪽  
            ("한남동", self.yongsan_locations["한남동"])       # 동쪽
        ]
        
        request_data = self._create_request_data(
            "distance-variety-test",
            ["음식점", "카페", "문화시설"],
            [loc[1] for loc in extreme_locations],
            "썸",
            area_names=[loc[0] for loc in extreme_locations]
        )
        
        start_time = time.time()
        response = self._call_api(request_data)
        elapsed_time = time.time() - start_time
        
        result = self._analyze_response(
            response,
            "거리 다양성 (극단)",
            elapsed_time
        )
        
        return result
    
    def _test_user_profile(self, profile_name: str) -> Dict[str, Any]:
        """사용자 프로필별 테스트"""
        print(f"  👤 {profile_name} 프로필 테스트")
        
        # 3개 카테고리로 고정, 위치는 중간 정도 거리
        locations = [
            self.yongsan_locations["용산역"],
            self.yongsan_locations["해방촌"], 
            self.yongsan_locations["이태원"]
        ]
        
        request_data = self._create_request_data(
            f"profile-{profile_name}-test",
            ["음식점", "카페", "문화시설"],
            locations,
            profile_name
        )
        
        start_time = time.time()
        response = self._call_api(request_data)
        elapsed_time = time.time() - start_time
        
        result = self._analyze_response(
            response,
            f"{profile_name} 프로필",
            elapsed_time
        )
        
        return result
    
    def _get_varied_locations(self, count: int) -> List[Dict[str, float]]:
        """다양한 거리의 위치들 선택"""
        location_list = list(self.yongsan_locations.values())
        
        if count == 1:
            return [location_list[0]]  # 용산역
        elif count == 2:
            # 가까운 곳 2개
            return [location_list[0], location_list[1]]  # 용산역, 용산전자상가
        elif count == 3:
            # 가까운 곳 + 중간 + 먼 곳
            return [
                self.yongsan_locations["용산역"],     # 기준점
                self.yongsan_locations["이태원"],     # 중간 거리
                self.yongsan_locations["해방촌"]      # 좀 더 먼 거리
            ]
        elif count == 4:
            # 다양한 거리 조합
            return [
                self.yongsan_locations["용산역"],
                self.yongsan_locations["한강진역"],   # 서쪽
                self.yongsan_locations["해방촌"],     # 북서쪽
                self.yongsan_locations["국립중앙박물관"] # 남서쪽
            ]
        else:  # count == 5
            # 용산 전 지역 커버
            return [
                self.yongsan_locations["용산역"],
                self.yongsan_locations["이태원"], 
                self.yongsan_locations["해방촌"],
                self.yongsan_locations["남산"],
                self.yongsan_locations["한남동"]
            ]
    
    def _create_request_data(
        self, 
        test_id: str,
        categories: List[str],
        locations: List[Dict[str, float]], 
        user_profile: str,
        area_names: List[str] = None
    ) -> Dict[str, Any]:
        """요청 데이터 생성"""
        
        profile = self.user_profiles[user_profile]
        
        if area_names is None:
            area_names = ["용산"] * len(categories)
        
        # semantic_query 템플릿
        semantic_templates = {
            "음식점": f"용산에서 {profile['relationship_stage']}이 가기 좋은 맛있는 레스토랑. {profile['preferences'][0]}를 선호하며 {profile['budget']} 예산.",
            "카페": f"용산에서 커피와 디저트를 즐길 수 있는 아늑한 카페. {profile['preferences'][0]} 분위기에서 대화하기 좋은 곳.",
            "문화시설": f"용산에서 {profile['relationship_stage']}이 함께 즐길 수 있는 박물관이나 전시관. 교육적이면서도 데이트 코스로 적절한 장소.",
            "휴식시설": f"용산에서 편안하게 쉴 수 있는 공간. {profile['preferences'][0]} 분위기에서 여유롭게 시간을 보낼 수 있는 곳.",
            "야외활동": f"용산에서 {profile['relationship_stage']}이 함께 즐길 수 있는 야외 활동 공간. 자연스럽고 활동적인 데이트를 위한 장소."
        }
        
        search_targets = []
        for i, (category, location, area_name) in enumerate(zip(categories, locations, area_names)):
            search_targets.append({
                "sequence": i + 1,
                "category": category,
                "location": {
                    "area_name": area_name,
                    "coordinates": location
                },
                "semantic_query": semantic_templates[category]
            })
        
        return {
            "request_id": test_id,
            "timestamp": "2025-07-01T16:30:00Z",
            "search_targets": search_targets,
            "user_context": {
                "demographics": {
                    "age": profile["age"],
                    "mbti": profile["mbti"],
                    "relationship_stage": profile["relationship_stage"]
                },
                "preferences": profile["preferences"],
                "requirements": {
                    "budget_range": profile["budget"],
                    "time_preference": "오후",
                    "party_size": 2,
                    "transportation": "지하철"
                }
            },
            "course_planning": {
                "optimization_goals": ["동선 최적화", "각 장소별 충분한 시간 확보", f"{profile['preferences'][0]} 극대화"],
                "route_constraints": {
                    "max_travel_time_between": 25,
                    "total_course_duration": 240,
                    "flexibility": "medium"
                },
                "sequence_optimization": {
                    "allow_reordering": True,
                    "prioritize_given_sequence": False
                }
            }
        }
    
    def _call_api(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """API 호출"""
        try:
            response = requests.post(
                f"{self.base_url}/recommend-course",
                json=request_data,
                timeout=60
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "error": f"HTTP {response.status_code}",
                    "message": response.text
                }
                
        except Exception as e:
            return {
                "error": "Connection Error",
                "message": str(e)
            }
    
    def _analyze_response(
        self, 
        response: Dict[str, Any], 
        test_name: str,
        elapsed_time: float
    ) -> Dict[str, Any]:
        """응답 분석 및 상세 결과 출력"""
        
        result = {
            "test_name": test_name,
            "elapsed_time": elapsed_time,
            "success": False,
            "status": "unknown",
            "issues": [],
            "good_points": [],
            "course_count": {"sunny": 0, "rainy": 0},
            "distance_range": {"min": 0, "max": 0},
            "unique_places": {"sunny": 0, "rainy": 0}
        }
        
        if "error" in response:
            result["issues"].append(f"API 오류: {response['error']}")
            print(f"    ❌ {test_name}: {response['error']}")
            return result
        
        result["success"] = True
        result["status"] = response.get("status", "unknown")
        
        # 기본 정보 출력
        print(f"\n    🎯 {test_name} 결과")
        print(f"    {'='*50}")
        print(f"    ⏱️ 처리시간: {elapsed_time:.1f}초")
        print(f"    📈 상태: {result['status']}")
        
        # 상태 분석
        if result["status"] == "success":
            result["good_points"].append("✅ 성공적으로 완료")
        elif result["status"] == "partial_success":
            result["issues"].append("⚠️ 일부 날씨 조건에서만 성공")
        else:
            result["issues"].append("❌ 완전 실패")
            return result
        
        # 제약 조건 적용 정보
        constraints = response.get("constraints_applied", {})
        print(f"\n    🔧 적용된 제약 조건:")
        sunny_attempt = constraints.get("sunny_weather", {}).get("attempt", "1차")
        rainy_attempt = constraints.get("rainy_weather", {}).get("attempt", "1차")
        sunny_radius = constraints.get("sunny_weather", {}).get("radius_used", "2000")
        rainy_radius = constraints.get("rainy_weather", {}).get("radius_used", "2000")
        
        print(f"       🌞 맑은 날: {sunny_attempt} 시도, 반경 {sunny_radius}m")
        print(f"       🌧️ 비오는 날: {rainy_attempt} 시도, 반경 {rainy_radius}m")
        
        # 코스 개수 분석
        results_data = response.get("results", {})
        
        sunny_courses = results_data.get("sunny_weather", [])
        rainy_courses = results_data.get("rainy_weather", [])
        
        result["course_count"]["sunny"] = len(sunny_courses)
        result["course_count"]["rainy"] = len(rainy_courses)
        
        print(f"\n    📊 생성된 코스 수:")
        print(f"       🌞 맑은 날: {len(sunny_courses)}개")
        print(f"       🌧️ 비오는 날: {len(rainy_courses)}개")
        
        # 상세 코스 정보 출력
        self._display_detailed_courses("☀️ 맑은 날 코스", sunny_courses)
        self._display_detailed_courses("🌧️ 비오는 날 코스", rainy_courses)
        
        if len(sunny_courses) == 3:
            result["good_points"].append("✅ 맑은 날 3개 코스 생성")
        else:
            result["issues"].append(f"⚠️ 맑은 날 코스 {len(sunny_courses)}개 (3개 기대)")
        
        if len(rainy_courses) == 3:
            result["good_points"].append("✅ 비오는 날 3개 코스 생성")
        else:
            result["issues"].append(f"⚠️ 비오는 날 코스 {len(rainy_courses)}개 (3개 기대)")
        
        # 거리 분석
        distances = []
        for courses in [sunny_courses, rainy_courses]:
            for course in courses:
                distance = course.get("total_distance_meters", 0)
                if distance > 0:
                    distances.append(distance)
        
        if distances:
            result["distance_range"]["min"] = min(distances)
            result["distance_range"]["max"] = max(distances)
            
            if max(distances) <= 5000:  # 5km 이하
                result["good_points"].append(f"✅ 적절한 이동 거리 (최대 {max(distances):.0f}m)")
            else:
                result["issues"].append(f"⚠️ 과도한 이동 거리 (최대 {max(distances):.0f}m)")
        
        # 장소 다양성 분석
        for weather, courses in [("sunny", sunny_courses), ("rainy", rainy_courses)]:
            unique_places = set()
            for course in courses:
                for place in course.get("places", []):
                    place_name = place.get("place_info", {}).get("name", "")
                    if place_name:
                        unique_places.add(place_name)
            
            result["unique_places"][weather] = len(unique_places)
            
            expected_unique = len(courses) * 2  # 최소한 코스 수의 2배는 되어야
            if len(unique_places) >= expected_unique:
                result["good_points"].append(f"✅ {weather} 날씨 장소 다양성 양호 ({len(unique_places)}개)")
            else:
                result["issues"].append(f"⚠️ {weather} 날씨 장소 중복 많음 ({len(unique_places)}개)")
        
        # 추천 이유 분석
        has_recommendations = False
        for courses in [sunny_courses, rainy_courses]:
            for course in courses:
                reason = course.get("recommendation_reason", "")
                if reason and len(reason) > 10:
                    has_recommendations = True
                    break
            if has_recommendations:
                break
        
        if has_recommendations:
            result["good_points"].append("✅ 추천 이유 생성됨")
        else:
            result["issues"].append("❌ 추천 이유 누락")
        
        # 좌표 정보 분석
        has_coordinates = True
        for courses in [sunny_courses, rainy_courses]:
            for course in courses:
                for place in course.get("places", []):
                    coords = place.get("place_info", {}).get("coordinates", {})
                    if not coords.get("latitude") or not coords.get("longitude"):
                        has_coordinates = False
                        break
                if not has_coordinates:
                    break
            if not has_coordinates:
                break
        
        if has_coordinates:
            result["good_points"].append("✅ 좌표 정보 완전")
        else:
            result["issues"].append("❌ 좌표 정보 누락")
        
        return result
    
    def _print_summary(self, test_results: List[Dict[str, Any]]):
        """전체 테스트 결과 요약"""
        print("\n" + "=" * 80)
        print("🏁 용산 종합 테스트 결과 요약")
        print("=" * 80)
        
        total_tests = len(test_results)
        successful_tests = sum(1 for r in test_results if r["success"])
        
        print(f"\n📈 전체 통계:")
        print(f"   총 테스트: {total_tests}개")
        print(f"   성공: {successful_tests}개")
        print(f"   실패: {total_tests - successful_tests}개")
        print(f"   성공률: {(successful_tests/total_tests*100):.1f}%")
        
        # 평균 처리 시간
        avg_time = sum(r["elapsed_time"] for r in test_results if r["success"]) / max(successful_tests, 1)
        print(f"   평균 처리시간: {avg_time:.1f}초")
        
        # 공통 이슈들
        all_issues = []
        all_good_points = []
        
        for result in test_results:
            all_issues.extend(result["issues"])
            all_good_points.extend(result["good_points"])
        
        # 이슈 빈도 분석
        issue_counts = {}
        for issue in all_issues:
            issue_counts[issue] = issue_counts.get(issue, 0) + 1
        
        good_counts = {}
        for good in all_good_points:
            good_counts[good] = good_counts.get(good, 0) + 1
        
        if issue_counts:
            print(f"\n❗ 주요 이슈들:")
            for issue, count in sorted(issue_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"   {issue} ({count}회)")
        
        if good_counts:
            print(f"\n✅ 잘 작동하는 기능들:")
            for good, count in sorted(good_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"   {good} ({count}회)")
        
        print(f"\n💡 시스템 상태:")
        if successful_tests >= total_tests * 0.8:
            print("   🟢 전체적으로 잘 작동하고 있습니다!")
        elif successful_tests >= total_tests * 0.5:
            print("   🟡 일부 개선이 필요합니다.")
        else:
            print("   🔴 시스템에 문제가 있을 수 있습니다.")
        
        print("\n🎯 테스트 완료!")

    def _display_detailed_courses(self, title: str, courses: List[Dict[str, Any]]):
        """코스 상세 정보 출력 (프론트엔드 스타일)"""
        if not courses:
            print(f"\n    {title}: 생성된 코스 없음")
            return
        
        print(f"\n    {title}:")
        print(f"    {'-'*50}")
        
        for i, course in enumerate(courses, 1):
            course_id = course.get("course_id", f"course_{i}")
            total_distance = course.get("total_distance_meters", 0)
            
            print(f"\n    📍 코스 {i}: {course_id}")
            print(f"       🚶 총 이동거리: {total_distance}m ({total_distance/1000:.1f}km)")
            
            # 장소 목록
            places = course.get("places", [])
            print(f"       🏢 장소 구성 ({len(places)}개):")
            
            for j, place in enumerate(places, 1):
                place_info = place.get("place_info", {})
                name = place_info.get("name", "Unknown")
                category = place_info.get("category", "Unknown")
                coords = place_info.get("coordinates", {})
                lat = coords.get("latitude", 0)
                lon = coords.get("longitude", 0)
                similarity = place_info.get("similarity_score", 0)
                
                print(f"          {j}. {name} ({category})")
                if lat and lon:
                    print(f"             📍 좌표: ({lat:.4f}, {lon:.4f})")
                    print(f"             🎯 유사도: {similarity:.3f}")
                else:
                    print(f"             ❌ 좌표 정보 없음")
            
            # 이동 경로
            travel_info = course.get("travel_info", [])
            if travel_info:
                print(f"       🗺️ 이동 경로:")
                for segment in travel_info:
                    from_place = segment.get("from", "Unknown")
                    to_place = segment.get("to", "Unknown")
                    distance = segment.get("distance_meters", 0)
                    print(f"          {from_place} → {to_place}: {distance}m")
            
            # GPT 추천 이유
            recommendation = course.get("recommendation_reason", "")
            if recommendation:
                print(f"       💡 GPT 추천 이유:")
                # 긴 추천 이유를 여러 줄로 나누어 표시
                words = recommendation.split('. ')
                for reason_part in words:
                    if reason_part.strip():
                        print(f"          • {reason_part.strip()}")
            else:
                print(f"       ❌ 추천 이유 없음")
            
            print(f"       {'-'*30}")

def main():
    """메인 실행 함수"""
    tester = YongsanComprehensiveTest()
    tester.run_all_tests()

if __name__ == "__main__":
    main()
