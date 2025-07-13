# Place Agent 메인 클래스
# - 지역 분석 및 좌표 반환 전문 서비스
# - LLM 기반 지역 추천 + 하이브리드 확장

import asyncio
import sys
import os
from typing import List, Dict, Any
from datetime import datetime

# 상위 디렉토리의 모듈들 import
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.models.request_models import PlaceAgentRequest
from src.models.response_models import PlaceAgentResponse, LocationResponse, Coordinates
from src.core.location_analyzer import LocationAnalyzer
from src.core.coordinates_service import CoordinatesService
from src.core.venue_search_service import VenueSearchService
from config.settings import settings

class PlaceAgent:
    """Place Agent 메인 클래스"""
    
    def __init__(self):
        """초기화"""
        self.location_analyzer = LocationAnalyzer()
        self.coordinates_service = CoordinatesService()
        self.venue_search_service = VenueSearchService()
        print("✅ Place Agent 초기화 완료")
    
    async def process_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        메인 에이전트로부터 받은 요청을 처리
        
        Args:
            request_data: 요청 데이터 (JSON)
            
        Returns:
            처리 결과 (JSON)
        """
        try:
            # 1. 요청 데이터 검증 및 모델 변환
            request = PlaceAgentRequest(**request_data)
            print(f"📍 Place Agent 요청 처리 시작 - ID: {request.request_id}")
            
            # 🔥 CRITICAL: location_clustering 최우선 처리 (사용자 지정 지역 정보 보장)
            location_clustering = getattr(request.location_request, 'location_clustering', None)
            print(f"🔍 [DEBUG] location_clustering 값: {location_clustering}")
            print(f"🔍 [DEBUG] location_clustering 타입: {type(location_clustering)}")
            if location_clustering:
                print(f"🔍 [DEBUG] location_clustering.get('valid'): {location_clustering.get('valid', False)}")
                print(f"🔍 [DEBUG] location_clustering.get('strategy'): {location_clustering.get('strategy', 'none')}")
            
            if location_clustering and location_clustering.get("valid", False):
                print(f"🎯 [PRIORITY] Location Clustering 모드 - 사용자 지정 지역 우선 처리")
                return await self.process_with_venue_search(request, location_clustering)
            else:
                print(f"🚨 [FALLBACK] Location Clustering 없음 - LLM 기반 지역 분석 실행")
                print(f"🚨 [FALLBACK] 이유: location_clustering={bool(location_clustering)}, valid={location_clustering.get('valid', False) if location_clustering else 'N/A'}")
            
            # 2. LLM 기반 지역 분석 (fallback)
            analysis_result = await self.location_analyzer.analyze_locations(request)
            areas = analysis_result.get("areas", [])
            reasons = analysis_result.get("reasons", [])
            
            if not areas:
                return PlaceAgentResponse(
                    request_id=request.request_id,
                    success=False,
                    locations=[],
                    error_message="적합한 지역을 찾을 수 없습니다."
                ).model_dump()
            
            # 3. 각 지역에 대한 좌표 조회
            locations = []
            for i, (area_name, reason) in enumerate(zip(areas, reasons)):
                try:
                    # 좌표 조회
                    coords = await self.coordinates_service.get_coordinates_for_area(
                        area_name, request.user_context
                    )
                    
                    # 같은 지역 내 다양성을 위한 미세 조정
                    if len([a for a in areas if a == area_name]) > 1:
                        same_area_index = [j for j, a in enumerate(areas[:i+1]) if a == area_name][-1]
                        coords = self.coordinates_service.adjust_coordinates_for_diversity(
                            coords, same_area_index, len([a for a in areas if a == area_name])
                        )
                    
                    # 좌표 유효성 검증
                    if not self.coordinates_service.validate_coordinates(coords):
                        print(f"⚠️ '{area_name}' 좌표 유효성 검증 실패, 기본 좌표 사용")
                        coords = {"latitude": 37.5665, "longitude": 126.9780}
                    
                    # 응답 객체 생성
                    location = LocationResponse(
                        sequence=i + 1,
                        area_name=area_name,
                        coordinates=Coordinates(**coords),
                        reason=reason
                    )
                    locations.append(location)
                    
                    print(f"✅ {i+1}. {area_name} - {coords['latitude']}, {coords['longitude']}")
                    
                except Exception as e:
                    print(f"❌ 지역 '{area_name}' 처리 실패: {e}")
                    continue
            
            # 4. 최종 응답 생성
            if not locations:
                return PlaceAgentResponse(
                    request_id=request.request_id,
                    success=False,
                    locations=[],
                    error_message="좌표 조회에 실패했습니다."
                ).model_dump()
            
            response = PlaceAgentResponse(
                request_id=request.request_id,
                success=True,
                locations=locations
            )
            
            print(f"🎉 Place Agent 요청 처리 완료 - {len(locations)}개 지역 반환")
            return response.model_dump()
            
        except Exception as e:
            print(f"❌ Place Agent 요청 처리 실패: {e}")
            return PlaceAgentResponse(
                request_id=request_data.get("request_id", "unknown"),
                success=False,
                locations=[],
                error_message=f"서버 처리 중 오류가 발생했습니다: {str(e)}"
            ).model_dump()
    
    async def process_with_venue_search(self, request: PlaceAgentRequest, location_clustering: Dict[str, Any]) -> Dict[str, Any]:
        """
        실제 장소 검색을 통한 처리 (NEW APPROACH)
        
        Args:
            request: PlaceAgentRequest 객체
            location_clustering: 사용자 지정 지역 정보
            
        Returns:
            처리 결과 (JSON)
        """
        try:
            print(f"🎯 [NEW VENUE SEARCH] 실제 장소 검색 모드 시작")
            
            # 1. 사용자 지정 지역 정보 파싱
            strategy = location_clustering.get("strategy", "user_defined")
            groups = location_clustering.get("groups", [])
            
            # 2. 카테고리 정보 추출
            selected_categories = getattr(request, 'selected_categories', [])
            if not selected_categories:
                print(f"❌ 카테고리 정보 없음")
                return PlaceAgentResponse(
                    request_id=request.request_id,
                    success=False,
                    locations=[],
                    error_message="카테고리 정보가 없습니다."
                ).model_dump()
            
            print(f"🔍 [DEBUG] 카테고리 정보: {selected_categories}")
            print(f"🔍 [DEBUG] 지역 전략: {strategy}")
            print(f"🔍 [DEBUG] 그룹 정보: {groups}")
            
            # 3. 장소별 지역 매핑 생성
            place_location_map = {}
            if (strategy == "custom_groups" or strategy == "user_defined") and groups:
                for group in groups:
                    places = group.get("places", [])
                    location = group.get("location", "")
                    if places and location:
                        for place_num in places:
                            place_location_map[place_num] = location
                            
            # 4. 실제 장소 검색 수행
            venues = []
            total_places = request.location_request.place_count
            
            for place_num in range(1, total_places + 1):
                # 지역 정보 가져오기
                area_name = place_location_map.get(place_num, "홍대")  # 기본값
                category = selected_categories[place_num - 1] if place_num - 1 < len(selected_categories) else "카페"
                
                print(f"🔍 [VENUE SEARCH] {place_num}번째 장소: {area_name} {category}")
                
                # 실제 장소 검색 (지역명으로만)
                venue = await self.venue_search_service.find_venue_for_location(
                    area_name=area_name,
                    category=category,
                    existing_venues=venues,
                    max_distance_between_venues=1.5
                )
                
                if venue:
                    venues.append(venue)
                    print(f"✅ {place_num}번째 장소 발견: {venue.name} ({venue.distance:.2f}km)")
                else:
                    print(f"❌ {place_num}번째 장소 검색 실패: {area_name} {category}")
                    
                    # 같은 지역 내 기존 장소가 있으면 그것을 재사용
                    same_area_existing = [v for v in venues if hasattr(v, 'area_name') and v.area_name == area_name]
                    if same_area_existing:
                        # 가장 최근에 추가된 같은 지역 장소 재사용
                        reused_venue = same_area_existing[-1]
                        
                        # 새로운 카테고리로 복사본 생성
                        reused_copy = type('ReusedVenue', (), {
                            'name': f"{reused_venue.name} ({category} 추가)",
                            'latitude': reused_venue.latitude,
                            'longitude': reused_venue.longitude,
                            'address': getattr(reused_venue, 'address', area_name),
                            'category': category,
                            'area_name': area_name,
                            'distance': getattr(reused_venue, 'distance', 0.0)
                        })()
                        
                        venues.append(reused_copy)
                        print(f"🔄 {place_num}번째 장소 재사용: {reused_venue.name} (같은 장소에서 {category} 활동)")
                    else:
                        # 같은 지역 기존 장소가 없으면 지역 중심 좌표 사용
                        center_coords = await self.coordinates_service.get_coordinates_for_area(area_name)
                        venues.append(type('MockVenue', (), {
                            'name': f"{area_name} {category}",
                            'latitude': center_coords["latitude"],
                            'longitude': center_coords["longitude"],
                            'address': f"{area_name} 지역",
                            'category': category,
                            'area_name': area_name,
                            'distance': 0.0
                        })())
                        print(f"🏢 {place_num}번째 장소 기본값: {area_name} 지역 중심")
            
            # 5. 같은 지역 내 거리 제한 확인
            same_region_groups = []
            if strategy == "custom_groups" and groups:
                for group in groups:
                    if len(group.get("places", [])) > 1:
                        same_region_groups.append(group["places"])
            
            if same_region_groups:
                is_valid = self.venue_search_service.check_distance_constraint(
                    venues, same_region_groups, max_distance_km=1.5
                )
                if not is_valid:
                    print(f"⚠️ 거리 제한 위반 - 그래도 결과 반환")
            
            # 6. 응답 생성
            locations = []
            for i, venue in enumerate(venues):
                location = LocationResponse(
                    sequence=i + 1,
                    area_name=place_location_map.get(i + 1, "검색된 지역"),
                    coordinates=Coordinates(
                        latitude=venue.latitude,
                        longitude=venue.longitude
                    ),
                    reason=f"'{venue.name}' 실제 장소 검색으로 발견됨 ({venue.distance:.2f}km)",
                    venue_name=venue.name,
                    venue_address=getattr(venue, 'address', ''),
                    venue_category=getattr(venue, 'category', ''),
                    distance_from_center=venue.distance
                )
                locations.append(location)
            
            response = PlaceAgentResponse(
                request_id=request.request_id,
                success=True,
                locations=locations
            )
            
            print(f"🎉 [NEW VENUE SEARCH] 완료 - {len(locations)}개 실제 장소 반환")
            return response.model_dump()
            
        except Exception as e:
            print(f"❌ [NEW VENUE SEARCH] 실패: {e}")
            return PlaceAgentResponse(
                request_id=request.request_id,
                success=False,
                locations=[],
                error_message=f"실제 장소 검색 중 오류가 발생했습니다: {str(e)}"
            ).model_dump()
    
    async def process_with_location_clustering(self, request: PlaceAgentRequest, location_clustering: Dict[str, Any]) -> Dict[str, Any]:
        """
        사용자 지정 location_clustering 정보를 기반으로 처리
        
        Args:
            request: PlaceAgentRequest 객체
            location_clustering: 사용자 지정 지역 정보
            
        Returns:
            처리 결과 (JSON)
        """
        try:
            print(f"🎯 [PRIORITY] Location Clustering 처리 시작")
            print(f"🎯 [PRIORITY] Strategy: {location_clustering.get('strategy', 'unknown')}")
            
            strategy = location_clustering.get("strategy", "user_defined")
            groups = location_clustering.get("groups", [])
            
            areas = []
            reasons = []
            
            # strategy가 "user_defined"인 경우도 "custom_groups"로 처리
            if (strategy == "custom_groups" or strategy == "user_defined") and groups:
                print(f"🎯 [PRIORITY] Custom Groups 처리 - {len(groups)}개 그룹")
                
                # 총 필요한 장소 개수 확인
                total_places_needed = request.location_request.place_count
                print(f"🎯 [PRIORITY] 총 필요한 장소 개수: {total_places_needed}")
                
                # 장소 번호별로 정렬하여 순서대로 처리
                place_location_map = {}  # {place_num: location}
                
                for i, group in enumerate(groups):
                    places = group.get("places", [])
                    location = group.get("location", "")
                    if places and location:
                        for place_num in places:
                            place_location_map[place_num] = location
                            print(f"🎯 [PRIORITY] 그룹 {i+1}: {place_num}번째 장소 → {location}")
                
                # 1번부터 순서대로 처리하여 누락 방지
                for place_num in range(1, total_places_needed + 1):
                    if place_num in place_location_map:
                        location = place_location_map[place_num]
                        areas.append(location)
                        reasons.append(f"사용자가 {place_num}번째 장소를 {location}에서 찾기를 명시적으로 요청했습니다.")
                        print(f"🎯 [PRIORITY] 최종 처리: {place_num}번째 장소 → {location}")
                    else:
                        print(f"🚨 [ERROR] {place_num}번째 장소에 대한 지역 지정이 없음!")
                        # 기본값으로 첫 번째 그룹의 location 사용
                        if groups and groups[0].get("location"):
                            default_location = groups[0]["location"]
                            areas.append(default_location)
                            reasons.append(f"{place_num}번째 장소는 지역 지정이 없어 {default_location}으로 배치했습니다.")
                            print(f"🚨 [FALLBACK] {place_num}번째 장소 → {default_location} (기본값)")
                
                print(f"🎯 [PRIORITY] 최종 지역 목록: {areas} (총 {len(areas)}개)")
            
            elif strategy == "same_area":
                target_area = location_clustering.get("target_area", "사용자 지정 지역")
                place_count = request.location_request.place_count
                print(f"🎯 [PRIORITY] Same Area 처리 - 모든 {place_count}개 장소를 {target_area}에서")
                for i in range(place_count):
                    areas.append(target_area)
                    reasons.append(f"사용자가 모든 장소를 {target_area} 내에서 찾기를 명시적으로 요청했습니다.")
            
            elif strategy == "different_areas":
                different_areas = location_clustering.get("areas", [])
                print(f"🎯 [PRIORITY] Different Areas 처리 - 각각 다른 지역: {different_areas}")
                for area in different_areas:
                    areas.append(area)
                    reasons.append(f"사용자가 각 장소를 서로 다른 지역에서 찾기를 요청했습니다.")
            
            if not areas:
                print(f"🚨 [ERROR] Location Clustering 처리 실패 - 지역 정보 없음")
                return PlaceAgentResponse(
                    request_id=request.request_id,
                    success=False,
                    locations=[],
                    error_message="사용자 지정 지역 정보를 처리할 수 없습니다."
                ).model_dump()
            
            print(f"🎯 [PRIORITY] 처리된 지역 목록: {areas}")
            
            # 3. 각 지역에 대한 좌표 조회
            locations = []
            for i, (area_name, reason) in enumerate(zip(areas, reasons)):
                try:
                    # 좌표 조회
                    coords = await self.coordinates_service.get_coordinates_for_area(
                        area_name, request.user_context
                    )
                    
                    # 같은 지역 내 다양성을 위한 미세 조정
                    if len([a for a in areas if a == area_name]) > 1:
                        same_area_index = [j for j, a in enumerate(areas[:i+1]) if a == area_name][-1]
                        coords = self.coordinates_service.adjust_coordinates_for_diversity(
                            coords, same_area_index, len([a for a in areas if a == area_name])
                        )
                    
                    # 좌표 유효성 검증
                    if not self.coordinates_service.validate_coordinates(coords):
                        print(f"⚠️ '{area_name}' 좌표 유효성 검증 실패, 기본 좌표 사용")
                        coords = {"latitude": 37.5665, "longitude": 126.9780}
                    
                    # 응답 객체 생성
                    location = LocationResponse(
                        sequence=i + 1,
                        area_name=area_name,
                        coordinates=Coordinates(**coords),
                        reason=reason
                    )
                    locations.append(location)
                    
                    print(f"✅ {i+1}. {area_name} - {coords['latitude']}, {coords['longitude']}")
                    
                except Exception as e:
                    print(f"❌ 지역 '{area_name}' 처리 실패: {e}")
                    continue
            
            # 4. 최종 응답 생성
            if not locations:
                return PlaceAgentResponse(
                    request_id=request.request_id,
                    success=False,
                    locations=[],
                    error_message="좌표 조회에 실패했습니다."
                ).model_dump()
            
            response = PlaceAgentResponse(
                request_id=request.request_id,
                success=True,
                locations=locations
            )
            
            print(f"🎉 [PRIORITY] Location Clustering 처리 완료 - {len(locations)}개 지역 반환")
            return response.model_dump()
            
        except Exception as e:
            print(f"❌ Location Clustering 처리 실패: {e}")
            return PlaceAgentResponse(
                request_id=request.request_id,
                success=False,
                locations=[],
                error_message=f"사용자 지정 지역 처리 중 오류가 발생했습니다: {str(e)}"
            ).model_dump()
    
    async def health_check(self) -> Dict[str, str]:
        """헬스 체크"""
        return {
            "status": "healthy",
            "service": "place-agent",
            "version": "2.0.0",
            "port": str(settings.SERVER_PORT)
        }

# 직접 실행 테스트용
async def main():
    """테스트용 메인 함수"""
    agent = PlaceAgent()
    
    # 테스트 데이터
    test_request = {
        "request_id": "test-place-001",
        "timestamp": datetime.now().isoformat(),
        "request_type": "proximity_based",
        "location_request": {
            "proximity_type": "near",
            "reference_areas": ["홍대"],
            "place_count": 3,
            "proximity_preference": "middle",
            "transportation": "지하철"
        },
        "user_context": {
            "demographics": {
                "age": 25,
                "mbti": "ENFP",
                "relationship_stage": "연인"
            },
            "preferences": ["트렌디한", "감성적인"],
            "requirements": {
                "budget_level": "medium",
                "time_preference": "저녁",
                "transportation": "지하철",
                "max_travel_time": 30
            }
        },
        "selected_categories": ["카페", "레스토랑"]
    }
    
    result = await agent.process_request(test_request)
    print("\n📋 테스트 결과:")
    print(f"성공: {result['success']}")
    if result['success']:
        for location in result['locations']:
            print(f"  {location['sequence']}. {location['area_name']}")
            print(f"     좌표: {location['coordinates']['latitude']}, {location['coordinates']['longitude']}")
            print(f"     이유: {location['reason']}")
    else:
        print(f"오류: {result['error_message']}")

if __name__ == "__main__":
    asyncio.run(main())