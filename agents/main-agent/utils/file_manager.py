import json
import os
from typing import Dict, Any

class FileManager:
    """파일 저장/로드 관리 유틸리티"""
    
    def __init__(self, base_path: str = "."):
        self.base_path = base_path
        self.ensure_directories()
    
    def ensure_directories(self):
        """필요한 디렉토리들 생성"""
        dirs = [
            "profiles",
            "requests/place", 
            "requests/rag"
        ]
        for dir_path in dirs:
            full_path = os.path.join(self.base_path, dir_path)
            os.makedirs(full_path, exist_ok=True)
    
    def save_profile(self, session_id: str, profile_data: Dict[str, Any]) -> str:
        """프로필 데이터 저장"""
        filename = f"profiles/profile_detail_{session_id}.json"
        filepath = os.path.join(self.base_path, filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(profile_data, f, ensure_ascii=False, indent=2)
        
        return filename
    
    def save_place_agent_request(self, session_id: str, request_data: Dict[str, Any]) -> str:
        """Place Agent 요청 데이터 저장"""
        filename = f"requests/place/place_agent_request_{session_id}.json"
        filepath = os.path.join(self.base_path, filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(request_data, f, ensure_ascii=False, indent=2)
        
        return filename
    
    def save_rag_agent_request(self, session_id: str, request_data: Dict[str, Any]) -> str:
        """RAG Agent 요청 데이터 저장"""
        filename = f"requests/rag/rag_agent_request_{session_id}.json"
        filepath = os.path.join(self.base_path, filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(request_data, f, ensure_ascii=False, indent=2)
        
        return filename
    
    def load_profile(self, session_id: str) -> Dict[str, Any]:
        """프로필 데이터 로드"""
        filename = f"profiles/profile_detail_{session_id}.json"
        filepath = os.path.join(self.base_path, filename)
        
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}
    
    def load_sample_place_response(self) -> Dict[str, Any]:
        """샘플 Place Agent 응답 로드"""
        filepath = os.path.join(self.base_path, "sample_place_agent_response.json")
        
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}
    
    def list_profiles(self) -> list:
        """저장된 프로필 목록 반환"""
        profiles_dir = os.path.join(self.base_path, "profiles")
        if not os.path.exists(profiles_dir):
            return []
        
        files = [f for f in os.listdir(profiles_dir) if f.endswith('.json')]
        return files
    
    def delete_profile(self, session_id: str) -> bool:
        """프로필 삭제"""
        filename = f"profiles/profile_detail_{session_id}.json"
        filepath = os.path.join(self.base_path, filename)
        
        if os.path.exists(filepath):
            os.remove(filepath)
            return True
        return False