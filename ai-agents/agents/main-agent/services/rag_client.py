"""
RAG Agent와의 A2A 통신 클라이언트
"""

import httpx
import json
import asyncio
from typing import Dict, Any, Optional
import os
from dotenv import load_dotenv

load_dotenv()

class RagAgentClient:
    """RAG Agent와의 HTTP 통신 클라이언트"""
    
    def __init__(self, base_url: str = None, timeout: int = 30):
        self.base_url = base_url or os.getenv("RAG_AGENT_URL", "http://localhost:8000")
        self.timeout = timeout
        
    async def health_check(self) -> Dict[str, Any]:
        """RAG Agent 헬스 체크"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(f"{self.base_url}/health")
                return {
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "status_code": response.status_code,
                    "response": response.json() if response.status_code == 200 else response.text
                }
            except Exception as e:
                return {
                    "status": "error",
                    "error": str(e)
                }
    
    async def search_places(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """장소 검색 요청"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/search/places",
                    json=request_data,
                    headers={"Content-Type": "application/json"}
                )
                
                return {
                    "success": response.status_code == 200,
                    "status_code": response.status_code,
                    "data": response.json() if response.status_code == 200 else None,
                    "error": response.text if response.status_code != 200 else None
                }
                
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e)
                }
    
    async def generate_course(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """코스 생성 요청"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/course/generate",
                    json=request_data,
                    headers={"Content-Type": "application/json"}
                )
                
                return {
                    "success": response.status_code == 200,
                    "status_code": response.status_code,
                    "data": response.json() if response.status_code == 200 else None,
                    "error": response.text if response.status_code != 200 else None
                }
                
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e)
                }

    async def process_rag_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """전체 RAG 처리 요청 (실제 구현된 엔드포인트 사용)"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                # RAG Agent의 실제 구현된 엔드포인트로 요청
                response = await client.post(
                    f"{self.base_url}/recommend-course",
                    json=request_data,
                    headers={"Content-Type": "application/json"}
                )
                
                return {
                    "success": response.status_code == 200,
                    "status_code": response.status_code,
                    "data": response.json() if response.status_code == 200 else None,
                    "error": response.text if response.status_code != 200 else None
                }
                
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e)
                }

# 동기 버전 (기존 코드 호환성용)
def sync_health_check(base_url: str = None) -> Dict[str, Any]:
    """동기 헬스 체크"""
    client = RagAgentClient(base_url)
    return asyncio.run(client.health_check())

def sync_process_rag_request(request_data: Dict[str, Any], base_url: str = None) -> Dict[str, Any]:
    """동기 RAG 요청 처리"""
    client = RagAgentClient(base_url)
    return asyncio.run(client.process_rag_request(request_data))