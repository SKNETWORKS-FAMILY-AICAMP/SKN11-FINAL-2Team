from langchain.memory import ConversationBufferMemory
from langchain_openai import ChatOpenAI
import os
import uuid
import json
from typing import Optional, Dict, Any, Tuple

from core.profile_extractor import (
    extract_profile_from_llm, 
    rule_based_gender_relationship, 
    llm_correct_field, 
    REQUIRED_KEYS
)
from core.location_processor import extract_location_request_from_llm
from core.agent_builders import (
    build_place_agent_json, 
    build_rag_agent_json
)
from models.request_models import MainAgentRequest, UserProfile, LocationRequest
from models.response_models import MainAgentResponse

# 필수 정보와 질문 매핑 (확장)
REQUIRED_FIELDS_AND_QUESTIONS = [
    ("age", "나이를 알려주세요. (예: 25살, 30대 등)"),
    ("gender", "성별을 알려주세요. (예: 남, 여)"),
    ("mbti", "MBTI 유형을 알려주세요. (예: ENFP, INFP 등)"),
    ("address", "어느 지역에서 데이트를 원하시나요? (예: 홍대, 강남 등)"),
    ("relationship_stage", "상대와의 관계를 알려주세요. (예: 연인, 썸, 친구 등)"),
    ("atmosphere", "어떤 분위기를 원하시나요? (예: 아늑한, 활기찬 등)"),
    ("budget", "예산은 얼마 정도 생각하시나요? (예: 5만원, 10만원 등)"),
    ("time_slot", "몇 시/시간대에 데이트를 원하시나요? (예: 오전, 오후, 저녁, 밤 등)"),
    ("place_type", "어떤 종류의 장소를 선호하시나요? (예: 맛집, 카페, 문화생활 등)")
]
REQUIRED_FIELDS = [f for f, _ in REQUIRED_FIELDS_AND_QUESTIONS]

OPTIONAL_FIELDS = [
    ("car_owned", "차량 소유 여부 (예/아니오): "),
    ("description", "자기소개를 입력해주세요: "),
    ("general_preferences", "선호하는 것(쉼표로 구분, 예: 조용한 곳,야외,디저트): "),
    ("place_count", "코스에 원하는 장소 개수(숫자, 예: 3, 미입력시 3): "),
    ("profile_image_url", "프로필 이미지 URL(선택): ")
]
FIELD_QUESTION_DICT = {
    "age": "나이를 입력해주세요 (숫자): ",
    "gender": "성별을 입력해주세요 (남/여): ",
    "mbti": "MBTI를 입력해주세요 (예: ENFP): ",
    "address": "데이트할 장소(지역/동네)를 입력해주세요: ",
    "relationship_stage": "상대방과의 관계를 입력해주세요 (연인/썸/친구 등): ",
    "atmosphere": "장소의 분위기를 입력해주세요 (예: 로맨틱, 조용한, 트렌디한, 활기찬 등): ",
    "budget": "예산을 입력해주세요 (예: 2만~5만원, 10만원 이하 등): ",
    "time_slot": "데이트 시간대를 입력해주세요 (예: 오전, 오후, 저녁, 밤 등): ",
    "place_type": "어떤 종류의 장소를 선호하시나요? (예: 맛집, 카페, 문화생활 등)"
}

# 세션별 정보 누적용 임시 메모리 (실제 서비스에서는 DB/Redis 권장)
SESSION_INFO: Dict[str, Dict[str, Any]] = {}

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
            
            # 세션별 정보 누적 및 상태 플래그
            session_info = SESSION_INFO.get(session_id, {})
            needs_optional_info_ask = session_info.get("_needs_optional_info_ask", False)
            optional_info_pending = session_info.get("_optional_info_pending", False)
            optional_idx = session_info.get("_optional_idx", 0)
            recommend_ready = session_info.get("_recommend_ready", False)

            # 1. LLM 기반 필수 정보 추출 및 규칙 기반 보정
            extracted = extract_profile_from_llm(self.llm, request.user_message)
            extracted = rule_based_gender_relationship(request.user_message, extracted)
            for k in REQUIRED_KEYS:
                if not session_info.get(k) and extracted.get(k):
                    session_info[k] = extracted[k]

            # 2. 위치 정보 추출 및 address 보완
            location_request = extract_location_request_from_llm(self.llm, request.user_message, address_hint=session_info.get("address"))
            if not session_info.get("address") and location_request.get("reference_areas"):
                session_info["address"] = location_request["reference_areas"][0]

            # 3. 누락 필드 체크 및 질문
            missing_fields = [k for k in REQUIRED_KEYS if not session_info.get(k)]
            if missing_fields:
                next_field = missing_fields[0]
                question = FIELD_QUESTION_DICT[next_field]
                SESSION_INFO[session_id] = session_info
                return MainAgentResponse(
                    success=True,
                    session_id=session_id,
                    profile=UserProfile(**session_info),
                    location_request=LocationRequest(**location_request),
                    message=question,
                    needs_recommendation=False,
                    suggestions=missing_fields
                )

            # 4. (선택) 부가 정보 입력 의사 질문
            if not needs_optional_info_ask and OPTIONAL_FIELDS:
                session_info["_needs_optional_info_ask"] = True
                SESSION_INFO[session_id] = session_info
                return MainAgentResponse(
                    success=True,
                    session_id=session_id,
                    profile=UserProfile(**session_info),
                    location_request=LocationRequest(**location_request),
                    message="추가 정보(차량, 자기소개, 선호 등)를 입력하시겠습니까? (예/아니오)",
                    needs_recommendation=False,
                    suggestions=[]
                )

            # 5. 부가 정보 입력 분기
            if needs_optional_info_ask and not optional_info_pending:
                user_reply = request.user_message.strip().lower()
                if user_reply in ["예", "yes", "y"]:
                    session_info["_optional_info_pending"] = True
                    session_info["_optional_idx"] = 0
                    SESSION_INFO[session_id] = session_info
                    key, question = OPTIONAL_FIELDS[0]
                    return MainAgentResponse(
                        success=True,
                        session_id=session_id,
                        profile=UserProfile(**session_info),
                        location_request=LocationRequest(**location_request),
                        message=question,
                        needs_recommendation=False,
                        suggestions=[]
                    )
                elif user_reply in ["아니오", "no", "n"]:
                    session_info["_optional_info_pending"] = False
                    session_info["_optional_idx"] = 0
                    SESSION_INFO[session_id] = session_info
                else:
                    SESSION_INFO[session_id] = session_info
                    return MainAgentResponse(
                        success=True,
                        session_id=session_id,
                        profile=UserProfile(**session_info),
                        location_request=LocationRequest(**location_request),
                        message="'예' 또는 '아니오'로 답변해 주세요. 추가 정보(차량, 자기소개, 선호 등)를 입력하시겠습니까? (예/아니오)",
                        needs_recommendation=False,
                        suggestions=[]
                    )

            # 6. 부가 정보 실제 입력
            if optional_info_pending:
                idx = session_info.get("_optional_idx", 0)
                if idx < len(OPTIONAL_FIELDS):
                    key, question = OPTIONAL_FIELDS[idx]
                    answer = request.user_message.strip()
                    if key == "general_preferences":
                        session_info[key] = [x.strip() for x in answer.split(",") if x.strip()]
                    elif key == "car_owned":
                        session_info[key] = answer in ["예", "yes", "Yes", "Y", "y", "true", "True"]
                    elif key == "place_count":
                        session_info[key] = int(answer) if answer.isdigit() else 3
                    else:
                        session_info[key] = answer
                    session_info["_optional_idx"] = idx + 1
                    SESSION_INFO[session_id] = session_info
                    if idx + 1 < len(OPTIONAL_FIELDS):
                        next_key, next_question = OPTIONAL_FIELDS[idx + 1]
                        return MainAgentResponse(
                            success=True,
                            session_id=session_id,
                            profile=UserProfile(**session_info),
                            location_request=LocationRequest(**location_request),
                            message=next_question,
                            needs_recommendation=False,
                            suggestions=[]
                        )
                    else:
                        session_info["_optional_info_pending"] = False
                        session_info["_optional_idx"] = 0
                        SESSION_INFO[session_id] = session_info

            # 7. 추천 시작 여부 질문
            if not recommend_ready:
                session_info["_recommend_ready"] = True
                SESSION_INFO[session_id] = session_info
                return MainAgentResponse(
                    success=True,
                    session_id=session_id,
                    profile=UserProfile(**session_info),
                    location_request=LocationRequest(**location_request),
                    message="이제 추천을 시작할까요? (예/아니오)",
                    needs_recommendation=False,
                    suggestions=[]
                )
            else:
                user_reply = request.user_message.strip().lower()
                if user_reply in ["예", "yes", "y"]:
                    profile = UserProfile(**session_info)
                    place_agent_request, rag_agent_request = self.build_agent_requests(
                        profile, LocationRequest(**location_request), request.max_travel_time
                    )
                    return MainAgentResponse(
                        success=True,
                        session_id=session_id,
                        profile=profile,
                        location_request=LocationRequest(**location_request),
                        place_agent_request=place_agent_request,
                        rag_agent_request=rag_agent_request,
                        message="추천이 완료되었습니다!",
                        needs_recommendation=True,
                        suggestions=[]
                    )
                elif user_reply in ["아니오", "no", "n"]:
                    session_info["_recommend_ready"] = False
                    SESSION_INFO[session_id] = session_info
                    return MainAgentResponse(
                        success=True,
                        session_id=session_id,
                        profile=UserProfile(**session_info),
                        location_request=LocationRequest(**location_request),
                        message="추천을 원하실 때 '예'라고 입력해 주세요.",
                        needs_recommendation=False,
                        suggestions=[]
                    )
                else:
                    return MainAgentResponse(
                        success=True,
                        session_id=session_id,
                        profile=UserProfile(**session_info),
                        location_request=LocationRequest(**location_request),
                        message="'예' 또는 '아니오'로 답변해 주세요. 이제 추천을 시작할까요? (예/아니오)",
                        needs_recommendation=False,
                        suggestions=[]
                    )
        except Exception as e:
            return MainAgentResponse(
                success=False,
                session_id=request.session_id or str(uuid.uuid4()),
                profile=UserProfile(),
                location_request=LocationRequest(),
                error=str(e),
                needs_recommendation=False,
                suggestions=REQUIRED_KEYS
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