#!/usr/bin/env python3
"""
웹 채팅 클라이언트
Main Agent와 채팅하면서 백엔드에서 Place Agent와 RAG Agent 자동 연동
"""

import requests
import json
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

class WebChatClient:
    """웹 채팅 클라이언트"""
    
    def __init__(self, main_agent_url: str = "http://localhost:8000"):
        self.main_agent_url = main_agent_url
        self.session_id = f"chat_{uuid.uuid4().hex[:8]}"
        self.conversation_history = []
        
    def check_connection(self) -> bool:
        """Main Agent 연결 확인"""
        try:
            response = requests.get(f"{self.main_agent_url}/api/v1/health", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def send_chat_message(self, message: str) -> Dict[str, Any]:
        """채팅 메시지 전송 및 전체 플로우 실행"""
        print(f"\n💬 사용자: {message}")
        print("🤖 처리 중...")
        
        # 채팅 요청 데이터
        chat_data = {
            "session_id": self.session_id,
            "user_message": message,
            "timestamp": datetime.now().isoformat()
        }
        
        # 대화 히스토리에 추가
        self.conversation_history.append({
            "role": "user",
            "content": message,
            "timestamp": datetime.now().isoformat()
        })
        
        try:
            # 새로운 통합 채팅 엔드포인트로 요청
            response = requests.post(
                f"{self.main_agent_url}/api/v1/chat/complete_flow",
                json=chat_data,
                headers={"Content-Type": "application/json"},
                timeout=120  # 전체 플로우는 시간이 오래 걸릴 수 있음
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # 결과 출력
                self._display_response(result)
                
                # 대화 히스토리에 추가
                self.conversation_history.append({
                    "role": "assistant", 
                    "content": result,
                    "timestamp": datetime.now().isoformat()
                })
                
                return result
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                print(f"❌ 오류: {error_msg}")
                return {"success": False, "error": error_msg}
                
        except requests.exceptions.Timeout:
            error_msg = "요청 타임아웃 (120초 초과)"
            print(f"❌ 오류: {error_msg}")
            return {"success": False, "error": error_msg}
        except Exception as e:
            error_msg = f"연결 오류: {str(e)}"
            print(f"❌ 오류: {error_msg}")
            return {"success": False, "error": error_msg}
    
    def _display_response(self, result: Dict[str, Any]):
        """응답 결과 표시"""
        if not result.get("success"):
            print(f"❌ 실패: {result.get('message', '알 수 없는 오류')}")
            return
        
        print(f"✅ 성공: {result.get('message', '처리 완료')}")
        
        # 단계별 결과 표시
        flow_results = result.get("flow_results", {})
        
        # 1. 프로필 추출 결과
        if "profile_extraction" in flow_results:
            profile_result = flow_results["profile_extraction"]
            print(f"\n📋 프로필 추출: {profile_result.get('status', 'N/A')}")
            if profile_result.get("extracted_info"):
                info = profile_result["extracted_info"]
                print("   추출된 정보:")
                for key, value in info.items():
                    if value:
                        print(f"   • {key}: {value}")
        
        # 2. Place Agent 결과
        if "place_agent" in flow_results:
            place_result = flow_results["place_agent"]
            print(f"\n📍 장소 추천: {place_result.get('status', 'N/A')}")
            if place_result.get("success") and place_result.get("data"):
                locations = place_result["data"].get("locations", [])
                print(f"   추천된 장소 수: {len(locations)}")
                for i, location in enumerate(locations, 1):
                    area = location.get("area_name", "N/A")
                    coords = location.get("coordinates", {})
                    lat = coords.get("latitude", "N/A")
                    lng = coords.get("longitude", "N/A") 
                    print(f"   {i}. {area} ({lat}, {lng})")
        
        # 3. RAG Agent 결과
        if "rag_agent" in flow_results:
            rag_result = flow_results["rag_agent"]
            print(f"\n🗓️ 코스 생성: {rag_result.get('status', 'N/A')}")
            if rag_result.get("success") and rag_result.get("data"):
                course_data = rag_result["data"]
                if "course" in course_data:
                    course = course_data["course"]
                    places = course.get("places", [])
                    print(f"   생성된 코스 장소 수: {len(places)}")
                    
                    # 코스 상세 정보 출력
                    for i, place in enumerate(places, 1):
                        name = place.get("name", "N/A")
                        category = place.get("category", "N/A")
                        area = place.get("area_name", "N/A")
                        print(f"   {i}. [{category}] {name} ({area})")
                        
                        # 추천 이유나 설명이 있다면 출력
                        if place.get("description"):
                            print(f"      💬 {place['description'][:100]}...")
                    
                    # 총 소요시간이나 거리 정보가 있다면 출력
                    if course.get("total_duration"):
                        print(f"   ⏱️ 총 소요시간: {course['total_duration']}")
                    if course.get("total_distance"):
                        print(f"   📏 총 이동거리: {course['total_distance']}")
        
        # 최종 추천 메시지
        if result.get("final_recommendation"):
            print(f"\n💡 최종 추천:\n{result['final_recommendation']}")
    
    def get_session_info(self) -> Dict[str, Any]:
        """현재 세션 정보 조회"""
        try:
            response = requests.get(
                f"{self.main_agent_url}/api/v1/profile/{self.session_id}",
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}
    
    def clear_session(self) -> bool:
        """세션 초기화"""
        try:
            response = requests.delete(
                f"{self.main_agent_url}/api/v1/session/{self.session_id}",
                timeout=10
            )
            if response.status_code == 200:
                result = response.json()
                success = result.get("cleared", False)
                if success:
                    self.conversation_history.clear()
                    self.session_id = f"chat_{uuid.uuid4().hex[:8]}"
                return success
            return False
        except Exception as e:
            return False
    
    def show_conversation_history(self):
        """대화 히스토리 표시"""
        print(f"\n📜 대화 히스토리 (세션: {self.session_id})")
        print("=" * 70)
        
        for i, entry in enumerate(self.conversation_history, 1):
            role = entry["role"]
            timestamp = entry["timestamp"]
            
            if role == "user":
                print(f"{i:2d}. 👤 사용자 ({timestamp})")
                print(f"    {entry['content']}")
            else:
                print(f"{i:2d}. 🤖 Assistant ({timestamp})")
                content = entry["content"]
                if isinstance(content, dict):
                    if content.get("success"):
                        print(f"    ✅ {content.get('message', '처리 완료')}")
                    else:
                        print(f"    ❌ {content.get('message', '처리 실패')}")
                else:
                    print(f"    {content}")
        
        print("=" * 70)
    
    def start_interactive_chat(self):
        """대화형 채팅 시작"""
        print("🌐 웹 채팅 클라이언트 시작")
        print("=" * 50)
        print(f"세션 ID: {self.session_id}")
        print(f"Main Agent URL: {self.main_agent_url}")
        print("=" * 50)
        print("명령어:")
        print("  /info - 세션 정보 조회")
        print("  /history - 대화 히스토리 보기")
        print("  /clear - 세션 초기화")
        print("  /quit - 종료")
        print("=" * 50)
        
        # 연결 확인
        if not self.check_connection():
            print("❌ Main Agent에 연결할 수 없습니다.")
            print("   서버가 실행 중인지 확인하세요:")
            print("   python start_all_servers.py")
            return
        
        print("✅ Main Agent에 연결되었습니다.")
        print("\n💡 메시지를 입력하세요:")
        print("   예: '29살 INTP 연인과 이촌동에서 로맨틱한 밤 데이트 3곳 추천해줘'")
        
        while True:
            try:
                user_input = input(f"\n[{self.session_id}] You: ").strip()
                
                if not user_input:
                    continue
                
                # 명령어 처리
                if user_input == "/quit":
                    print("\n👋 채팅을 종료합니다.")
                    break
                    
                elif user_input == "/info":
                    info = self.get_session_info()
                    print("\n📋 세션 정보:")
                    print(json.dumps(info, ensure_ascii=False, indent=2))
                    continue
                    
                elif user_input == "/history":
                    self.show_conversation_history()
                    continue
                    
                elif user_input == "/clear":
                    if self.clear_session():
                        print("✅ 세션이 초기화되었습니다.")
                        print(f"🆔 새 세션 ID: {self.session_id}")
                    else:
                        print("❌ 세션 초기화에 실패했습니다.")
                    continue
                
                # 일반 채팅 메시지 처리
                start_time = time.time()
                result = self.send_chat_message(user_input)
                end_time = time.time()
                
                print(f"\n⏱️ 처리 시간: {end_time - start_time:.1f}초")
                
            except KeyboardInterrupt:
                print("\n\n👋 채팅을 종료합니다.")
                break
            except Exception as e:
                print(f"\n❌ 예상치 못한 오류: {e}")

def main():
    """메인 실행 함수"""
    print("🚀 웹 채팅 클라이언트")
    
    # Main Agent URL 설정
    main_agent_url = "http://localhost:8000"
    
    # 환경변수에서 URL 가져오기 (선택사항)
    import os
    if os.getenv("MAIN_AGENT_URL"):
        main_agent_url = os.getenv("MAIN_AGENT_URL")
    
    client = WebChatClient(main_agent_url)
    
    print("\n실행 모드를 선택하세요:")
    print("1. 대화형 채팅")
    print("2. 빠른 테스트")
    print("3. 연결 테스트만")
    
    try:
        choice = input("\n선택 (1-3): ").strip()
    except KeyboardInterrupt:
        print("\n👋 종료합니다.")
        return
    
    if choice == "1":
        client.start_interactive_chat()
        
    elif choice == "2":
        print("\n🎯 빠른 테스트 실행")
        test_message = "29살 INTP 연인과 이촌동에서 로맨틱한 밤 데이트를 하고 싶어. 도보로 이동 가능한 3곳 추천해줘."
        
        if client.check_connection():
            result = client.send_chat_message(test_message)
            print(f"\n🏁 테스트 완료")
        else:
            print("❌ 서버 연결 실패")
    
    elif choice == "3":
        print("\n🔍 연결 테스트")
        if client.check_connection():
            print("✅ Main Agent 연결 성공")
        else:
            print("❌ Main Agent 연결 실패")
            print("   서버를 시작하세요: python start_all_servers.py")
    
    else:
        print("❌ 잘못된 선택입니다.")

if __name__ == "__main__":
    main()