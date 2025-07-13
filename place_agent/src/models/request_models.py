# Place Agent 요청 모델들
# - 메인 에이전트로부터 받는 요청 데이터 구조

from pydantic import BaseModel
from typing import List, Optional

class LocationRequest(BaseModel):
    """위치 요청 모델"""
    proximity_type: str  # "exact", "near", "between", "multi"
    reference_areas: List[str]  # 장소명 리스트
    place_count: Optional[int] = 3  # 추천받을 장소 개수 - 문자열도 허용
    proximity_preference: Optional[str] = None  # "middle", "near", null
    transportation: Optional[str] = None  # "도보", "차", "지하철", null
    location_clustering: Optional[dict] = None  # 장소 배치 전략 정보
    ai_location_instructions: Optional[dict] = None  # AI를 위한 명확한 지시사항
    
    def __init__(self, **data):
        # place_count가 문자열인 경우 정수로 변환
        if 'place_count' in data and isinstance(data['place_count'], str):
            try:
                data['place_count'] = int(data['place_count'])
            except (ValueError, TypeError):
                data['place_count'] = 3
        super().__init__(**data)

class Demographics(BaseModel):
    """사용자 인구통계 정보"""
    age: int
    mbti: str
    relationship_stage: str  # "연인", "썸", "친구"

class Requirements(BaseModel):
    """사용자 요구사항"""
    budget_level: Optional[str] = None  # "low", "medium", "high", null
    time_preference: str  # "오전", "오후", "저녁", "밤"
    transportation: Optional[str] = None  # "도보", "차", "지하철", null
    max_travel_time: Optional[int] = None

class UserContext(BaseModel):
    """사용자 컨텍스트 정보"""
    demographics: Demographics
    preferences: List[str]  # ["조용한 분위기", "트렌디한"] - 단순 리스트
    requirements: Requirements

class PlaceAgentRequest(BaseModel):
    """Place Agent 메인 요청 모델"""
    request_id: str
    timestamp: str
    request_type: str = "proximity_based"  # 현재는 고정
    location_request: LocationRequest
    user_context: UserContext
    selected_categories: Optional[List[str]] = None  # ["카페", "레스토랑"]