import requests
import json

BASE = "http://localhost:8001"

USER_PROFILE = {
    "gender": "FEMALE",
    "age": 25,
    "mbti": "ENFP",
    "address": "서울시 강남구",
    "car_owned": False,
    "description": "카페 투어를 좋아하는 개발자입니다",
    "relationship_stage": "썸",
    "general_preferences": ["조용한 곳", "야외", "디저트"],
    "profile_image_url": "https://example.com/profile.jpg",
    # 추가 데이트 정보 필드 (일부는 빈 값으로 시작)
    "atmosphere": "",
    "budget": "",
    "time_slot": "",
    "transportation": "",
    "place_count": 3
}

REQUIRED_FIELDS = [
    ("atmosphere", "어떤 분위기를 원하시나요? (예: 아늑한, 활기찬 등)"),
    ("budget", "예산은 얼마 정도 생각하시나요? (예: 5만원, 10만원 등)"),
    ("duration", "몇 시간 정도 데이트를 원하시나요? (예: 2-3시간, 4-5시간 등)"),
    ("place_type", "어떤 종류의 장소를 선호하시나요? (예: 맛집, 카페, 문화생활 등)")
]

def get_next_question(session_info):
    for field, question in REQUIRED_FIELDS:
        if not session_info.get(field):
            return field, question
    return None, None

def start_new_session():
    print("💬 데이트 코스 추천을 시작합니다!")
    print("더 정확한 추천을 위해 다음과 같은 정보를 포함해서 말씀해 주세요:")
    print()
    print("📍 예시:")
    print("  • '홍대에서 25살 여자친구랑 로맨틱한 저녁 데이트 하고 싶어. 예산은 10만원 정도로 생각하고 있어'")
    print("  • '강남에서 썸타는 사람이랑 오후에 조용한 분위기로 데이트할 계획이야. 지하철로 이동할 예정'")
    print("  • '이태원에서 연인과 ENFP 성격에 맞는 활기찬 데이트 코스 추천해줘. 차 있어서 운전 가능'")
    print("  • '성수동에서 30대 커플 데이트. 카페나 문화생활 좋아하고 예산은 넉넉하게 15만원'")
    print()
    print("💡 포함하면 좋은 정보:")
    print("  🏢 지역, 👥 나이/관계, 🌅 시간대, 💰 예산, 🎭 분위기/성격, 🚇 교통수단, 🍽️ 선호 장소")
    print()
    initial_message = input("📝 어떤 데이트를 원하시나요? ")
    data = {
        "user_id": 12345,
        "initial_message": initial_message,
        "user_profile": USER_PROFILE
    }
    
    print(f"\n📤 [REQUEST] POST {BASE}/chat/new-session")
    print(f"📦 [REQUEST BODY]:")
    print(json.dumps(data, ensure_ascii=False, indent=2))
    
    r = requests.post(f"{BASE}/chat/new-session", json=data)
    
    print(f"\n📥 [RESPONSE] Status: {r.status_code}")
    print(f"📋 [RESPONSE HEADERS]:")
    for key, value in r.headers.items():
        print(f"  {key}: {value}")
    
    res = r.json()
    print(f"\n📄 [RESPONSE BODY]:")
    print(json.dumps(res, ensure_ascii=False, indent=2))
    
    print("\n=== Assistant ===")
    print(res["response"]["message"])
    return res["session_id"]

def send_message(session_id, message):
    data = {
        "session_id": session_id,
        "message": message,
        "user_id": 12345,
        "user_profile": USER_PROFILE
    }
    
    print(f"\n📤 [REQUEST] POST {BASE}/chat/send-message")
    print(f"📦 [REQUEST BODY]:")
    print(json.dumps(data, ensure_ascii=False, indent=2))
    
    r = requests.post(f"{BASE}/chat/send-message", json=data)
    
    print(f"\n📥 [RESPONSE] Status: {r.status_code}")
    print(f"📋 [RESPONSE HEADERS]:")
    for key, value in r.headers.items():
        print(f"  {key}: {value}")
    
    res = r.json()
    print(f"\n📄 [RESPONSE BODY]:")
    print(json.dumps(res, ensure_ascii=False, indent=2))
    
    print("\n=== Assistant ===")
    print(res["response"]["message"])
    return res

def start_recommendation(session_id):
    """추천 시작"""
    data = {"session_id": session_id}
    print("\n⏳ 추천 생성 중... (Place Agent → RAG Agent 처리)")
    
    print(f"\n📤 [REQUEST] POST {BASE}/chat/start-recommendation")
    print(f"📦 [REQUEST BODY]:")
    print(json.dumps(data, ensure_ascii=False, indent=2))
    
    try:
        r = requests.post(f"{BASE}/chat/start-recommendation", json=data)
        
        print(f"\n📥 [RESPONSE] Status: {r.status_code}")
        print(f"📋 [RESPONSE HEADERS]:")
        for key, value in r.headers.items():
            print(f"  {key}: {value}")
        
        res = r.json()
        print(f"\n📄 [RESPONSE BODY]:")
        print(json.dumps(res, ensure_ascii=False, indent=2))
        
        print("\n=== 🎉 추천 결과 ===")
        
        if res.get("success", False):
            print(f"✅ {res['message']}")
            
            if "course_data" in res:
                course_data = res["course_data"]
                places = course_data.get("places", [])
                course = course_data.get("course", {})
                
                print(f"\n📍 총 추천 장소: {len(places)}개")
                
                # 맑은 날 코스 표시 - RAG Agent 응답 구조에 맞춤
                results = course.get("results", {})
                sunny_courses = results.get("sunny_weather", [])
                print(f"\n☀️ 맑은 날 코스 ({len(sunny_courses)}개):")
                for i, sunny_course in enumerate(sunny_courses, 1):
                    print(f"  {i}. {sunny_course.get('recommendation_reason', 'N/A')}")
                    for place in sunny_course.get("places", [])[:2]:  # 처음 2개만
                        place_info = place.get("place_info", {})
                        print(f"     • {place_info.get('name', 'Unknown')}: {place.get('description', '')[:50]}...")
                
                # 비오는 날 코스 표시 - RAG Agent 응답 구조에 맞춤
                rainy_courses = results.get("rainy_weather", [])
                print(f"\n🌧️ 비오는 날 코스 ({len(rainy_courses)}개):")
                for i, rainy_course in enumerate(rainy_courses, 1):
                    print(f"  {i}. {rainy_course.get('recommendation_reason', 'N/A')}")
                    for place in rainy_course.get("places", [])[:2]:  # 처음 2개만
                        place_info = place.get("place_info", {})
                        print(f"     • {place_info.get('name', 'Unknown')}: {place.get('description', '')[:50]}...")
                
                # 세션 정보
                session_info = res.get("session_info", {})
                print(f"\n📋 세션 상태: {session_info.get('session_status', 'Unknown')}")
                print(f"📋 코스 보유: {session_info.get('has_course', False)}")
                
                # 처리 정보 (있는 경우)
                processing_info = res.get("processing_info")
                if processing_info:
                    print(f"\n📊 처리 정보:")
                    print(f"  ⏱️ 총 처리 시간: {processing_info.get('total_processing_time', 'Unknown')}초")
                    print(f"  📍 추천 장소 수: {processing_info.get('place_count', 'Unknown')}개")
                    print(f"  ☀️ 맑은 날 코스: {processing_info.get('sunny_course_count', 'Unknown')}개")
                    print(f"  🌧️ 비오는 날 코스: {processing_info.get('rainy_course_count', 'Unknown')}개")
                    print(f"  🎯 총 코스 변형: {processing_info.get('total_course_variations', 'Unknown')}개")
                    print(f"  📈 Place Agent: {processing_info.get('place_agent_status', 'Unknown')}")
                    print(f"  📈 RAG Agent: {processing_info.get('rag_agent_status', 'Unknown')}")
                
                # 완전한 JSON 출력 옵션
                print(f"\n💾 전체 응답 JSON 보기? (y/n): ", end="")
                show_json = input().strip().lower()
                if show_json in ['y', 'yes']:
                    print(f"\n===== COMPLETE RESPONSE JSON =====")
                    print(json.dumps(res, ensure_ascii=False, indent=2))
                    print(f"===================================")
            else:
                print("⚠️ 코스 데이터가 응답에 포함되지 않았습니다.")
        else:
            print(f"❌ 추천 실패: {res['message']}")
            error_code = res.get('error_code')
            if error_code:
                print(f"오류 코드: {error_code}")
            
            # 상세 오류 정보 표시
            if 'error_details' in res:
                print("상세 오류 정보:")
                for key, value in res['error_details'].items():
                    print(f"  {key}: {value}")
        
        return res
        
    except requests.exceptions.RequestException as e:
        print(f"❌ 네트워크 오류: {e}")
        return {"success": False, "error": str(e)}
    except json.JSONDecodeError as e:
        print(f"❌ JSON 파싱 오류: {e}")
        return {"success": False, "error": str(e)}
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")
        return {"success": False, "error": str(e)}

# handle_message 함수는 새로운 통합 API에서 자동 처리됨

def test_error_cases():
    """오류 케이스 테스트 (정상적인 에러 처리 확인용)"""
    print("\n=== 🧪 오류 케이스 테스트 (정상 동작 확인) ===")
    
    # 1. 잘못된 session_id로 추천 시도
    print("1. 잘못된 session_id 테스트")
    try:
        r = requests.post(f"{BASE}/chat/start-recommendation", json={"session_id": "invalid_session_123"})
        result = r.json()
        print(f"   ✅ 예상된 오류 응답: {result.get('message', 'Unknown error')}")
        print(f"   📋 에러 코드: {result.get('error_code', 'N/A')}")
    except Exception as e:
        print(f"   ❌ 예상치 못한 오류: {e}")
    
    # 2. session_id 누락 테스트
    print("\n2. session_id 누락 테스트")
    try:
        r = requests.post(f"{BASE}/chat/start-recommendation", json={})
        result = r.json()
        print(f"   ✅ 예상된 오류 응답: {result.get('message', 'Unknown error')}")
        print(f"   📋 에러 코드: {result.get('error_code', 'N/A')}")
    except Exception as e:
        print(f"   ❌ 예상치 못한 오류: {e}")
    
    print("\n💡 위의 오류들은 정상적인 에러 처리 테스트입니다!")

def run_full_test():
    """전체 테스트 실행"""
    print("🚀 Main Agent 통합 채팅 + 추천 API 테스트")
    print("=" * 60)
    
    # 1. 새 세션 시작
    print("\n📝 1단계: 새 세션 시작")
    session_id = start_new_session()
    
    # 2. 대화형 정보 수집
    print("\n💬 2단계: 정보 수집 (대화형)")
    recommendation_ready = False
    
    while True:
        user_msg = input("\n👤 나: ")
        
        if user_msg.strip().lower() in ["exit", "quit", "종료"]:
            print("채팅을 종료합니다.")
            break
        elif user_msg.strip().lower() in ["추천", "추천시작", "start", "recommendation"]:
            if recommendation_ready:
                # 추천 시작
                print("\n🎯 3단계: 추천 생성 시작")
                start_recommendation(session_id)
                
                # 4. 세션 상세 조회
                print("\n📋 4단계: 최종 세션 정보 확인")
                try:
                    r = requests.get(f"{BASE}/chat/sessions/{session_id}")
                    session_detail = r.json()
                    if session_detail["success"]:
                        session_info = session_detail["session"]
                        print(f"세션 제목: {session_info['session_title']}")
                        print(f"세션 상태: {session_info['session_status']}")
                        print(f"메시지 개수: {len(session_detail['messages'])}개")
                        print(f"코스 보유 여부: {session_info.get('has_course', False)}")
                    else:
                        print("세션 정보 조회 실패")
                except Exception as e:
                    print(f"세션 정보 조회 오류: {e}")
                
                # 5. 오류 케이스 테스트
                test_error_cases()
                break
            else:
                print("❌ 아직 정보 수집이 완료되지 않았습니다. 먼저 모든 정보를 입력해주세요.")
                continue
        
        # 메시지 전송
        resp = send_message(session_id, user_msg)
        
        # 추천 준비 완료 메시지 확인
        if "추천을 시작하시려면" in resp["response"]["message"]:
            recommendation_ready = True
            print("\n✅ 정보 수집 완료!")
            print("💡 이제 '추천' 또는 '추천시작'을 입력하면 데이트 코스를 생성합니다!")
        
        # 코스 추천이 완성되면 자동 종료(혹시나 하는 케이스)
        if resp["response"].get("message_type") == "COURSE_RECOMMENDATION":
            print("\n[코스 추천이 완료되었습니다!]")
            break
    
    print("\n" + "=" * 60)
    print("✅ 전체 테스트 완료!")

def run_quick_test():
    """빠른 자동 테스트 (입력 없이)"""
    print("🚀 Main Agent 자동 테스트 (입력 없음)")
    print("=" * 60)
    
    # 1. 새 세션 시작 (자동으로 풍부한 정보 제공)
    print("\n📝 1단계: 새 세션 시작")
    print("자동 입력: '홍대에서 25살 INFP 여자친구랑 로맨틱한 저녁 데이트. 예산 10만원, 지하철 이용, 조용한 카페나 맛집 선호'")
    
    data = {
        "user_id": 12345,
        "initial_message": "홍대에서 25살 INFP 여자친구랑 로맨틱한 저녁 데이트. 예산 10만원, 지하철 이용, 조용한 카페나 맛집 선호",
        "user_profile": USER_PROFILE
    }
    r = requests.post(f"{BASE}/chat/new-session", json=data)
    res = r.json()
    print("\n=== Assistant ===")
    print(res["response"]["message"])
    session_id = res["session_id"]
    
    # 2. 자동 정보 입력 (이미 첫 메시지에서 많은 정보를 제공했으므로 적게 필요)
    print("\n💬 2단계: 자동 정보 입력")
    test_inputs = [
        "아니오"  # 추가 정보 입력 안함 (이미 충분한 정보 제공)
    ]
    
    for i, msg in enumerate(test_inputs, 1):
        print(f"\n{i}. 입력: {msg}")
        resp = send_message(session_id, msg)
        
        # 추천 준비 완료 확인
        if "추천을 시작하시려면" in resp["response"]["message"]:
            print("✅ 정보 수집 완료!")
            break
    
    # 3. 추천 시작
    print("\n🎯 3단계: 추천 생성")
    start_recommendation(session_id)
    
    # 4. 테스트 완료
    print("\n" + "=" * 60)
    print("✅ 자동 테스트 완료!")
    return session_id

if __name__ == "__main__":
    print("🎯 Main Agent 데이트 코스 추천 테스트")
    print("=" * 50)
    print("Main Agent 테스트 모드를 선택하세요:")
    print("1. 대화형 테스트 (직접 입력) - 실제 사용자 경험")
    print("2. 자동 테스트 (입력 없음) - 빠른 기능 확인")
    print()
    print("💡 팁: 첫 메시지에 많은 정보를 포함할수록 더 빠르고 정확한 추천을 받을 수 있습니다!")
    
    choice = input("\n선택 (1 또는 2): ").strip()
    
    if choice == "2":
        run_quick_test()
    else:
        run_full_test() 