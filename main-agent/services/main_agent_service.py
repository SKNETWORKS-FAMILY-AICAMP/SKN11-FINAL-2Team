from langchain.memory import ConversationBufferMemory
from langchain_openai import ChatOpenAI
import os
import uuid
import json
from typing import Optional, Dict, Any

from ..core.profile_extractor import (
    extract_profile_from_llm, 
    llm_correct_field, 
    REQUIRED_KEYS
)
from ..core.location_processor import extract_location_request_from_llm
from ..core.agent_builders import (
    build_place_agent_json, 
    build_rag_agent_json
)
from ..models.request_models import MainAgentRequest, UserProfile, LocationRequest
from ..models.response_models import MainAgentResponse

class MainAgentService:
    def __init__(self, openai_api_key: Optional[str] = None):
        self.openai_api_key = openai_api_key or os.environ.get("OPENAI_API_KEY")
        self.llm = None
        if self.openai_api_key:
            self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, openai_api_key=self.openai_api_key)
        self.memory_sessions: Dict[str, ConversationBufferMemory] = {}
    
    def get_or_create_memory(self, session_id: str) -> ConversationBufferMemory:
        """세션별 메모리 관리"""
        if session_id not in self.memory_sessions:
            self.memory_sessions[session_id] = ConversationBufferMemory()
        return self.memory_sessions[session_id]
    
    def extract_and_validate_profile(self, user_message: str, session_id: str) -> UserProfile:
        """사용자 메시지에서 프로필 추출 및 검증"""
        if not self.llm:
            # OpenAI API 키가 없는 경우 기본값 반환
            return UserProfile()
        
        # LLM으로 프로필 추출
        extracted = extract_profile_from_llm(self.llm, user_message)
        
        # 필수 키들로 프로필 구성
        profile_data = {}
        for k in REQUIRED_KEYS:
            profile_data[k] = extracted.get(k, "")
        
        # 검증 및 교정 (필요시)
        for k in REQUIRED_KEYS:
            if k == "address":
                continue
            if profile_data[k]:
                corrected = llm_correct_field(self.llm, k, profile_data[k])
                if corrected:
                    profile_data[k] = corrected
        
        return UserProfile(**profile_data)
    
    def extract_location_request(self, user_message: str, address_hint: Optional[str] = None) -> LocationRequest:
        """위치 요청 정보 추출"""
        if not self.llm:
            # 기본값 반환
            return LocationRequest(reference_areas=[address_hint] if address_hint else [])
        
        location_data = extract_location_request_from_llm(self.llm, user_message, address_hint)
        return LocationRequest(**location_data)
    
    def build_agent_requests(self, profile: UserProfile, location_request: LocationRequest, max_travel_time: int = 30) -> tuple:
        """Place Agent와 RAG Agent 요청 JSON 생성"""
        # Place Agent 요청
        place_json = build_place_agent_json(
            profile.dict(), 
            location_request.dict(), 
            max_travel_time
        )
        
        # RAG Agent 요청 (샘플 응답 사용)
        rag_json = None
        sample_place_path = os.path.join(os.path.dirname(__file__), "../sample_place_agent_response.json")
        if os.path.exists(sample_place_path) and self.openai_api_key:
            with open(sample_place_path, "r", encoding="utf-8") as f:
                place_response = json.load(f)
            rag_json = build_rag_agent_json(
                place_response, 
                profile.dict(), 
                location_request.dict(),
                self.openai_api_key
            )
        
        return place_json, rag_json
    
    def process_request(self, request: MainAgentRequest) -> MainAgentResponse:
        """메인 요청 처리"""
        try:
            session_id = request.session_id or str(uuid.uuid4())
            memory = self.get_or_create_memory(session_id)
            
            # 대화 기록 저장
            memory.save_context(
                {"input": "사용자 요청"}, 
                {"output": request.user_message}
            )
            
            # 프로필 추출
            profile = self.extract_and_validate_profile(request.user_message, session_id)
            
            # 위치 정보 추출
            location_request = self.extract_location_request(
                request.user_message, 
                profile.address if profile.address else None
            )
            
            # address가 누락된 경우 location_request에서 보완
            if not profile.address and location_request.reference_areas:
                profile.address = location_request.reference_areas[0]
            
            # Agent 요청 생성
            place_agent_request, rag_agent_request = self.build_agent_requests(
                profile, 
                location_request, 
                request.max_travel_time
            )
            
            return MainAgentResponse(
                success=True,
                session_id=session_id,
                profile=profile,
                location_request=location_request,
                place_agent_request=place_agent_request,
                rag_agent_request=rag_agent_request,
                message="요청 처리 완료"
            )
            
        except Exception as e:
            return MainAgentResponse(
                success=False,
                session_id=request.session_id or str(uuid.uuid4()),
                profile=UserProfile(),
                location_request=LocationRequest(),
                error=str(e)
            )
    
    def get_session_memory(self, session_id: str) -> Optional[str]:
        """세션 메모리 내용 반환"""
        if session_id in self.memory_sessions:
            return self.memory_sessions[session_id].buffer
        return None
    
    def clear_session(self, session_id: str) -> bool:
        """세션 메모리 삭제"""
        if session_id in self.memory_sessions:
            del self.memory_sessions[session_id]
            return True
        return False