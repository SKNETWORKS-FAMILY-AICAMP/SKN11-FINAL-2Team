# 메인 엔트리포인트
# - 전체 시스템 orchestration
# - 요청 수신 및 응답 생성

import asyncio
import time
import json
import sys
import os
from typing import Dict, Any, List
from loguru import logger

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.utils.data_validator import DataValidator
from src.utils.parallel_executor import ParallelExecutor
from src.core.weather_processor import WeatherProcessor
from src.models.request_models import DateCourseRequestModel
from src.models.response_models import DateCourseResponseModel, FailedResponseModel
from src.models.internal_models import InternalResponseModel

class DateCourseAgent:
    """데이트 코스 추천 서브 에이전트 메인 클래스"""
    
    def __init__(self):
        """초기화"""
        self.parallel_executor = ParallelExecutor()
        self.weather_processor = WeatherProcessor()
        self.data_validator = DataValidator()
    
    async def process_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        메인 에이전트로부터 받은 요청을 처리
        
        Args:
            request_data: 요청 데이터 (JSON)
            
        Returns:
            처리 결과 (JSON)
        """
        start_time = time.time()
        
        try:
            # 1. 입력 데이터 검증
            validated_data = self.data_validator.validate_request_data(request_data)
            request_model = DateCourseRequestModel(**validated_data)
            
            # 2. 병렬 처리: 맑을 때 & 비올 때 시나리오
            weather_results = await self.parallel_executor.execute_weather_scenarios_parallel(
                self.weather_processor._process_scenario(
                    weather="sunny",
                    search_targets=request_model.search_targets,
                    user_context=request_model.user_context.model_dump(),
                    course_planning=request_model.course_planning.model_dump()
                ),
                self.weather_processor._process_scenario(
                    weather="rainy",
                    search_targets=request_model.search_targets,
                    user_context=request_model.user_context.model_dump(),
                    course_planning=request_model.course_planning.model_dump()
                )
            )
            
            # 3. 결과 통합
            processing_time = time.time() - start_time
            internal_result = InternalResponseModel(
                request_id=request_model.request_id,
                sunny_result=weather_results['sunny'],
                rainy_result=weather_results['rainy'],
                total_processing_time=processing_time,
                success_count=self._count_successful_results(weather_results)
            )
            
            # 4. 최종 응답 생성
            final_response = self._create_final_response(internal_result)
            
            return final_response.model_dump()
            
        except Exception as e:
            # 예외 처리
            processing_time = time.time() - start_time
            error_response = FailedResponseModel(
                request_id=request_data.get('request_id', 'unknown'),
                processing_time=f"{processing_time:.1f}초",
                message=f"처리 중 오류가 발생했습니다: {str(e)}",
                suggestions=[
                    "요청 데이터 형식을 확인해주세요",
                    "네트워크 연결을 확인해주세요",
                    "잠시 후 다시 시도해주세요"
                ]
            )
            return error_response.model_dump()
    
    def _count_successful_results(self, weather_results: Dict[str, Any]) -> int:
        """성공한 날씨 시나리오 개수 계산"""
        success_count = 0
        
        if weather_results['sunny'] and weather_results['sunny'].status == 'success':
            success_count += 1
        if weather_results['rainy'] and weather_results['rainy'].status == 'success':
            success_count += 1
            
        return success_count
    
    def _create_final_response(self, internal_result: InternalResponseModel) -> DateCourseResponseModel:
        """내부 결과를 최종 응답 형태로 변환"""
        try:
            # 상태 결정
            if internal_result.is_complete_success():
                status = "success"
            elif internal_result.is_partial_success():
                status = "partial_success"
            else:
                status = "failed"
            
            # 제약 조건 정보 수집
            constraints_applied = {
                "sunny_weather": {
                    "attempt": internal_result.sunny_result.attempt,
                    "radius_used": internal_result.sunny_result.radius_used
                },
                "rainy_weather": {
                    "attempt": internal_result.rainy_result.attempt,
                    "radius_used": internal_result.rainy_result.radius_used
                }
            }
            
            # 결과 데이터 조직
            results = {
                "sunny_weather": self._format_weather_result(internal_result.sunny_result),
                "rainy_weather": self._format_weather_result(internal_result.rainy_result)
            }
            
            # 완화된 제약 조건 수집
            constraints_relaxed = []
            if internal_result.sunny_result.attempt in ["2차", "3차"]:
                if internal_result.sunny_result.attempt == "2차":
                    constraints_relaxed.append("검색 결과 수 확대")
                elif internal_result.sunny_result.attempt == "3차":
                    constraints_relaxed.append("검색 반경 확대")
            
            if internal_result.rainy_result.attempt in ["2차", "3차"]:
                if internal_result.rainy_result.attempt == "2차" and "검색 결과 수 확대" not in constraints_relaxed:
                    constraints_relaxed.append("검색 결과 수 확대")
                elif internal_result.rainy_result.attempt == "3차" and "검색 반경 확대" not in constraints_relaxed:
                    constraints_relaxed.append("검색 반경 확대")
            
            # 백업 코스 준비 (성공한 경우에만)
            backup_courses = {}
            if status in ["success", "partial_success"]:
                backup_courses = self._prepare_backup_courses(internal_result)
            
            # 최종 응답 생성
            response = DateCourseResponseModel(
                request_id=internal_result.request_id,
                processing_time=f"{internal_result.total_processing_time:.1f}초",
                status=status,
                constraints_applied=constraints_applied,
                results=results,
                backup_courses=backup_courses,
                constraints_relaxed=constraints_relaxed if constraints_relaxed else None
            )
            
            return response
            
        except Exception as e:
            # 변환 실패 시 기본 오류 응답 생성
            return FailedResponseModel(
                request_id=internal_result.request_id,
                processing_time=f"{internal_result.total_processing_time:.1f}초",
                message=f"결과 변환 중 오류가 발생했습니다: {str(e)}",
                suggestions=["잠시 후 다시 시도해보세요"]
            )
    
    def _format_weather_result(self, weather_result) -> List[Dict[str, Any]]:
        """날씨별 결과를 외부 형식으로 변환"""
        try:
            if weather_result.status != "success" or not weather_result.courses:
                return []
            
            formatted_courses = []
            for course in weather_result.courses:
                formatted_course = {
                    "course_id": course.course_id,
                    "places": [
                        {
                            "sequence": place.get("sequence", i + 1),
                            "place_info": {
                                "place_id": place.get("place_id", ""),
                                "name": place.get("place_name", place.get("name", "")),
                                "category": place.get("category", ""),
                                "coordinates": place.get("coordinates", {}),
                                "similarity_score": place.get("similarity_score", 0)
                            },
                            "description": place.get("description", "")
                        }
                        for i, place in enumerate(course.places)
                    ],
                    "travel_info": course.travel_info,
                    "total_distance_meters": course.total_distance_meters,
                    "recommendation_reason": course.recommendation_reason
                }
                formatted_courses.append(formatted_course)
            
            return formatted_courses
            
        except Exception as e:
            from loguru import logger
            logger.error(f"❗ 날씨 결과 변환 실패: {e}")
            return []
    
    def _prepare_backup_courses(self, internal_result: InternalResponseModel) -> Dict[str, Any]:
        """백업 코스 준비"""
        try:
            backup = {}
            
            # 성공한 날씨 시나리오에서 추가 코스 추출
            if internal_result.sunny_result.status == "success" and len(internal_result.sunny_result.courses) > 3:
                backup["sunny_additional"] = self._format_weather_result(
                    type('obj', (object,), {
                        'status': 'success',
                        'courses': internal_result.sunny_result.courses[3:6]  # 4-6번째 코스
                    })
                )
            
            if internal_result.rainy_result.status == "success" and len(internal_result.rainy_result.courses) > 3:
                backup["rainy_additional"] = self._format_weather_result(
                    type('obj', (object,), {
                        'status': 'success',
                        'courses': internal_result.rainy_result.courses[3:6]  # 4-6번째 코스
                    })
                )
            
            return backup
            
        except Exception as e:
            from loguru import logger
            logger.error(f"❗ 백업 코스 준비 실패: {e}")
            return {}
    
    async def health_check(self) -> Dict[str, str]:
        """헬스 체크"""
        return {
            "status": "healthy",
            "service": "date-course-agent",
            "version": "1.0.0"
        }

# FastAPI 서버로 실행할 경우
if __name__ == "__main__":
    import uvicorn
    from fastapi import FastAPI
    
    app = FastAPI(title="Date Course Recommendation Agent")
    agent = DateCourseAgent()
    
    @app.post("/recommend-course")
    async def recommend_course(request_data: Dict[str, Any]):
        """데이트 코스 추천 API"""
        return await agent.process_request(request_data)
    
    @app.get("/health")
    async def health_check():
        """헬스 체크 API"""
        return await agent.health_check()
    
    # 서버 실행
    uvicorn.run(app, host="0.0.0.0", port=8000)

# 직접 함수 호출로 사용할 경우
async def main():
    """테스트용 메인 함수"""
    agent = DateCourseAgent()
    
    # 테스트 데이터 (실제 사용 시에는 메인 에이전트로부터 받음)
    test_request = {
        "request_id": "test-001",
        "timestamp": "2025-06-30T15:30:00Z",
        "search_targets": [
            {
                "sequence": 1,
                "category": "음식점",
                "location": {
                    "area_name": "홍대",
                    "coordinates": {"latitude": 37.5519, "longitude": 126.9245}
                },
                "semantic_query": "홍대에서 커플이 가기 좋은 로맨틱한 파인다이닝 레스토랑"
            }
        ],
        "user_context": {
            "demographics": {"age": 28, "mbti": "ENFJ", "relationship_stage": "연인"},
            "preferences": ["로맨틱한 분위기", "저녁 데이트"],
            "requirements": {
                "budget_range": "커플 기준 15-20만원",
                "time_preference": "저녁",
                "party_size": 2,
                "transportation": "대중교통"
            }
        },
        "course_planning": {
            "optimization_goals": ["로맨틱한 저녁 데이트 경험 극대화"],
            "route_constraints": {
                "max_travel_time_between": 30,
                "total_course_duration": 300,
                "flexibility": "low"
            },
            "sequence_optimization": {
                "allow_reordering": False,
                "prioritize_given_sequence": True
            }
        }
    }
    
    result = await agent.process_request(test_request)
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(main())