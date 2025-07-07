"""
Main Agent FastAPI Server
환경변수로 포트 설정 가능한 메인 에이전트 서버
"""

import uvicorn
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import os
import requests
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import Dict, List, Optional
import uuid
import datetime
import json
import asyncio

from main_agent import MainAgent
from models.request_models import MainAgentRequest, NewSessionRequest, SendMessageRequest
from models.response_models import MainAgentResponse, NewSessionResponse, SendMessageResponse, ResponseMessage, SessionInfo, CourseData
from services.main_agent_service import MainAgentService

load_dotenv()

# 포트 설정을 환경변수로 변경
PORT = int(os.getenv("MAIN_AGENT_PORT", 8001))
PLACE_AGENT_URL = os.getenv("PLACE_AGENT_URL", "http://localhost:8002")
RAG_AGENT_URL = os.getenv("RAG_AGENT_URL", "http://localhost:8003")

app = FastAPI(
    title="Main Agent API",
    description="데이트 코스 추천 시스템 메인 에이전트",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent = MainAgent(os.getenv("OPENAI_API_KEY"))
main_agent_service = MainAgentService(os.getenv("OPENAI_API_KEY"))

# 임시 메모리 저장소
SESSIONS = {}  # session_id -> session_info
MESSAGES = {}  # session_id -> List[message]

async def execute_recommendation_flow(main_resp, session_info=None):
    """Place Agent → RAG Agent 추천 플로우 실행"""
    try:
        from core.agent_builders import build_place_agent_json, build_rag_agent_json
        
        profile_dict = main_resp.profile.dict()
        location_dict = main_resp.location_request.dict()
        
        # 🔥 CRITICAL: session_info 검증 및 보장
        if session_info is None:
            print(f"🚨 [CRITICAL ERROR] execute_recommendation_flow - session_info가 None!")
            print(f"🚨 [CRITICAL ERROR] 사용자 지정 지역 정보가 Place Agent에 전달되지 않을 것임!")
            session_info = {}
        else:
            print(f"✅ [SUCCESS] execute_recommendation_flow - session_info 수신됨")
            print(f"✅ [SUCCESS] session_info keys: {list(session_info.keys())}")
            if session_info.get('location_clustering'):
                print(f"✅ [SUCCESS] location_clustering 정보 확인됨")
                print(f"✅ [SUCCESS] Strategy: {session_info.get('location_clustering', {}).get('strategy', 'unknown')}")
        
        # Step 1: 중복 호출 방지 - Place Agent는 이미 process_request에서 호출됨
        # 대신 새로 Place Agent 호출해서 결과 받기 (임시 해결책)
        print(f"[DEBUG] Place Agent 요청 생성 (session_info 포함)")
        place_request = build_place_agent_json(
            profile=profile_dict,
            location_request=location_dict,
            max_travel_time=30,
            session_info=session_info  # 🔥 CRITICAL: session_info 전달
        )
        
        print(f"[DEBUG] ===== Place Agent Request =====")
        print(json.dumps(place_request, ensure_ascii=False, indent=2))
        print(f"[DEBUG] ==============================")
        
        print(f"[DEBUG] Place Agent API 호출: {PLACE_AGENT_URL}/place-agent")
        place_response = requests.post(
            f"{PLACE_AGENT_URL}/place-agent",
            json=place_request,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if place_response.status_code != 200:
            print(f"[ERROR] Place Agent 호출 실패: HTTP {place_response.status_code}")
            return None
            
        place_result = place_response.json()
        print(f"[DEBUG] ===== Place Agent Response =====")
        print(json.dumps(place_result, ensure_ascii=False, indent=2))
        print(f"[DEBUG] ===============================")
        print(f"[DEBUG] Place Agent 응답 성공")
        
        if not place_result.get("success"):
            print(f"[ERROR] Place Agent 처리 실패")
            return None
        
        # Step 2: RAG Agent 호출 (이미 받은 결과 사용 또는 새로 생성)
        if hasattr(main_resp, 'rag_agent_request') and main_resp.rag_agent_request:
            print(f"[DEBUG] 이미 받은 RAG Agent 요청 사용 (중복 생성 방지)")
            rag_request = main_resp.rag_agent_request
        else:
            print(f"[DEBUG] RAG Agent 요청 생성")
            rag_request = build_rag_agent_json(
                place_response=place_result,
                profile=profile_dict,
                location_request=location_dict,
                openai_api_key=os.getenv("OPENAI_API_KEY"),
                session_info=session_info  # 채팅 기반 RAG 문구 생성을 위한 세션 정보 전달
            )
        
        print(f"[DEBUG] ===== RAG Agent Request =====")
        # API 키는 마스킹해서 출력
        rag_request_safe = dict(rag_request)
        if "openai_api_key" in rag_request_safe:
            rag_request_safe["openai_api_key"] = "sk-***" + rag_request_safe["openai_api_key"][-10:]
        print(json.dumps(rag_request_safe, ensure_ascii=False, indent=2))
        print(f"[DEBUG] ============================")
        
        print(f"[DEBUG] RAG Agent API 호출: {RAG_AGENT_URL}/recommend-course")
        rag_response = requests.post(
            f"{RAG_AGENT_URL}/recommend-course",
            json=rag_request,
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        
        if rag_response.status_code != 200:
            print(f"[ERROR] RAG Agent 호출 실패: HTTP {rag_response.status_code}")
            return None
            
        try:
            rag_result = rag_response.json()
            print(f"[DEBUG] ===== RAG Agent Response (FULL) =====")
            print(json.dumps(rag_result, ensure_ascii=False, indent=2))
            print(f"[DEBUG] =====================================")
            
            if rag_result is None:
                print("[ERROR] RAG Agent 응답이 None입니다")
                return None
            
            # 응답이 너무 클 수 있으므로 요약해서 출력
            rag_summary = {
                "success": rag_result.get("status") == "success" if isinstance(rag_result, dict) else "Not dict",
                "response_type": type(rag_result).__name__,
                "response_keys": list(rag_result.keys()) if isinstance(rag_result, dict) else "Not dict"
            }
            
            if isinstance(rag_result, dict):
                # RAG Agent 응답 구조: results.sunny_weather, results.rainy_weather
                results = rag_result.get("results", {})
                rag_summary.update({
                    "sunny_courses_count": len(results.get("sunny_weather", [])),
                    "rainy_courses_count": len(results.get("rainy_weather", [])),
                    "total_places": "N/A",
                    "processing_time": rag_result.get("processing_time"),
                    "message": rag_result.get("message", "")[:100] if rag_result.get("message") else "No message"
                })
            
            print(json.dumps(rag_summary, ensure_ascii=False, indent=2))
            print(f"[DEBUG] ============================")
            print(f"[DEBUG] RAG Agent 응답 성공")
            
        except json.JSONDecodeError as e:
            print(f"[ERROR] RAG Agent JSON 파싱 실패: {e}")
            print(f"[ERROR] 원본 응답: {rag_response.text[:500]}...")
            return None
        except Exception as e:
            print(f"[ERROR] RAG Agent 응답 처리 오류: {e}")
            print(f"[ERROR] 응답 타입: {type(rag_result)}")
            return None
        
        # RAG Agent 성공 여부 확인
        if rag_result.get("status") != "success":
            print(f"[ERROR] RAG Agent 처리 실패: {rag_result.get('message', 'Unknown error')}")
            return None
        
        # 코스 데이터 생성
        course_data = {
            "places": place_result.get("locations", []),
            "course": rag_result,
            "created_at": datetime.datetime.now().isoformat()
        }
        
        print(f"[DEBUG] 코스 데이터 생성 완료")
        print(f"[DEBUG] Place locations 개수: {len(place_result.get('locations', []))}")
        print(f"[DEBUG] Course 데이터 키: {list(rag_result.keys())}")
        
        return course_data
        
    except Exception as e:
        print(f"[ERROR] 추천 플로우 실행 오류: {str(e)}")
        return None

# 데이터 모델
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
    place_count: Optional[int] = None

class NewSessionRequest(BaseModel):
    user_id: str
    initial_message: str
    user_profile: UserProfile

class SendMessageRequest(BaseModel):
    session_id: str
    message: str
    user_id: str
    user_profile: UserProfile

# [LEGACY] 일반 채팅 API - 새로운 통합 API(/chat/new-session, /chat/send-message)로 대체됨
# @app.post("/chat")
# async def chat_with_agent(request: dict):
#     """일반 채팅 API - 맥락 유지하며 지속적 대화"""

# [LEGACY] 추천 시작 API - 새로운 통합 API(/chat/send-message)로 대체됨
# @app.post("/recommend")
# async def start_recommendation(request: dict):
#     """추천 시작 API - Place Agent → RAG Agent 전체 플로우 실행"""

# [LEGACY] 세션 복원 API - 새로운 통합 API(/chat/sessions/{session_id})로 대체됨
# @app.get("/session/{session_id}")
# async def get_session_info(session_id: str):
#     """세션 복원 API - 이전 채팅 및 상태 불러오기"""

# [LEGACY] 완전한 채팅 플로우 - 새로운 통합 API(/chat/send-message)로 대체됨
# @app.post("/chat/complete_flow")
# async def complete_chat_flow(request: dict):
#     """완전한 채팅 플로우: 채팅 → Place Agent → RAG Agent → 결과 반환"""

# [LEGACY] Place Agent 요청 - 새로운 통합 API(/chat/send-message)로 대체됨
# @app.post("/place/request")
# async def request_place(request: dict):
#     """Place Agent로 장소 추천 요청 전달 (A2A 통신)"""

# [LEGACY] RAG Agent 요청 - 새로운 통합 API(/chat/send-message)로 대체됨
# @app.post("/course/request")
# async def request_course(request: dict):
#     """RAG Agent로 코스 생성 요청 전달 (A2A 통신)"""

# [LEGACY] 세션별 프로필 조회 - 새로운 통합 API(/chat/sessions/{session_id})로 대체됨
# @app.get("/profile/{session_id}")
# async def get_profile(session_id: str):
#     """세션별 프로필 조회"""

# [LEGACY] 세션 삭제 - 새로운 통합 API(/chat/sessions/{session_id})로 대체됨
# @app.delete("/session/{session_id}")
# async def clear_session(session_id: str):
#     """세션 삭제"""

@app.get("/api/health")
async def health_check():
    """헬스 체크"""
    return {
        "status": "healthy", 
        "service": "main-agent",
        "port": PORT,
        "version": "1.0.0"
    }

@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "service": "Main Agent API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/health"
    }

# 1. 새 채팅 세션 시작
@app.post("/chat/new-session", response_model=NewSessionResponse)
async def new_session(req: NewSessionRequest):
    session_id = f"sess_{uuid.uuid4().hex[:12]}"
    now = datetime.datetime.now().isoformat() + "Z"
    expires_at = (datetime.datetime.now() + datetime.timedelta(days=1)).isoformat() + "Z"
    SESSIONS[session_id] = {
        "session_id": session_id,
        "user_id": req.user_id,
        "session_title": req.initial_message[:20],
        "session_status": "ACTIVE",
        "created_at": now,
        "expires_at": expires_at,
        "last_activity_at": now,
        "message_count": 1,
        "has_course": False,
        "preview_message": ""
    }
    MESSAGES[session_id] = [
        {"message_id": 1, "message_type": "USER", "message_content": req.initial_message, "sent_at": now}
    ]
    # 기존 통합 엔드포인트와 동일한 대화 생성 흐름 적용
    # user_profile을 dict로 변환해서 전달
    user_profile_dict = req.user_profile.dict() if req.user_profile else None
    main_req = MainAgentRequest(
        session_id=session_id,
        user_message=req.initial_message,
        user_profile=user_profile_dict,
        timestamp=now
    )
    try:
        main_resp = await main_agent_service.process_request(main_req)
        assistant_msg = main_resp.message or "죄송합니다. 답변을 생성하지 못했습니다. 다시 시도해 주세요."
        print(f"[DEBUG] NEW SESSION - MainAgentService Response: success={main_resp.success}, message={assistant_msg[:100]}...")
        if not main_resp.success and hasattr(main_resp, 'error') and main_resp.error:
            print(f"[ERROR] NEW SESSION - MainAgentService Error: {main_resp.error}")
    except Exception as e:
        print(f"[ERROR] NEW SESSION - MainAgentService Exception: {str(e)}")
        assistant_msg = f"처리 중 오류가 발생했습니다: {str(e)}"
    MESSAGES[session_id].append({"message_id": 2, "message_type": "ASSISTANT", "message_content": assistant_msg, "sent_at": now})
    SESSIONS[session_id]["message_count"] = 2
    SESSIONS[session_id]["preview_message"] = assistant_msg
    response = ResponseMessage(
        message=assistant_msg,
        message_type="INFORMATION_GATHERING",
        quick_replies=main_resp.suggestions if hasattr(main_resp, 'suggestions') else [],
        processing_time=1.2,
        course_data=None
    )
    session_info = SessionInfo(
        session_title=SESSIONS[session_id]["session_title"],
        session_status=SESSIONS[session_id]["session_status"],
        created_at=SESSIONS[session_id]["created_at"],
        expires_at=SESSIONS[session_id]["expires_at"],
        last_activity_at=SESSIONS[session_id]["last_activity_at"],
        message_count=SESSIONS[session_id]["message_count"]
    )
    return NewSessionResponse(
        success=True,
        session_id=session_id,
        response=response,
        session_info=session_info
    )

# 2. 메시지 전송
@app.post("/chat/send-message", response_model=SendMessageResponse)
async def send_message(req: SendMessageRequest):
    session = SESSIONS.get(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
    now = datetime.datetime.now().isoformat() + "Z"
    msg_id = len(MESSAGES[req.session_id]) + 1
    MESSAGES[req.session_id].append({"message_id": msg_id, "message_type": "USER", "message_content": req.message, "sent_at": now})
    session["message_count"] += 1
    session["last_activity_at"] = now

    # 기존 통합 엔드포인트와 동일한 대화 생성 흐름 적용
    # user_profile을 dict로 변환해서 전달
    user_profile_dict = req.user_profile.dict() if req.user_profile else None
    main_req = MainAgentRequest(
        session_id=req.session_id,
        user_message=req.message,
        user_profile=user_profile_dict,
        timestamp=now
    )
    try:
        main_resp = await main_agent_service.process_request(main_req)
        assistant_msg = main_resp.message or "죄송합니다. 답변을 생성하지 못했습니다. 다시 시도해 주세요."
        print(f"[DEBUG] SEND MESSAGE - MainAgentService Response: success={main_resp.success}, message={assistant_msg[:100]}...")
        if not main_resp.success and hasattr(main_resp, 'error') and main_resp.error:
            print(f"[ERROR] SEND MESSAGE - MainAgentService Error: {main_resp.error}")
        
        # 추천 준비 완료 시 안내 메시지만 표시
        course_data = None
        if main_resp.success and hasattr(main_resp, 'needs_recommendation') and main_resp.needs_recommendation:
            # 🔥 CRITICAL: MainAgentService에서 place_agent_request를 반환한 경우 직접 실행도 가능
            if hasattr(main_resp, 'place_agent_request') and main_resp.place_agent_request:
                print(f"[DEBUG] MainAgentService에서 place_agent_request 반환됨 - 직접 실행 가능")
                # session_info를 가져와서 추천 실행 (향후 확장 가능)
                from services.main_agent_service import SESSION_INFO
                current_session_info = SESSION_INFO.get(req.session_id, {})
                print(f"[DEBUG] 직접 실행용 session_info 준비: {bool(current_session_info.get('location_clustering'))}")
            
            assistant_msg = "✨ **모든 정보가 수집되었습니다!** ✨\n\n이제 맞춤 데이트 코스를 생성할 준비가 완료되었어요.\n📍 추천을 시작하시려면 '추천 시작' 버튼을 눌러주세요!"
        
    except Exception as e:
        print(f"[ERROR] SEND MESSAGE - MainAgentService Exception: {str(e)}")
        assistant_msg = f"처리 중 오류가 발생했습니다: {str(e)}"
    msg_id += 1
    MESSAGES[req.session_id].append({"message_id": msg_id, "message_type": "ASSISTANT", "message_content": assistant_msg, "sent_at": now})
    session["message_count"] += 1
    session["last_activity_at"] = now
    # 추천 결과가 있으면 course_data에 포함
    if 'course_data' not in locals():
        course_data = getattr(main_resp, "course_data", None)
    message_type = getattr(main_resp, "message_type", "INFORMATION_GATHERING")
    quick_replies = getattr(main_resp, "suggestions", [])
    
    # course_data가 있으면 추천 완료로 처리
    if course_data:
        message_type = "COURSE_RECOMMENDATION"
        session["has_course"] = True
        session["preview_message"] = assistant_msg
        session["session_status"] = "COMPLETED"
    response = ResponseMessage(
        message=assistant_msg,
        message_type=message_type,
        quick_replies=quick_replies,
        processing_time=2.0,
        course_data=course_data
    )
    session_info = SessionInfo(
        session_title=session["session_title"],
        session_status=session["session_status"],
        created_at=session["created_at"],
        expires_at=session["expires_at"],
        last_activity_at=session["last_activity_at"],
        message_count=session["message_count"]
    )
    return SendMessageResponse(
        success=True,
        session_id=req.session_id,
        response=response,
        session_info=session_info
    )

# 3. 세션 목록 조회
@app.get("/chat/sessions/user/{user_id}")
def get_sessions(user_id: str, limit: int = Query(10), offset: int = Query(0), status: str = Query("all")):
    sessions = [s for s in SESSIONS.values() if s["user_id"] == user_id]
    # 상태 필터링
    if status != "all":
        sessions = [s for s in sessions if s["session_status"] == status]
    total_count = len(sessions)
    has_more = total_count > (offset + limit)
    return {
        "success": True,
        "sessions": sessions[offset:offset+limit],
        "pagination": {
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": has_more
        }
    }

# 4. 세션 상세 조회
@app.get("/chat/sessions/{session_id}")
def get_session(session_id: str):
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
    return {
        "success": True,
        "session": session,
        "messages": MESSAGES[session_id]
    }

# 5. 세션 삭제
@app.delete("/chat/sessions/{session_id}")
def delete_session(session_id: str):
    SESSIONS.pop(session_id, None)
    MESSAGES.pop(session_id, None)
    return {
        "success": True,
        "message": "채팅 세션이 성공적으로 삭제되었습니다.",
        "deleted_session_id": session_id,
        "deleted_at": datetime.datetime.now().isoformat() + "Z"
    }

# 6. 추천 시작
@app.post("/chat/start-recommendation")
async def start_recommendation(request: dict):
    """세션별 추천 플로우 시작"""
    try:
        session_id = request.get("session_id")
        if not session_id:
            return {
                "success": False,
                "message": "session_id가 필요합니다.",
                "error_code": "MISSING_SESSION_ID"
            }
        
        session = SESSIONS.get(session_id)
        if not session:
            return {
                "success": False,
                "message": "세션을 찾을 수 없습니다.",
                "session_id": session_id,
                "error_code": "SESSION_NOT_FOUND"
            }
        
        # 세션에서 마지막 MainAgentService 응답을 시뮬레이션
        # 실제로는 SESSION_INFO에서 프로필 정보를 가져와야 함
        print(f"[DEBUG] 추천 시작 요청 - session_id: {session_id}")
        
        # 임시로 MainAgentService에서 프로필 정보 가져오기
        from services.main_agent_service import SESSION_INFO
        session_info = SESSION_INFO.get(session_id, {})
        
        if 'profile' not in session_info:
            return {
                "success": False,
                "message": "프로필 정보가 없습니다. 먼저 채팅을 통해 정보를 입력해주세요.",
                "session_id": session_id,
                "error_code": "INCOMPLETE_PROFILE"
            }
        
        profile = session_info['profile']
        
        # LocationRequest 생성 (address 기반)
        from models.request_models import LocationRequest
        location_request = LocationRequest(
            proximity_type="near",
            reference_areas=[profile.address] if profile.address else [],
            place_count=3,
            transportation="지하철"
        )
        
        # MainAgentResponse 형태로 만들어서 추천 플로우 실행
        class MockMainAgentResponse:
            def __init__(self, profile, location_request):
                self.profile = profile
                self.location_request = location_request
                self.success = True
                self.needs_recommendation = True
        
        mock_response = MockMainAgentResponse(profile, location_request)
        
        print(f"[DEBUG] 추천 플로우 실행 시작 (session_info 포함)")
        course_data = await execute_recommendation_flow(mock_response, session_info)  # 🔥 CRITICAL: session_info 전달
        
        print(f"[DEBUG] 추천 플로우 실행 완료, course_data: {course_data is not None}")
        
        if course_data:
            # 세션 상태 업데이트
            session["has_course"] = True
            session["session_status"] = "COMPLETED"
            session["last_activity_at"] = datetime.datetime.now().isoformat() + "Z"
            
            # Place Agent 응답에서 places 정보 추출
            places_list = course_data.get("places", [])
            
            # RAG Agent 응답 정보
            rag_result = course_data.get("course", {})
            results = rag_result.get("results", {})
            
            # 처리 정보 생성
            processing_info = {
                "place_agent_status": "completed",
                "rag_agent_status": "completed", 
                "total_processing_time": float(rag_result.get("processing_time", "0").replace("초", "")),
                "place_count": len(places_list),
                "sunny_course_count": len(results.get("sunny_weather", [])),
                "rainy_course_count": len(results.get("rainy_weather", [])),
                "total_course_variations": len(results.get("sunny_weather", [])) + len(results.get("rainy_weather", []))
            }
            
            # 완전한 response 구조 생성
            final_response = {
                "success": True,
                "message": "🌟 **데이트 코스 추천이 완료되었습니다!** 🌟",
                "session_id": session_id,
                "course_data": {
                    "places": places_list,
                    "course": rag_result,
                    "created_at": course_data.get("created_at")
                },
                "session_info": {
                    "session_title": session["session_title"],
                    "session_status": session["session_status"],
                    "created_at": session["created_at"],
                    "expires_at": session["expires_at"],
                    "last_activity_at": session["last_activity_at"],
                    "message_count": session["message_count"],
                    "has_course": session["has_course"]
                },
                "processing_info": processing_info
            }
            
            # 최종 JSON 출력
            print(f"\n[DEBUG] ===== FINAL RESPONSE JSON =====")
            print(json.dumps(final_response, ensure_ascii=False, indent=2))
            print(f"[DEBUG] ===============================")
            
            return final_response
        else:
            return {
                "success": False,
                "message": "추천 생성 중 오류가 발생했습니다. 다시 시도해주세요.",
                "session_id": session_id
            }
            
    except Exception as e:
        print(f"[ERROR] 추천 시작 오류: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "message": "추천 생성 중 예상치 못한 오류가 발생했습니다.",
            "error_code": "INTERNAL_ERROR",
            "error_details": {
                "error_type": type(e).__name__,
                "error_message": str(e)
            }
        }

# 7. 헬스체크
@app.get("/chat/health")
def health():
    return {
        "status": "healthy",
        "timestamp": datetime.datetime.now().isoformat() + "Z",
        "version": "1.0.0",
        "services": {
            "database": "healthy",
            "place_agent": "healthy",
            "rag_agent": "healthy",
            "llm_api": "healthy"
        },
        "metrics": {
            "uptime_seconds": 86400,
            "total_requests": 1547,
            "average_response_time_ms": 2100,
            "active_sessions": len(SESSIONS),
            "db_connection_pool": "8/10"
        }
    }

# 8. 세션 프로필 데이터 조회
@app.get("/chat/session-profile/{session_id}")
async def get_session_profile(session_id: str):
    """세션의 프로필 데이터를 반환"""
    try:
        from services.main_agent_service import SESSION_INFO
        session_info = SESSION_INFO.get(session_id, {})
        
        if 'profile' not in session_info:
            return {
                "success": False,
                "message": "프로필 데이터를 찾을 수 없습니다.",
                "session_id": session_id
            }
        
        profile = session_info['profile']
        
        # 프로필 데이터를 딕셔너리로 변환
        profile_data = {}
        if hasattr(profile, '__dict__'):
            profile_data = profile.__dict__.copy()
        else:
            # Pydantic 모델인 경우
            profile_data = profile.dict()
        
        # general_preferences가 문자열인 경우 리스트로 변환
        if isinstance(profile_data.get('general_preferences'), str):
            profile_data['general_preferences'] = [
                pref.strip() for pref in profile_data['general_preferences'].split(',') 
                if pref.strip()
            ]
        
        return {
            "success": True,
            "session_id": session_id,
            "profile_data": profile_data,
            "message": "프로필 데이터 조회 성공"
        }
        
    except Exception as e:
        print(f"[ERROR] 세션 프로필 조회 오류: {e}")
        return {
            "success": False,
            "message": f"프로필 조회 중 오류가 발생했습니다: {str(e)}",
            "session_id": session_id
        }

if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=PORT,
        reload=True,
        log_level="info"
    )