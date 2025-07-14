# 요청 데이터 모델
# - 메인 에이전트로부터 받는 입력 데이터 구조

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class LocationModel(BaseModel):
    """위치 정보 모델"""
    area_name: str
    coordinates: Dict[str, float]  # {"latitude": float, "longitude": float}

class SearchTargetModel(BaseModel):
    """검색 대상 모델"""
    sequence: int
    category: str
    location: LocationModel
    semantic_query: str

class DemographicsModel(BaseModel):
    """사용자 인구통계 정보"""
    age: int
    mbti: Optional[str] = None
    relationship_stage: str

class RequirementsModel(BaseModel):
    """사용자 요구사항"""
    budget_range: str
    time_preference: str
    party_size: int
    transportation: str

class UserContextModel(BaseModel):
    """사용자 컨텍스트"""
    demographics: DemographicsModel
    preferences: List[str]
    requirements: RequirementsModel

class RouteConstraintsModel(BaseModel):
    """경로 제약 조건"""
    max_travel_time_between: int
    total_course_duration: int
    flexibility: str

class SequenceOptimizationModel(BaseModel):
    """순서 최적화 설정"""
    allow_reordering: bool
    prioritize_given_sequence: bool

class CoursePlanningModel(BaseModel):
    """코스 계획 설정"""
    optimization_goals: List[str]
    route_constraints: RouteConstraintsModel
    sequence_optimization: SequenceOptimizationModel

class DateCourseRequestModel(BaseModel):
    """전체 요청 모델"""
    request_id: str
    timestamp: str
    search_targets: List[SearchTargetModel]
    user_context: UserContextModel
    course_planning: CoursePlanningModel
    
    class Config:
        """Pydantic 설정"""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
