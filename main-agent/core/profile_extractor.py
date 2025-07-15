from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
import json
import re

REQUIRED_KEYS = [
    "age", "gender", "mbti", "address", "relationship_stage", "atmosphere", "budget", "time_slot", "duration", "place_count"
]

def rule_based_gender_relationship(user_message, extracted):
    """여자친구/남자친구 등에서 성별 및 관계 추론 및 정규화"""
    # LLM이 '여자', '남자' 등으로 추출한 경우도 정규화
    if extracted.get("gender"):
        if extracted["gender"] in ["여자", "여성", "여자사람"]:
            extracted["gender"] = "여"
        elif extracted["gender"] in ["남자", "남성", "남자사람"]:
            extracted["gender"] = "남"
    # 여자친구/남자친구 키워드가 있으면 무조건 덮어씀
    if re.search(r"여자친구", user_message):
        extracted["gender"] = "남"
    elif re.search(r"남자친구", user_message):
        extracted["gender"] = "여"
    
    if not extracted.get("relationship_stage") or extracted["relationship_stage"] == "":
        if re.search(r"여자친구|남자친구", user_message):
            extracted["relationship_stage"] = "연인"
        elif re.search(r"썸", user_message):
            extracted["relationship_stage"] = "썸"
        elif re.search(r"친구", user_message):
            extracted["relationship_stage"] = "친구"
    return extracted

def extract_profile_from_llm(llm, user_message):
    """LLM을 사용하여 사용자 메시지에서 프로필 정보 추출"""
    prompt = (
        "아래 사용자의 답변에서 나이, 성별, MBTI, 데이트 장소, 상대방과의 관계, 장소 분위기, 예산, 데이트 시간대, 데이트 시간(몇시간), 방문 장소 개수를 추출해서 "
        "각 항목별로 key:value 형태로 JSON으로 출력해줘. "
        "\n**중요한 변환 규칙:**\n"
        "- 한국어 숫자는 반드시 아라비아 숫자로 변환: 스물다섯살→25, 서른살→30, 십만원→100000\n"
        "- 한국어 나이 표현 정규화: 스물다섯살→25, 이십대 중반→25, 서른 중반→35\n"
        "- 한국어 금액 표현 정규화: 십만원→100000, 오만원→50000, 삼만원→30000\n"
        "- 역명, 동명은 그대로 유지: 용산역→용산역, 홍대입구역→홍대입구역, 강남→강남\n"
        "- 성별 정규화: 남자→남, 여자→여, 남성→남, 여성→여\n"
        "성별은 상대방 호칭(여자친구/남자친구 등)에서 유추할 수 있으면 반드시 추론해서 채워줘. "
        "장소(지역/동네), 분위기(로맨틱, 조용한, 트렌디한, 활기찬 등), 예산(2만~5만원, 10만원 이하 등), 시간대(오전, 오후, 저녁, 밤 등), "
        "데이트 시간(2시간, 3시간, 반나절, 하루종일 등), 방문 장소 개수(2개, 3개 등)도 문장 안에서 최대한 추출해줘. "
        "없는 항목은 빈 문자열로 둬.\n"
        "예시1: 답변: '여자친구랑 홍대에서 분위기 좋은 로맨틱 데이트할거야. 저녁에 오만원 정도 생각해. 3시간 정도 할 예정이고 2-3개 장소 가고 싶어.' → {\"age\": \"\", \"gender\": \"남\", \"mbti\": \"\", \"address\": \"홍대\", \"relationship_stage\": \"연인\", \"atmosphere\": \"로맨틱\", \"budget\": \"50000\", \"time_slot\": \"저녁\", \"duration\": \"3시간\", \"place_count\": \"3개\"}\n"
        "예시2: 답변: '남자친구랑 강남에서 조용한 저녁 데이트, 예산은 십만원 이하, 4시간 정도 할 예정' → {\"age\": \"\", \"gender\": \"여\", \"mbti\": \"\", \"address\": \"강남\", \"relationship_stage\": \"연인\", \"atmosphere\": \"조용한\", \"budget\": \"100000\", \"time_slot\": \"저녁\", \"duration\": \"4시간\", \"place_count\": \"\"}\n"
        "예시3: 답변: '스물다섯살 ENFP, 썸타는 사람과 용산역에서 트렌디한 데이트, 오후에 삼만원 정도, 반나절' → {\"age\": \"25\", \"gender\": \"\", \"mbti\": \"ENFP\", \"address\": \"용산역\", \"relationship_stage\": \"썸\", \"atmosphere\": \"트렌디한\", \"budget\": \"30000\", \"time_slot\": \"오후\", \"duration\": \"반나절\", \"place_count\": \"\"}\n"
        "예시4: 답변: '서른살 남자, 여자친구와 홍대입구역 근처에서 십오만원 예산으로 저녁 데이트' → {\"age\": \"30\", \"gender\": \"남\", \"mbti\": \"\", \"address\": \"홍대입구역\", \"relationship_stage\": \"연인\", \"atmosphere\": \"\", \"budget\": \"150000\", \"time_slot\": \"저녁\", \"duration\": \"\", \"place_count\": \"\"}\n"
        f"답변: {user_message}\n"
        "반드시 JSON만 출력해줘."
    )
    result = llm.invoke([HumanMessage(content=prompt)])
    try:
        profile = json.loads(result.content)
    except Exception:
        profile = {k: "" for k in REQUIRED_KEYS}
    
    profile = rule_based_gender_relationship(user_message, profile)
    return profile

def llm_correct_field(llm, key, value):
    """각 항목별 교정 프롬프트"""
    field_desc = {
        "age": "나이(숫자, 10~100세 사이)",
        "gender": "성별(남/여)",
        "mbti": "MBTI(예: ENFP, INFP 등 4글자)",
        "address": "장소(지역/동네)",
        "relationship_stage": "관계(연인/썸/친구 등)",
        "atmosphere": "장소 분위기(로맨틱, 조용한, 트렌디한, 활기찬 등)",
        "budget": "예산(예: 2만~5만원, 10만원 이하 등)",
        "time_slot": "데이트 시간대(오전, 오후, 저녁, 밤 등)",
        "duration": "데이트 시간(예: 2시간, 3시간, 반나절, 하루종일 등)",
        "place_count": "방문 장소 개수(예: 2개, 3개, 4개 등)"
    }[key]
    
    prompt = (
        f"입력값: '{value}'\n"
        f"이 값이 {field_desc}에 적합한지 확인하고, 오타나 비정상 입력이면 올바른 값으로 교정해줘. "
        f"교정이 불가능하면 빈 문자열만 출력해.\n"
        f"**필수 한국어 변환 규칙:**\n"
        f"- 한국어 숫자 → 아라비아 숫자: 스물다섯→25, 서른→30, 마흔→40, 십만→100000\n"
        f"- 한국어 나이: 스물다섯살→25, 이십대 중반→25, 서른 중반→35\n"
        f"- 한국어 금액: 십만원→100000, 오만원→50000, 삼만원→30000\n"
        f"- 역명/동명은 그대로 유지: 용산역→용산역, 홍대입구역→홍대입구역\n"
        f"예시1: 입력값: '스물다섯살' → '25'\n"
        f"예시2: 입력값: '십만원 이하' → '100000'\n"
        f"예시3: 입력값: '조용한 분우기' → '조용한 분위기'\n"
        f"예시4: 입력값: 'enfp' → 'ENFP'\n"
        f"예시5: 입력값: '남자' → '남'\n"
        f"예시6: 입력값: '29살' → '29'\n"
        f"예시7: 입력값: '밤시간' → '밤'\n"
        f"예시8: 입력값: '서른살' → '30'\n"
        f"예시9: 입력값: '오만원' → '50000'\n"
        f"예시8: 입력값: '강남역' → '강남'\n"
        f"예시9: 입력값: 'ㅇㄴㅁ' → ''\n"
        f"입력값: '{value}'\n"
        f"교정값만 출력해줘."
    )
    result = llm.invoke([HumanMessage(content=prompt)])
    return result.content.strip().replace('"', '').replace("'", "")