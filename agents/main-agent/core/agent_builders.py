from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
import uuid
from datetime import datetime

def build_place_agent_json(profile, location_request, max_travel_time=30):
    """Place Agent용 JSON 생성"""
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
    
    preferences = []
    if profile.get("atmosphere"):
        preferences.append(profile["atmosphere"])
    
    requirements = {
        "budget_level": map_budget(profile.get("budget")),
        "time_preference": profile.get("time_slot"),
        "transportation": map_transportation(location_request.get("transportation")),
        "max_travel_time": max_travel_time,
        "weather_condition": None
    }
    
    demographics = {
        "age": int(profile["age"]) if profile.get("age") and profile["age"].isdigit() else None,
        "mbti": profile.get("mbti"),
        "relationship_stage": profile.get("relationship_stage")
    }
    
    request_id = f"req-{str(uuid.uuid4())[:8]}"
    timestamp = datetime.datetime.now().isoformat(timespec="seconds")
    request_type = "proximity_based"
    
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
    """사용자 요구 기반 카테고리/톤 추천"""
    atmosphere = profile.get("atmosphere", "").lower()
    time_slot = profile.get("time_slot", "").lower()
    relationship = profile.get("relationship_stage", "").lower()
    budget = profile.get("budget", "")
    weather = location_request.get("weather_condition", "")

    if "비" in weather or "rain" in weather:
        categories = ["카페", "문화시설", "쇼핑"]
    elif "저녁" in time_slot or "밤" in time_slot:
        if "연인" in relationship or "로맨틱" in atmosphere:
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
    
    categories = (categories * ((place_count // len(categories)) + 1))[:place_count]

    # 술집이 2개 이상 연속으로 오지 않도록, 항상 마지막에만 오도록 보정
    if "술집" in categories:
        last_idx = max(idx for idx, cat in enumerate(categories) if cat == "술집")
        for idx, cat in enumerate(categories):
            if cat == "술집" and idx != last_idx:
                categories[idx] = "음식점" if "음식점" in categories else "카페"

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
    """메타데이터 스타일 시맨틱 쿼리 생성"""
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

def build_rag_agent_json(place_response, profile, location_request, openai_api_key, user_course_planning=None):
    """RAG Agent용 JSON 생성"""
    place_count = len(place_response["locations"])
    categories, tones = recommend_categories_and_tones(profile, location_request, place_count)
    
    requirements = {
        "budget_range": profile.get("budget"),
        "time_preference": profile.get("time_slot"),
        "party_size": 2,
        "transportation": location_request.get("transportation")
    }
    
    user_ctx = {
        "demographics": {
            "age": int(profile["age"]) if profile.get("age") and str(profile["age"]).isdigit() else None,
            "mbti": profile.get("mbti"),
            "relationship_stage": profile.get("relationship_stage")
        },
        "preferences": [profile["atmosphere"]] if profile.get("atmosphere") else [],
        "requirements": requirements
    }
    
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7, openai_api_key=openai_api_key)
    
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
    
    default_course_planning = {
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
    
    course_planning = default_course_planning.copy()
    if user_course_planning:
        for k in ["optimization_goals", "route_constraints", "sequence_optimization"]:
            if user_course_planning.get(k):
                course_planning[k] = user_course_planning[k]
    
    rag_json = {
        "request_id": place_response["request_id"],
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        "search_targets": search_targets,
        "user_context": user_ctx,
        "course_planning": course_planning
    }
    return rag_json