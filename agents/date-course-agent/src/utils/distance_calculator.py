# Haversine 공식을 이용한 거리 계산
# - 위도/경도 간 직선거리 계산
# - 코스 총 이동거리 계산

import math
from typing import Tuple, List, Dict, Any
from loguru import logger

def calculate_haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Haversine 공식을 사용하여 두 지점 간의 거리를 계산
    
    Args:
        lat1, lon1: 첫 번째 지점의 위도, 경도
        lat2, lon2: 두 번째 지점의 위도, 경도
    
    Returns:
        두 지점 간의 거리 (미터)
    """
    try:
        # 지구의 반지름 (km)
        R = 6371.0
        
        # 위도, 경도를 라디안으로 변환
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        # 위도, 경도 차이
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        # Haversine 공식
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        # 거리 (km)
        distance_km = R * c
        
        # 미터로 변환
        distance_meters = distance_km * 1000
        
        return distance_meters
        
    except Exception as e:
        logger.error(f"❌ 거리 계산 실패: {e}")
        return 0.0

def calculate_total_course_distance(places: List[Dict[str, Any]]) -> float:
    """
    코스의 총 이동 거리 계산
    
    Args:
        places: 장소 리스트 (latitude, longitude 포함)
    
    Returns:
        총 이동 거리 (미터)
    """
    try:
        if len(places) < 2:
            return 0.0
        
        total_distance = 0.0
        
        for i in range(len(places) - 1):
            current_place = places[i]
            next_place = places[i + 1]
            
            distance = calculate_haversine_distance(
                current_place['latitude'], current_place['longitude'],
                next_place['latitude'], next_place['longitude']
            )
            
            total_distance += distance
        
        return total_distance
        
    except Exception as e:
        logger.error(f"❌ 코스 총 거리 계산 실패: {e}")
        return 0.0

def calculate_travel_segments(places: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    코스의 각 구간별 이동 정보 계산
    
    Args:
        places: 장소 리스트
    
    Returns:
        구간별 이동 정보 리스트
    """
    try:
        if len(places) < 2:
            return []
        
        segments = []
        
        for i in range(len(places) - 1):
            current_place = places[i]
            next_place = places[i + 1]
            
            distance = calculate_haversine_distance(
                current_place['latitude'], current_place['longitude'],
                next_place['latitude'], next_place['longitude']
            )
            
            segment = {
                'from': current_place.get('place_name', f'장소 {i+1}'),
                'to': next_place.get('place_name', f'장소 {i+2}'),
                'distance_meters': round(distance),
                'from_coordinates': {
                    'latitude': current_place['latitude'],
                    'longitude': current_place['longitude']
                },
                'to_coordinates': {
                    'latitude': next_place['latitude'],
                    'longitude': next_place['longitude']
                }
            }
            
            segments.append(segment)
        
        return segments
        
    except Exception as e:
        logger.error(f"❌ 이동 구간 계산 실패: {e}")
        return []

def find_closest_place(
    target_place: Dict[str, Any], 
    candidate_places: List[Dict[str, Any]]
) -> Tuple[Dict[str, Any], float]:
    """
    대상 장소에서 가장 가까운 후보 장소 찾기
    
    Args:
        target_place: 기준 장소
        candidate_places: 후보 장소들
    
    Returns:
        (가장 가까운 장소, 거리) 튜플
    """
    try:
        if not candidate_places:
            return None, float('inf')
        
        target_lat = target_place['latitude']
        target_lon = target_place['longitude']
        
        closest_place = None
        min_distance = float('inf')
        
        for candidate in candidate_places:
            distance = calculate_haversine_distance(
                target_lat, target_lon,
                candidate['latitude'], candidate['longitude']
            )
            
            if distance < min_distance:
                min_distance = distance
                closest_place = candidate
        
        return closest_place, min_distance
        
    except Exception as e:
        logger.error(f"❌ 최근접 장소 찾기 실패: {e}")
        return None, float('inf')

def calculate_center_coordinates(places: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    여러 장소들의 중심 좌표 계산
    
    Args:
        places: 장소 리스트
    
    Returns:
        중심 좌표 {'latitude': float, 'longitude': float}
    """
    try:
        if not places:
            return {'latitude': 0.0, 'longitude': 0.0}
        
        total_lat = sum(place['latitude'] for place in places)
        total_lon = sum(place['longitude'] for place in places)
        
        center_lat = total_lat / len(places)
        center_lon = total_lon / len(places)
        
        return {
            'latitude': center_lat,
            'longitude': center_lon
        }
        
    except Exception as e:
        logger.error(f"❌ 중심 좌표 계산 실패: {e}")
        return {'latitude': 0.0, 'longitude': 0.0}

def is_within_radius(
    center_lat: float, center_lon: float,
    target_lat: float, target_lon: float,
    radius_meters: float
) -> bool:
    """
    특정 지점이 반경 내에 있는지 확인
    
    Args:
        center_lat, center_lon: 중심점 좌표
        target_lat, target_lon: 확인할 지점 좌표
        radius_meters: 반경 (미터)
    
    Returns:
        반경 내에 있으면 True
    """
    try:
        distance = calculate_haversine_distance(
            center_lat, center_lon, target_lat, target_lon
        )
        
        return distance <= radius_meters
        
    except Exception as e:
        logger.error(f"❌ 반경 내 확인 실패: {e}")
        return False

def optimize_route_by_distance(places: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    거리 기준으로 경로 최적화 (간단한 그리디 알고리즘)
    
    Args:
        places: 최적화할 장소 리스트
    
    Returns:
        최적화된 장소 순서
    """
    try:
        if len(places) <= 2:
            return places
        
        # 첫 번째 장소부터 시작
        optimized_route = [places[0]]
        remaining_places = places[1:].copy()
        
        current_place = places[0]
        
        while remaining_places:
            # 현재 장소에서 가장 가까운 다음 장소 찾기
            closest_place, _ = find_closest_place(current_place, remaining_places)
            
            if closest_place:
                optimized_route.append(closest_place)
                remaining_places.remove(closest_place)
                current_place = closest_place
            else:
                # 남은 장소가 있지만 찾지 못한 경우 (에러 상황)
                optimized_route.extend(remaining_places)
                break
        
        return optimized_route
        
    except Exception as e:
        logger.error(f"❌ 경로 최적화 실패: {e}")
        return places

# 편의 함수들
def meters_to_km(meters: float) -> float:
    """미터를 킬로미터로 변환"""
    return meters / 1000

def km_to_meters(km: float) -> float:
    """킬로미터를 미터로 변환"""
    return km * 1000

def format_distance(distance_meters: float) -> str:
    """거리를 읽기 쉬운 형태로 포맷"""
    if distance_meters < 1000:
        return f"{round(distance_meters)}m"
    else:
        return f"{round(distance_meters/1000, 1)}km"

if __name__ == "__main__":
    # 테스트 실행
    def test_distance_calculator():
        try:
            # 테스트 좌표들 (홍대 ~ 강남)
            hongdae = {'latitude': 37.5519, 'longitude': 126.9245, 'place_name': '홍대'}
            gangnam = {'latitude': 37.4979, 'longitude': 127.0276, 'place_name': '강남'}
            
            # 거리 계산 테스트
            distance = calculate_haversine_distance(
                hongdae['latitude'], hongdae['longitude'],
                gangnam['latitude'], gangnam['longitude']
            )
            
            print(f"✅ 거리 계산기 테스트 성공")
            print(f"홍대 ↔ 강남: {format_distance(distance)}")
            
            # 코스 거리 계산 테스트
            test_places = [hongdae, gangnam]
            total_distance = calculate_total_course_distance(test_places)
            print(f"총 코스 거리: {format_distance(total_distance)}")
            
            # 이동 구간 계산 테스트
            segments = calculate_travel_segments(test_places)
            print(f"이동 구간: {len(segments)}개")
            
        except Exception as e:
            print(f"❌ 거리 계산기 테스트 실패: {e}")
    
    test_distance_calculator()
