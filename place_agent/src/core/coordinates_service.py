# 좌표 계산 및 검증 서비스
# - 지역명을 좌표로 변환
# - 좌표 유효성 검증 및 보정

import asyncio
import httpx
import math
import os
import sys
from typing import Dict, Tuple, Optional, List

# 상위 디렉토리의 모듈들 import  
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from src.data.area_data import get_area_coordinates, get_area_characteristics, AREA_CENTERS
from src.models.request_models import UserContext
from src.core.location_analyzer import LocationAnalyzer
from config.settings import settings

class CoordinatesService:
    """좌표 계산 및 변환 서비스"""
    
    def __init__(self):
        """초기화"""
        self.kakao_api_key = os.getenv("KAKAO_API_KEY")
        self.location_analyzer = LocationAnalyzer()
    
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

    def calculate_center_coordinates(self, coordinates_list: List[Dict]) -> Dict[str, float]:
        """여러 좌표의 중심점 계산"""
        if not coordinates_list:
            return {"latitude": 37.5665, "longitude": 126.9780}  # 서울시청
        
        total_lat = sum(coord["latitude"] for coord in coordinates_list)
        total_lng = sum(coord["longitude"] for coord in coordinates_list)
        count = len(coordinates_list)
        
        return {
            "latitude": round(total_lat / count, settings.COORDINATE_PRECISION),
            "longitude": round(total_lng / count, settings.COORDINATE_PRECISION)
        }

    async def get_coordinates_from_kakao(self, area_name: str) -> Optional[Dict[str, float]]:
        """카카오 API로 지역 좌표 조회"""
        if not self.kakao_api_key:
            print("카카오 API 키가 설정되지 않음")
            return None
            
        try:
            url = "https://dapi.kakao.com/v2/local/search/keyword.json"
            headers = {"Authorization": f"KakaoAK {self.kakao_api_key}"}
            params = {"query": f"서울 {area_name}", "category_group_code": "", "size": 1}
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers, params=params)
                
            if response.status_code == 200:
                data = response.json()
                if data.get("documents"):
                    place = data["documents"][0]
                    return {
                        "latitude": float(place["y"]),
                        "longitude": float(place["x"])
                    }
                    
        except Exception as e:
            print(f"카카오 API 조회 실패: {e}")
            
        return None

    async def get_coordinates_for_area(self, area_name: str, user_context: UserContext = None) -> Dict[str, float]:
        """지역명에 대한 좌표 조회 (기존 데이터 우선, 없으면 카카오 API 사용)"""
        # 1. 기존 정의된 지역 데이터에서 조회
        if area_name in AREA_CENTERS:
            coords = get_area_coordinates(area_name)
            print(f"기존 데이터에서 '{area_name}' 좌표 조회: {coords}")
            return coords
        
        # 2. 카카오 API로 조회
        coords = await self.get_coordinates_from_kakao(area_name)
        if coords:
            print(f"카카오 API에서 '{area_name}' 좌표 조회: {coords}")
            return coords
        
        # 3. 실패시 LLM으로 새 지역 특성 분석 (로깅용)
        if user_context:
            try:
                characteristics = await self.location_analyzer.analyze_new_area_characteristics(
                    area_name, user_context
                )
                print(f"새 지역 '{area_name}' 특성 분석 완료: {characteristics}")
            except Exception as e:
                print(f"새 지역 특성 분석 실패: {e}")
        
        # 4. 최종 기본값 (서울시청)
        print(f"'{area_name}' 좌표 조회 실패, 서울시청 좌표 사용")
        return {"latitude": 37.5665, "longitude": 126.9780}

    def validate_coordinates(self, coords: Dict[str, float]) -> bool:
        """서울 지역 좌표 유효성 검증"""
        lat = coords.get("latitude", 0)
        lng = coords.get("longitude", 0)
        
        # 서울 대략적 범위 (위도: 37.4~37.7, 경도: 126.8~127.2)
        return 37.4 <= lat <= 37.7 and 126.8 <= lng <= 127.2

    def adjust_coordinates_for_diversity(self, base_coords: Dict[str, float], index: int, total_count: int) -> Dict[str, float]:
        """좌표 다양성을 위한 미세 조정 (같은 지역 내 여러 위치)"""
        if total_count <= 1:
            return base_coords
            
        # 작은 반경 내에서 다양성 확보 (약 500m 내)
        offset_range = 0.005  # 약 500m
        angle = (index * 2 * math.pi) / total_count
        
        lat_offset = offset_range * math.cos(angle)
        lng_offset = offset_range * math.sin(angle)
        
        return {
            "latitude": round(base_coords["latitude"] + lat_offset, settings.COORDINATE_PRECISION),
            "longitude": round(base_coords["longitude"] + lng_offset, settings.COORDINATE_PRECISION)
        }