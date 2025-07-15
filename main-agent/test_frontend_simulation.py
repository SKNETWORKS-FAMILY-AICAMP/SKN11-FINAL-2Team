#!/usr/bin/env python3
"""
프런트엔드 역할 시뮬레이션 테스트 코드
main-agent 서버에 8개 필수 필드를 전달하는 테스트
"""

import requests
import json
from typing import Dict, Any

# 서버 설정
SERVER_URL = "http://localhost:8001"
NEW_SESSION_ENDPOINT = f"{SERVER_URL}/chat/new-session"
SEND_MESSAGE_ENDPOINT = f"{SERVER_URL}/chat/send-message"

def test_complete_8_fields():
    """8개 필드를 모두 채워서 보내는 테스트"""
    print("=== 테스트 1: 8개 필드 완전 전달 ===")
    
    # 8개 필수 필드 완전 데이터
    complete_profile = {
        "age": 25,
        "gender": "여",
        "mbti": "ENFP",
        "relationship_stage": "연인",
        "atmosphere": "로맨틱",
        "budget": "10만원",
        "time_slot": "저녁",
        "transportation": "지하철",
        # 추가 필드들 (선택사항)
        "address": "홍대",
        "free_description": "",
        "general_preferences": [],
        "profile_image_url": ""
    }
    
    request_data = {
        "user_id": "test_user_complete",
        "initial_message": "데이트 코스 추천 받고 싶어요",
        "user_profile": complete_profile
    }
    
    try:
        response = requests.post(NEW_SESSION_ENDPOINT, json=request_data)
        
        if response.status_code == 200:
            result = response.json()
            session_id = result.get("session_id")
            print(f"✅ 세션 생성 성공: {session_id}")
            
            # 대화형 스타일로 초기 응답 출력
            if result.get('response', {}).get('message'):
                bot_message = result['response']['message']
                print(f"\n🤖 Main-Agent: {bot_message}")
                
                # 퀵 리플라이가 있으면 표시
                quick_replies = result.get('response', {}).get('quick_replies', [])
                if quick_replies:
                    print(f"💡 제안: {', '.join(quick_replies)}")
            
            return session_id
        else:
            print(f"❌ 세션 생성 실패: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ 요청 실패: {str(e)}")
        return None

def test_partial_fields():
    """일부 필드만 채워서 보내는 테스트"""
    print("\n=== 테스트 2: 일부 필드만 전달 ===")
    
    # 일부 필드만 채운 데이터
    partial_profile = {
        "age": 30,
        "gender": "남",
        "mbti": "INFP",
        "relationship_stage": "썸",
        # atmosphere, budget, time_slot, transportation 누락
        "address": "강남",
        "free_description": "",
        "general_preferences": [],
        "profile_image_url": ""
    }
    
    request_data = {
        "user_id": "test_user_partial",
        "initial_message": "데이트 코스 추천해주세요",
        "user_profile": partial_profile
    }
    
    try:
        response = requests.post(NEW_SESSION_ENDPOINT, json=request_data)
        
        if response.status_code == 200:
            result = response.json()
            session_id = result.get("session_id")
            print(f"✅ 세션 생성 성공: {session_id}")
            
            # 대화형 스타일로 초기 응답 출력
            if result.get('response', {}).get('message'):
                bot_message = result['response']['message']
                print(f"\n🤖 Main-Agent: {bot_message}")
                
                # 퀵 리플라이가 있으면 표시
                quick_replies = result.get('response', {}).get('quick_replies', [])
                if quick_replies:
                    print(f"💡 제안: {', '.join(quick_replies)}")
            
            return session_id
        else:
            print(f"❌ 세션 생성 실패: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ 요청 실패: {str(e)}")
        return None

def test_empty_fields():
    """빈 필드들로 보내는 테스트 (기존 방식)"""
    print("\n=== 테스트 3: 빈 필드들 전달 (기존 방식) ===")
    
    # 거의 빈 데이터
    empty_profile = {
        "age": None,
        "gender": "",
        "mbti": "",
        "relationship_stage": "",
        "atmosphere": "",
        "budget": "",
        "time_slot": "",
        "transportation": "",
        "address": "",
        "free_description": "",
        "general_preferences": [],
        "profile_image_url": ""
    }
    
    request_data = {
        "user_id": "test_user_empty",
        "initial_message": "25살 여자고 ENFP에요. 남자친구와 로맨틱한 데이트하고 싶어요",
        "user_profile": empty_profile
    }
    
    try:
        response = requests.post(NEW_SESSION_ENDPOINT, json=request_data)
        
        if response.status_code == 200:
            result = response.json()
            session_id = result.get("session_id")
            print(f"✅ 세션 생성 성공: {session_id}")
            
            # 대화형 스타일로 초기 응답 출력
            if result.get('response', {}).get('message'):
                bot_message = result['response']['message']
                print(f"\n🤖 Main-Agent: {bot_message}")
                
                # 퀵 리플라이가 있으면 표시
                quick_replies = result.get('response', {}).get('quick_replies', [])
                if quick_replies:
                    print(f"💡 제안: {', '.join(quick_replies)}")
            
            return session_id
        else:
            print(f"❌ 세션 생성 실패: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ 요청 실패: {str(e)}")
        return None

def test_send_message(session_id: str, message: str, show_full_response: bool = False):
    """메시지 전송 테스트"""
    request_data = {
        "session_id": session_id,
        "message": message,
        "user_id": "test_user",
        "user_profile": {
            "age": 25,
            "gender": "여",
            "mbti": "ENFP",
            "relationship_stage": "연인",
            "atmosphere": "로맨틱",
            "budget": "10만원",
            "time_slot": "저녁",
            "transportation": "지하철"
        }
    }
    
    try:
        response = requests.post(SEND_MESSAGE_ENDPOINT, json=request_data)
        
        if show_full_response:
            print(f"상태 코드: {response.status_code}")
            print(f"응답: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
        
        if response.status_code == 200:
            result = response.json()
            
            # 대화형 스타일로 응답 출력
            if result.get('response', {}).get('message'):
                bot_message = result['response']['message']
                print(f"\n🤖 Main-Agent: {bot_message}")
                
                # 퀵 리플라이가 있으면 표시
                quick_replies = result.get('response', {}).get('quick_replies', [])
                if quick_replies:
                    print(f"💡 제안: {', '.join(quick_replies)}")
            
            return True
        else:
            print(f"❌ 메시지 전송 실패: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 요청 실패: {str(e)}")
        return False

def check_server_health():
    """서버 상태 확인"""
    print("=== 서버 상태 확인 ===")
    try:
        response = requests.get(f"{SERVER_URL}/api/health")
        if response.status_code == 200:
            print("✅ 서버 정상 작동")
            result = response.json()
            print(f"📋 서비스: {result.get('service', 'unknown')}")
            print(f"📋 포트: {result.get('port', 'unknown')}")
            return True
        else:
            print(f"❌ 서버 응답 이상: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 서버 연결 실패: {str(e)}")
        print("💡 main-agent 서버가 실행되고 있는지 확인하세요.")
        print("💡 실행 명령: cd /mnt/d/SK-AI/final-project/ttt/main-agent && python server.py")
        return False

def interactive_test(session_id: str):
    """대화형 테스트 함수"""
    print(f"\n🎮 대화형 테스트 시작 (세션 ID: {session_id})")
    print("💡 'quit' 입력시 종료")
    print("-" * 50)
    
    while True:
        user_input = input("\n👤 You: ")
        
        if user_input.lower() in ['quit', 'exit', '종료']:
            print("👋 테스트 종료")
            break
        
        if not user_input.strip():
            continue
        
        success = test_send_message(session_id, user_input)
        
        if not success:
            print("❌ 메시지 전송 실패")
            break

def main():
    """메인 테스트 함수"""
    print("🚀 main-agent 프런트엔드 시뮬레이션 테스트 시작")
    print("=" * 60)
    
    # 서버 상태 확인
    if not check_server_health():
        return
    
    print("\n📋 테스트 옵션을 선택하세요:")
    print("1. 자동 테스트 (기존 방식)")
    print("2. 대화형 테스트 (8개 필드 완전 전달)")
    print("3. 대화형 테스트 (일부 필드만 전달)")
    print("4. 대화형 테스트 (빈 필드들 전달)")
    
    choice = input("\n선택 (1-4): ").strip()
    
    if choice == "1":
        # 기존 자동 테스트
        print("\n🤖 자동 테스트 실행")
        
        # 테스트 1: 8개 필드 완전 전달
        session_id_1 = test_complete_8_fields()
        if session_id_1:
            # 완전한 필드로 생성된 세션에서 추가 메시지 테스트
            print("\n👤 You: 활발한 성격이고 새로운 경험을 좋아해요")
            test_send_message(session_id_1, "활발한 성격이고 새로운 경험을 좋아해요")
        
        # 테스트 2: 일부 필드만 전달
        session_id_2 = test_partial_fields()
        if session_id_2:
            # 부분 필드로 생성된 세션에서 누락 정보 보완 테스트
            print("\n👤 You: 로맨틱한 분위기")
            test_send_message(session_id_2, "로맨틱한 분위기")
        
        # 테스트 3: 빈 필드들 전달 (기존 방식)
        session_id_3 = test_empty_fields()
        if session_id_3:
            # 빈 필드로 생성된 세션에서 대화 테스트
            print("\n👤 You: 예산은 15만원 정도")
            test_send_message(session_id_3, "예산은 15만원 정도")
    
    elif choice == "2":
        # 8개 필드 완전 전달 + 대화형 테스트
        print("\n🎯 8개 필드 완전 전달 + 대화형 테스트")
        session_id = test_complete_8_fields()
        if session_id:
            interactive_test(session_id)
    
    elif choice == "3":
        # 일부 필드만 전달 + 대화형 테스트
        print("\n🎯 일부 필드만 전달 + 대화형 테스트")
        session_id = test_partial_fields()
        if session_id:
            interactive_test(session_id)
    
    elif choice == "4":
        # 빈 필드들 전달 + 대화형 테스트
        print("\n🎯 빈 필드들 전달 + 대화형 테스트")
        session_id = test_empty_fields()
        if session_id:
            interactive_test(session_id)
    
    else:
        print("❌ 잘못된 선택입니다.")
        return
    
    print("\n" + "=" * 60)
    print("🎯 테스트 완료")
    print("💡 각 테스트 케이스의 동작 방식:")
    print("   - 완전한 8개 필드 → 바로 free_description 수집 (필수) → duration, place_count 질문")
    print("   - 부분 필드 → 누락된 필드 먼저 수집 → free_description → duration, place_count")
    print("   - 빈 필드 → 기존 방식대로 8개 필드 대화 수집 → free_description → duration, place_count")

if __name__ == "__main__":
    main()