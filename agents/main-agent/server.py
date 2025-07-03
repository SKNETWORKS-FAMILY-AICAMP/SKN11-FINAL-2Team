"""
Main Agent FastAPI Server
환경변수로 포트 설정 가능한 메인 에이전트 서버
"""

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import requests
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import Dict, List, Optional
import uuid
import datetime
import json

from main_agent import MainAgent
from models.request_models import MainAgentRequest
from models.response_models import MainAgentResponse

load_dotenv()

# 포트 설정을 환경변수로 변경
PORT = int(os.getenv("MAIN_AGENT_PORT", 8000))
PLACE_AGENT_URL = os.getenv("PLACE_AGENT_URL", "http://localhost:8001")
RAG_AGENT_URL = os.getenv("RAG_AGENT_URL", "http://localhost:8002")

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

# 임시 메모리 저장소
SESSIONS = {}  # session_id -> session_info
MESSAGES = {}  # session_id -> List[message]

# 데이터 모델
class UserProfile(BaseModel):
    gender: str
    age: int
    mbti: str
    address: str
    car_owned: bool
    description: str
    relationship_stage: str
    general_preferences: List[str]
    profile_image_url: Optional[str] = None

class NewSessionRequest(BaseModel):
    user_id: int
    initial_message: str
    user_profile: UserProfile

class SendMessageRequest(BaseModel):
    session_id: str
    message: str
    user_id: int
    user_profile: UserProfile

@app.post("/chat")
async def chat_with_agent(request: dict):
    """일반 채팅 API - 맥락 유지하며 지속적 대화"""
    try:
        from models.request_models import MainAgentRequest
        
        # 요청 데이터 추출
        session_id = request.get("session_id")
        user_message = request.get("user_message")
        timestamp = request.get("timestamp")
        
        if not all([session_id, user_message]):
            raise HTTPException(status_code=400, detail="session_id와 user_message가 필요합니다")
        
        # 채팅 요청 생성
        chat_request = MainAgentRequest(
            session_id=session_id,
            user_message=user_message,
            timestamp=timestamp or ""
        )
        
        # 프로필 추출 및 응답 생성
        response = agent.process_request_with_file_save(chat_request)
        
        # 응답 구성
        result = {
            "session_id": session_id,
            "success": response.success,
            "message": response.message,
            "profile_status": "completed" if response.success else "incomplete",
            "needs_recommendation": response.needs_recommendation if hasattr(response, 'needs_recommendation') else False,
            "extracted_info": response.profile.dict() if response.success else None,
            "suggestions": getattr(response, 'suggestions', [])
        }
        
        # 추천 준비 완료 시 추가 정보 제공
        if response.success and hasattr(response, 'needs_recommendation') and response.needs_recommendation:
            result["recommendation_ready"] = True
            result["next_action"] = "추천을 시작하려면 /recommend 엔드포인트를 호출하세요"
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/recommend")
async def start_recommendation(request: dict):
    """추천 시작 API - Place Agent → RAG Agent 전체 플로우 실행"""
    try:
        from core.agent_builders import build_place_agent_json, build_rag_agent_json
        
        # 요청 데이터 추출
        session_id = request.get("session_id")
        
        if not session_id:
            raise HTTPException(status_code=400, detail="session_id가 필요합니다")
        
        # 세션에서 저장된 프로필 정보 가져오기
        try:
            session_memory = agent.get_session_memory(session_id)
            if session_memory == "세션을 찾을 수 없습니다.":
                raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")
            
            # 저장된 프로필과 위치 요청 정보 추출
            # 실제 구현에서는 파일에서 불러오거나 메모리에서 가져와야 함
            # 여기서는 임시로 기본값 사용
            profile_dict = {
                "age": "29",
                "mbti": "INTP", 
                "relationship_stage": "연인",
                "atmosphere": "로맨틱",
                "budget": "medium",
                "time_slot": "밤"
            }
            
            location_dict = {
                "proximity_type": "exact",
                "reference_areas": ["이촌동"],
                "place_count": 3,
                "transportation": "도보"
            }
            
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"프로필 정보를 가져올 수 없습니다: {str(e)}")
        
        flow_results = {}
        
        # Step 1: Place Agent 요청
        try:
            place_request = build_place_agent_json(
                profile=profile_dict,
                location_request=location_dict
            )
            
            # Place Agent API 호출
            place_agent_url = f"{PLACE_AGENT_URL}/place-agent"
            print("\n[PlaceAgent Request] ↓↓↓")
            print(json.dumps(place_request, ensure_ascii=False, indent=2))
            place_response = requests.post(
                place_agent_url,
                json=place_request,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            print("[PlaceAgent Response] ↑↑↑")
            try:
                print(json.dumps(place_response.json(), ensure_ascii=False, indent=2))
            except Exception:
                print(place_response.text)
            
            if place_response.status_code == 200:
                place_result = place_response.json()
                flow_results["place_agent"] = {
                    "status": "completed",
                    "success": place_result.get("success", False),
                    "data": place_result
                }
                
                if not place_result.get("success"):
                    return {
                        "success": False,
                        "message": "장소 추천 실패",
                        "flow_results": flow_results
                    }
            else:
                flow_results["place_agent"] = {
                    "status": "failed",
                    "error": f"HTTP {place_response.status_code}"
                }
                return {
                    "success": False,
                    "message": "Place Agent 호출 실패",
                    "flow_results": flow_results
                }
                
        except Exception as e:
            flow_results["place_agent"] = {
                "status": "failed",
                "error": str(e)
            }
            return {
                "success": False,
                "message": f"Place Agent 오류: {str(e)}",
                "flow_results": flow_results
            }
        
        # Step 2: RAG Agent 요청
        try:
            rag_request = build_rag_agent_json(
                place_response=place_result,
                profile=profile_dict,
                location_request=location_dict,
                openai_api_key=os.getenv("OPENAI_API_KEY")
            )
            print("\n[RagAgent Request] ↓↓↓")
            print(json.dumps(rag_request, ensure_ascii=False, indent=2))
            # RAG Agent API 호출
            rag_agent_url = f"{RAG_AGENT_URL}/recommend-course"
            rag_response = requests.post(
                rag_agent_url,
                json=rag_request,
                headers={"Content-Type": "application/json"},
                timeout=60
            )
            print("[RagAgent Response] ↑↑↑")
            try:
                print(json.dumps(rag_response.json(), ensure_ascii=False, indent=2))
            except Exception:
                print(rag_response.text)
            
            if rag_response.status_code == 200:
                rag_result = rag_response.json()
                flow_results["rag_agent"] = {
                    "status": "completed",
                    "success": True,
                    "data": rag_result
                }
                
                return {
                    "success": True,
                    "message": "추천 완료",
                    "session_id": session_id,
                    "flow_results": flow_results,
                    "recommendation": {
                        "places": flow_results["place_agent"]["data"]["locations"],
                        "course": rag_result,
                        "created_at": datetime.datetime.now().isoformat()
                    }
                }
            else:
                flow_results["rag_agent"] = {
                    "status": "failed",
                    "error": f"HTTP {rag_response.status_code}"
                }
                return {
                    "success": False,
                    "message": "RAG Agent 호출 실패",
                    "flow_results": flow_results
                }
                
        except Exception as e:
            flow_results["rag_agent"] = {
                "status": "failed",
                "error": str(e)
            }
            return {
                "success": False,
                "message": f"RAG Agent 오류: {str(e)}",
                "flow_results": flow_results
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/session/{session_id}")
async def get_session_info(session_id: str):
    """세션 복원 API - 이전 채팅 및 상태 불러오기"""
    try:
        # 세션 메모리 조회
        session_memory = agent.get_session_memory(session_id)
        
        if session_memory == "세션을 찾을 수 없습니다.":
            return {
                "session_id": session_id,
                "exists": False,
                "message": "세션을 찾을 수 없습니다"
            }
        
        # 프로필 상태 확인
        profile_status = "incomplete"
        extracted_info = None
        needs_recommendation = False
        
        # 여기서 실제로는 저장된 프로필 파일이나 메모리에서 상태를 확인해야 함
        # 임시로 간단한 로직 사용
        if session_memory and len(session_memory) > 0:
            profile_status = "completed"
            extracted_info = {
                "age": "29",
                "mbti": "INTP",
                "relationship_stage": "연인"
            }
            needs_recommendation = True
        
        return {
            "session_id": session_id,
            "exists": True,
            "session_memory": session_memory,
            "profile_status": profile_status,
            "extracted_info": extracted_info,
            "needs_recommendation": needs_recommendation,
            "last_activity": datetime.datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat/complete_flow")
async def complete_chat_flow(request: dict):
    """완전한 채팅 플로우: 채팅 → Place Agent → RAG Agent → 결과 반환"""
    try:
        from core.agent_builders import build_place_agent_json, build_rag_agent_json
        from models.request_models import MainAgentRequest
        
        # 요청 데이터 추출
        session_id = request.get("session_id")
        user_message = request.get("user_message")
        timestamp = request.get("timestamp")
        
        if not all([session_id, user_message]):
            raise HTTPException(status_code=400, detail="session_id와 user_message가 필요합니다")
        
        flow_results = {}
        
        # Step 1: 채팅 메시지로부터 프로필 추출
        chat_request = MainAgentRequest(
            session_id=session_id,
            user_message=user_message,
            timestamp=timestamp or ""
        )
        
        profile_response = agent.process_request_with_file_save(chat_request)
        flow_results["profile_extraction"] = {
            "status": "completed" if profile_response.success else "failed",
            "extracted_info": profile_response.profile.dict() if profile_response.success else None,
            "location_request": profile_response.location_request.dict() if profile_response.success else None
        }
        
        if not profile_response.success:
            return {
                "success": False,
                "message": "프로필 추출 실패",
                "flow_results": flow_results
            }
        
        # 추천 요청이 있는 경우에만 Place Agent와 RAG Agent 호출
        if not profile_response.needs_recommendation:
            return {
                "success": True,
                "message": profile_response.message,
                "flow_results": flow_results,
                "final_recommendation": None
            }
        
        # Step 2: Place Agent 요청
        try:
            profile_dict = profile_response.profile.dict()
            location_dict = profile_response.location_request.dict()
            
            place_request = build_place_agent_json(
                profile=profile_dict,
                location_request=location_dict
            )
            
            # Place Agent API 호출
            place_agent_url = f"{PLACE_AGENT_URL}/place-agent"
            place_response = requests.post(
                place_agent_url,
                json=place_request,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if place_response.status_code == 200:
                place_result = place_response.json()
                flow_results["place_agent"] = {
                    "status": "completed",
                    "success": place_result.get("success", False),
                    "data": place_result
                }
                
                if not place_result.get("success"):
                    return {
                        "success": False,
                        "message": "장소 추천 실패",
                        "flow_results": flow_results
                    }
            else:
                flow_results["place_agent"] = {
                    "status": "failed",
                    "error": f"HTTP {place_response.status_code}"
                }
                return {
                    "success": False,
                    "message": "Place Agent 호출 실패",
                    "flow_results": flow_results
                }
                
        except Exception as e:
            flow_results["place_agent"] = {
                "status": "failed",
                "error": str(e)
            }
            return {
                "success": False,
                "message": f"Place Agent 오류: {str(e)}",
                "flow_results": flow_results
            }
        
        # Step 3: RAG Agent 요청
        try:
            # Place Agent 응답을 RAG Agent 요청으로 변환
            rag_request = build_rag_agent_json(
                place_response=place_result,
                profile=profile_dict,
                location_request=location_dict,
                openai_api_key=os.getenv("OPENAI_API_KEY")
            )
            
            # RAG Agent API 호출
            rag_agent_url = f"{RAG_AGENT_URL}/recommend-course"
            rag_response = requests.post(
                rag_agent_url,
                json=rag_request,
                headers={"Content-Type": "application/json"},
                timeout=60
            )
            
            if rag_response.status_code == 200:
                rag_result = rag_response.json()
                flow_results["rag_agent"] = {
                    "status": "completed",
                    "success": True,
                    "data": rag_result
                }
                
                # 최종 추천 메시지 생성
                final_message = "데이트 코스가 성공적으로 생성되었습니다! 위의 코스 정보를 확인해보세요."
                
                return {
                    "success": True,
                    "message": "전체 플로우 완료",
                    "flow_results": flow_results,
                    "final_recommendation": final_message
                }
            else:
                flow_results["rag_agent"] = {
                    "status": "failed",
                    "error": f"HTTP {rag_response.status_code}"
                }
                return {
                    "success": False,
                    "message": "RAG Agent 호출 실패",
                    "flow_results": flow_results
                }
                
        except Exception as e:
            flow_results["rag_agent"] = {
                "status": "failed",
                "error": str(e)
            }
            return {
                "success": False,
                "message": f"RAG Agent 오류: {str(e)}",
                "flow_results": flow_results
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/place/request")
async def request_place(request: dict):
    """Place Agent로 장소 추천 요청 전달 (A2A 통신)"""
    try:
        # Place Agent로 요청 전송 (환경변수 사용)
        place_agent_url = f"{PLACE_AGENT_URL}/place-agent"
        response = requests.post(
            place_agent_url,
            json=request,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return {
                "success": True,
                "message": "Place Agent 요청 처리 완료",
                "data": result
            }
        else:
            return {
                "success": False,
                "message": "Place Agent 요청 처리 실패",
                "error": response.text
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/course/request")
async def request_course(request: dict):
    """RAG Agent로 코스 생성 요청 전달 (A2A 통신)"""
    try:
        from services.rag_client import RagAgentClient
        
        # RAG Agent 클라이언트 생성
        rag_client = RagAgentClient()
        
        # RAG Agent로 요청 전송
        result = await rag_client.process_rag_request(request)
        
        if result["success"]:
            return {
                "success": True,
                "message": "RAG Agent 요청 처리 완료",
                "data": result["data"]
            }
        else:
            return {
                "success": False,
                "message": "RAG Agent 요청 처리 실패",
                "error": result["error"]
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/profile/{session_id}")
async def get_profile(session_id: str):
    """세션별 프로필 조회"""
    try:
        memory = agent.get_session_memory(session_id)
        return {
            "session_id": session_id, 
            "memory": memory,
            "status": "found" if memory != "세션을 찾을 수 없습니다." else "not_found"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/session/{session_id}")
async def clear_session(session_id: str):
    """세션 삭제"""
    try:
        success = agent.clear_session(session_id)
        return {"session_id": session_id, "cleared": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
@app.post("/chat/new-session")
def new_session(req: NewSessionRequest):
    session_id = f"sess_{uuid.uuid4().hex[:12]}"
    now = datetime.datetime.now().isoformat() + "Z"
    SESSIONS[session_id] = {
        "session_id": session_id,
        "user_id": req.user_id,
        "session_title": req.initial_message[:20],
        "session_status": "ACTIVE",
        "created_at": now,
        "expires_at": (datetime.datetime.now() + datetime.timedelta(days=1)).isoformat() + "Z",
        "message_count": 1
    }
    MESSAGES[session_id] = [
        {"message_id": 1, "message_type": "USER", "message_content": req.initial_message, "sent_at": now}
    ]
    # 첫 답변(임시)
    assistant_msg = "홍대에서 로맨틱한 저녁 데이트 계획을 도와드릴게요! 💕\n\n더 맞춤형 추천을 위해 몇 가지 물어볼게요:\n\n1. **어떤 분위기**를 선호하시나요?\n   🕯️ 아늑하고 조용한 곳 vs 🌃 활기찬 곳\n\n2. **예산대**는 어느 정도로 생각하고 계신가요?\n   💰 2인 기준 5만원 이하 / 5-10만원 / 10만원 이상"
    MESSAGES[session_id].append({"message_id": 2, "message_type": "ASSISTANT", "message_content": assistant_msg, "sent_at": now})
    SESSIONS[session_id]["message_count"] = 2
    return {
        "success": True,
        "session_id": session_id,
        "response": {
            "message": assistant_msg,
            "message_type": "INFORMATION_GATHERING",
            "quick_replies": [
                "아늑하고 조용한 곳",
                "활기찬 곳",
                "예산은 10만원 정도"
            ],
            "processing_time": 1.2
        },
        "session_info": SESSIONS[session_id]
    }

# 2. 메시지 전송
@app.post("/chat/send-message")
def send_message(req: SendMessageRequest):
    session = SESSIONS.get(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
    now = datetime.datetime.now().isoformat() + "Z"
    msg_id = len(MESSAGES[req.session_id]) + 1
    MESSAGES[req.session_id].append({"message_id": msg_id, "message_type": "USER", "message_content": req.message, "sent_at": now})
    # 실제로 Place Agent, RAG Agent 연동해서 답변 생성 (여기선 임시 답변)
    assistant_msg = "좋아요! 아늑하고 조용한 분위기에 10만원 예산이면 정말 멋진 코스를 만들 수 있을 것 같아요 ✨\n\n마지막으로 몇 가지만 더 확인할게요:\n\n3. **몇 시간 정도** 데이트를 계획하고 계신가요?\n   ⏰ 2-3시간 / 4-5시간 / 하루 종일\n\n4. **어떤 종류의 장소**를 선호하시나요?\n   🍽️ 맛집 위주 / ☕ 카페 위주 / 🎨 문화생활 포함"
    msg_id += 1
    MESSAGES[req.session_id].append({"message_id": msg_id, "message_type": "ASSISTANT", "message_content": assistant_msg, "sent_at": now})
    session["message_count"] += 2
    session["last_activity_at"] = now
    return {
        "success": True,
        "session_id": req.session_id,
        "response": {
            "message": assistant_msg,
            "message_type": "INFORMATION_GATHERING",
            "quick_replies": [
                "4-5시간 예정이에요",
                "맛집 위주로",
                "카페 위주로"
            ],
            "processing_time": 1.8
        },
        "session_info": session
    }

# 3. 세션 목록 조회
@app.get("/chat/sessions/{user_id}")
def get_sessions(user_id: int):
    result = [s for s in SESSIONS.values() if s["user_id"] == user_id]
    return {"success": True, "sessions": result, "pagination": {"total_count": len(result)}}

# 4. 세션 상세 조회
@app.get("/chat/sessions/{session_id}")
def get_session(session_id: str):
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
    return {"success": True, "session": session, "messages": MESSAGES[session_id]}

# 5. 세션 삭제
@app.delete("/chat/sessions/{session_id}")
def delete_session(session_id: str):
    SESSIONS.pop(session_id, None)
    MESSAGES.pop(session_id, None)
    return {"success": True, "message": "채팅 세션이 성공적으로 삭제되었습니다.", "deleted_session_id": session_id}

# 6. 헬스체크
@app.get("/chat/health")
def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=PORT,
        reload=True,
        log_level="info"
    )