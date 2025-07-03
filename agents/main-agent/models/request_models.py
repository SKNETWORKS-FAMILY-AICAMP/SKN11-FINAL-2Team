from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class UserProfile(BaseModel):
    age: str = ""
    gender: str = ""
    mbti: str = ""
    address: str = ""
    relationship_stage: str = ""
    atmosphere: str = ""
    budget: str = ""
    time_slot: str = ""
    
    # 선택 사항들
    car_owned: Optional[bool] = None
    description: Optional[str] = None
    general_preferences: Optional[List[str]] = None
    place_count: Optional[int] = 3
    profile_image_url: Optional[str] = None

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