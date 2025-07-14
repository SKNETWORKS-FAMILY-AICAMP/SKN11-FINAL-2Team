#!/usr/bin/env python3
"""
클러스터링 로직 상세 분석
"""

import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '.'))

from src.utils.location_analyzer import SmartLocationAnalyzer

def debug_clustering():
    """클러스터링 로직 디버깅"""
    print("🔍 클러스터링 로직 상세 분석")
    print("=" * 60)
    
    # 실제 테스트 데이터
    search_targets = [
        {
            "sequence": 1,
            "category": "음식점",
            "location": {
                "area_name": "이촌동",
                "coordinates": {"latitude": 37.5227, "longitude": 126.9755}
            },
            "semantic_query": "이촌동에서 커플이 가기 좋은 로맨틱한 레스토랑"
        },
        {
            "sequence": 2,
            "category": "카페",
            "location": {
                "area_name": "이촌동",
                "coordinates": {"latitude": 37.5227, "longitude": 126.9755}
            },
            "semantic_query": "이촌동에서 디저트와 커피를 즐길 수 있는 아늑한 카페"
        },
        {
            "sequence": 3,
            "category": "문화시설",
            "location": {
                "area_name": "이태원",
                "coordinates": {"latitude": 37.5344, "longitude": 126.9943}
            },
            "semantic_query": "이태원에서 커플이 함께 즐길 수 있는 박물관이나 전시관"
        }
    ]
    
    # 이촌동-이태원 거리 계산
    distance = calculate_distance(37.5227, 126.9755, 37.5344, 126.9943)
    print(f"🗺️ 이촌동 ↔ 이태원 거리: {distance:.0f}m")
    print(f"   클러스터링 임계값: 1500m")
    print(f"   거리가 임계값보다 큼: {distance > 1500}")
    
    analyzer = SmartLocationAnalyzer()
    
    # 분석 실행
    location_analysis = analyzer.analyze_search_targets(search_targets, "sunny")
    
    print(f"\n📊 분석 결과:")
    print(f"   분석 타입: {location_analysis['analysis_type']}")
    print(f"   클러스터 개수: {len(location_analysis['clusters'])}")
    print(f"   분석 요약: {location_analysis['analysis_summary']}")
    print(f"   거리 제한: {location_analysis['distance_limit']}")
    
    # 각 클러스터 상세 분석
    for i, cluster in enumerate(location_analysis['clusters']):
        print(f"\n🏢 클러스터 {i+1}:")
        print(f"   ID: {cluster.cluster_id}")
        print(f"   중심 좌표: ({cluster.center_lat:.4f}, {cluster.center_lon:.4f})")
        print(f"   검색 반경: {cluster.search_radius}m")
        print(f"   포함 타겟 수: {len(cluster.targets)}")
        
        for j, target in enumerate(cluster.targets):
            area_name = target['location']['area_name']
            coords = target['location']['coordinates']
            print(f"     타겟 {j+1}: {target['sequence']}번 ({target['category']}) - {area_name}")
            print(f"               좌표: ({coords['latitude']}, {coords['longitude']})")
    
    # 클러스터링 과정 시뮬레이션
    print(f"\n🔄 클러스터링 과정 시뮬레이션:")
    simulate_clustering_process(search_targets, analyzer)

def simulate_clustering_process(search_targets, analyzer):
    """클러스터링 과정을 단계별로 시뮬레이션"""
    
    clusters = []
    CLUSTERING_THRESHOLD = 1500
    
    print(f"   임계값: {CLUSTERING_THRESHOLD}m")
    
    for i, target in enumerate(search_targets):
        coords = analyzer._get_coords_from_target(target)
        if not coords:
            print(f"   타겟 {i+1}: 좌표 추출 실패")
            continue
        
        print(f"\n   타겟 {i+1} 처리: {target['sequence']}번 ({target['location']['area_name']})")
        print(f"     좌표: ({coords['lat']}, {coords['lon']})")
        
        assigned_cluster = None
        min_distance = float('inf')
        
        # 기존 클러스터들과의 거리 계산
        for j, cluster in enumerate(clusters):
            distance = calculate_distance(coords['lat'], coords['lon'], cluster['center_lat'], cluster['center_lon'])
            print(f"     클러스터 {j+1}과의 거리: {distance:.0f}m")
            
            if distance <= CLUSTERING_THRESHOLD and distance < min_distance:
                min_distance = distance
                assigned_cluster = cluster
                print(f"       → 할당 가능 (거리: {distance:.0f}m)")
        
        target_dict = analyzer._convert_target_to_dict(target)
        
        if assigned_cluster:
            print(f"     결과: 기존 클러스터에 할당")
            assigned_cluster['targets'].append(target_dict)
            # 중심점 재계산
            total_lat = sum(t['location']['coordinates']['latitude'] for t in assigned_cluster['targets'])
            total_lon = sum(t['location']['coordinates']['longitude'] for t in assigned_cluster['targets'])
            assigned_cluster['center_lat'] = total_lat / len(assigned_cluster['targets'])
            assigned_cluster['center_lon'] = total_lon / len(assigned_cluster['targets'])
        else:
            print(f"     결과: 새 클러스터 생성")
            new_cluster = {
                'cluster_id': len(clusters) + 1,
                'targets': [target_dict],
                'center_lat': coords['lat'],
                'center_lon': coords['lon'],
                'search_radius': 2000
            }
            clusters.append(new_cluster)
    
    print(f"\n📋 최종 클러스터링 결과:")
    for i, cluster in enumerate(clusters):
        print(f"   클러스터 {i+1}: {len(cluster['targets'])}개 타겟")
        for target in cluster['targets']:
            area_name = target['location']['area_name']
            print(f"     - {target['sequence']}번 {area_name}")

def calculate_distance(lat1, lon1, lat2, lon2):
    """거리 계산"""
    import math
    R = 6371000
    lat1_rad, lon1_rad, lat2_rad, lon2_rad = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = lat2_rad - lat1_rad, lon2_rad - lon1_rad
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

if __name__ == "__main__":
    debug_clustering()