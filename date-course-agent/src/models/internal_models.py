# 내부 처리용 데이터 모델
# - 시스템 내부에서 사용하는 중간 데이터 구조

from pydantic import BaseModel
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum

class WeatherType(str, Enum):
    """날씨 타입"""
    SUNNY = "sunny"
    RAINY = "rainy"

class SearchAttemptType(str, Enum):
    """검색 시도 타입"""
    FIRST = "1차"
    SECOND = "2차"
    THIRD = "3차"

class PlaceModel(BaseModel):
    """벡터 DB에서 가져온 장소 정보"""
    place_id: str
    place_name: str
    latitude: float
    longitude: float
    description: str
    category: str
    similarity_score: Optional[float] = None

class SearchResultModel(BaseModel):
    """검색 결과 모델"""
    search_target_sequence: int
    places: List[PlaceModel]
    attempt_type: SearchAttemptType
    radius_used: int

class VectorSearchResult(BaseModel):
    """벡터 검색 전체 결과"""
    status: str  # "success", "failed"
    attempt: str  # "1차", "2차", "3차"
    radius_used: int
    places: List[List[Dict]] = []  # 각 search_target별 장소 리스트
    total_found: int = 0
    radius_expanded: bool = False
    error_message: Optional[str] = None

class CourseCombination(BaseModel):
    """코스 조합 모델"""
    combination_id: str
    course_sequence: List[Dict[str, Any]]
    travel_distances: List[Dict[str, Any]]
    total_distance_meters: int
    average_similarity_score: float = 0.0

class SelectedCourse(BaseModel):
    """GPT가 선택한 코스"""
    course_id: str
    places: List[Dict[str, Any]]
    travel_info: List[Dict[str, Any]]
    total_distance_meters: int
    recommendation_reason: str
    average_similarity_score: float = 0.0

class WeatherScenarioResult(BaseModel):
    """날씨 시나리오 처리 결과"""
    weather: str  # "sunny" or "rainy"
    status: str  # "success", "failed", "no_results"
    attempt: str  # "1차", "2차", "3차", "none"
    radius_used: int
    courses: List[SelectedCourse] = []
    total_combinations: int = 0
    category_conversions: List[Dict[str, Any]] = []  # 비올 때 카테고리 변환 내역
    error_message: Optional[str] = None

class EmbeddingResultModel(BaseModel):
    """임베딩 결과 모델"""
    sequence: int
    semantic_query: str
    embedding_vector: List[float]

class ProcessingContextModel(BaseModel):
    """처리 컨텍스트 모델"""
    weather_type: str
    search_radius: int
    embeddings: List[EmbeddingResultModel]
    search_attempts: List[str]
    constraints_relaxed: List[str] = []

class InternalResponseModel(BaseModel):
    """내부 처리 응답 모델"""
    request_id: str
    sunny_result: WeatherScenarioResult
    rainy_result: WeatherScenarioResult
    total_processing_time: float
    success_count: int  # 성공한 날씨 시나리오 수
    
    def is_complete_success(self) -> bool:
        """완전 성공 여부"""
        return self.success_count == 2
    
    def is_partial_success(self) -> bool:
        """부분 성공 여부"""
        return self.success_count == 1
    
    def is_failed(self) -> bool:
        """완전 실패 여부"""
        return self.success_count == 0

# 거리 계산 관련 모델
class LocationModel(BaseModel):
    """위치 정보 모델"""
    latitude: float
    longitude: float
    area_name: Optional[str] = None

class DistanceInfo(BaseModel):
    """거리 정보 모델"""
    from_place: str
    to_place: str
    distance_meters: float
    travel_time_minutes: Optional[float] = None

class RouteOptimizationResult(BaseModel):
    """경로 최적화 결과"""
    optimized_sequence: List[PlaceModel]
    total_distance: float
    total_travel_time: float
    distance_breakdown: List[DistanceInfo]

# GPT 선택 관련 모델
class GPTSelectionInput(BaseModel):
    """GPT 선택 입력 모델"""
    weather_condition: str
    user_context: Dict[str, Any]
    search_attempt: str
    course_combinations: List[CourseCombination]

class GPTSelectionResult(BaseModel):
    """GPT 선택 결과 모델"""
    selected_courses: List[SelectedCourse]
    is_appropriate: bool
    selection_reasoning: str

# 재시도 로직 관련 모델
class FailureReason(BaseModel):
    """실패 원인 모델"""
    type: str  # "system_error", "no_suitable_results", "partial_failure", "unknown"
    message: str
    suggestions: List[str] = []

class RetryResult(BaseModel):
    """재시도 결과 모델"""
    success: bool
    final_attempt: int
    final_result: Any = None
    attempts_history: List[Dict[str, Any]] = []
    constraints_relaxed: List[str] = []
    failure_reason: Optional[FailureReason] = None

# 오류 처리 모델
class ProcessingError(BaseModel):
    """처리 오류 모델"""
    error_type: str
    error_message: str
    occurred_at: str  # 발생 단계
    recovery_attempted: bool = False

# 품질 평가 모델
class QualityMetrics(BaseModel):
    """품질 평가 지표"""
    similarity_score: float
    distance_efficiency: float
    category_diversity: float
    user_preference_match: float
    overall_score: float

class CourseEvaluation(BaseModel):
    """코스 평가 결과"""
    course_id: str
    quality_metrics: QualityMetrics
    strengths: List[str]
    weaknesses: List[str]
    improvement_suggestions: List[str]

# 성능 모니터링 모델
class PerformanceMetrics(BaseModel):
    """성능 지표"""
    total_processing_time: float
    embedding_generation_time: float
    vector_search_time: float
    gpt_selection_time: float
    parallel_efficiency: float
    
class SystemStatus(BaseModel):
    """시스템 상태"""
    service_name: str
    status: str  # "healthy", "degraded", "error"
    last_check: str
    response_time: float
    error_rate: float

# 통계 및 분석 모델
class UsageStatistics(BaseModel):
    """사용 통계"""
    total_requests: int
    successful_requests: int
    failed_requests: int
    average_processing_time: float
    popular_categories: List[str]
    popular_areas: List[str]

class TrendAnalysis(BaseModel):
    """트렌드 분석"""
    time_period: str
    request_volume_trend: str  # "increasing", "decreasing", "stable"
    popular_preferences: List[str]
    common_failure_reasons: List[str]
    performance_trend: str
