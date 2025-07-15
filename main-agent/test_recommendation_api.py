#!/usr/bin/env python3
"""
추천 API 전용 테스트 클라이언트
"""

import requests
import json

BASE_URL = "http://localhost:8001"

def test_start_recommendation():
    """추천 시작 API 테스트"""
    
    # 1. 새 세션 생성
    print("=== 1. 새 세션 생성 ===")
    new_session_data = {
        "user_id": "12345",
        "initial_message": "이태원에서 28살 여자친구랑 ENFP 성격에 맞는 로맨틱한 저녁 데이트 하고 싶어. 예산은 10만원 정도 생각하고 지하철로 이동할 예정이야. 조용한 실내 분위기 좋아해",
        "user_profile": {
            "gender": "MALE",
            "age": 28,
            "mbti": "ENFP",
            "address": "서울시 용산구",
            "car_owned": False,
            "description": "카페 투어를 좋아하는 개발자입니다",
            "relationship_stage": "연인",
            "general_preferences": ["조용한 곳", "야외", "디저트"],
            "profile_image_url": "https://example.com/profile.jpg",
            "atmosphere": "로맨틱한",
            "budget": "10만원",
            "time_slot": "저녁",
            "transportation": "지하철",
            "place_count": 3
        }
    }
    
    response = requests.post(f"{BASE_URL}/chat/new-session", json=new_session_data)
    session_result = response.json()
    session_id = session_result["session_id"]
    print(f"세션 생성 완료: {session_id}")
    print(f"응답: {session_result['response']['message'][:100]}...")
    
    # 2. 정보 수집 완료까지 시뮬레이션 (이미 프로필에 모든 정보가 있다고 가정)
    print("\n=== 2. 정보 수집 시뮬레이션 ===")
    messages = [
        "28살이야",
        "ENFP",
        "연인",
        "로맨틱한 분위기",
        "10만원 정도",
        "저녁 시간대",
        "아니오"  # 추가 정보 입력 안함
    ]
    
    for msg in messages:
        send_data = {
            "session_id": session_id,
            "message": msg,
            "user_id": "12345",
            "user_profile": new_session_data["user_profile"]
        }
        
        response = requests.post(f"{BASE_URL}/chat/send-message", json=send_data)
        result = response.json()
        print(f"입력: {msg} → 응답: {result['response']['message'][:50]}...")
        
        # 추천 준비 완료 메시지 확인
        if "추천을 시작하시려면" in result['response']['message']:
            print("✅ 정보 수집 완료!")
            break
    
    # 3. 추천 시작
    print("\n=== 3. 추천 시작 ===")
    recommendation_data = {
        "session_id": session_id
    }
    
    print("추천 요청 전송 중...")
    response = requests.post(f"{BASE_URL}/chat/start-recommendation", json=recommendation_data)
    
    if response.status_code == 200:
        result = response.json()
        
        if result["success"]:
            print("🎉 추천 성공!")
            print(f"메시지: {result['message']}")
            
            # 코스 데이터 분석
            course_data = result.get("course_data", {})
            places = course_data.get("places", [])
            course = course_data.get("course", {})
            
            print(f"\n📍 총 추천 장소: {len(places)}개")
            for i, place in enumerate(places[:3]):  # 처음 3개만 표시
                print(f"  {i+1}. {place.get('name', 'Unknown')} ({place.get('category', 'Unknown')})")
            
            # 날씨별 코스 정보 - RAG Agent 응답 구조에 맞춤
            results = course.get("results", {})
            sunny_courses = results.get("sunny_weather", [])
            rainy_courses = results.get("rainy_weather", [])
            
            print(f"\n☀️ 맑은 날 코스: {len(sunny_courses)}개")
            print(f"🌧️ 비오는 날 코스: {len(rainy_courses)}개")
            
            # 세션 정보
            session_info = result.get("session_info", {})
            print(f"\n📋 세션 상태: {session_info.get('session_status')}")
            print(f"📋 코스 생성 완료: {session_info.get('has_course')}")
            
            # 처리 정보
            processing_info = result.get("processing_info", {})
            if processing_info:
                print(f"\n📊 처리 정보:")
                print(f"  ⏱️ 총 처리 시간: {processing_info.get('total_processing_time', 'Unknown')}초")
                print(f"  📍 추천 장소 수: {processing_info.get('place_count', 'Unknown')}개")
                print(f"  ☀️ 맑은 날 코스: {processing_info.get('sunny_course_count', 'Unknown')}개")
                print(f"  🌧️ 비오는 날 코스: {processing_info.get('rainy_course_count', 'Unknown')}개")
                print(f"  🎯 총 코스 변형: {processing_info.get('total_course_variations', 'Unknown')}개")
                print(f"  📈 Place Agent: {processing_info.get('place_agent_status', 'Unknown')}")
                print(f"  📈 RAG Agent: {processing_info.get('rag_agent_status', 'Unknown')}")
            
            # 완전한 JSON 출력
            print(f"\n===== COMPLETE RESPONSE JSON =====")
            print(json.dumps(result, ensure_ascii=False, indent=2))
            print(f"===================================")
        else:
            print("❌ 추천 실패!")
            print(f"오류: {result['message']}")
            print(f"오류 코드: {result.get('error_code', 'Unknown')}")
            
    else:
        print(f"❌ HTTP 오류: {response.status_code}")
        try:
            error_data = response.json()
            print(f"오류 내용: {error_data}")
        except:
            print(f"응답 내용: {response.text}")
    
    return session_id

def test_recommendation_errors():
    """추천 API 오류 케이스 테스트"""
    
    print("\n=== 오류 케이스 테스트 ===")
    
    # 1. 잘못된 session_id
    print("1. 잘못된 session_id 테스트")
    response = requests.post(f"{BASE_URL}/chat/start-recommendation", json={
        "session_id": "invalid_session_123"
    })
    
    result = response.json()
    print(f"응답: {result}")
    
    # 2. session_id 누락
    print("\n2. session_id 누락 테스트")
    response = requests.post(f"{BASE_URL}/chat/start-recommendation", json={})
    
    result = response.json()
    print(f"응답: {result}")

if __name__ == "__main__":
    print("🚀 추천 API 테스트 시작")
    print("=" * 50)
    
    try:
        # 정상 케이스 테스트
        session_id = test_start_recommendation()
        
        # 오류 케이스 테스트
        test_recommendation_errors()
        
        print("\n" + "=" * 50)
        print("✅ 모든 테스트 완료!")
        
    except Exception as e:
        print(f"\n❌ 테스트 중 오류 발생: {e}")