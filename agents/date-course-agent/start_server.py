#!/usr/bin/env python3
"""
FastAPI 서버 시작 스크립트
"""

import sys
import os
import uvicorn
from fastapi import FastAPI
from typing import Dict, Any

# 프로젝트 루트를 Python 경로에 추가
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

try:
    from src.main import DateCourseAgent
    print("✅ DateCourseAgent 임포트 성공")
except ImportError as e:
    print(f"❌ DateCourseAgent 임포트 실패: {e}")
    sys.exit(1)

# FastAPI 앱 생성
app = FastAPI(
    title="Date Course Recommendation Agent",
    description="데이트 코스 추천 서브 에이전트",
    version="1.0.0"
)

# 에이전트 인스턴스 생성
try:
    agent = DateCourseAgent()
    print("✅ DateCourseAgent 인스턴스 생성 성공")
except Exception as e:
    print(f"❌ DateCourseAgent 인스턴스 생성 실패: {e}")
    sys.exit(1)

@app.post("/recommend-course")
async def recommend_course(request_data: Dict[str, Any]):
    """데이트 코스 추천 API"""
    try:
        result = await agent.process_request(request_data)
        return result
    except Exception as e:
        return {
            "error": str(e),
            "status": "error",
            "message": "서버 처리 중 오류가 발생했습니다"
        }

@app.get("/health")
async def health_check():
    """헬스 체크 API"""
    try:
        result = await agent.health_check()
        return result
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {"message": "Date Course Recommendation Agent is running"}

if __name__ == "__main__":
    # 포트 설정 (환경변수 우선)
    port = int(os.getenv("DATE_COURSE_AGENT_PORT", "8003"))
    
    print("🚀 FastAPI 서버를 시작합니다...")
    print(f"   - URL: http://localhost:{port}")
    print(f"   - 문서: http://localhost:{port}/docs")
    print("   - 종료: Ctrl+C\n")
    
    # 서버 실행
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info",
        reload=False  # 개발 중이 아니므로 reload 비활성화
    )
