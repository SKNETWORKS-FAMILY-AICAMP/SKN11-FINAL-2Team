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
from config.settings import settings

class PlaceAgent:
    """Place Agent 메인 클래스"""
    
    def __init__(self):
        """초기화"""
        self.location_analyzer = LocationAnalyzer()
        self.coordinates_service = CoordinatesService()
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
            
            # 2. LLM 기반 지역 분석
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
        "timestamp": datetime.datetime.now().isoformat(),
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