from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class UserProfile(BaseModel):
    gender: Optional[str] = ""
    age: Optional[int] = None
    mbti: Optional[str] = ""
    address: Optional[str] = ""
    car_owned: Optional[bool] = None
    description: Optional[str] = ""
    relationship_stage: Optional[str] = ""
    general_preferences: Optional[List[str]] = []
    profile_image_url: Optional[str] = ""
    # 추가 데이트 정보 필드
    atmosphere: Optional[str] = ""
    budget: Optional[str] = ""
    time_slot: Optional[str] = ""
    duration: Optional[str] = ""  # 데이트 시간 (2시간, 3시간, 반나절 등)
    transportation: Optional[str] = ""
    place_count: Optional[int] = None

class LocationRequest(BaseModel):
    proximity_type: str = ""
    reference_areas: List[str] = []
    place_count: Optional[int] = None
    proximity_preference: Optional[str] = None
    transportation: str = ""

class CoursePlanning(BaseModel):
    optimization_goals: Optional[List[str]] = None
    route_constraints: Optional[Dict[str, Any]] = None
    sequence_optimization: Optional[Dict[str, Any]] = None

class MainAgentRequest(BaseModel):
    user_message: str
    session_id: Optional[str] = None
    user_profile: Optional[Dict[str, Any]] = None
    max_travel_time: int = 30
    course_planning: Optional[CoursePlanning] = None
    timestamp: Optional[str] = None

class NewSessionRequest(BaseModel):
    user_id: str
    initial_message: str
    user_profile: UserProfile

class SendMessageRequest(BaseModel):
    session_id: str
    message: str
    user_id: str
    user_profile: UserProfile