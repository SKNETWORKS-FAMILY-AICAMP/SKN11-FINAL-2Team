# Place Agent 응답 모델들
# - 메인 에이전트로 반환하는 응답 데이터 구조

from pydantic import BaseModel
from typing import List, Optional

class Coordinates(BaseModel):
    """좌표 모델"""
    latitude: float
    longitude: float

class LocationResponse(BaseModel):
    """위치 응답 모델"""
    sequence: int
    area_name: str
    coordinates: Coordinates
    reason: str  # 자연스러운 문장 형태

class PlaceAgentResponse(BaseModel):
    """Place Agent 메인 응답 모델"""
    request_id: str
    success: bool
    locations: List[LocationResponse]
    error_message: Optional[str] = None