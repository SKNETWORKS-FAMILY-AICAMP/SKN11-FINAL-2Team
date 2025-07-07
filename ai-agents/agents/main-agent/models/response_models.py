from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from .request_models import UserProfile, LocationRequest

class PlaceAgentResponse(BaseModel):
    request_id: str
    timestamp: str
    request_type: str
    location_request: Dict[str, Any]
    user_context: Dict[str, Any]
    selected_categories: List[str]

class RagAgentResponse(BaseModel):
    request_id: str
    timestamp: str
    search_targets: List[Dict[str, Any]]
    user_context: Dict[str, Any]
    course_planning: Dict[str, Any]

class MainAgentResponse(BaseModel):
    success: bool
    session_id: str
    profile: UserProfile
    location_request: LocationRequest
    place_agent_request: Optional[PlaceAgentResponse] = None
    rag_agent_request: Optional[RagAgentResponse] = None
    message: Optional[str] = None
    error: Optional[str] = None
    needs_recommendation: Optional[bool] = None
    suggestions: Optional[List[str]] = None
    save_profile: Optional[bool] = None

class Coordinates(BaseModel):
    latitude: float
    longitude: float

class PlaceInfo(BaseModel):
    place_id: str
    name: str
    category: str
    coordinates: Coordinates
    similarity_score: Optional[float]

class PlaceStep(BaseModel):
    sequence: int
    place_info: PlaceInfo
    description: Optional[str]

class TravelInfo(BaseModel):
    from_: str = Field(..., alias="from")
    to: str
    distance_meters: int

class WeatherCourse(BaseModel):
    course_id: str
    places: List[PlaceStep]
    travel_info: List[TravelInfo]
    total_distance_meters: int
    recommendation_reason: Optional[str]

class CourseData(BaseModel):
    course_id: str
    sunny_weather: Optional[List[WeatherCourse]]
    rainy_weather: Optional[List[WeatherCourse]]
    total_duration: Optional[int]
    total_cost: Optional[int]
    weather_adaptive: Optional[bool]

class ResponseMessage(BaseModel):
    message: str
    message_type: str
    quick_replies: Optional[List[str]]
    processing_time: Optional[float]
    course_data: Optional[CourseData]

class SessionInfo(BaseModel):
    session_title: str
    session_status: str
    created_at: Optional[str]
    expires_at: Optional[str]
    last_activity_at: Optional[str]
    message_count: Optional[int]

class NewSessionResponse(BaseModel):
    success: bool
    session_id: str
    response: ResponseMessage
    session_info: SessionInfo

class SendMessageResponse(BaseModel):
    success: bool
    session_id: str
    response: ResponseMessage
    session_info: SessionInfo