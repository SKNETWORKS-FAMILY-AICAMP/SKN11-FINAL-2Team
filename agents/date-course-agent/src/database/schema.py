# 데이터 스키마 정의
# - Qdrant 컬렉션 스키마
# - 입출력 데이터 구조

from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class PlaceSchema(BaseModel):
    """장소 정보 스키마"""
    place_id: str
    place_name: str
    latitude: float
    longitude: float
    description: str
    category: str
    embedding_vector: List[float]

class SearchTargetSchema(BaseModel):
    """검색 대상 스키마"""
    sequence: int
    category: str
    location: Dict[str, Any]
    semantic_query: str

class UserContextSchema(BaseModel):
    """사용자 컨텍스트 스키마"""
    demographics: Dict[str, Any]
    preferences: List[str]
    requirements: Dict[str, Any]

class RequestSchema(BaseModel):
    """전체 요청 스키마"""
    request_id: str
    timestamp: str
    search_targets: List[SearchTargetSchema]
    user_context: UserContextSchema
    course_planning: Dict[str, Any]
