"""
Main Agent - FastAPI 통합용 모듈화된 버전
데이트 코스 추천 시스템의 메인 에이전트
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import os
from dotenv import load_dotenv

from services.main_agent_service import MainAgentService
from models.request_models import MainAgentRequest
from models.response_models import MainAgentResponse
from utils.file_manager import FileManager

load_dotenv()

class MainAgent:
    """FastAPI 통합용 메인 에이전트 클래스"""
    
    def __init__(self, openai_api_key: str = None):
        self.service = MainAgentService(openai_api_key)
        self.file_manager = FileManager()
    
    def process_request(self, request: MainAgentRequest) -> MainAgentResponse:
        """요청 처리 및 응답 반환"""
        return self.service.process_request(request)
    
    def process_request_with_file_save(self, request: MainAgentRequest) -> MainAgentResponse:
        """요청 처리 + 파일 저장"""
        response = self.service.process_request(request)
        
        if response.success:
            # 파일 저장
            try:
                profile_data = {
                    "profile": response.profile.dict(),
                    "location_request": response.location_request.dict()
                }
                self.file_manager.save_profile(response.session_id, profile_data)
                
                if response.place_agent_request:
                    self.file_manager.save_place_agent_request(
                        response.session_id, 
                        response.place_agent_request
                    )
                
                if response.rag_agent_request:
                    self.file_manager.save_rag_agent_request(
                        response.session_id,
                        response.rag_agent_request
                    )
            except Exception as e:
                response.message = f"처리 완료, 파일 저장 중 오류: {str(e)}"
        
        return response
    
    def get_session_memory(self, session_id: str) -> str:
        """세션 메모리 조회"""
        memory = self.service.get_session_memory(session_id)
        return memory if memory else "세션을 찾을 수 없습니다."
    
    def clear_session(self, session_id: str) -> bool:
        """세션 삭제"""
        return self.service.clear_session(session_id)

# FastAPI 앱 인스턴스 (필요시 사용)
def create_fastapi_app(openai_api_key: str = None) -> FastAPI:
    """FastAPI 앱 생성"""
    app = FastAPI(
        title="Main Agent API",
        description="데이트 코스 추천 시스템 메인 에이전트",
        version="1.0.0"
    )
    
    agent = MainAgent(openai_api_key)
    
    @app.post("/process", response_model=MainAgentResponse)
    async def process_request(request: MainAgentRequest):
        """요청 처리 엔드포인트"""
        try:
            response = agent.process_request_with_file_save(request)
            return response
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/memory/{session_id}")
    async def get_memory(session_id: str):
        """세션 메모리 조회"""
        memory = agent.get_session_memory(session_id)
        return {"session_id": session_id, "memory": memory}
    
    @app.delete("/session/{session_id}")
    async def clear_session(session_id: str):
        """세션 삭제"""
        success = agent.clear_session(session_id)
        return {"session_id": session_id, "cleared": success}
    
    @app.get("/health")
    async def health_check():
        """헬스 체크"""
        return {"status": "healthy", "service": "main-agent"}
    
    return app

# 편의 함수들
def create_agent(openai_api_key: str = None) -> MainAgent:
    """에이전트 인스턴스 생성"""
    return MainAgent(openai_api_key)

def quick_process(user_message: str, session_id: str = None, openai_api_key: str = None) -> MainAgentResponse:
    """빠른 처리 함수"""
    agent = MainAgent(openai_api_key)
    request = MainAgentRequest(user_message=user_message, session_id=session_id)
    return agent.process_request(request)

# 기존 호환성을 위한 메인 함수 (CLI 사용자용)
def main():
    """CLI 실행을 위한 메인 함수"""
    print("CLI 모드로 실행하려면 'python cli.py'를 사용하세요.")
    print("또는 다음과 같이 프로그래밍 방식으로 사용하세요:")
    print()
    print("from main_agent import MainAgent, MainAgentRequest")
    print("agent = MainAgent()")
    print("request = MainAgentRequest(user_message='홍대에서 데이트하고 싶어요')")
    print("response = agent.process_request(request)")
    print("print(response)")

if __name__ == "__main__":
    main()