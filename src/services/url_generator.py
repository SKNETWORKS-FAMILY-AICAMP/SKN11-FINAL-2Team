"""
장소 URL 생성 서비스
각 장소에 대한 네이버맵, 구글맵, 카카오맵 URL을 생성합니다.
"""
import urllib.parse
from typing import Dict, Optional
from loguru import logger


class URLGenerator:
    """장소 URL 생성 서비스"""
    
    def __init__(self):
        """초기화"""
        logger.info("🔗 URL 생성 서비스 초기화")
    
    def generate_place_urls(
        self, 
        place_name: str, 
        latitude: float, 
        longitude: float,
        place_id: Optional[str] = None
    ) -> Dict[str, str]:
        """
        장소의 모든 URL을 생성합니다.
        
        Args:
            place_name: 장소 이름
            latitude: 위도
            longitude: 경도
            place_id: 장소 ID (선택사항)
            
        Returns:
            Dict[str, str]: 플랫폼별 URL 딕셔너리
        """
        urls = {}
        
        try:
            # 네이버 지도 URL
            urls["naver_map"] = self._generate_naver_map_url(place_name, latitude, longitude)
            
            # 구글 지도 URL
            urls["google_map"] = self._generate_google_map_url(place_name, latitude, longitude)
            
            # 카카오맵 URL
            urls["kakao_map"] = self._generate_kakao_map_url(place_name, latitude, longitude)
            
            # 장소 검색 URL (네이버 통합 검색)
            urls["naver_search"] = self._generate_naver_search_url(place_name)
            
            logger.debug(f"🔗 URL 생성 완료: {place_name}")
            
        except Exception as e:
            logger.error(f"❌ URL 생성 실패: {place_name}, 오류: {str(e)}")
            urls = self._get_fallback_urls(place_name, latitude, longitude)
        
        return urls
    
    def _generate_naver_map_url(self, place_name: str, lat: float, lng: float) -> str:
        """네이버 지도 URL 생성"""
        encoded_name = urllib.parse.quote(place_name)
        return f"https://map.naver.com/p/search/{encoded_name}?c={lng:.6f},{lat:.6f},15,0,0,0,dh"
    
    def _generate_google_map_url(self, place_name: str, lat: float, lng: float) -> str:
        """구글 지도 URL 생성"""
        encoded_name = urllib.parse.quote(place_name)
        return f"https://maps.google.com/maps?q={encoded_name}@{lat:.6f},{lng:.6f},15z"
    
    def _generate_kakao_map_url(self, place_name: str, lat: float, lng: float) -> str:
        """카카오맵 URL 생성"""
        encoded_name = urllib.parse.quote(place_name)
        return f"https://map.kakao.com/link/search/{encoded_name},{lat:.6f},{lng:.6f}"
    
    def _generate_naver_search_url(self, place_name: str) -> str:
        """네이버 통합 검색 URL 생성"""
        encoded_name = urllib.parse.quote(place_name)
        return f"https://search.naver.com/search.naver?query={encoded_name}"
    
    def _get_fallback_urls(self, place_name: str, lat: float, lng: float) -> Dict[str, str]:
        """오류 시 기본 URL 생성"""
        encoded_name = urllib.parse.quote(place_name)
        return {
            "naver_map": f"https://map.naver.com/p/search/{encoded_name}",
            "google_map": f"https://maps.google.com/maps?q={encoded_name}",
            "kakao_map": f"https://map.kakao.com/link/search/{encoded_name}",
            "naver_search": f"https://search.naver.com/search.naver?query={encoded_name}"
        }
    
    def generate_course_sharing_url(self, places: list, weather: str) -> str:
        """
        전체 코스 공유 URL 생성 (구글 마이맵 스타일)
        
        Args:
            places: 장소 리스트
            weather: 날씨 정보
            
        Returns:
            str: 코스 공유 URL
        """
        try:
            # 장소들의 좌표를 모아서 구글 마이맵 URL 생성
            waypoints = []
            for place in places:
                coords = place.get('coordinates', {})
                lat = coords.get('latitude', 0)
                lng = coords.get('longitude', 0)
                name = place.get('name', '')
                if lat and lng:
                    waypoints.append(f"{lat:.6f},{lng:.6f}")
            
            if waypoints:
                waypoints_str = "/".join(waypoints)
                return f"https://www.google.com/maps/dir/{waypoints_str}"
            else:
                return ""
                
        except Exception as e:
            logger.error(f"❌ 코스 공유 URL 생성 실패: {str(e)}")
            return ""