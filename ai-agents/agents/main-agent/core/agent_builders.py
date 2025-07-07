from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
import uuid
import json
from datetime import datetime

def generate_chat_summary_for_rag(session_info, llm):
    """전체 대화를 요약해서 핵심 요구사항 추출"""
    chat_history = session_info.get('chat_history', [])
    user_messages = [msg.get('content', '') for msg in chat_history if msg.get('role') == 'user']
    
    if not user_messages:
        return ""
    
    all_chat = ' '.join(user_messages)
    
    prompt = f"""사용자의 전체 대화를 분석해서 데이트 장소 추천을 위한 핵심 요구사항만 간결하게 추출하세요.

**전체 대화:**
{all_chat}

**추출할 정보:**
- 원하는 분위기/스타일
- 특별한 요구사항  
- 선호하는 활동
- 피하고 싶은 것들
- 특별한 상황/목적

**출력 형식:** 핵심 요구사항을 1-2문장으로 요약

**요약:**"""
    
    result = llm.invoke([HumanMessage(content=prompt)])
    return result.content.strip()

def _extract_categories_safely(session_info):
    """안전하게 카테고리 리스트 추출 (None 값 방지)"""
    if not session_info:
        return []
    
    recommendations = session_info.get("category_recommendations", [])
    if not recommendations:
        return []
    
    categories = []
    for rec in recommendations:
        if hasattr(rec, 'category') and rec.category:
            categories.append(rec.category)
        elif isinstance(rec, dict):
            category = rec.get("category") or rec.get("primary")
            if category:
                categories.append(category)
            else:
                categories.append("카페")  # 기본값
        else:
            categories.append("카페")  # 기본값
    
    return categories

def build_place_agent_json(profile, location_request, max_travel_time=30, session_info=None):
    """Place Agent용 JSON 생성"""
    
    # session_info 검증 및 초기화
    if session_info is None:
        session_info = {}
        print(f"[WARNING] build_place_agent_json - session_info가 None으로 전달됨")
    
    print(f"[DEBUG] build_place_agent_json - session_info 수신: {bool(session_info)}")
    if session_info:
        print(f"[DEBUG] build_place_agent_json - session_info keys: {list(session_info.keys())}")
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
    
    # profile을 딕셔너리로 변환 (UserProfile 객체 대응)
    if hasattr(profile, 'model_dump'):
        profile_dict = profile.model_dump()
    elif hasattr(profile, '__dict__'):
        profile_dict = profile.__dict__
    else:
        profile_dict = profile
    
    preferences = []
    if profile_dict.get("atmosphere"):
        preferences.append(profile_dict["atmosphere"])
    
    requirements = {
        "budget_level": map_budget(profile_dict.get("budget")),
        "time_preference": profile_dict.get("time_slot"),
        "transportation": map_transportation(profile_dict.get("transportation")),
        "max_travel_time": max_travel_time,
        "weather_condition": None
    }
    
    demographics = {
        "age": int(profile_dict["age"]) if profile_dict.get("age") and str(profile_dict["age"]).isdigit() else (profile_dict.get("age") if isinstance(profile_dict.get("age"), int) else None),
        "mbti": profile_dict.get("mbti"),
        "relationship_stage": profile_dict.get("relationship_stage")
    }
    
    request_id = f"req-{str(uuid.uuid4())[:8]}"
    timestamp = datetime.now().isoformat(timespec="seconds")
    request_type = "proximity_based"
    
    # 🔥 CRITICAL: location_clustering 정보 처리 및 AI에게 명확한 지시사항 생성
    location_clustering = session_info.get("location_clustering")
    ai_location_instructions = None
    
    print(f"[DEBUG] build_place_agent_json - location_clustering 추출: {bool(location_clustering)}")
    if location_clustering:
        print(f"[DEBUG] build_place_agent_json - location_clustering 내용: {location_clustering}")
        print(f"🎯 [PRIORITY] 사용자 지정 지역 정보가 확인됨 - AI 지시사항 생성 중")
    else:
        print(f"🚨 [CRITICAL ERROR] build_place_agent_json - location_clustering이 없음!")
        print(f"🚨 [CRITICAL ERROR] 사용자 지정 지역 정보 누락! Place Agent가 임의 추천할 것임!")
    
    if location_clustering and location_clustering.get("valid", False):
        strategy = location_clustering.get("strategy", "user_defined")
        groups = location_clustering.get("groups", [])
        
        print(f"🤖 AI 지시사항 생성 중 - Strategy: {strategy}")
        
        if strategy == "same_area":
            reference_area = location_request.get('reference_areas', ['사용자 지정 지역'])[0] if location_request.get('reference_areas') else '사용자 지정 지역'
            ai_location_instructions = {
                "strategy": "same_area",
                "instruction": f"🎯 사용자가 모든 {profile_dict.get('place_count', 3)}개 장소를 같은 지역({reference_area}) 내에서만 찾기를 명시적으로 요청함. 반드시 해당 지역 내 서로 다른 세부 위치들에서만 선택할 것.",
                "constraint": "⚠️ 절대 다른 구/동으로 나가지 말고, 오직 지정된 지역 내부의 서로 다른 장소들만 추천. 다른 지역 언급 시 즉시 중단."
            }
        elif strategy == "different_areas":
            ai_location_instructions = {
                "strategy": "different_areas", 
                "instruction": f"🎯 사용자가 각 장소를 서로 완전히 다른 지역에서 찾기를 명시적으로 요청함. {profile_dict.get('place_count', 3)}개 장소 모두 다른 구/동에서 선택할 것.",
                "constraint": "⚠️ 같은 지역에서 2개 이상 절대 선택 금지. 각각 완전히 다른 지역에서만 추천."
            }
        else:
            # 그룹별 처리 (가장 중요한 케이스)
            group_instructions = []
            detailed_instructions = []
            for i, group in enumerate(groups, 1):
                places = group.get("places", [])
                location = group.get("location", "")
                if places and location:
                    group_instructions.append(f"{places}번째 장소들은 {location}에서 선택")
                    detailed_instructions.append(f"그룹 {i}: {places}번째 장소 → 반드시 {location} 지역")
            
            ai_location_instructions = {
                "strategy": "custom_groups",
                "instruction": f"🎯 사용자가 장소별로 구체적인 지역을 명시적으로 지정함: {'; '.join(group_instructions)}. 이는 절대적인 요구사항임.",
                "constraint": f"⚠️ 다음 그룹별 지역 배치를 100% 준수할 것: {'; '.join(detailed_instructions)}. 다른 지역 선택 시 즉시 실패로 간주.",
                "groups_detail": groups  # 상세 그룹 정보 추가 전달
            }
        
        print(f"✅ [SUCCESS] AI 지시사항 생성 완료:")
        print(f"✅ [SUCCESS] - Strategy: {ai_location_instructions['strategy']}")
        print(f"✅ [SUCCESS] - Instruction: {ai_location_instructions['instruction'][:100]}...")
        print(f"✅ [SUCCESS] - Constraint: {ai_location_instructions['constraint'][:100]}...")
    else:
        print(f"🚨 [CRITICAL ERROR] location_clustering이 invalid 또는 없음")
        print(f"🚨 [CRITICAL ERROR] Valid: {location_clustering.get('valid', False) if location_clustering else 'N/A'}")
        print(f"🚨 [CRITICAL ERROR] AI 지시사항 생성 불가 - Place Agent가 임의 추천할 것임!")
    
    place_json = {
        "request_id": request_id,
        "timestamp": timestamp,
        "request_type": request_type,
        "location_request": {
            "proximity_type": location_request.get("proximity_type"),
            "reference_areas": location_request.get("reference_areas"),
            "place_count": profile_dict.get("place_count"),
            "proximity_preference": location_request.get("proximity_preference"),
            "location_clustering": location_clustering,
            "ai_location_instructions": ai_location_instructions
        },
        "user_context": {
            "demographics": demographics,
            "preferences": preferences,
            "requirements": requirements
        },
        "selected_categories": _extract_categories_safely(session_info)
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

def make_metadata_style_semantic_query_llm(llm, area_name, category, tone, user_ctx, profile, location, reason=None, session_info=None):
    """메타데이터 스타일 시맨틱 쿼리 생성 (채팅 기반)"""
    age = user_ctx['demographics'].get('age')
    relationship = user_ctx['demographics'].get('relationship_stage', '')
    time_pref = user_ctx['requirements'].get('time_preference', '')
    budget = user_ctx['requirements'].get('budget_range', '')
    transport = user_ctx['requirements'].get('transportation', '')
    atmosphere = profile.get('atmosphere', '')
    
    # 전체 대화 요약으로 핵심 요구사항 추출
    user_chat_context = ''
    if session_info:
        user_chat_context = generate_chat_summary_for_rag(session_info, llm)
    
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
    
    prompt = f"""당신은 장소 설명문 작성 전문가입니다.

**임무:**
- 아래 정보를 바탕으로 RAG DB의 metadata(설명문)와 최대한 유사한 스타일로, 2~3문장 이상의 자연스러운 설명문을 작성하세요.
- 장소명으로 시작하지 말고, 분위기, 특징, 경험, 추천 상황을 구체적으로 묘사하세요.
- 감성적/활기찬/고급스러운/편안한 톤 중 상황에 맞는 톤을 자연스럽게 녹여주세요.
- 사용자의 실제 채팅 내용을 반영하여 맞춤형 설명문을 작성하세요.

**사용자 채팅 내용:**
{user_chat_context}

**장소 정보:**
- 지역명: {area_name}
- 카테고리: {category}
- 분위기: {tone} / {atmosphere}
- 추천 상황: {situation_str}
- 선정 이유: {reason if reason else ''}

**예시:**
- 한강의 야경을 감상하며 연인과 프라이빗하게 와인을 즐길 수 있는 고급스러운 와인바. 라이브 음악과 함께 특별한 날을 기념하기 좋은 곳. 저녁 시간에 분위기가 한층 더 로맨틱해지는 공간.
- 트렌디한 감성의 카페에서 친구와 함께 여유로운 오후를 보내기에 완벽한 곳. 다양한 디저트와 감각적인 인테리어가 어우러져 특별한 경험을 선사합니다.

**설명문:**"""
    
    result = llm.invoke([HumanMessage(content=prompt)])
    return result.content.strip()

def build_rag_agent_json(place_response, profile, location_request, openai_api_key, user_course_planning=None, session_info=None):
    """RAG Agent용 JSON 생성 - GPT로 완벽한 데이터 매핑"""
    
    # 실제 Place Agent 응답에서 locations 추출
    locations = place_response.get("locations", [])
    if not locations:
        print(f"[ERROR] build_rag_agent_json - locations 데이터 없음")
        return None
    
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3, openai_api_key=openai_api_key)
    
    # 1. 모든 데이터 수집
    collected_data = _collect_all_data(place_response, profile, location_request, session_info, llm)
    
    # 2. JSON 템플릿 정의
    json_template = _get_json_template()
    
    # 3. GPT로 JSON 채우기
    filled_json = _fill_json_with_gpt(collected_data, json_template, llm)
    
    return filled_json

def _collect_all_data(place_response, profile, location_request, session_info, llm):
    """모든 데이터 수집"""
    locations = place_response.get("locations", [])
    session_profile = session_info.get("profile", {}) if session_info else {}
    
    # Place Agent 응답 정리
    place_info = []
    for idx, loc in enumerate(locations):
        # Place Agent에서 받은 실제 카테고리 사용
        actual_category = loc.get('venue_category', loc.get('category', '카페'))
        place_info.append(f"{idx+1}번째 장소: {loc.get('place_name', '이름없음')} ({loc['area_name']}, {actual_category}, {loc['coordinates']['latitude']}, {loc['coordinates']['longitude']})")
    
    # 사용자 프로필 정리
    profile_info = []
    if getattr(session_profile, "age", None):
        profile_info.append(f"나이: {session_profile.age}")
    if getattr(session_profile, "mbti", None):
        profile_info.append(f"MBTI: {session_profile.mbti}")
    if getattr(session_profile, "relationship_stage", None):
        profile_info.append(f"관계: {session_profile.relationship_stage}")
    if getattr(session_profile, "budget", None):
        profile_info.append(f"예산: {session_profile.budget}")
    if getattr(session_profile, "time_slot", None):
        profile_info.append(f"시간: {session_profile.time_slot}")
    if getattr(session_profile, "atmosphere", None):
        profile_info.append(f"분위기: {session_profile.atmosphere}")
    if getattr(session_profile, "transportation", None):
        profile_info.append(f"교통수단: {session_profile.transportation}")
    
    # 사용자 채팅 내용 추출
    chat_messages = []
    if session_info and session_info.get('chat_history'):
        user_messages = [msg.get('content', '') for msg in session_info['chat_history'] if msg.get('role') == 'user']
        chat_messages = user_messages[-5:]  # 최근 5개 메시지
    
    return {
        "place_agent_response": place_info,
        "user_profile": profile_info,
        "user_chat": chat_messages,
        "raw_locations": locations,
        "raw_profile": session_profile,
        "request_id": place_response.get("request_id", f"req-{datetime.now().strftime('%Y%m%d%H%M%S')}")
    }

def _generate_semantic_queries_with_gpt(collected_data, llm):
    """GPT로 semantic_query 생성"""
    locations = collected_data['raw_locations']
    chat_content = '\n'.join(collected_data['user_chat'])
    
    semantic_queries = []
    
    for idx, loc in enumerate(locations):
        # Place Agent에서 받은 실제 카테고리 사용
        category = loc.get('venue_category', loc.get('category', '카페'))
        
        prompt = f"""사용자 채팅 내용:
{chat_content}

카테고리: {category}

**지시사항:**
1. 위 채팅 내용을 분석해서 사용자의 의도와 상황을 파악하세요
2. RAG 데이터베이스 검색에 최적화된 자연스러운 한국어 문장으로 생성하세요
3. 다음 요소들을 포함해서 4-5문장으로 구성하세요:
   - 사용자가 원하는 분위기/상황
   - 누구와 함께하는지 (관계)
   - 어떤 경험을 원하는지
   - 해당 카테고리에서 찾고자 하는 특징
   - 구체적인 활동이나 순간들

**예시 스타일:**
"연인과 함께 로맨틱한 분위기에서 특별한 저녁 식사를 즐길 수 있는 음식점. 소중한 사람과 깊은 대화를 나누며 기념일 같은 순간을 만들어주는 곳. 고급스러운 인테리어와 분위기 좋은 조명이 어우러져 특별한 데이트를 연출할 수 있습니다. 맛있는 요리와 함께 여유로운 시간을 보내며 서로의 마음을 나눌 수 있는 공간. 오랫동안 기억에 남을 소중한 추억을 만들 수 있는 완벽한 장소입니다."

**생성된 검색 문구 (4-5문장):**"""
        
        try:
            result = llm.invoke([HumanMessage(content=prompt)])
            semantic_query = result.content.strip()
            semantic_queries.append(f"{idx+1}번 {category}: \"{semantic_query}\"")
            print(f"[DEBUG] semantic_query 생성 완료: {category}")
        except Exception as e:
            print(f"[ERROR] semantic_query 생성 실패: {str(e)}")
            # 실패시 기본 문구 사용
            fallback_query = f"{category}에서 편안하고 좋은 시간을 보낼 수 있는 곳"
            semantic_queries.append(f"{idx+1}번 {category}: \"{fallback_query}\"")
    
    return semantic_queries

def _get_json_template():
    """JSON 템플릿 반환"""
    return {
        "request_id": "채워주세요",
        "timestamp": "채워주세요",
        "search_targets": [
            {
                "sequence": "채워주세요",
                "category": "채워주세요",
                "location": {
                    "area_name": "채워주세요",
                    "coordinates": {
                        "latitude": "채워주세요",
                        "longitude": "채워주세요"
                    }
                },
                "semantic_query": "채워주세요"
            }
        ],
        "user_context": {
            "demographics": {
                "age": "채워주세요",
                "mbti": "채워주세요",
                "relationship_stage": "채워주세요"
            },
            "preferences": ["채워주세요"],
            "requirements": {
                "budget_range": "채워주세요",
                "time_preference": "채워주세요",
                "party_size": 2,
                "transportation": "채워주세요"
            }
        },
        "course_planning": {
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
    }

def _fill_json_with_gpt(collected_data, json_template, llm):
    """GPT로 JSON 채우기"""
    
    # semantic_query는 새롭게 생성
    semantic_queries = _generate_semantic_queries_with_gpt(collected_data, llm)
    
    prompt = f"""다음 수집된 정보를 바탕으로 JSON 템플릿의 모든 '채워주세요' 부분을 실제 데이터로 채워주세요.

**Place Agent 응답:**
{chr(10).join(collected_data['place_agent_response'])}

**사용자 프로필:**
{', '.join(collected_data['user_profile'])}

**사용자 채팅:**
{chr(10).join(collected_data['user_chat'])}

**새로 생성된 semantic_query들:**
{chr(10).join(semantic_queries)}

**채워야 할 JSON 템플릿:**
{json.dumps(json_template, ensure_ascii=False, indent=2)}

**지시사항:**
1. 모든 '채워주세요' 부분을 위의 수집된 정보로 정확히 채워주세요
2. semantic_query는 위에 새로 생성된 문구들을 그대로 사용하세요
3. search_targets 배열은 장소 개수만큼 생성하세요
4. 숫자값은 따옴표 없이, 문자값은 따옴표와 함께 반환하세요 (단, budget_range는 반드시 문자열로 처리)
5. timestamp는 현재 시간으로 ISO 형식으로 생성하세요
6. course_planning 부분은 그대로 유지하세요

**완성된 JSON만 반환해주세요:**"""
    
    try:
        result = llm.invoke([HumanMessage(content=prompt)])
        json_str = result.content.strip()
        
        # JSON 파싱 시도
        if json_str.startswith('```json'):
            json_str = json_str.replace('```json', '').replace('```', '').strip()
        
        filled_json = json.loads(json_str)
        print(f"[DEBUG] GPT로 JSON 채우기 성공")
        return filled_json
        
    except Exception as e:
        print(f"[ERROR] GPT JSON 채우기 실패: {str(e)}")
        # 실패시 fallback으로 기본 구조 반환
        return _create_fallback_json(collected_data)

def _create_fallback_json(collected_data):
    """GPT 실패시 fallback JSON 생성"""
    locations = collected_data['raw_locations']
    profile = collected_data['raw_profile']
    
    search_targets = []
    for idx, loc in enumerate(locations):
        # Place Agent에서 받은 실제 카테고리 사용
        actual_category = loc.get("venue_category", loc.get("category", "카페"))
        search_targets.append({
            "sequence": loc["sequence"],
            "category": actual_category,
            "location": {
                "area_name": loc["area_name"],
                "coordinates": loc["coordinates"]
            },
            "semantic_query": f"기본 검색 문구 - {loc['area_name']} {actual_category}"
        })
    
    return {
        "request_id": collected_data['request_id'],
        "timestamp": datetime.now().isoformat(),
        "search_targets": search_targets,
        "user_context": {
            "demographics": {
                "age": profile.get("age"),
                "mbti": profile.get("mbti"),
                "relationship_stage": profile.get("relationship_stage")
            },
            "preferences": [profile.get("atmosphere")] if profile.get("atmosphere") else [],
            "requirements": {
                "budget_range": str(profile.get("budget", "")) if profile.get("budget") else "",
                "time_preference": profile.get("time_slot"),
                "party_size": 2,
                "transportation": profile.get("transportation")
            }
        },
        "course_planning": {
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
    }