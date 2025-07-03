#!/usr/bin/env python3
"""
개선된 웹 채팅 클라이언트 v2
새로운 API 구조에 맞춘 채팅 클라이언트
- /chat: 일반 채팅 (맥락 유지)
- /recommend: 추천 시작 (전체 플로우)
- /session/{id}: 세션 복원
"""

import requests
import json
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

class WebChatClientV2:
    """개선된 웹 채팅 클라이언트"""
    
    def __init__(self, main_agent_url: str = "http://localhost:8000"):
        self.main_agent_url = main_agent_url
        self.session_id = f"chat_{uuid.uuid4().hex[:8]}"
        self.conversation_history = []
        self.profile_completed = False
        
    def check_connection(self) -> bool:
        """Main Agent 연결 확인"""
        try:
            response = requests.get(f"{self.main_agent_url}/api/health", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def chat_with_agent(self, message: str) -> Dict[str, Any]:
        """일반 채팅 메시지 전송"""
        print(f"\n💬 사용자: {message}")
        print("🤖 처리 중...")
        
        # 채팅 요청 데이터
        chat_data = {
            "session_id": self.session_id,
            "user_message": message,
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        # 대화 히스토리에 추가
        self.conversation_history.append({
            "role": "user",
            "content": message,
            "timestamp": datetime.datetime.now().isoformat()
        })
        
        try:
            # 일반 채팅 API 호출
            response = requests.post(
                f"{self.main_agent_url}/chat",
                json=chat_data,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # 결과 출력
                self._display_chat_response(result)
                
                # 프로필 완성 상태 업데이트
                if result.get("needs_recommendation"):
                    self.profile_completed = True
                
                # 대화 히스토리에 추가
                self.conversation_history.append({
                    "role": "assistant", 
                    "content": result,
                    "timestamp": datetime.datetime.now().isoformat()
                })
                
                return result
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                print(f"❌ 오류: {error_msg}")
                return {"success": False, "error": error_msg}
                
        except requests.exceptions.Timeout:
            error_msg = "요청 타임아웃 (30초 초과)"
            print(f"❌ 오류: {error_msg}")
            return {"success": False, "error": error_msg}
        except Exception as e:
            error_msg = f"연결 오류: {str(e)}"
            print(f"❌ 오류: {error_msg}")
            return {"success": False, "error": error_msg}
    
    def start_recommendation(self) -> Dict[str, Any]:
        """추천 시작 (전체 플로우 실행)"""
        print(f"\n🎯 추천 시작 중...")
        print("   Place Agent → RAG Agent 플로우 실행...")
        
        # 추천 요청 데이터
        recommend_data = {
            "session_id": self.session_id
        }
        
        try:
            # 추천 API 호출
            response = requests.post(
                f"{self.main_agent_url}/recommend",
                json=recommend_data,
                headers={"Content-Type": "application/json"},
                timeout=120  # 추천 처리는 시간이 오래 걸릴 수 있음
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # 결과 출력
                self._display_recommendation_response(result)
                
                return result
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                print(f"❌ 추천 실패: {error_msg}")
                return {"success": False, "error": error_msg}
                
        except requests.exceptions.Timeout:
            error_msg = "추천 타임아웃 (120초 초과)"
            print(f"❌ 오류: {error_msg}")
            return {"success": False, "error": error_msg}
        except Exception as e:
            error_msg = f"연결 오류: {str(e)}"
            print(f"❌ 오류: {error_msg}")
            return {"success": False, "error": error_msg}
    
    def restore_session(self, session_id: str) -> bool:
        """세션 복원"""
        print(f"\n🔄 세션 복원 중: {session_id}")
        
        try:
            response = requests.get(
                f"{self.main_agent_url}/session/{session_id}",
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get("exists"):
                    self.session_id = session_id
                    self.profile_completed = result.get("needs_recommendation", False)
                    
                    print("✅ 세션 복원 성공")
                    print(f"   프로필 상태: {result.get('profile_status')}")
                    print(f"   추천 가능: {result.get('needs_recommendation')}")
                    
                    if result.get("extracted_info"):
                        print("   추출된 정보:")
                        for key, value in result["extracted_info"].items():
                            print(f"   • {key}: {value}")
                    
                    return True
                else:
                    print("❌ 세션을 찾을 수 없습니다")
                    return False
            else:
                print(f"❌ 세션 복원 실패: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ 세션 복원 오류: {e}")
            return False
    
    def _display_chat_response(self, result: Dict[str, Any]):
        """채팅 응답 표시"""
        if not result.get("success"):
            print(f"❌ 실패: {result.get('message', '알 수 없는 오류')}")
            return
        
        print(f"✅ {result.get('message', '처리 완료')}")
        
        # 프로필 상태 표시
        profile_status = result.get("profile_status", "incomplete")
        print(f"📋 프로필 상태: {profile_status}")
        
        # 추출된 정보 표시
        if result.get("extracted_info"):
            print("   추출된 정보:")
            for key, value in result["extracted_info"].items():
                if value:
                    print(f"   • {key}: {value}")
        
        # 추천 준비 완료 안내
        if result.get("recommendation_ready"):
            print(f"🎯 {result.get('next_action', '추천을 시작할 수 있습니다')}")
            print("   명령어: /recommend")
        
        # 제안사항 표시
        if result.get("suggestions"):
            print(f"💡 제안: {', '.join(result['suggestions'])}")
    
    def _display_recommendation_response(self, result: Dict[str, Any]):
        """추천 응답 표시"""
        if not result.get("success"):
            print(f"❌ 추천 실패: {result.get('message', '알 수 없는 오류')}")
            
            # 플로우 결과가 있다면 상세 정보 표시
            if result.get("flow_results"):
                print("상세 정보:")
                flow_results = result["flow_results"]
                
                if "place_agent" in flow_results:
                    place_result = flow_results["place_agent"]
                    print(f"   - Place Agent: {place_result.get('status', 'N/A')}")
                    if place_result.get("error"):
                        print(f"     오류: {place_result['error']}")
                
                if "rag_agent" in flow_results:
                    rag_result = flow_results["rag_agent"]
                    print(f"   - RAG Agent: {rag_result.get('status', 'N/A')}")
                    if rag_result.get("error"):
                        print(f"     오류: {rag_result['error']}")
            return
        
        print(f"✅ {result.get('message', '추천 완료')}")
        
        # 추천 결과 표시
        if result.get("recommendation"):
            recommendation = result["recommendation"]
            
            # 장소 정보
            places = recommendation.get("places", [])
            print(f"\n📍 추천된 장소 ({len(places)}곳):")
            for i, place in enumerate(places, 1):
                area = place.get("area_name", "N/A")
                coords = place.get("coordinates", {})
                lat = coords.get("latitude", "N/A")
                lng = coords.get("longitude", "N/A")
                reason = place.get("reason", "")
                print(f"   {i}. {area} ({lat}, {lng})")
                if reason:
                    print(f"      💬 {reason}")
            
            # 코스 정보
            course = recommendation.get("course", {})
            if course and isinstance(course, dict):
                print(f"\n🗓️ 생성된 데이트 코스:")
                
                # course가 직접적인 응답인 경우
                if "course" in course:
                    course_data = course["course"]
                    if "places" in course_data:
                        course_places = course_data["places"]
                        print(f"   코스 장소 수: {len(course_places)}")
                        
                        for i, place in enumerate(course_places, 1):
                            name = place.get("name", "N/A")
                            category = place.get("category", "N/A")
                            area = place.get("area_name", "N/A")
                            print(f"   {i}. [{category}] {name} ({area})")
                            
                            if place.get("description"):
                                print(f"      💬 {place['description'][:100]}...")
                        
                        # 추가 정보
                        if course_data.get("total_duration"):
                            print(f"   ⏱️ 총 소요시간: {course_data['total_duration']}")
                        if course_data.get("total_distance"):
                            print(f"   📏 총 이동거리: {course_data['total_distance']}")
                else:
                    # course가 최상위 응답인 경우
                    print(f"   응답 키: {list(course.keys())}")
            
            # 생성 시간
            created_at = recommendation.get("created_at")
            if created_at:
                print(f"\n📅 생성 시간: {created_at}")
    
    def clear_session(self) -> bool:
        """세션 초기화"""
        try:
            response = requests.delete(
                f"{self.main_agent_url}/session/{self.session_id}",
                timeout=10
            )
            if response.status_code == 200:
                result = response.json()
                success = result.get("cleared", False)
                if success:
                    self.conversation_history.clear()
                    self.profile_completed = False
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
        """대화형 채팅 시작 (정보수집 → 추천까지 자동 진행)"""
        print("🌐 개선된 웹 채팅 클라이언트 v2 (정보수집 자동화)")
        print("=" * 50)
        print(f"세션 ID: {self.session_id}")
        print(f"Main Agent URL: {self.main_agent_url}")
        print("=" * 50)
        print("명령어:")
        print("  /recommend - 추천 시작 (프로필 완성 후)")
        print("  /restore <session_id> - 세션 복원")
        print("  /history - 대화 히스토리 보기")
        print("  /clear - 세션 초기화")
        print("  /status - 현재 상태 확인")
        print("  /quit - 종료")
        print("=" * 50)
        
        # 연결 확인
        if not self.check_connection():
            print("❌ Main Agent에 연결할 수 없습니다.")
            print("   서버가 실행 중인지 확인하세요:")
            print("   python start_all_servers.py")
            return
        
        print("✅ Main Agent에 연결되었습니다.")
        print("\n💡 시작해보세요:")
        print("   예: '29살 INTP 연인과 이촌동에서 로맨틱한 밤 데이트 3곳 추천해줘'")
        print("   또는: '안녕하세요! 데이트 코스 추천을 받고 싶어요'")
        
        while True:
            try:
                user_input = input(f"\n[{self.session_id[:8]}] You: ").strip()
                
                if not user_input:
                    continue
                
                # 명령어 처리
                if user_input == "/quit":
                    print("\n👋 채팅을 종료합니다.")
                    break
                
                elif user_input == "/recommend":
                    if not self.profile_completed:
                        print("❌ 아직 프로필이 완성되지 않았습니다.")
                        print("   더 많은 정보를 제공해주세요.")
                    else:
                        start_time = time.time()
                        result = self.start_recommendation()
                        end_time = time.time()
                        print(f"\n⏱️ 추천 처리 시간: {end_time - start_time:.1f}초")
                    continue
                
                elif user_input.startswith("/restore "):
                    session_id = user_input[9:].strip()
                    if session_id:
                        self.restore_session(session_id)
                    else:
                        print("❌ 세션 ID를 입력하세요. 예: /restore chat_12345678")
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
                
                elif user_input == "/status":
                    print(f"\n📊 현재 상태:")
                    print(f"   세션 ID: {self.session_id}")
                    print(f"   프로필 완성: {'✅' if self.profile_completed else '❌'}")
                    print(f"   대화 수: {len(self.conversation_history)}")
                    print(f"   추천 가능: {'✅' if self.profile_completed else '❌'}")
                    continue
                
                # 일반 채팅 메시지 처리 (질문-응답 루프)
                while True:
                    start_time = time.time()
                    result = self.chat_with_agent(user_input)
                    end_time = time.time()
                    print(f"\n⏱️ 처리 시간: {end_time - start_time:.1f}초")

                    # assistant가 추가 질문(정보수집) 메시지를 반환하면, 바로 사용자 입력을 다시 받음
                    if result.get("message") and not self.profile_completed:
                        # assistant의 질문 출력 후 사용자 입력 받기
                        user_input = input(f"\n[{self.session_id[:8]}] (질문) {result['message']}\nYou: ").strip()
                        if not user_input:
                            continue
                        # 루프 계속 (다음 정보 입력)
                        continue
                    # 프로필이 완성되면 추천까지 자동 진행
                    if self.profile_completed:
                        print("\n💡 프로필이 완성되었습니다! 추천을 바로 시작합니다.")
                        rec_start = time.time()
                        rec_result = self.start_recommendation()
                        rec_end = time.time()
                        print(f"\n⏱️ 추천 처리 시간: {rec_end - rec_start:.1f}초")
                        break
                    # 기타 종료 조건
                    break
                # 추천까지 끝나면 대화 종료(옵션)
                if self.profile_completed:
                    print("\n[전체 플로우가 완료되었습니다!]")
                    break
            except KeyboardInterrupt:
                print("\n\n👋 채팅을 종료합니다.")
                break
            except Exception as e:
                print(f"\n❌ 예상치 못한 오류: {e}")

def main():
    """메인 실행 함수"""
    print("🚀 개선된 웹 채팅 클라이언트 v2")
    
    # Main Agent URL 설정
    main_agent_url = "http://localhost:8000"
    
    client = WebChatClientV2(main_agent_url)
    
    print("\n실행 모드를 선택하세요:")
    print("1. 대화형 채팅")
    print("2. 빠른 테스트 (채팅 → 추천)")
    print("3. 세션 복원 테스트")
    print("4. 연결 테스트만")
    
    try:
        choice = input("\n선택 (1-4): ").strip()
    except KeyboardInterrupt:
        print("\n👋 종료합니다.")
        return
    
    if choice == "1":
        client.start_interactive_chat()
        
    elif choice == "2":
        print("\n🎯 빠른 테스트 실행")
        
        if not client.check_connection():
            print("❌ 서버 연결 실패")
            return
        
        # 1단계: 채팅
        test_message = "29살 INTP 연인과 이촌동에서 로맨틱한 밤 데이트를 하고 싶어. 도보로 이동 가능한 3곳 추천해줘."
        print(f"\n1️⃣ 채팅 테스트")
        chat_result = client.chat_with_agent(test_message)
        
        # 2단계: 추천 (프로필이 완성된 경우)
        if chat_result.get("needs_recommendation"):
            print(f"\n2️⃣ 추천 테스트")
            time.sleep(2)
            recommend_result = client.start_recommendation()
            print(f"\n🏁 전체 테스트 완료")
        else:
            print("\n⚠️ 프로필이 완성되지 않아 추천을 시작할 수 없습니다.")
    
    elif choice == "3":
        print("\n🔄 세션 복원 테스트")
        session_id = input("복원할 세션 ID를 입력하세요: ").strip()
        if session_id:
            if client.restore_session(session_id):
                print("세션 복원 성공! 대화형 모드로 전환합니다.")
                client.start_interactive_chat()
            else:
                print("세션 복원 실패")
        else:
            print("세션 ID가 입력되지 않았습니다.")
    
    elif choice == "4":
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