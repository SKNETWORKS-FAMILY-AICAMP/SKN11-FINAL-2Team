import requests

BASE = "http://localhost:8000"

USER_PROFILE = {
    "gender": "FEMALE",
    "age": 25,
    "mbti": "ENFP",
    "address": "서울시 강남구",
    "car_owned": False,
    "description": "카페 투어를 좋아하는 개발자입니다",
    "relationship_stage": "썸",
    "general_preferences": ["조용한 곳", "야외", "디저트"],
    "profile_image_url": "https://example.com/profile.jpg"
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
    initial_message = input("📝 첫 메시지를 입력하세요: ")
    data = {
        "user_id": 12345,
        "initial_message": initial_message,
        "user_profile": USER_PROFILE
    }
    r = requests.post(f"{BASE}/chat/new-session", json=data)
    res = r.json()
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
    r = requests.post(f"{BASE}/chat/send-message", json=data)
    res = r.json()
    print("\n=== Assistant ===")
    print(res["response"]["message"])
    return res

def handle_message(session_id, message):
    # 1. 세션별 정보 누적
    session_info = SESSIONS[session_id]
    update_session_info(session_info, message)  # 사용자가 입력한 정보를 필드에 저장

    # 2. 아직 입력 안 된 필수 정보 중 하나만 질문
    field, question = get_next_question(session_info)
    if field:
        return question  # 한 번에 하나만 질문
    else:
        # 모든 정보가 모이면 추천 진행
        return recommend_course(session_info)

if __name__ == "__main__":
    session_id = start_new_session()

    while True:
        user_msg = input("\n👤 나: ")
        if user_msg.strip().lower() in ["exit", "quit", "종료"]:
            print("채팅을 종료합니다.")
            break
        resp = send_message(session_id, user_msg)
        # 코스 추천이 완성되면 자동 종료(옵션)
        if resp["response"].get("message_type") == "COURSE_RECOMMENDATION":
            print("\n[코스 추천이 완료되었습니다!]")
            break

    # 세션 상세 조회 (최종 결과 확인)
    r = requests.get(f"{BASE}/chat/sessions/{session_id}")
    print("\n=== Session Detail ===")
    print(r.json()) 