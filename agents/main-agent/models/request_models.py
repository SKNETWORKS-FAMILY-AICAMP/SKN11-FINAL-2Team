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
    transportation: Optional[str] = ""
    place_count: Optional[int] = 3

class LocationRequest(BaseModel):
    proximity_type: str = ""
    reference_areas: List[str] = []
    place_count: int = 3
    proximity_preference: Optional[str] = None
    transportation: str = ""

class CoursePlanning(BaseModel):
    optimization_goals: Optional[List[str]] = None
    route_constraints: Optional[Dict[str, Any]] = None
    sequence_optimization: Optional[Dict[str, Any]] = None

class MainAgentRequest(BaseModel):
    user_message: str
    session_id: Optional[str] = None
    max_travel_time: int = 30
    course_planning: Optional[CoursePlanning] = None

class NewSessionRequest(BaseModel):
    user_id: int
    initial_message: str
    user_profile: UserProfile

class SendMessageRequest(BaseModel):
    session_id: str
    message: str
    user_id: int
    user_profile: UserProfile