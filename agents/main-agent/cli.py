#!/usr/bin/env python3
"""
CLI 인터페이스 - 기존 main_agent.py의 대화형 기능을 위한 CLI
"""

from langchain.memory import ConversationBufferMemory
from langchain_openai import ChatOpenAI
import json
import uuid
import os
import re
from dotenv import load_dotenv
from datetime import datetime

from core.profile_extractor import (
    extract_profile_from_llm, 
    llm_correct_field, 
    REQUIRED_KEYS
)
from core.location_processor import extract_location_request_from_llm
from core.agent_builders import build_place_agent_json, build_rag_agent_json
from utils.file_manager import FileManager

load_dotenv()
openai_api_key = os.environ.get("OPENAI_API_KEY")

OPTIONAL_FIELDS = [
    ("car_owned", "차량 소유 여부 (예/아니오): "),
    ("description", "자기소개를 입력해주세요: "),
    ("general_preferences", "선호하는 것(쉼표로 구분, 예: 조용한 곳,야외,디저트): "),
    ("place_count", "코스에 원하는 장소 개수(숫자, 예: 3, 미입력시 3): "),
    ("profile_image_url", "프로필 이미지 URL(선택): ")
]

def ask_and_store(memory, profile, key, question):
    """사용자에게 질문하고 응답을 메모리와 프로필에 저장"""
    answer = input(question).strip()
    memory.save_context({"input": question}, {"output": answer})
    
    if key == "general_preferences":
        profile[key] = [x.strip() for x in answer.split(",") if x.strip()]
    elif key == "car_owned":
        profile[key] = answer in ["예", "yes", "Yes", "Y", "y", "true", "True"]
    elif key == "place_count":
        if answer.isdigit():
            profile[key] = int(answer)
        else:
            profile[key] = 3
    else:
        profile[key] = answer

def main():
    """CLI 메인 함수"""
    session_id = str(uuid.uuid4())
    print(f"\n===== DayToCourse 사용자 정보 입력 =====\n세션 ID: {session_id}\n")
    
    memory = ConversationBufferMemory()
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, openai_api_key=openai_api_key) if openai_api_key else None
    file_manager = FileManager()
    profile = {}
    location_request = {}

    if not llm:
        print("⚠️ OpenAI API 키가 설정되지 않았습니다. 기본 모드로 실행됩니다.")

    # 1. 오픈 프롬프트
    first_message = input(
        "\n💬 [데이트 코스 요청]\n"
        "어떤 데이트 코스를 원하시나요? 아래 예시처럼 자유롭게 입력해 주세요!\n"
        "────────────────────────────\n"
        "예시1) 27살 ENFP, 여자친구와 홍대에서 저녁에 조용하고 감성적인 데이트를 하고 싶어요. 예산은 5만원, 도보 이동.\n"
        "예시2) 30대 커플, 강남에서 트렌디한 분위기의 카페와 레스토랑, 밤 시간대 추천 부탁해요.\n"
        "────────────────────────────\n"
        "포함하면 좋은 정보: 나이, 성별, MBTI, 지역, 관계, 분위기, 예산, 시간대, 이동수단 등\n"
        "👉 입력: "
    ).strip()
    memory.save_context({"input": "오픈 프롬프트"}, {"output": first_message})

    # 2. LLM으로 필수 정보 추출 + 규칙 기반 보정
    if llm:
        extracted = extract_profile_from_llm(llm, first_message)
        for k in REQUIRED_KEYS:
            profile[k] = extracted.get(k, "")
    else:
        for k in REQUIRED_KEYS:
            profile[k] = ""

    # 2-1. 장소 위치/주소 정보 통합 입력 및 구조화
    def ask_location_and_address():
        loc_input = input(
            "\n📍 [장소 위치 입력]\n"
            "정확한 지역, 근처, 사이, 여러 곳 등 원하는 위치를 입력해 주세요.\n"
            "────────────────────────────\n"
            "예시1) 이촌동에서 데이트할 거예요\n"
            "예시2) 합정, 망원동 근처에서 산책하고 싶어요\n"
            "예시3) 홍대랑 강남 사이에서 만나요\n"
            "────────────────────────────\n"
            "👉 입력: "
        ).strip()
        
        if llm:
            loc_req = extract_location_request_from_llm(llm, loc_input, address_hint=None)
            addr_extracted = extract_profile_from_llm(llm, loc_input)
            address = addr_extracted.get("address", "")
        else:
            # 기본 파싱 로직
            loc_req = {"reference_areas": [loc_input], "place_count": 3, "proximity_type": "exact", "proximity_preference": None, "transportation": ""}
            address = loc_input
            
        return loc_req, address

    if llm:
        address_hint = profile.get("address") if profile.get("address") else None
        location_request = extract_location_request_from_llm(llm, first_message, address_hint=address_hint)
    else:
        location_request = {"reference_areas": [], "place_count": 3, "proximity_type": "exact", "proximity_preference": None, "transportation": ""}
    
    if not profile.get("address"):
        if location_request.get("reference_areas"):
            profile["address"] = location_request["reference_areas"][0]
    
    # location_request 또는 address가 누락된 경우 통합 질문 반복
    while not location_request.get("reference_areas") or not profile.get("address"):
        location_request, address = ask_location_and_address()
        if not profile.get("address") and address:
            profile["address"] = address
        if not location_request.get("reference_areas") and address:
            location_request["reference_areas"] = [address]
        if not profile.get("address") and location_request.get("reference_areas"):
            profile["address"] = location_request["reference_areas"][0]

    # 이동수단 입력
    transportation = input(
        "\n🚶 [이동수단]\n"
        "주로 어떤 이동수단을 이용하시나요?\n"
        "────────────────────────────\n"
        "예시: 도보, 대중교통, 자차, 상관없음\n"
        "👉 입력: "
    ).strip()
    if not transportation:
        transportation = "도보"
    location_request["transportation"] = transportation

    # 코스 추가 요구사항
    add_course_planning = input(
        "\n🗺️ [코스 추가 요구사항]\n"
        "코스 최적화, 이동, 순서, 최대 이동시간, 머무는 시간 등 추가로 원하는 조건이 있으신가요? (예/아니오)\n"
        "예시: 예\n"
        "👉 입력: "
    ).strip().lower()

    user_course_planning = None
    max_travel_time = 30

    if add_course_planning == "예":
        print(
            "\n예시: '최소 이동, 최대 만족도, 최대 이동시간 20분, 총 3시간, 순서 고정, 각 장소 1시간씩'\n"
            "────────────────────────────"
        )
        course_input = input("코스 관련 요구사항을 자유롭게 입력해 주세요:\n👉 입력: ").strip()
        user_course_planning = {}
        
        # 최대 이동시간 추출
        match = re.search(r"최대 ?이동시간 ?(\d+)", course_input)
        if match:
            max_travel_time = int(match.group(1))
        
        # 나머지 키워드 매핑
        if "최소 이동" in course_input:
            user_course_planning.setdefault("optimization_goals", []).append("최소 이동")
        if "최대 만족도" in course_input:
            user_course_planning.setdefault("optimization_goals", []).append("최대 만족도")
        if "순서 고정" in course_input:
            user_course_planning["sequence_optimization"] = {"allow_reordering": False, "prioritize_given_sequence": True}
        if "1시간 이내" in course_input:
            user_course_planning.setdefault("route_constraints", {})["max_travel_time_between"] = 60
        if "총 3시간" in course_input:
            user_course_planning.setdefault("route_constraints", {})["total_course_duration"] = 180

    # 3. 누락된 필수 정보만 재질문
    for k in REQUIRED_KEYS:
        if not profile[k] and k != "address":
            q = {
                "age": "\n👤 [나이]\n나이를 입력해 주세요 (예: 27): ",
                "gender": "\n👤 [성별]\n성별을 입력해 주세요 (남/여): ",
                "mbti": "\n👤 [MBTI]\nMBTI를 입력해 주세요 (예: ENFP): ",
                "relationship_stage": "\n💑 [관계]\n상대방과의 관계를 입력해 주세요 (연인/썸/친구 등): ",
                "atmosphere": "\n🌈 [분위기]\n장소의 분위기를 입력해 주세요 (예: 로맨틱, 조용한, 트렌디한, 활기찬 등): ",
                "budget": "\n💸 [예산]\n예산을 입력해 주세요 (예: 2만~5만원, 10만원 이하 등): ",
                "time_slot": "\n🕒 [시간대]\n데이트 시간대를 입력해 주세요 (예: 오전, 오후, 저녁, 밤 등): "
            }[k]
            ask_and_store(memory, profile, k, q)

    # 4. LLM 기반 교정/검증
    if llm:
        for k in REQUIRED_KEYS:
            if k == "address":
                continue
            while True:
                corrected = llm_correct_field(llm, k, profile[k])
                if corrected and corrected != profile[k]:
                    print(f"입력하신 {k} 값을 '{corrected}'로 교정했습니다.")
                    profile[k] = corrected
                    break
                elif corrected == profile[k]:
                    break
                else:
                    q = {
                        "age": "\n👤 [나이]\n나이를 다시 입력해 주세요 (예: 27): ",
                        "gender": "\n👤 [성별]\n성별을 다시 입력해 주세요 (남/여): ",
                        "mbti": "\n👤 [MBTI]\nMBTI를 다시 입력해 주세요 (예: ENFP): ",
                        "relationship_stage": "\n💑 [관계]\n상대방과의 관계를 다시 입력해 주세요 (연인/썸/친구 등): ",
                        "atmosphere": "\n🌈 [분위기]\n장소의 분위기를 다시 입력해 주세요 (예: 로맨틱, 조용한, 트렌디한, 활기찬 등): ",
                        "budget": "\n💸 [예산]\n예산을 다시 입력해 주세요 (예: 2만~5만원, 10만원 이하 등): ",
                        "time_slot": "\n🕒 [시간대]\n데이트 시간대를 다시 입력해 주세요 (예: 오전, 오후, 저녁, 밤 등): "
                    }[k]
                    profile[k] = input(q).strip()

    # 5. 부가 정보 입력 의사 확인
    add_more = input(
        "\n✨ [추가 정보]\n"
        "차량 소유, 자기소개, 선호사항 등 더 입력하시겠어요? (예/아니오)\n"
        "예시: 예\n"
        "👉 입력: "
    ).strip().lower()
    memory.save_context({"input": "추가 정보 입력 의사"}, {"output": add_more})
    
    if add_more == "예":
        for key, question in OPTIONAL_FIELDS:
            ask_and_store(memory, profile, key, question)

    # 6. JSON 저장
    output = {"profile": profile, "location_request": location_request}
    profile_filename = file_manager.save_profile(session_id, output)
    print(f"\n✅ 사용자 정보가 {profile_filename} 파일에 저장되었습니다!\n")
    print(json.dumps(output, ensure_ascii=False, indent=2))
    print(f"\n[세션 ID: {session_id}]\n")

    # 7. place agent용 JSON 생성 및 출력/저장
    place_json = build_place_agent_json(profile, location_request, max_travel_time)
    place_filename = file_manager.save_place_agent_request(session_id, place_json)
    print(f"\n✅ place agent 전송용 JSON이 {place_filename} 파일에 저장되었습니다!\n")
    print(json.dumps(place_json, ensure_ascii=False, indent=2))

    # 8. rag agent용 JSON 생성
    if llm:
        sample_place_response = file_manager.load_sample_place_response()
        if sample_place_response:
            rag_json = build_rag_agent_json(sample_place_response, profile, location_request, openai_api_key, user_course_planning)
            rag_filename = file_manager.save_rag_agent_request(session_id, rag_json)
            print(f"\n✅ rag agent 전송용 JSON이 {rag_filename} 파일에 저장되었습니다!\n")
            print(json.dumps(rag_json, ensure_ascii=False, indent=2))
        else:
            print("\n⚠️ sample_place_agent_response.json 파일이 존재하지 않아 rag agent용 JSON을 생성하지 않았습니다.\n")
    else:
        print("\n⚠️ OpenAI API 키가 없어 rag agent용 JSON을 생성하지 않았습니다.\n")

if __name__ == "__main__":
    main()