"""
Place Agent Implementation
지역 선정 및 좌표 반환 전문 서비스 (LLM 통합 + 하이브리드 확장)
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import httpx
import asyncio
from openai import OpenAI
import os
from datetime import datetime
import json
from dotenv import load_dotenv
import math

# 환경변수 로드
load_dotenv()

# FastAPI 앱 초기화
app = FastAPI(title="Place Agent", description="지역 분석 및 좌표 반환 서비스", version="2.0.0")

# OpenAI 클라이언트 초기화
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 메인 에이전트 스펙에 맞춘 요청 모델들
class LocationRequest(BaseModel):
    proximity_type: str  # "exact", "near", "between", "multi"
    reference_areas: List[str]  # 장소명 리스트
    place_count: int = 3  # 추천받을 장소 개수
    proximity_preference: Optional[str] = None  # "middle", "near", null
    transportation: Optional[str] = None  # "도보", "차", "지하철", null

class Demographics(BaseModel):
    age: int
    mbti: str
    relationship_stage: str  # "연인", "썸", "친구"

class Requirements(BaseModel):
    budget_level: Optional[str] = None  # "low", "medium", "high", null
    time_preference: str  # "오전", "오후", "저녁", "밤"
    transportation: Optional[str] = None  # "도보", "차", "지하철", null
    max_travel_time: Optional[int] = None

class UserContext(BaseModel):
    demographics: Demographics
    preferences: List[str]  # ["조용한 분위기", "트렌디한"] - 단순 리스트
    requirements: Requirements

class PlaceAgentRequest(BaseModel):
    request_id: str
    timestamp: str
    request_type: str = "proximity_based"  # 현재는 고정
    location_request: LocationRequest
    user_context: UserContext
    selected_categories: Optional[List[str]] = None  # ["카페", "레스토랑"]

# 응답 모델들
class Coordinates(BaseModel):
    latitude: float
    longitude: float

class LocationResponse(BaseModel):
    sequence: int
    area_name: str
    coordinates: Coordinates
    reason: str  # 자연스러운 문장 형태

class PlaceAgentResponse(BaseModel):
    request_id: str
    success: bool
    locations: List[LocationResponse]
    error_message: Optional[str] = None

# 서울 지역 중심 좌표 및 특성 데이터
AREA_CENTERS = {
    "홍대": {
        "lat": 37.5563, "lng": 126.9233,
        "signature_traits": ["젊은문화중심지", "자유로운예술가", "라이브음악"],
        "vibe": "자유롭고 창의적인",
        "keywords": ["클럽", "라이브 음악", "길거리 공연", "독특한 카페"]
    },
    "강남": {
        "lat": 37.4982, "lng": 127.0274,
        "signature_traits": ["세련된비즈니스가", "고급엔터테인먼트", "모던라이프스타일"],
        "vibe": "세련되고 모던한",
        "keywords": ["고급 레스토랑", "루프탑바", "쇼핑몰", "스타일리시한 카페"]
    },
    "강남역": {
        "lat": 37.4982, "lng": 127.0274,
        "signature_traits": ["교통허브중심", "지하상가", "만남의장소"],
        "vibe": "바쁘고 활기찬",
        "keywords": ["지하상가", "교통중심", "쇼핑", "만남의 장소"]
    },
    "이태원": {
        "lat": 37.5344, "lng": 126.9947,
        "signature_traits": ["이국적분위기", "글로벌다이닝", "루프탑뷰"],
        "vibe": "글로벌하고 이색적인",
        "keywords": ["다국적 음식", "이국적 분위기", "펜션카페", "루프탑 테라스"]
    },
    "성수": {
        "lat": 37.5447, "lng": 127.0557,
        "signature_traits": ["힙스터감성공간", "인더스트리얼카페", "아트갤러리"],
        "vibe": "힙하고 트렌디한",
        "keywords": ["인더스트리얼 카페", "갤러리", "공장 개조", "감성적인 공간"]
    },
    "연남": {
        "lat": 37.5589, "lng": 126.9239,
        "signature_traits": ["아늑한골목길", "감성브런치", "조용한데이트"],
        "vibe": "아늑하고 감성적인",
        "keywords": ["골목 카페", "아기자기한 상점", "감성 브런치", "조용한 분위기"]
    },
    "신촌": {
        "lat": 37.5596, "lng": 126.9422,
        "signature_traits": ["대학가활력", "젊은에너지", "친근한분위기"],
        "vibe": "활기차고 친근한",
        "keywords": ["저렴한 맛집", "학생 카페", "노래방", "활기찬 거리"]
    },
    "명동": {
        "lat": 37.5636, "lng": 126.9826,
        "signature_traits": ["전통현대조화", "관광명소", "쇼핑중심지"],
        "vibe": "전통적이면서 현대적인",
        "keywords": ["전통 찻집", "한옥 카페", "쇼핑", "관광 명소"]
    },
    "인사동": {
        "lat": 37.5717, "lng": 126.9857,
        "signature_traits": ["한국문화중심", "전통예술", "고즈넉한분위기"],
        "vibe": "고즈넉하고 문화적인",
        "keywords": ["전통차", "갤러리", "공예품", "한국 문화"]
    },
    "압구정": {
        "lat": 37.5270, "lng": 127.0276,
        "signature_traits": ["고급쇼핑문화", "럭셔리라이프", "프리미엄경험"],
        "vibe": "고급스럽고 우아한",
        "keywords": ["럭셔리 카페", "프리미엄 브런치", "디자이너 브랜드", "고급 베이커리"]
    },
    "건대": {
        "lat": 37.5403, "lng": 127.0695,
        "signature_traits": ["학생친화적공간", "24시간활력", "합리적선택"],
        "vibe": "역동적이고 친근한",
        "keywords": ["24시간 카페", "스터디 카페", "합리적 가격", "학생 친화적"]
    },
    "여의도": {
        "lat": 37.5219, "lng": 126.9245,
        "signature_traits": ["비즈니스금융중심", "한강뷰", "야경명소"],
        "vibe": "현대적이고 세련된",
        "keywords": ["한강공원", "고층빌딩", "금융가", "야경명소"]
    },
    "잠실": {
        "lat": 37.5134, "lng": 127.1000,
        "signature_traits": ["대형복합문화공간", "엔터테인먼트", "편의시설완비"],
        "vibe": "활기차고 편리한",
        "keywords": ["롯데월드", "쇼핑몰", "스카이타워", "복합문화공간"]
    },
    "고대": {
        "lat": 37.5895, "lng": 127.0323,
        "signature_traits": ["젊은학구적분위기", "대학가문화", "청춘에너지"],
        "vibe": "젊고 학구적인",
        "keywords": ["대학가", "학생문화", "저렴한식당", "스터디카페"]
    }
}

# MBTI별 선호 지역 매핑
MBTI_PREFERENCES = {
    "E": ["홍대", "강남", "신촌", "건대"],  # 외향형
    "I": ["연남", "성수", "인사동", "압구정"],  # 내향형
    "N": ["성수", "홍대", "이태원", "연남"],  # 직관형
    "S": ["명동", "인사동", "압구정", "강남"],  # 감각형
    "T": ["강남", "압구정", "성수"],  # 사고형
    "F": ["연남", "홍대", "인사동"],  # 감정형
    "J": ["압구정", "명동", "인사동"],  # 판단형
    "P": ["홍대", "성수", "이태원"]   # 인식형
}

# 관계단계별 추천 지역
RELATIONSHIP_PREFERENCES = {
    "썸": ["연남", "성수", "홍대", "이태원"],
    "연인": ["강남", "이태원", "압구정", "홍대"],
    "친구": ["홍대", "강남", "성수", "건대"]
}

class PlaceAgent:
    def __init__(self):
        self.kakao_api_key = os.getenv("KAKAO_API_KEY")

    def create_analysis_prompt(self, request: PlaceAgentRequest) -> str:
        """LLM을 위한 지역 분석 프롬프트 생성 (하이브리드 - 기존지역 + 새지역)"""
        user_ctx = request.user_context
        loc_req = request.location_request
        
        # 기존 정의된 지역들
        predefined_areas = list(AREA_CENTERS.keys())
        
        # null 값 처리
        budget = user_ctx.requirements.budget_level or "제한없음"
        transportation = user_ctx.requirements.transportation or loc_req.transportation or "제한없음"
        
        prompt = f"""당신은 서울 지역 분석 전문가입니다.
사용자 요청에 맞는 최적의 서울 지역을 선정하고, 선정 이유를 자연스러운 문장으로 설명해주세요.

사용자 정보:
- 나이: {user_ctx.demographics.age}세
- MBTI: {user_ctx.demographics.mbti}
- 관계: {user_ctx.demographics.relationship_stage}
- 선호사항: {', '.join(user_ctx.preferences) if user_ctx.preferences else '특별한 선호 없음'}
- 예산: {budget}
- 시간대: {user_ctx.requirements.time_preference}
- 교통수단: {transportation}

위치 요청:
- 타입: {loc_req.proximity_type}
- 기준지역: {loc_req.reference_areas if loc_req.reference_areas else '없음'}
- 필요개수: {loc_req.place_count}곳

추천 우선순위:
1. 기존 주요 지역: {', '.join(predefined_areas)}
2. 서울 내 다른 지역도 가능 (예: 마포구, 서초구, 용산구, 성북구, 송파구, 영등포구 등)

요청:
1. 위 조건에 맞는 서울 지역 {loc_req.place_count}곳을 선정하세요.
2. 기존 주요 지역을 우선 고려하되, 사용자 요청에 더 적합한 다른 지역이 있다면 추천해주세요.
3. 각 지역별로 선정 이유를 자연스러운 1~2문장으로 설명하세요.
4. 교통 접근성(지하철역 등)도 함께 언급해주세요.

응답 형식 (정확히 준수):
지역명1|이곳은 ~한 이유로 추천합니다. ~해서 ~합니다.
지역명2|이곳은 ~한 이유로 추천합니다. ~해서 ~합니다.
지역명3|이곳은 ~한 이유로 추천합니다. ~해서 ~합니다.

예시:
성수|이곳은 조용한 분위기와 감각적인 카페들이 많아 INTJ 성향의 편안한 대화를 즐기기에 적합하여 추천합니다. 또한, 지하철 2호선으로 접근성이 좋아서 이동이 편리합니다.
마포구|이곳은 조용한 주거지역으로 {user_ctx.demographics.age}세 {user_ctx.demographics.relationship_stage}가 편안하게 대화할 수 있는 환경을 제공하여 추천합니다. 지하철 6호선과 공항철도로 접근이 용이합니다."""
        
        return prompt

    def parse_llm_response(self, llm_text: str) -> Dict[str, List[str]]:
        """LLM 응답을 파싱하여 지역명과 이유 추출 (하이브리드 지원)"""
        try:
            lines = [line.strip() for line in llm_text.strip().split('\n') if line.strip()]
            areas = []
            reasons = []
            
            for line in lines:
                if '|' in line:
                    parts = line.split('|', 1)
                    if len(parts) == 2:
                        area = parts[0].strip()
                        reason = parts[1].strip()
                        
                        # 모든 지역 허용 (AREA_CENTERS에 없는 지역도 포함)
                        areas.append(area)
                        reasons.append(reason)
            
            return {"areas": areas, "reasons": reasons}
        
        except Exception as e:
            print(f"LLM 응답 파싱 실패: {e}")
            return {"areas": [], "reasons": []}

    async def analyze_new_area_characteristics(self, area_name: str, user_context: UserContext) -> Dict:
        """새로운 지역에 대한 LLM 특성 분석"""
        try:
            prompt = f"""'{area_name}' 지역에 대해 분석해주세요.

사용자 정보:
- 나이: {user_context.demographics.age}세
- MBTI: {user_context.demographics.mbti}
- 관계: {user_context.demographics.relationship_stage}
- 선호: {', '.join(user_context.preferences)}
- 예산: {user_context.requirements.budget_level}
- 시간대: {user_context.requirements.time_preference}

다음 형식으로 정확히 응답해주세요:
특성:|키워드1,키워드2,키워드3
분위기:|한단어설명
이유:|사용자에게적합한상세이유문장

예시:
특성:|주거지역,조용한분위기,가족친화적
분위기:|평온한
이유:|조용한 주거지역으로 {user_context.demographics.age}세 {user_context.demographics.relationship_stage}가 편안하게 대화하기 좋은 환경입니다. 지하철 접근성도 우수합니다."""

            response = await asyncio.to_thread(
                client.chat.completions.create,
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=300
            )
            
            llm_text = response.choices[0].message.content.strip()
            print(f"새 지역 '{area_name}' 특성 분석: {llm_text}")
            
            # 응답 파싱
            result = {"signature_traits": ["일반지역"], "vibe": "특별한", "reason": f"{area_name} 지역 추천"}
            
            lines = llm_text.split('\n')
            for line in lines:
                if '특성:|' in line:
                    traits = line.split('특성:|')[1].strip().split(',')
                    result["signature_traits"] = [t.strip() for t in traits if t.strip()]
                elif '분위기:|' in line:
                    result["vibe"] = line.split('분위기:|')[1].strip()
                elif '이유:|' in line:
                    result["reason"] = line.split('이유:|')[1].strip()
            
            return result
            
        except Exception as e:
            print(f"지역 특성 분석 실패: {e}")
            return {
                "signature_traits": ["일반지역"],
                "vibe": "특별한",
                "reason": f"{area_name} 지역으로 데이트하기 좋은 곳입니다."
            }

    async def analyze_with_llm(self, request: PlaceAgentRequest) -> Dict[str, List[str]]:
        """LLM을 활용한 지역 분석 (하이브리드 지원)"""
        try:
            prompt = self.create_analysis_prompt(request)
            
            response = await asyncio.to_thread(
                client.chat.completions.create,
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=500
            )
            
            llm_text = response.choices[0].message.content
            print(f"LLM 응답: {llm_text}")
            
            return self.parse_llm_response(llm_text)
            
        except Exception as e:
            print(f"LLM 분석 실패: {e}")
            return {"areas": [], "reasons": []}

    def generate_simple_reason(self, area_name: str, user_context: UserContext) -> str:
        """간단한 이유 생성 (fallback용)"""
        demo = user_context.demographics
        req = user_context.requirements
        
        # 지역 정보 확인
        area_info = AREA_CENTERS.get(area_name, {})
        vibe = area_info.get('vibe', '특별한')
        
        reason = f"이곳은 {vibe} 분위기로 {demo.age}세 {demo.relationship_stage}에게 적합하여 추천합니다. "
        
        # transportation null 처리
        transport = req.transportation
        if transport == "지하철":
            reason += "지하철 접근성이 좋아 이동이 편리합니다."
        elif transport:
            reason += f"{transport} 이용 시 접근성이 우수합니다."
        else:
            reason += "접근성이 우수합니다."
            
        return reason

    async def get_multiple_coordinates_for_area(self, area_name: str, count: int, user_context: UserContext) -> List[Dict]:
        """같은 지역 내에서 여러 세부 위치 좌표 조회"""
        results = []
        # 1. 기본 지역 정보 먼저 조회
        base_info = await self.get_coordinates_from_kakao(area_name, user_context)
        if base_info:
            results.append({
                **base_info,
                "sub_location": f"{area_name} 중심가",
                "detail": "메인 상권 지역"
            })
        if not self.kakao_api_key or len(results) >= count:
            return results[:count]
        # 2. 같은 지역의 다른 세부 위치들 검색
        search_variations = [
            f"{area_name} 공원",  
            f"{area_name} 관광명소",
            f"{area_name} 맛집",
            f"{area_name} 까페",
            f"{area_name} 주점",
        ]
        try:
            headers = {"Authorization": f"KakaoAK {self.kakao_api_key}"}
            async with httpx.AsyncClient() as client_session:
                for variation in search_variations:
                    if len(results) >= count:
                        break
                    response = await client_session.get(
                        "https://dapi.kakao.com/v2/local/search/keyword.json",
                        params={"query": variation + " 서울", "size": 3},
                        headers=headers
                    )
                    if response.status_code == 200:
                        data = response.json()
                        for place in data.get("documents", []):
                            if len(results) >= count:
                                break
                            lat, lng = float(place["y"]), float(place["x"])
                            # 기존 좌표와 너무 가깝지 않은지 체크 (최소 100m 거리)
                            is_duplicate = False
                            for existing in results:
                                distance = math.sqrt(
                                    (lat - existing["lat"]) ** 2 +
                                    (lng - existing["lng"]) ** 2
                                ) * 111000  # 대략적인 미터 변환
                                if distance < 100:  # 100m 이내면 중복으로 간주
                                    is_duplicate = True
                                    break
                            if not is_duplicate:
                                # 새로운 지역인 경우 LLM 분석
                                if area_name not in AREA_CENTERS and user_context:
                                    area_analysis = await self.analyze_new_area_characteristics(area_name, user_context)
                                    llm_reason = area_analysis["reason"]
                                    signature_traits = area_analysis["signature_traits"]
                                    vibe = area_analysis["vibe"]
                                else:
                                    area_info = AREA_CENTERS.get(area_name, {})
                                    llm_reason = None
                                    signature_traits = area_info.get("signature_traits", ["일반지역"])
                                    vibe = area_info.get("vibe", "특별한")
                                results.append({
                                    "lat": lat,
                                    "lng": lng,
                                    "signature_traits": signature_traits,
                                    "vibe": vibe,
                                    "keywords": signature_traits,
                                    "llm_reason": llm_reason,
                                    "sub_location": place.get("place_name", f"{area_name} 주변"),
                                    "detail": f"{place.get('category_name', '장소')} 근처"
                                })
        except Exception as e:
            print(f"세부 위치 검색 실패: {e}")
        # 부족한 만큼 기본 위치 주변으로 약간씩 변경해서 채우기
        while len(results) < count and base_info:
            offset_lat = base_info["lat"] + (len(results) * 0.001)  # 약 100m씩 offset
            offset_lng = base_info["lng"] + (len(results) * 0.001)
            results.append({
                **base_info,
                "lat": offset_lat,
                "lng": offset_lng,
                "sub_location": f"{area_name} {len(results)+1}번 구역",
                "detail": f"{area_name} 주변 지역"
            })
        return results[:count]

    async def get_coordinates_from_kakao(self, area_name: str, user_context: Optional[UserContext] = None) -> Optional[Dict]:
        """하이브리드 지역 정보 조회 - 기존 데이터 우선, 새 지역은 LLM 분석"""
        # 1단계: 기존 하드코딩 데이터 우선 사용
        if area_name in AREA_CENTERS:
            return AREA_CENTERS[area_name]
        # 2단계: Kakao API로 좌표 확인
        if not self.kakao_api_key:
            print(f"알 수 없는 지역: {area_name}, Kakao API 키도 없음")
            return None
        try:
            headers = {"Authorization": f"KakaoAK {self.kakao_api_key}"}
            async with httpx.AsyncClient() as client_session:
                response = await client_session.get(
                    "https://dapi.kakao.com/v2/local/search/keyword.json",
                    params={"query": area_name + " 서울"},  # 서울로 한정
                    headers=headers
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get("documents"):
                        place = data["documents"][0]
                        coords = {
                            "lat": float(place["y"]),
                            "lng": float(place["x"])
                        }
                        # 3단계: 사용자 컨텍스트가 있으면 LLM으로 지역 특성 분석
                        if user_context:
                            print(f"새로운 지역 '{area_name}' LLM 분석 시작...")
                            area_analysis = await self.analyze_new_area_characteristics(area_name, user_context)
                            return {
                                "lat": coords["lat"],
                                "lng": coords["lng"],
                                "signature_traits": area_analysis["signature_traits"],
                                "vibe": area_analysis["vibe"],
                                "keywords": area_analysis["signature_traits"],
                                "llm_reason": area_analysis["reason"]  # LLM 생성 이유 별도 저장
                            }
                        # 4단계: 컨텍스트 없으면 기본값
                        return {
                            "lat": coords["lat"],
                            "lng": coords["lng"],
                            "signature_traits": ["일반지역"],
                            "vibe": "특별한",
                            "keywords": ["일반지역"]
                        }
        except Exception as e:
            print(f"Kakao API 요청 실패: {e}")
        return None

    def select_areas_by_proximity(self, request: PlaceAgentRequest) -> List[str]:
        """proximity_type에 따른 지역 선정 (룰 기반 fallback)"""
        location_req = request.location_request
        user_context = request.user_context
        
        proximity_type = location_req.proximity_type
        reference_areas = location_req.reference_areas
        place_count = location_req.place_count
        
        if proximity_type == "exact":
            # 정확한 장소 - reference_areas 그대로 반환
            return reference_areas[:place_count]
            
        elif proximity_type == "near":
            # 근처 - 첫 번째 reference_area 근처 지역들
            if not reference_areas:
                return list(AREA_CENTERS.keys())[:place_count]
            
            base_area = reference_areas[0]
            base_info = AREA_CENTERS.get(base_area)
            if not base_info:
                return list(AREA_CENTERS.keys())[:place_count]
            
            # 거리 기반 정렬
            scored = []
            for area_name, area_data in AREA_CENTERS.items():
                if area_name != base_area:
                    distance = math.sqrt(
                        (area_data["lat"] - base_info["lat"]) ** 2 + 
                        (area_data["lng"] - base_info["lng"]) ** 2
                    )
                    scored.append((area_name, distance))
            
            scored.sort(key=lambda x: x[1])  # 거리순 정렬
            return [area for area, _ in scored[:place_count]]
            
        elif proximity_type == "between":
            # 두 장소 사이 - 중간지점 계산
            if len(reference_areas) < 2:
                return list(AREA_CENTERS.keys())[:place_count]
            
            area1_info = AREA_CENTERS.get(reference_areas[0])
            area2_info = AREA_CENTERS.get(reference_areas[1])
            if not area1_info or not area2_info:
                return list(AREA_CENTERS.keys())[:place_count]
            
            # 중간지점 계산
            mid_lat = (area1_info["lat"] + area2_info["lat"]) / 2
            mid_lng = (area1_info["lng"] + area2_info["lng"]) / 2
            
            # 중간지점에서 가까운 순으로 정렬
            scored = []
            for area_name, area_data in AREA_CENTERS.items():
                if area_name not in reference_areas:
                    distance = math.sqrt(
                        (area_data["lat"] - mid_lat) ** 2 + 
                        (area_data["lng"] - mid_lng) ** 2
                    )
                    scored.append((area_name, distance))
            
            scored.sort(key=lambda x: x[1])
            return [area for area, _ in scored[:place_count]]
            
        elif proximity_type == "multi":
            # 여러 곳 - 개인화 추천
            candidates = list(AREA_CENTERS.keys())
            
            # MBTI 기반 필터링
            mbti_preferred = []
            for char in user_context.demographics.mbti:
                mbti_preferred.extend(MBTI_PREFERENCES.get(char, []))
            
            # 관계단계 기반 필터링
            relationship_preferred = RELATIONSHIP_PREFERENCES.get(
                user_context.demographics.relationship_stage, []
            )
            
            # 점수 계산
            scored = []
            for area in candidates:
                score = 0
                if area in mbti_preferred:
                    score += 2
                if area in relationship_preferred:
                    score += 3
                scored.append((area, score))
            
            scored.sort(key=lambda x: x[1], reverse=True)
            return [area for area, _ in scored[:place_count]]
        
        # 기본값
        return list(AREA_CENTERS.keys())[:place_count]

    async def process_request(self, request: PlaceAgentRequest) -> List[LocationResponse]:
        """메인 요청 처리 - 하이브리드 지역 처리"""
        
        # proximity_type이 "exact"인 경우 특별 처리
        if request.location_request.proximity_type == "exact":
            print("Exact 모드: reference_areas 내 여러 위치 제공")
            
            locations = []
            areas_to_process = request.location_request.reference_areas
            
            for area_name in areas_to_process:
                remaining_count = request.location_request.place_count - len(locations)
                if remaining_count <= 0:
                    break
                
                # 같은 지역 내 여러 위치 조회
                area_locations = await self.get_multiple_coordinates_for_area(
                    area_name, remaining_count, request.user_context
                )
                
                for i, area_info in enumerate(area_locations, len(locations) + 1):
                    # exact 모드에서의 reason 생성
                    if "llm_reason" in area_info and area_info["llm_reason"]:
                        reason = area_info["llm_reason"]
                    else:
                        reason = self.generate_simple_reason(area_name, request.user_context)
                    
                    # 세부 위치 정보를 reason에 반영
                    if "place_name" in area_info and area_info["place_name"] and area_info["place_name"] != f"{area_name} 중심가":
                        if "detail" in area_info and area_info["detail"]:
                            reason = f"이곳은 {area_info['place_name']}({area_info['detail']}) 근처로, " + reason[4:]  # "이곳은" 부분 대체
                        else:
                            reason = f"이곳은 {area_info['place_name']} 근처로, " + reason[4:]  # "이곳은" 부분 대체
                    
                    locations.append(LocationResponse(
                        sequence=i,
                        area_name=area_name,
                        coordinates=Coordinates(
                            latitude=area_info["lat"],
                            longitude=area_info["lng"]
                        ),
                        reason=reason
                    ))
            
            return locations
        
        # proximity_type이 "exact"가 아닌 경우 기존 로직 수행
        try:
            # LLM으로 지역 분석 시도
            llm_result = await self.analyze_with_llm(request)
            if llm_result["areas"] and len(llm_result["areas"]) >= request.location_request.place_count:
                selected_areas = llm_result["areas"][:request.location_request.place_count]
                reasons = llm_result["reasons"][:request.location_request.place_count]
                print("LLM 기반 지역 선정 성공")
            else:
                raise Exception("LLM 결과 부족")
                
        except Exception as e:
            print(f"LLM 분석 실패, 룰 기반 처리: {e}")
            # 기존 룰 기반 로직으로 fallback
            selected_areas = self.select_areas_by_proximity(request)
            reasons = [
                self.generate_simple_reason(area, request.user_context) 
                for area in selected_areas
            ]
        
        # 좌표 변환 및 최종 응답 생성 (하이브리드 처리)
        locations = []
        for i, area_name in enumerate(selected_areas, 1):
            # 사용자 컨텍스트를 포함해서 지역 정보 조회 (하이브리드)
            area_info = await self.get_coordinates_from_kakao(area_name, request.user_context)
            
            if not area_info:
                print(f"지역 정보를 찾을 수 없음: {area_name}")
                continue
            
            # reason 결정 우선순위
            if "llm_reason" in area_info and area_info["llm_reason"]:
                # 새로운 지역의 경우 LLM이 생성한 상세 이유 사용
                reason = area_info["llm_reason"]
            elif i-1 < len(reasons):
                # 기존 지역이거나 LLM에서 생성된 이유 사용
                reason = reasons[i-1]
            else:
                # fallback: 간단한 이유 생성
                reason = self.generate_simple_reason(area_name, request.user_context)
            
            locations.append(LocationResponse(
                sequence=i,
                area_name=area_name,
                coordinates=Coordinates(
                    latitude=area_info["lat"],
                    longitude=area_info["lng"]
                ),
                reason=reason
            ))
        
        return locations

# Place Agent 인스턴스
place_agent = PlaceAgent()

@app.post("/analyze", response_model=PlaceAgentResponse)
async def analyze_location(request: PlaceAgentRequest):
    """지역 분석 및 좌표 반환 메인 엔드포인트"""
    try:
        locations = await place_agent.process_request(request)
        
        if not locations:
            raise HTTPException(status_code=404, detail="추천할 지역을 찾을 수 없습니다.")
        
        return PlaceAgentResponse(
            request_id=request.request_id,
            success=True,
            locations=locations,
            error_message=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        return PlaceAgentResponse(
            request_id=request.request_id,
            success=False,
            locations=[],
            error_message=str(e)
        )

@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {"status": "healthy", "service": "Place Agent v2.0 (Hybrid)"}

@app.get("/areas")
async def get_available_areas():
    """사용 가능한 지역 목록 반환"""
    return {"areas": list(AREA_CENTERS.keys())}

@app.post("/test-llm")
async def test_llm_analysis(request: PlaceAgentRequest):
    """LLM 분석 테스트용 엔드포인트"""
    try:
        llm_result = await place_agent.analyze_with_llm(request)
        return {
            "success": True,
            "llm_areas": llm_result.get("areas", []),
            "llm_reasons": llm_result.get("reasons", []),
            "prompt": place_agent.create_analysis_prompt(request)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/test-hybrid")
async def test_hybrid_analysis(request: PlaceAgentRequest):
    """하이브리드 지역 분석 테스트용 엔드포인트 - 정해진 응답 형식 준수"""
    try:
        # 새로운 지역으로 강제 테스트
        test_areas = ["마포구", "서초구", "용산구"]
        locations = []
        
        for i, area in enumerate(test_areas, 1):
            area_info = await place_agent.get_coordinates_from_kakao(area, request.user_context)
            if area_info:
                reason = area_info.get("llm_reason", f"{area} 지역 추천")
                locations.append(LocationResponse(
                    sequence=i,
                    area_name=area,
                    coordinates=Coordinates(
                        latitude=area_info["lat"],
                        longitude=area_info["lng"]
                    ),
                    reason=reason
                ))
        
        return PlaceAgentResponse(
            request_id=request.request_id,
            success=True,
            locations=locations,
            error_message=None
        )
    except Exception as e:
        return PlaceAgentResponse(
            request_id=request.request_id,
            success=False,
            locations=[],
            error_message=str(e)
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)