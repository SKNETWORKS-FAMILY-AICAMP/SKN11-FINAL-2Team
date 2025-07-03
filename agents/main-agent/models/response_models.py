from pydantic import BaseModel
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