# 응답 데이터 모델
# - 메인 에이전트로 보내는 출력 데이터 구조

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from enum import Enum

class ProcessingStatus(str, Enum):
    """처리 상태"""
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"

class PlaceInfoModel(BaseModel):
    """장소 정보 모델"""
    sequence: int
    place_info: Dict[str, Any]
    description: str

class TravelSegmentModel(BaseModel):
    """이동 구간 정보"""
    from_place: str = Field(alias="from")
    to_place: str = Field(alias="to")
    distance_meters: int

class CourseModel(BaseModel):
    """개별 코스 모델"""
    course_id: str
    places: List[PlaceInfoModel]
    travel_info: List[TravelSegmentModel]
    total_distance_meters: int
    recommendation_reason: str

class WeatherResultsModel(BaseModel):
    """날씨별 결과"""
    sunny_weather: List[CourseModel]
    rainy_weather: List[CourseModel]

class ConstraintsAppliedModel(BaseModel):
    """적용된 제약 조건"""
    sunny_weather: Dict[str, Any]  # {"attempt": str, "radius_used": int}
    rainy_weather: Dict[str, Any]  # {"attempt": str, "radius_used": int}

class DateCourseResponseModel(BaseModel):
    """전체 응답 모델"""
    request_id: str
    processing_time: str
    status: ProcessingStatus
    constraints_applied: ConstraintsAppliedModel
    results: WeatherResultsModel
    backup_courses: Optional[Dict[str, Any]] = None
    constraints_relaxed: Optional[List[str]] = None
    message: Optional[str] = None  # 실패 시 메시지
    suggestions: Optional[List[str]] = None  # 실패 시 제안사항
    
    class Config:
        """Pydantic 설정"""
        validate_by_name = True

class FailedResponseModel(BaseModel):
    """실패 응답 모델"""
    request_id: str
    processing_time: str
    status: ProcessingStatus = ProcessingStatus.FAILED
    message: str
    suggestions: List[str]

class PartialSuccessResponseModel(BaseModel):
    """부분 성공 응답 모델"""
    request_id: str
    processing_time: str
    status: ProcessingStatus = ProcessingStatus.PARTIAL_SUCCESS
    message: str
    constraints_applied: ConstraintsAppliedModel
    results: WeatherResultsModel
    constraints_relaxed: Optional[List[str]] = None