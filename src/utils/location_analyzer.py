# 위치 분석기 (상황인지형 동적 거리 제한) - 최종 개선안
# - '단일/다중 지역' 검색 시나리오를 명확히 구분
# - '단일 지역' 검색 시에만 날씨에 따라 검색 반경과 이동 제한을 동적으로 조절
# - '다중 지역' 검색 시에는 각 지역별로 독립적인 표준 검색 반경 적용

import math
from typing import List, Dict, Any, Tuple
from loguru import logger

class LocationCluster:
    """사용자가 요청한 희망 위치들의 그룹을 나타내는 클래스"""
    def __init__(self, cluster_id: int):
        self.cluster_id = cluster_id
        self.targets = []
        self.center_lat = 0.0
        self.center_lon = 0.0
        # 이 클러스터에 적용될 최종 검색 반경 (동적으로 결정됨)
        self.search_radius = 2000 # 기본값

    def add_target(self, target: Dict[str, Any]):
        self.targets.append(target)
        self._update_center()

    def _update_center(self):
        if not self.targets: return
        total_lat = sum(t['location']['coordinates']['latitude'] for t in self.targets)
        total_lon = sum(t['location']['coordinates']['longitude'] for t in self.targets)
        self.center_lat = total_lat / len(self.targets)
        self.center_lon = total_lon / len(self.targets)

class SmartLocationAnalyzer:
    """상황인지형 스마트 위치 분석기"""

    def __init__(self):
        """초기화. 각종 기준값 설정"""
        # '같은 지역'으로 판단하는 클러스터링 기준 (15초 최적화: 1km → 800m)
        self.CLUSTERING_THRESHOLD = 800 # 800m

        # '단일 지역'일 때, 날씨별 동적 거리 기준
        self.distance_limits_by_weather = {
            'sunny':  {'radius': 1500, 'limit': 1500},
            'cloudy': {'radius': 1500, 'limit': 1500},
            'hot':    {'radius': 1000, 'limit': 1000},
            'cold':   {'radius': 1000, 'limit': 1000},
            'rainy':  {'radius': 700,  'limit': 700},
            'snowy':  {'radius': 700,  'limit': 700},
            'default':{'radius': 1200, 'limit': 1200}
        }
        # '다중 지역'일 때, 각 지역별 표준 검색 반경
        self.MULTI_REGION_STANDARD_RADIUS = 1000 # 1km

        logger.info("✅ 상황인지형 스마트 위치 분석기 초기화 완료")

    def _get_weather_config(self, weather: str) -> Dict[str, int]:
        weather_key = weather.lower()
        for key, config in self.distance_limits_by_weather.items():
            if key in weather_key:
                return config
        return self.distance_limits_by_weather['default']

    def analyze_search_targets(self, search_targets: List[Dict[str, Any]], weather: str = "sunny") -> Dict[str, Any]:
        """
        검색 타겟을 분석하여 '단일/다중 지역' 시나리오를 판단하고,
        그에 맞는 동적 검색 반경 및 거리 제한 정책을 수립한다.
        """
        try:
            logger.info(f"🗺️ 위치 분석 시작 - {len(search_targets)}개 타겟 ({weather} 날씨)")

            # 1. 요청 위치들을 클러스터링하여 '단일/다중 지역' 여부 판단
            clusters = self._perform_clustering(search_targets)
            is_single_region = len(clusters) == 1

            # 2. 시나리오에 맞는 정책 수립
            if is_single_region:
                # '단일 지역' 시나리오: 날씨에 따라 동적으로 검색 반경/이동 제한 설정
                weather_config = self._get_weather_config(weather)
                search_radius = weather_config['radius']
                distance_limit = weather_config['limit']
                clusters[0].search_radius = search_radius # 클러스터 객체에 직접 설정
                analysis_summary = f"단일 지역 검색 ({weather}): 검색 반경 {search_radius}m, 이동 제한 {distance_limit}m"
            else:
                # '다중 지역' 시나리오: 각 지역별로 고정된 표준 검색 반경 설정
                distance_limit = float('inf') # 지역 간 이동이므로 제한 없음
                for cluster in clusters:
                    cluster.search_radius = self.MULTI_REGION_STANDARD_RADIUS
                cluster_names = [c.targets[0]['location']['area_name'] for c in clusters]
                analysis_summary = f"다중 지역 검색: 각 지역({', '.join(cluster_names)})을 {self.MULTI_REGION_STANDARD_RADIUS}m 반경으로 독립 검색"

            # 3. 최종 분석 결과 생성
            analysis_result = {
                'analysis_type': 'single_region' if is_single_region else 'multi_region',
                'clusters': clusters,
                'distance_limit': distance_limit, # 최종 이동 제한
                'analysis_summary': analysis_summary
            }

            logger.info(f"✅ 위치 분석 완료 - {analysis_result['analysis_summary']}")
            return analysis_result

        except Exception as e:
            logger.error(f"❌ 위치 분석 실패: {e}")
            return self._get_default_analysis(weather)

    def _perform_clustering(self, search_targets: List[Dict[str, Any]]) -> List[LocationCluster]:
        """요청 위치들을 1.5km 기준으로 클러스터링"""
        clusters = []
        for i, target in enumerate(search_targets):
            try:
                coords = self._get_coords_from_target(target)
                if not coords: 
                    logger.debug(f"타겟 {i+1}: 좌표 추출 실패")
                    continue

                assigned_cluster = None
                min_distance = float('inf')

                for cluster in clusters:
                    distance = self._calculate_distance(coords['lat'], coords['lon'], cluster.center_lat, cluster.center_lon)
                    if distance <= self.CLUSTERING_THRESHOLD and distance < min_distance:
                        min_distance = distance
                        assigned_cluster = cluster

                # 타겟을 딕셔너리로 변환
                target_dict = self._convert_target_to_dict(target)
                if not target_dict:
                    logger.warning(f"타겟 {i+1}: 변환 실패, 건너뛀")
                    continue

                if assigned_cluster:
                    logger.debug(f"타겟 {i+1} → 클러스터 {assigned_cluster.cluster_id} 할당")
                    assigned_cluster.add_target(target_dict)
                else:
                    logger.debug(f"타겟 {i+1} → 새 클러스터 {len(clusters) + 1} 생성")
                    new_cluster = LocationCluster(len(clusters) + 1)
                    new_cluster.add_target(target_dict)
                    clusters.append(new_cluster)
                    
            except Exception as e:
                logger.error(f"클러스터링 실패: {e}")
                continue
                
        return clusters

    def validate_course_distance(self, course: List[Dict[str, Any]], location_analysis: Dict[str, Any]) -> Tuple[bool, str]:
        """
        생성된 코스가 이동 거리 제한 정책을 준수하는지 검증.
        '단일 지역' 시나리오일 때만 검증이 의미 있음.
        """
        if location_analysis['analysis_type'] == 'multi_region':
            return True, "다중 지역 코스는 거리 검증 불필요"
        
        if not course or len(course) < 2:
            return True, "검증 불필요"

        distance_limit = location_analysis['distance_limit']
        violations = []

        for i in range(len(course) - 1):
            p1, p2 = course[i], course[i+1]
            segment_distance = self._calculate_distance(p1['latitude'], p1['longitude'], p2['latitude'], p2['longitude'])

            if segment_distance > distance_limit:
                violations.append(f"이동 거리 초과: {segment_distance:.0f}m > {distance_limit}m")

        if violations:
            return False, "; ".join(violations)
        return True, "적절한 거리"

    # --- Helper Functions (보조 함수들) ---
    def _get_coords_from_target(self, target) -> Dict[str, float]:
        try:
            # Pydantic 모델 처리
            if hasattr(target, 'location'):
                loc = target.location
                if hasattr(loc, 'coordinates'):
                    coords = loc.coordinates
                    if hasattr(coords, 'latitude'):
                        return {'lat': coords.latitude, 'lon': coords.longitude}
                    else:
                        return {'lat': coords['latitude'], 'lon': coords['longitude']}
                elif hasattr(loc, 'latitude'):
                    return {'lat': loc.latitude, 'lon': loc.longitude}
            
            # 딕셔너리 처리
            if isinstance(target, dict) and 'location' in target:
                location = target['location']
                if 'coordinates' in location:
                    coords = location['coordinates']
                    return {'lat': coords['latitude'], 'lon': coords['longitude']}
                elif 'latitude' in location and 'longitude' in location:
                    return {'lat': location['latitude'], 'lon': location['longitude']}
            
            logger.warning(f"좌표 추출 실패: 예상치 못한 타겟 구조 - {type(target)}")
            return None
            
        except (AttributeError, KeyError, TypeError) as e:
            logger.warning(f"좌표 추출 예외: {e}")
            return None

    def _convert_target_to_dict(self, target) -> Dict[str, Any]:
        try:
            # 이미 딕셔너리라면 그대로 반환
            if isinstance(target, dict):
                return target
                
            # Pydantic 모델인 경우 딕셔너리로 변환
            if hasattr(target, 'sequence'):
                coords = self._get_coords_from_target(target)
                if not coords:
                    logger.warning(f"타겟 {target.sequence}: 좌표 추출 실패")
                    return None
                    
                # area_name 안전하게 추출
                area_name = 'Unknown'
                if hasattr(target, 'location'):
                    if hasattr(target.location, 'area_name'):
                        area_name = target.location.area_name
                    elif isinstance(target.location, dict) and 'area_name' in target.location:
                        area_name = target.location['area_name']
                
                return {
                    'sequence': target.sequence,
                    'category': target.category,
                    'location': {
                        'area_name': area_name,
                        'coordinates': {'latitude': coords['lat'], 'longitude': coords['lon']}
                    }
                }
            
            logger.warning(f"예상치 못한 타겟 타입: {type(target)}")
            return target
            
        except Exception as e:
            logger.error(f"타겟 변환 실패: {e}")
            return None

    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        R = 6371000
        lat1_rad, lon1_rad, lat2_rad, lon2_rad = map(math.radians, [lat1, lon1, lat2, lon2])
        dlat, dlon = lat2_rad - lat1_rad, lon2_rad - lon1_rad
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c

    def _get_default_analysis(self, weather: str) -> Dict[str, Any]:
        config = self._get_weather_config(weather)
        return {
            'analysis_type': 'single_region',
            'clusters': [],
            'distance_limit': config['limit'],
            'analysis_summary': f'위치 분석 실패 - 기본 단일 지역 정책 적용 ({config["limit"]}m)'
        }

# 전역 인스턴스
location_analyzer = SmartLocationAnalyzer()
