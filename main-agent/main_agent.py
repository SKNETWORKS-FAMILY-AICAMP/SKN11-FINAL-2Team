from langchain.memory import ConversationBufferMemory
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
import json, uuid, os, re
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
openai_api_key = os.environ["OPENAI_API_KEY"]

REQUIRED_KEYS = [
    "age", "gender", "mbti", "address", "relationship_stage", "atmosphere", "budget", "time_slot"
]
OPTIONAL_FIELDS = [
    ("car_owned", "차량 소유 여부 (예/아니오): "),
    ("description", "자기소개를 입력해주세요: "),
    ("general_preferences", "선호하는 것(쉼표로 구분, 예: 조용한 곳,야외,디저트): "),
    ("place_count", "코스에 원하는 장소 개수(숫자, 예: 3, 미입력시 3): "),
    ("profile_image_url", "프로필 이미지 URL(선택): ")
]

def rule_based_gender_relationship(user_message, extracted):
    # 여자친구/남자친구 등에서 성별 추론
    if not extracted.get("gender") or extracted["gender"] == "":
        if re.search(r"여자친구", user_message):
            extracted["gender"] = "남"
        elif re.search(r"남자친구", user_message):
            extracted["gender"] = "여"
    # 관계 추론
    if not extracted.get("relationship_stage") or extracted["relationship_stage"] == "":
        if re.search(r"여자친구|남자친구", user_message):
            extracted["relationship_stage"] = "연인"
        elif re.search(r"썸", user_message):
            extracted["relationship_stage"] = "썸"
        elif re.search(r"친구", user_message):
            extracted["relationship_stage"] = "친구"
    return extracted

def extract_profile_from_llm(llm, user_message):
    prompt = (
        "아래 사용자의 답변에서 나이, 성별, MBTI, 데이트 장소, 상대방과의 관계, 장소 분위기, 예산, 데이트 시간대를 추출해서 "
        "각 항목별로 key:value 형태로 JSON으로 출력해줘. "
        "성별은 상대방 호칭(여자친구/남자친구 등)에서 유추할 수 있으면 반드시 추론해서 채워줘. "
        "장소(지역/동네), 분위기(로맨틱, 조용한, 트렌디한, 활기찬 등), 예산(2만~5만원, 10만원 이하 등), 시간대(오전, 오후, 저녁, 밤 등)도 문장 안에서 최대한 추출해줘. "
        "없는 항목은 빈 문자열로 둬.\n"
        "예시1: 답변: '여자친구랑 홍대에서 분위기 좋은 로맨틱 데이트할거야. 저녁에 5만원 정도 생각해.' → {\"age\": \"\", \"gender\": \"남\", \"mbti\": \"\", \"address\": \"홍대\", \"relationship_stage\": \"연인\", \"atmosphere\": \"로맨틱\", \"budget\": \"5만원\", \"time_slot\": \"저녁\"}\n"
        "예시2: 답변: '남자친구랑 강남에서 조용한 저녁 데이트, 예산은 10만원 이하' → {\"age\": \"\", \"gender\": \"여\", \"mbti\": \"\", \"address\": \"강남\", \"relationship_stage\": \"연인\", \"atmosphere\": \"조용한\", \"budget\": \"10만원 이하\", \"time_slot\": \"저녁\"}\n"
        "예시3: 답변: '25살 ENFP, 썸타는 사람과 이태원에서 트렌디한 데이트, 오후에 3만원 정도' → {\"age\": \"25\", \"gender\": \"\", \"mbti\": \"ENFP\", \"address\": \"이태원\", \"relationship_stage\": \"썸\", \"atmosphere\": \"트렌디한\", \"budget\": \"3만원\", \"time_slot\": \"오후\"}\n"
        f"답변: {user_message}\n"
        "반드시 JSON만 출력해줘."
    )
    result = llm.invoke([HumanMessage(content=prompt)])
    try:
        profile = json.loads(result.content)
    except Exception:
        profile = {k: "" for k in REQUIRED_KEYS}
    # 규칙 기반 보정
    profile = rule_based_gender_relationship(user_message, profile)
    return profile

def ask_and_store(memory, profile, key, question):
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

def llm_correct_field(llm, key, value):
    # 각 항목별 교정 프롬프트
    field_desc = {
        "age": "나이(숫자, 10~100세 사이)",
        "gender": "성별(남/여)",
        "mbti": "MBTI(예: ENFP, INFP 등 4글자)",
        "address": "장소(지역/동네)",
        "relationship_stage": "관계(연인/썸/친구 등)",
        "atmosphere": "장소 분위기(로맨틱, 조용한, 트렌디한, 활기찬 등)",
        "budget": "예산(예: 2만~5만원, 10만원 이하 등)",
        "time_slot": "데이트 시간대(오전, 오후, 저녁, 밤 등)"
    }[key]
    prompt = (
        f"입력값: '{value}'\n"
        f"이 값이 {field_desc}에 적합한지 확인하고, 오타나 비정상 입력이면 올바른 값으로 교정해줘. "
        f"교정이 불가능하면 빈 문자열만 출력해.\n"
        f"예시1: 입력값: '10만원이하' → '10만원 이하'\n"
        f"예시2: 입력값: '10만~5만' → '5만~10만원'\n"
        f"예시3: 입력값: '조용한 분우기' → '조용한 분위기'\n"
        f"예시4: 입력값: 'enfp' → 'ENFP'\n"
        f"예시5: 입력값: '남자' → '남'\n"
        f"예시6: 입력값: '29살' → '29'\n"
        f"예시7: 입력값: '밤시간' → '밤'\n"
        f"예시8: 입력값: '강남역' → '강남'\n"
        f"예시9: 입력값: 'ㅇㄴㅁ' → ''\n"
        f"입력값: '{value}'\n"
        f"교정값만 출력해줘."
    )
    result = llm.invoke([HumanMessage(content=prompt)])
    return result.content.strip().replace('"', '').replace("'", "")

def clean_area(area):
    # 쉼표, 슬래시 등으로 분할 후 위치 특성 단어만 제거, '역'은 남김
    areas = re.split(r'[,/]', area)
    result = []
    for a in areas:
        a = a.strip()
        a = re.sub(r"(근처|부근|인근|쪽|사이|중간|에서)", "", a)
        a = a.strip()
        if a:
            result.append(a)
    return result

def extract_location_request_from_llm(llm, user_message, address_hint=None):
    prompt = (
        "아래 사용자의 입력에서 데이트 장소 위치 정보를 구조화해줘.\n"
        "- reference_areas에는 반드시 장소명(예: '강남', '홍대입구역')만 넣고, '근처', '부근', '인근', '사이', '중간' 등 위치 특성 단어는 절대 포함하지 마세요.\n"
        "- 위치 특성 단어(근처, 부근, 인근, 사이, 중간 등)는 반드시 proximity_type/proximity_preference에만 넣으세요.\n"
        "- proximity_type: 'exact'(정확한 장소), 'near'(근처), 'between'(사이), 'multi'(여러 곳) 중 하나\n"
        "- proximity_preference: 'middle', 'near', 'any' 등(있으면)\n"
        "- place_count: 장소 개수(숫자, 없으면 3)\n"
        "- transportation: 이동 수단(도보, 차, 대중교통 중 하나, 없으면 빈 문자열)\n"
        "\n"
        "예시1: '강남역 근처에서 대중교통으로 3군데' → {\"proximity_type\": \"near\", \"reference_areas\": [\"강남역\"], \"place_count\": 3, \"proximity_preference\": \"near\", \"transportation\": \"대중교통\"}\n"
        "예시2: '홍대, 합정역 근처를 도보로' → {\"proximity_type\": \"multi\", \"reference_areas\": [\"홍대\", \"합정역\"], \"place_count\": 3, \"proximity_preference\": \"near\", \"transportation\": \"도보\"}\n"
        "예시3: '홍대랑 강남 사이에서 차로 이동' → {\"proximity_type\": \"between\", \"reference_areas\": [\"홍대\", \"강남\"], \"place_count\": 3, \"proximity_preference\": \"middle\", \"transportation\": \"차\"}\n"
        "예시4: '홍대입구역에서 데이트' → {\"proximity_type\": \"exact\", \"reference_areas\": [\"홍대입구역\"], \"place_count\": 3, \"proximity_preference\": null, \"transportation\": ""}\n"
        f"입력: {user_message}\n"
        + (f"address 힌트: {address_hint}\n" if address_hint else "") +
        "반드시 JSON만 출력해줘."
    )
    result = llm.invoke([HumanMessage(content=prompt)])
    try:
        location_request = json.loads(result.content)
    except Exception:
        location_request = {}
    # 기본값 보정
    if "place_count" not in location_request or not location_request["place_count"]:
        location_request["place_count"] = 3
    # 후처리: reference_areas에서 쉼표, 슬래시 등 분할 및 위치 특성 단어 제거
    if "reference_areas" in location_request:
        cleaned = []
        for a in location_request["reference_areas"]:
            cleaned += clean_area(a)
        location_request["reference_areas"] = [x for x in cleaned if x]
    # proximity_type/proximity_preference 자동 보정
    if "reference_areas" in location_request and len(location_request["reference_areas"]) == 2 and not location_request.get("proximity_type"):
        location_request["proximity_type"] = "between"
        location_request["proximity_preference"] = "middle"
    if "reference_areas" in location_request and len(location_request["reference_areas"]) == 1:
        if not location_request.get("proximity_type"):
            location_request["proximity_type"] = "exact"
        if not location_request.get("proximity_preference"):
            location_request["proximity_preference"] = None
    if any(kw in user_message for kw in ["근처", "부근", "인근"]):
        location_request["proximity_type"] = "near"
        location_request["proximity_preference"] = "near"
    if any(kw in user_message for kw in ["사이", "중간"]):
        location_request["proximity_type"] = "between"
        location_request["proximity_preference"] = "middle"
    # 네 필드 모두 포함하도록 보정
    for k in ["proximity_type", "reference_areas", "place_count", "proximity_preference", "transportation"]:
        if k not in location_request:
            location_request[k] = "" if k == "transportation" else (None if k != "place_count" else 3)
    return location_request

def build_place_agent_json(profile, location_request):
    # budget_level 변환(간단 매핑)
    def map_budget(budget):
        if not budget:
            return None
        if "2만" in budget or "3만" in budget or "5만" in budget:
            return "low"
        if "10만" in budget or "10만원" in budget:
            return "medium"
        if "15만" in budget or "20만" in budget or "이상" in budget:
            return "high"
        return None
    # transportation 변환
    def map_transportation(trans):
        if not trans:
            return None
        if "지하철" in trans or "대중" in trans:
            return "지하철"
        if "도보" in trans:
            return "도보"
        if "차" in trans or "자동차" in trans or "운전" in trans:
            return "차"
        return trans
    # preferences 추출(분위기 등)
    preferences = []
    if profile.get("atmosphere"):
        preferences.append(profile["atmosphere"])
    # 기타 선호(추가 가능)
    # requirements
    requirements = {
        "budget_level": map_budget(profile.get("budget")),
        "time_preference": profile.get("time_slot"),
        "transportation": map_transportation(location_request.get("transportation")),
        "max_travel_time": None,
        "weather_condition": None
    }
    # demographics
    demographics = {
        "age": int(profile["age"]) if profile.get("age") and profile["age"].isdigit() else None,
        "mbti": profile.get("mbti"),
        "relationship_stage": profile.get("relationship_stage")
    }
    # request_id, timestamp
    request_id = f"req-{str(uuid.uuid4())[:8]}"
    timestamp = datetime.now().isoformat(timespec="seconds")
    # request_type
    request_type = "proximity_based"
    # place agent json
    place_json = {
        "request_id": request_id,
        "timestamp": timestamp,
        "request_type": request_type,
        "location_request": {
            "proximity_type": location_request.get("proximity_type"),
            "reference_areas": location_request.get("reference_areas"),
            "place_count": location_request.get("place_count"),
            "proximity_preference": location_request.get("proximity_preference")
        },
        "user_context": {
            "demographics": demographics,
            "preferences": preferences,
            "requirements": requirements
        },
        "selected_categories": []
    }
    return place_json

def recommend_categories_and_tones(profile, location_request, place_count):
    # 사용자 요구 기반 카테고리/톤 추천
    atmosphere = profile.get("atmosphere", "").lower()
    time_slot = profile.get("time_slot", "").lower()
    relationship = profile.get("relationship_stage", "").lower()
    budget = profile.get("budget", "")
    weather = location_request.get("weather_condition", "")

    # 카테고리 우선순위 규칙 예시
    if "비" in weather or "rain" in weather:
        categories = ["카페", "문화시설", "쇼핑"]
    elif "저녁" in time_slot or "밤" in time_slot:
        if "연인" in relationship or "로맨틱" in atmosphere:
            # 술집이 마지막에 오도록 보정
            categories = ["음식점", "카페", "술집"]
        else:
            categories = ["음식점", "카페", "술집"]
    elif "오후" in time_slot:
        if "트렌디" in atmosphere or "젊은" in atmosphere:
            categories = ["카페", "문화시설", "쇼핑"]
        else:
            categories = ["카페", "음식점", "문화시설"]
    else:
        categories = ["카페", "음식점", "문화시설"]
    # place_count만큼 반복/슬라이스
    categories = (categories * ((place_count // len(categories)) + 1))[:place_count]

    # 술집이 2개 이상 연속으로 오지 않도록, 항상 마지막에만 오도록 보정
    if "술집" in categories:
        # 술집이 여러 번 등장하면 마지막 하나만 남기고 앞의 것은 음식점/카페로 대체
        last_idx = max(idx for idx, cat in enumerate(categories) if cat == "술집")
        for idx, cat in enumerate(categories):
            if cat == "술집" and idx != last_idx:
                # 앞쪽 술집은 음식점 또는 카페로 대체 (음식점 우선)
                categories[idx] = "음식점" if "음식점" in categories else "카페"

    # 톤 추천 규칙 예시
    if "로맨틱" in atmosphere or "연인" in relationship:
        tones = ["감성적", "고급스러운", "편안한"]
    elif "트렌디" in atmosphere or "젊은" in atmosphere:
        tones = ["활기찬", "감성적", "편안한"]
    elif "조용" in atmosphere or "편안" in atmosphere:
        tones = ["편안한", "감성적", "고급스러운"]
    else:
        tones = ["감성적", "활기찬", "편안한"]
    tones = (tones * ((place_count // len(tones)) + 1))[:place_count]
    return categories, tones

def make_metadata_style_semantic_query_llm(llm, area_name, category, tone, user_ctx, profile, location, reason=None):
    # 프롬프트 구성
    age = user_ctx['demographics'].get('age')
    relationship = user_ctx['demographics'].get('relationship_stage', '')
    time_pref = user_ctx['requirements'].get('time_preference', '')
    budget = user_ctx['requirements'].get('budget_range', '')
    transport = user_ctx['requirements'].get('transportation', '')
    atmosphere = profile.get('atmosphere', '')
    situation = []
    if relationship:
        situation.append(f"{relationship}과(와) 함께")
    if time_pref:
        situation.append(f"{time_pref}에")
    if transport:
        situation.append(f"{transport}로 이동하기 좋은")
    if budget:
        situation.append(f"예산 {budget} 내에서")
    situation_str = ', '.join(situation) if situation else ''
    prompt = f"""당신은 장소 설명문 작성 전문가입니다.\n\n**임무:**\n- 아래 정보를 바탕으로 RAG DB의 metadata(설명문)와 최대한 유사한 스타일로, 2~3문장 이상의 자연스러운 설명문을 작성하세요.\n- 장소명으로 시작하지 말고, 분위기, 특징, 경험, 추천 상황을 구체적으로 묘사하세요.\n- 감성적/활기찬/고급스러운/편안한 톤 중 상황에 맞는 톤을 자연스럽게 녹여주세요.\n- 방문객의 경험, 추천 상황, 시간대, 관계, 예산, 교통 등도 자연스럽게 포함하세요.\n- 뻔한 표현은 피하고, 실제 metadata와 유사한 문장 구조와 어휘를 사용하세요.\n\n**장소 정보:**\n- 지역명: {area_name}\n- 카테고리: {category}\n- 분위기: {tone} / {atmosphere}\n- 추천 상황: {situation_str}\n- 선정 이유: {reason if reason else ''}\n\n**예시:**\n- 한강의 야경을 감상하며 연인과 프라이빗하게 와인을 즐길 수 있는 고급스러운 와인바. 라이브 음악과 함께 특별한 날을 기념하기 좋은 곳. 저녁 시간에 분위기가 한층 더 로맨틱해지는 공간.\n- 트렌디한 감성의 카페에서 친구와 함께 여유로운 오후를 보내기에 완벽한 곳. 다양한 디저트와 감각적인 인테리어가 어우러져 특별한 경험을 선사합니다.\n\n**설명문:**"""
    result = llm.invoke([HumanMessage(content=prompt)])
    return result.content.strip()

def build_rag_agent_json(place_response, profile, location_request):
    # 카테고리/톤 추천
    place_count = len(place_response["locations"])
    categories, tones = recommend_categories_and_tones(profile, location_request, place_count)
    # user_context
    user_ctx = {
        "demographics": {
            "age": int(profile["age"]) if profile.get("age") and profile["age"].isdigit() else None,
            "mbti": profile.get("mbti"),
            "relationship_stage": profile.get("relationship_stage")
        },
        "preferences": [profile["atmosphere"]] if profile.get("atmosphere") else [],
        "requirements": {
            "budget_range": profile.get("budget"),
            "time_preference": profile.get("time_slot"),
            "party_size": 2,
            "transportation": location_request.get("transportation"),
            "weather_condition": location_request.get("weather_condition", None)
        }
    }
    # LLM 준비
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7, openai_api_key=openai_api_key)
    # search_targets 생성
    search_targets = []
    for idx, loc in enumerate(place_response["locations"]):
        category = categories[idx]
        tone = tones[idx]
        semantic_query = make_metadata_style_semantic_query_llm(
            llm=llm,
            area_name=loc["area_name"],
            category=category,
            tone=tone,
            user_ctx=user_ctx,
            profile=profile,
            location=loc,
            reason=loc.get("reason", None)
        )
        search_targets.append({
            "sequence": loc["sequence"],
            "category": category,
            "location": {
                "area_name": loc["area_name"],
                "coordinates": loc["coordinates"]
            },
            "semantic_query": semantic_query.strip()
        })
    # course_planning 예시(실제론 옵션화 가능)
    course_planning = {
        "optimization_goals": [
            "사용자 선호와 동선 최적화",
            "각 장소별 적절한 머무름 시간 제안"
        ],
        "route_constraints": {
            "max_travel_time_between": 30,
            "total_course_duration": 240,
            "flexibility": "medium"
        },
        "sequence_optimization": {
            "allow_reordering": True,
            "prioritize_given_sequence": True
        }
    }
    rag_json = {
        "request_id": place_response["request_id"],
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "search_targets": search_targets,
        "user_context": user_ctx,
        "course_planning": course_planning
    }
    return rag_json

def main():
    session_id = str(uuid.uuid4())
    print(f"\n===== DayToCourse 사용자 정보 입력 =====\n세션 ID: {session_id}\n")
    memory = ConversationBufferMemory()
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, openai_api_key=openai_api_key)
    profile = {}
    location_request = {}

    # 1. 오픈 프롬프트 (필수 정보 안내 추가)
    first_message = input(
        "오늘 데이트 코스를 어떻게 진행하고 싶으신가요? 자유롭게 말씀해 주세요!\n"
        "아래 항목들을 포함해서 한 번에 입력해주셔도 좋습니다.\n"
        "(나이, 성별, MBTI, 데이트 장소, 상대방과의 관계, 장소 분위기, 예산, 데이트 시간대, 장소 위치 표현)\n"
    ).strip()
    memory.save_context({"input": "오픈 프롬프트"}, {"output": first_message})

    # 2. LLM으로 필수 정보 추출 + 규칙 기반 보정
    extracted = extract_profile_from_llm(llm, first_message)
    for k in REQUIRED_KEYS:
        profile[k] = extracted.get(k, "")

    # 2-1. 장소 위치/주소 정보 통합 입력 및 구조화
    def ask_location_and_address():
        loc_input = input("장소 위치(정확한 지역, 근처, 사이, 여러 곳 등)를 입력해주세요: ").strip()
        # location_request 추출
        address_hint = None
        loc_req = extract_location_request_from_llm(llm, loc_input, address_hint=None)
        # address 추출
        addr_extracted = extract_profile_from_llm(llm, loc_input)
        address = addr_extracted.get("address", "")
        return loc_req, address

    address_hint = profile.get("address") if profile.get("address") else None
    location_request = extract_location_request_from_llm(llm, first_message, address_hint=address_hint)
    if not profile.get("address"):
        # address가 누락된 경우 location_request에서 reference_areas의 첫 번째 값 사용
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

    # 3. 누락된 필수 정보만 재질문
    for k in REQUIRED_KEYS:
        if not profile[k] and k != "address":
            q = {
                "age": "나이를 입력해주세요 (숫자): ",
                "gender": "성별을 입력해주세요 (남/여): ",
                "mbti": "MBTI를 입력해주세요 (예: ENFP): ",
                # "address": "데이트할 장소(지역/동네)를 입력해주세요: ", # address는 위에서 통합
                "relationship_stage": "상대방과의 관계를 입력해주세요 (연인/썸/친구 등): ",
                "atmosphere": "장소의 분위기를 입력해주세요 (예: 로맨틱, 조용한, 트렌디한, 활기찬 등): ",
                "budget": "예산을 입력해주세요 (예: 2만~5만원, 10만원 이하 등): ",
                "time_slot": "데이트 시간대를 입력해주세요 (예: 오전, 오후, 저녁, 밤 등): "
            }[k]
            ask_and_store(memory, profile, k, q)

    # 4. LLM 기반 교정/검증
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
                # 교정 불가, 재질문
                q = {
                    "age": "나이를 다시 입력해주세요 (숫자): ",
                    "gender": "성별을 다시 입력해주세요 (남/여): ",
                    "mbti": "MBTI를 다시 입력해주세요 (예: ENFP): ",
                    # "address": "데이트할 장소(지역/동네)를 다시 입력해주세요: ",
                    "relationship_stage": "상대방과의 관계를 다시 입력해주세요 (연인/썸/친구 등): ",
                    "atmosphere": "장소의 분위기를 다시 입력해주세요 (예: 로맨틱, 조용한, 트렌디한, 활기찬 등): ",
                    "budget": "예산을 다시 입력해주세요 (예: 2만~5만원, 10만원 이하 등): ",
                    "time_slot": "데이트 시간대를 다시 입력해주세요 (예: 오전, 오후, 저녁, 밤 등): "
                }[k]
                profile[k] = input(q).strip()

    # 5. 부가 정보 입력 의사 확인
    add_more = input("추가 정보(차량, 자기소개, 선호 등)를 입력하시겠습니까? (예/아니오): ").strip().lower()
    memory.save_context({"input": "추가 정보 입력 의사"}, {"output": add_more})
    if add_more == "예":
        for key, question in OPTIONAL_FIELDS:
            ask_and_store(memory, profile, key, question)

    # 6. JSON 저장 (location_request도 함께 저장)
    filename = f"profile_detail_{session_id}.json"
    output = {"profile": profile, "location_request": location_request}
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 사용자 정보가 {filename} 파일에 저장되었습니다!\n")
    print(json.dumps(output, ensure_ascii=False, indent=2))
    print(f"\n[세션 ID: {session_id}]\n")

    # 7. place agent용 JSON 생성 및 출력/저장
    place_json = build_place_agent_json(profile, location_request)
    place_filename = f"place_agent_request_from_chat.json"
    with open(place_filename, "w", encoding="utf-8") as f:
        json.dump(place_json, f, ensure_ascii=False, indent=2)
    print(f"\n✅ place agent 전송용 JSON이 {place_filename} 파일에 저장되었습니다!\n")
    print(json.dumps(place_json, ensure_ascii=False, indent=2))

    # 8. rag agent용 JSON 생성 (샘플 place agent 응답 사용)
    sample_place_path = os.path.join(os.path.dirname(__file__), "sample_place_agent_response.json")
    if os.path.exists(sample_place_path):
        with open(sample_place_path, "r", encoding="utf-8") as f:
            place_response = json.load(f)
        rag_json = build_rag_agent_json(place_response, profile, location_request)
        rag_filename = f"rag_agent_request_from_chat.json"
        with open(rag_filename, "w", encoding="utf-8") as f:
            json.dump(rag_json, f, ensure_ascii=False, indent=2)
        print(f"\n✅ rag agent 전송용 JSON이 {rag_filename} 파일에 저장되었습니다!\n")
        print(json.dumps(rag_json, ensure_ascii=False, indent=2))
    else:
        print("\n⚠️ sample_place_agent_response.json 파일이 존재하지 않아 rag agent용 JSON을 생성하지 않았습니다.\n")

if __name__ == "__main__":
    main()
