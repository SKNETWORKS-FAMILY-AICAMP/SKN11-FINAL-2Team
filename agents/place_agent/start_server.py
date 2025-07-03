# Place Agent FastAPI 서버
# - 모듈화된 Place Agent를 위한 HTTP API 서버
# - A2A 통신 지원

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import sys
import os
from typing import Dict, Any

# 현재 디렉토리를 path에 추가
sys.path.append(os.path.dirname(__file__))
from src.main import PlaceAgent
from src.models.request_models import PlaceAgentRequest
from config.settings import settings

# FastAPI 앱 생성
app = FastAPI(
    title="Place Agent API",
    description="서울 지역 추천 및 좌표 반환 서비스 (모듈화 버전)",
    version="2.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Place Agent 인스턴스
place_agent = PlaceAgent()

@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "service": "place-agent",
        "version": "2.0.0",
        "status": "running",
        "description": "서울 지역 추천 및 좌표 반환 서비스 (모듈화 버전)"
    }

@app.get("/health")
async def health_check():
    """헬스 체크"""
    return await place_agent.health_check()

@app.post("/place-agent")
async def process_place_request(request_data: Dict[str, Any]):
    """
    Place Agent 요청 처리
    
    Args:
        request_data: PlaceAgentRequest 형식의 JSON 데이터
        
    Returns:
        PlaceAgentResponse: 처리 결과
    """
    try:
        print(f"📥 Place Agent 요청 수신: {request_data.get('request_id', 'unknown')}")
        
        # Place Agent로 요청 처리
        result = await place_agent.process_request(request_data)
        
        return result
        
    except Exception as e:
        print(f"❌ Place Agent API 오류: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"서버 처리 중 오류가 발생했습니다: {str(e)}"
        )

@app.get("/test")
async def test_endpoint():
    """테스트용 엔드포인트"""
    test_request = {
        "request_id": "test-api-001",
        "timestamp": "2024-01-01T12:00:00",
        "request_type": "proximity_based",
        "location_request": {
            "proximity_type": "near",
            "reference_areas": ["홍대"],
            "place_count": 3,
            "proximity_preference": "middle",
            "transportation": "지하철"
        },
        "user_context": {
            "demographics": {
                "age": 25,
                "mbti": "ENFP",
                "relationship_stage": "연인"
            },
            "preferences": ["트렌디한", "감성적인"],
            "requirements": {
                "budget_level": "medium",
                "time_preference": "저녁",
                "transportation": "지하철",
                "max_travel_time": 30
            }
        },
        "selected_categories": ["카페", "레스토랑"]
    }
    
    result = await place_agent.process_request(test_request)
    return result

if __name__ == "__main__":
    print("🚀 Place Agent 서버 시작")
    print(f"📍 포트: {settings.SERVER_PORT}")
    print(f"🔑 OpenAI API 키 설정: {'✅' if settings.OPENAI_API_KEY else '❌'}")
    print("=" * 50)
    
    uvicorn.run(
        "start_server:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )