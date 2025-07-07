import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
from fastapi.testclient import TestClient
from server import app

client = TestClient(app)

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

def test_full_chat_flow():
    # 1. 새 세션 시작 (직접 입력)
    initial_message = input("\n[USER] 첫 메시지를 입력하세요: ")
    resp = client.post("/chat/new-session", json={
        "user_id": 12345,
        "initial_message": initial_message,
        "user_profile": USER_PROFILE
    })
    assert resp.status_code == 200
    data = resp.json()
    session_id = data["session_id"]
    print("[ASSISTANT]", data["response"]["message"])

    # 채팅 루프: 사용자가 직접 입력할 때까지 반복
    while True:
        user_msg = input("\n[USER] 메시지를 입력하세요 (종료하려면 /quit): ")
        if user_msg.strip() == "/quit":
            print("\n채팅을 종료합니다.")
            break
        resp2 = client.post("/chat/send-message", json={
            "session_id": session_id,
            "message": user_msg,
            "user_id": 12345,
            "user_profile": USER_PROFILE
        })
        if resp2.status_code != 200:
            print("[ERROR] 응답 코드:", resp2.status_code, resp2.text)
            break
        data2 = resp2.json()
        print("[ASSISTANT]", data2["response"]["message"])
        # 코스 추천이 나오면 course_data도 출력
        if data2["response"]["message_type"] == "COURSE_RECOMMENDATION":
            print("[ASSISTANT] 추천 코스 데이터:", data2["response"].get("course_data"))
            break

if __name__ == "__main__":
    test_full_chat_flow()