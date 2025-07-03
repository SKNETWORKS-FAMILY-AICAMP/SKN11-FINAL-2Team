from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
import json
import re
from .profile_extractor import extract_profile_from_llm

def clean_area(area):
    """쉼표, 슬래시 등으로 분할 후 위치 특성 단어만 제거, '동', '역'으로 끝나면 그대로 둠"""
    areas = re.split(r'[,/]', area)
    result = []
    for a in areas:
        a = a.strip()
        if a.endswith("동") or a.endswith("역"):
            result.append(a)
            continue
        a = re.sub(r"(근처|부근|인근|쪽|사이|중간|에서)", "", a)
        a = a.strip()
        if a:
            result.append(a)
    return result

def extract_location_request_from_llm(llm, user_message, address_hint=None):
    """사용자 입력에서 데이트 장소 위치 정보를 구조화"""
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