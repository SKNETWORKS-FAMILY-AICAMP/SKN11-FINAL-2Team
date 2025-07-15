from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class IntentAnalysis(BaseModel):
    action: str  # "normal_flow", "exception_handling", "modification_request"
    field: Optional[str] = None
    confidence: float
    next_action: str
    context_understanding: Dict[str, Any]

class CategoryRecommendation(BaseModel):
    sequence: int
    category: str
    reason: str
    alternatives: List[str]

class SmartResponse(BaseModel):
    success: bool
    message: str
    recommendations: Optional[List[CategoryRecommendation]] = None
    next_stage: str
    requires_input: bool
    suggestions: List[str]
    retry_count: int = 0