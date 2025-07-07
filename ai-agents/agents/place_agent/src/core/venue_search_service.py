# 실제 장소 검색 서비스
# - 카카오 API를 통한 카테고리별 실제 장소 검색
# - 1.5km 이내 제한 로직 구현

import asyncio
import httpx
import math
import os
import random
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

@dataclass
class VenueInfo:
    """검색된 장소 정보"""
    name: str
    latitude: float
    longitude: float
    address: str
    category: str
    area_name: str = ""
    distance: float = 0.0
    phone: str = ""
    
class VenueSearchService:
    """실제 장소 검색 서비스"""
    
    def __init__(self):
        """초기화"""
        self.kakao_api_key = os.getenv("KAKAO_API_KEY")
        
        # 카카오 API 카테고리 코드 매핑
        self.category_codes = {
            "카페": "CE7",
            "음식점": "FD6", 
            "레스토랑": "FD6",
            "식당": "FD6",
            "술집": None,  # 키워드 검색 사용
            "바": None,     # 키워드 검색 사용
            "펜션": "AD5",
            "숙박": "AD5",
            "문화시설": "CT1",
            "관광명소": "AT4",
            "쇼핑": "MT1"
        }
        
        # 술집/바 검색용 키워드
        self.bar_keywords = ["술집", "바", "호프", "맥주", "와인바", "칵테일", "이자카야", "포차"]
        
    def calculate_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """두 좌표 간의 거리 계산 (km)"""
        def to_radians(degree):
            return degree * math.pi / 180

        R = 6371  # 지구의 반지름 (km)
        dLat = to_radians(lat2 - lat1)
        dLng = to_radians(lng2 - lng1)
        
        a = (math.sin(dLat/2) * math.sin(dLat/2) + 
             math.cos(to_radians(lat1)) * math.cos(to_radians(lat2)) * 
             math.sin(dLng/2) * math.sin(dLng/2))
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    async def search_venues_by_category(self, area_name: str, category: str) -> List[VenueInfo]:
        """카테고리별 실제 장소 검색"""
        if not self.kakao_api_key:
            print(f"❌ 카카오 API 키가 설정되지 않음")
            return []
        
        try:
            category_code = self.category_codes.get(category)
            venues = []
            
            if category_code:
                # 카테고리 코드가 있는 경우 (카페, 음식점 등)
                venues = await self._search_by_category_code(area_name, category, category_code)
            else:
                # 카테고리 코드가 없는 경우 (술집, 바 등) - 키워드 검색
                venues = await self._search_by_keywords(area_name, category)
            
            print(f"✅ {area_name} {category} 검색 완료: {len(venues)}개 발견")
            return venues
            
        except Exception as e:
            print(f"❌ {area_name} {category} 검색 실패: {e}")
            return []
    
    async def _search_by_category_code(self, area_name: str, category: str, category_code: str) -> List[VenueInfo]:
        """카테고리 코드로 검색"""
        url = "https://dapi.kakao.com/v2/local/search/category.json"
        headers = {"Authorization": f"KakaoAK {self.kakao_api_key}"}
        # 먼저 해당 지역의 중심 좌표를 가져와서 반경 검색
        from src.data.area_data import get_area_coordinates
        area_coords = get_area_coordinates(area_name)
        
        params = {
            "category_group_code": category_code,
            "x": area_coords["longitude"],  # 경도
            "y": area_coords["latitude"],   # 위도
            "radius": 3000,  # 3km 반경으로 검색
            "size": 15,
            "sort": "distance"
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers, params=params)
            
        if response.status_code == 200:
            data = response.json()
            venues = []
            
            for place in data.get("documents", []):
                venue_lat = float(place["y"])
                venue_lng = float(place["x"])
                
                venues.append(VenueInfo(
                    name=place["place_name"],
                    latitude=venue_lat,
                    longitude=venue_lng,
                    address=place.get("address_name", ""),
                    category=category,
                    area_name=area_name,
                    distance=0.0,  # 거리는 나중에 계산
                    phone=place.get("phone", "")
                ))
            
            return venues
        else:
            print(f"❌ 카카오 API 오류: {response.status_code}")
            return []
    
    async def _search_by_keywords(self, area_name: str, category: str) -> List[VenueInfo]:
        """키워드로 검색 (술집, 바 등)"""
        url = "https://dapi.kakao.com/v2/local/search/keyword.json"
        headers = {"Authorization": f"KakaoAK {self.kakao_api_key}"}
        
        all_venues = []
        keywords = self.bar_keywords if category in ["술집", "바"] else [category]
        
        # 먼저 해당 지역의 중심 좌표를 가져와서 반경 검색
        from src.data.area_data import get_area_coordinates
        area_coords = get_area_coordinates(area_name)
        
        for keyword in keywords:
            params = {
                "query": f"{area_name} {keyword}",
                "x": area_coords["longitude"],  # 경도
                "y": area_coords["latitude"],   # 위도
                "radius": 3000,  # 3km 반경으로 검색
                "size": 10,
                "sort": "distance"
            }
            
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(url, headers=headers, params=params)
                    
                if response.status_code == 200:
                    data = response.json()
                    
                    for place in data.get("documents", []):
                        venue_lat = float(place["y"])
                        venue_lng = float(place["x"])
                        
                        # 중복 제거 (같은 이름의 장소)
                        if not any(v.name == place["place_name"] for v in all_venues):
                            all_venues.append(VenueInfo(
                                name=place["place_name"],
                                latitude=venue_lat,
                                longitude=venue_lng,
                                address=place.get("address_name", ""),
                                category=category,
                                area_name=area_name,
                                distance=0.0,  # 거리는 나중에 계산
                                phone=place.get("phone", "")
                            ))
                
            except Exception as e:
                print(f"❌ 키워드 '{keyword}' 검색 실패: {e}")
                continue
        
        return all_venues
    
    async def find_venue_for_location(self, area_name: str, category: str, 
                                    existing_venues: List[VenueInfo] = None,
                                    max_distance_between_venues: float = 1.5) -> Optional[VenueInfo]:
        """특정 지역/카테고리에서 장소 1개 선택"""
        venues = await self.search_venues_by_category(area_name, category)
        
        if not venues:
            print(f"❌ {area_name}에서 {category} 장소를 찾을 수 없음")
            return None
        
        # 같은 지역 내 기존 장소들과의 1.5km 이내 제약 확인
        if existing_venues:
            same_area_venues = [v for v in existing_venues if v.area_name == area_name]
            if same_area_venues:
                filtered_venues = []
                for venue in venues:
                    is_within_constraint = True
                    
                    # 같은 지역 내 모든 기존 장소들과의 거리 확인
                    for existing in same_area_venues:
                        distance = self.calculate_distance(
                            venue.latitude, venue.longitude,
                            existing.latitude, existing.longitude
                        )
                        print(f"🔍 거리 확인: {venue.name} ↔ {existing.name} = {distance:.2f}km")
                        if distance > max_distance_between_venues:  # 1.5km 초과시 제외
                            is_within_constraint = False
                            print(f"❌ {venue.name}이 {existing.name}로부터 {distance:.2f}km로 1.5km 초과")
                            break
                        else:
                            print(f"✅ {venue.name}이 {existing.name}로부터 {distance:.2f}km로 1.5km 이내")
                    
                    if is_within_constraint:
                        filtered_venues.append(venue)
                
                if filtered_venues:
                    venues = filtered_venues
                    print(f"✅ {area_name} {category}: 1.5km 제약 만족하는 장소 {len(venues)}개 발견")
                else:
                    print(f"⚠️ {area_name}에서 1.5km 제약을 만족하는 {category} 장소 없음")
                    return None
        
        # 랜덤 선택
        selected_venue = random.choice(venues)
        
        # 선택된 장소의 좌표 정보 출력
        print(f"✅ {area_name} {category} 선택: {selected_venue.name}")
        print(f"📍 좌표: ({selected_venue.latitude:.6f}, {selected_venue.longitude:.6f})")
        
        return selected_venue
    
    def check_distance_constraint(self, venues: List[VenueInfo], 
                                same_region_groups: List[List[int]], 
                                max_distance_km: float = 1.5) -> bool:
        """같은 지역 내 장소들 간 거리 제한 확인"""
        for group in same_region_groups:
            if len(group) < 2:
                continue
                
            # 그룹 내 모든 장소 쌍의 거리 확인
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    venue1 = venues[group[i] - 1]  # 1-based index
                    venue2 = venues[group[j] - 1]
                    
                    distance = self.calculate_distance(
                        venue1.latitude, venue1.longitude,
                        venue2.latitude, venue2.longitude
                    )
                    
                    if distance > max_distance_km:
                        print(f"❌ 거리 제한 위반: {venue1.name} - {venue2.name} ({distance:.2f}km > {max_distance_km}km)")
                        return False
        
        return True