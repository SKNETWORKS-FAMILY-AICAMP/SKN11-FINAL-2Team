#!/usr/bin/env python3
"""
지리적 필터 계산 버그 분석
"""

import math

def debug_geo_filter():
    """지리적 필터 계산 분석"""
    print("🗺️ 지리적 필터 계산 버그 분석")
    print("=" * 60)
    
    # 테스트 데이터
    locations = {
        "이촌동": {"lat": 37.5227, "lon": 126.9755},
        "이태원": {"lat": 37.5344, "lon": 126.9943}
    }
    
    radius_meters = 2000
    
    for name, coords in locations.items():
        lat, lon = coords["lat"], coords["lon"]
        
        print(f"\n📍 {name} ({lat}, {lon}) - 반경 {radius_meters}m")
        
        # 현재 코드의 잘못된 계산
        lat_diff_current = radius_meters / 111000
        lon_diff_current = radius_meters / (111000 * abs(lat) / 90) if lat != 0 else radius_meters / 111000
        
        print(f"   현재 (잘못된) 계산:")
        print(f"     위도 차이: {lat_diff_current:.6f}°")
        print(f"     경도 차이: {lon_diff_current:.6f}°")
        
        # 올바른 계산
        lat_diff_correct = radius_meters / 111000
        lon_diff_correct = radius_meters / (111000 * math.cos(math.radians(lat)))
        
        print(f"   올바른 계산:")
        print(f"     위도 차이: {lat_diff_correct:.6f}°")
        print(f"     경도 차이: {lon_diff_correct:.6f}°")
        
        # 필터 범위 비교
        print(f"\n   현재 필터 범위:")
        print(f"     위도: {lat - lat_diff_current:.4f} ~ {lat + lat_diff_current:.4f}")
        print(f"     경도: {lon - lon_diff_current:.4f} ~ {lon + lon_diff_current:.4f}")
        
        print(f"   올바른 필터 범위:")
        print(f"     위도: {lat - lat_diff_correct:.4f} ~ {lat + lat_diff_correct:.4f}")
        print(f"     경도: {lon - lon_diff_correct:.4f} ~ {lon + lon_diff_correct:.4f}")
        
        # 실제 범위 크기 비교 (미터 단위)
        current_lat_range = lat_diff_current * 111000 * 2
        current_lon_range = lon_diff_current * 111000 * math.cos(math.radians(lat)) * 2
        
        correct_lat_range = lat_diff_correct * 111000 * 2
        correct_lon_range = lon_diff_correct * 111000 * 2
        
        print(f"\n   실제 검색 범위 (미터):")
        print(f"     현재 - 위도: {current_lat_range:.0f}m, 경도: {current_lon_range:.0f}m")
        print(f"     올바른 - 위도: {correct_lat_range:.0f}m, 경도: {correct_lon_range:.0f}m")
        
        # 문제점 진단
        if abs(current_lon_range - 4000) > 500:
            print(f"   ❌ 경도 범위 오류: {current_lon_range:.0f}m (예상: 4000m)")
        else:
            print(f"   ✅ 경도 범위 정상: {current_lon_range:.0f}m")
    
    # 두 지역이 서로의 필터에 포함되는지 확인
    print(f"\n🔄 상호 필터 포함 여부 확인:")
    
    ichon_lat, ichon_lon = locations["이촌동"]["lat"], locations["이촌동"]["lon"]
    itaewon_lat, itaewon_lon = locations["이태원"]["lat"], locations["이태원"]["lon"]
    
    # 이촌동 기준 필터로 이태원이 포함되는지
    ichon_lat_diff = radius_meters / 111000
    ichon_lon_diff = radius_meters / (111000 * abs(ichon_lat) / 90)
    
    ichon_lat_min = ichon_lat - ichon_lat_diff
    ichon_lat_max = ichon_lat + ichon_lat_diff
    ichon_lon_min = ichon_lon - ichon_lon_diff
    ichon_lon_max = ichon_lon + ichon_lon_diff
    
    itaewon_in_ichon_filter = (
        ichon_lat_min <= itaewon_lat <= ichon_lat_max and
        ichon_lon_min <= itaewon_lon <= ichon_lon_max
    )
    
    print(f"   이촌동 필터에 이태원 포함? {itaewon_in_ichon_filter}")
    if itaewon_in_ichon_filter:
        print(f"   ❌ 문제: 이촌동 검색에서 이태원 장소도 검색됨!")
    
    # 이태원 기준 필터로 이촌동이 포함되는지
    itaewon_lat_diff = radius_meters / 111000
    itaewon_lon_diff = radius_meters / (111000 * abs(itaewon_lat) / 90)
    
    itaewon_lat_min = itaewon_lat - itaewon_lat_diff
    itaewon_lat_max = itaewon_lat + itaewon_lat_diff
    itaewon_lon_min = itaewon_lon - itaewon_lon_diff
    itaewon_lon_max = itaewon_lon + itaewon_lon_diff
    
    ichon_in_itaewon_filter = (
        itaewon_lat_min <= ichon_lat <= itaewon_lat_max and
        itaewon_lon_min <= ichon_lon <= itaewon_lon_max
    )
    
    print(f"   이태원 필터에 이촌동 포함? {ichon_in_itaewon_filter}")
    if ichon_in_itaewon_filter:
        print(f"   ❌ 문제: 이태원 검색에서 이촌동 장소도 검색됨!")
    
    # 실제 거리 vs 필터 크기
    actual_distance = calculate_distance(ichon_lat, ichon_lon, itaewon_lat, itaewon_lon)
    print(f"\n📏 실제 거리 vs 필터 크기:")
    print(f"   이촌동 ↔ 이태원 실제 거리: {actual_distance:.0f}m")
    print(f"   각 지역의 검색 반경: {radius_meters}m")
    print(f"   필터가 겹치는 정도: {max(0, radius_meters * 2 - actual_distance):.0f}m")

def calculate_distance(lat1, lon1, lat2, lon2):
    """거리 계산"""
    R = 6371000
    lat1_rad, lon1_rad, lat2_rad, lon2_rad = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = lat2_rad - lat1_rad, lon2_rad - lon1_rad
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

if __name__ == "__main__":
    debug_geo_filter()