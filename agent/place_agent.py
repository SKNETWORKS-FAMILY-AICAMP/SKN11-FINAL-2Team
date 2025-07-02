"""
Place Agent Implementation
지역 선정 및 좌표 반환 전문 서비스 (LLM 통합)
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
    transportation: str  # "도보", "차", "지하철"

class Demographics(BaseModel):
    age: int
    mbti: str
    relationship_stage: str  # "연인", "썸", "친구"

class Requirements(BaseModel):
    budget_level: Optional[str] = None  # "low", "medium", "high", null
    time_preference: str  # "오전", "오후", "저녁", "밤"
    transportation: str  # "도보", "차", "지하철"
    max_travel_time: Optional[int] = None
    weather_condition: Optional[str] = None

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
    reason: str  # 핵심 키워드로 구성

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
       """LLM을 위한 지역 분석 프롬프트 생성 (자연스러운 문장 형태)"""
       user_ctx = request.user_context
       loc_req = request.location_request
    
       # 사용 가능한 지역 목록
       available_areas = list(AREA_CENTERS.keys())
    
       prompt = f"""당신은 서울 지역 분석 전문가입니다.
    사용자 요청에 맞는 최적의 지역을 선정하고, 선정 이유를 자연스러운 문장으로 설명해주세요.

    사용자 정보:
    - 나이: {user_ctx.demographics.age}세
    - MBTI: {user_ctx.demographics.mbti}
    - 관계: {user_ctx.demographics.relationship_stage}
    - 선호사항: {', '.join(user_ctx.preferences)}
    - 예산: {user_ctx.requirements.budget_level}
    - 시간대: {user_ctx.requirements.time_preference}
    - 교통수단: {user_ctx.requirements.transportation}

    위치 요청:
    - 타입: {loc_req.proximity_type}
    - 기준지역: {loc_req.reference_areas if loc_req.reference_areas else '없음'}
    - 필요개수: {loc_req.place_count}곳

    사용 가능한 서울 지역: {', '.join(available_areas)}

    요청:
    1. 위 조건에 맞는 서울 지역 {loc_req.place_count}곳을 선정하세요.
    2. 각 지역별로 선정 이유를 자연스러운 1~2문장으로 설명하세요.

    응답 형식 (정확히 준수):
    지역명1|이곳은 ~한 이유로 추천합니다. ~해서 ~하다.
    지역명2|이곳은 ~한 이유로 추천합니다. ~해서 ~하다.
    지역명3|이곳은 ~한 이유로 추천합니다. ~해서 ~하다.

    예시:
    홍대|이곳은 젊은 문화의 중심지로 ENFP 성향에 맞는 자유로운 분위기와 지하철 접근성이 우수하여 추천합니다
    이태원|이곳은 이국적인 분위기와 트렌디한 공간들이 많아 {user_ctx.demographics.age}세 {user_ctx.demographics.relationship_stage}에게 적합하여 추천합니다
    강남|이곳은 세련된 분위기와 다양한 선택지가 있어 {user_ctx.requirements.time_preference} 데이트에 완벽하여 추천합니다"""
    
       return prompt

    def parse_llm_response(self, llm_text: str) -> Dict[str, List[str]]:
        """LLM 응답을 파싱하여 지역명과 키워드 추출"""
        try:
            lines = [line.strip() for line in llm_text.strip().split('\n') if line.strip()]
            areas = []
            reasons = []
            
            for line in lines:
                if '|' in line:
                    parts = line.split('|', 1)
                    if len(parts) == 2:
                        area = parts[0].strip()
                        keywords = parts[1].strip()
                        
                        # 유효한 지역인지 확인
                        if area in AREA_CENTERS:
                            areas.append(area)
                            reasons.append(keywords)
            
            return {"areas": areas, "reasons": reasons}
        
        except Exception as e:
            print(f"LLM 응답 파싱 실패: {e}")
            return {"areas": [], "reasons": []}

    async def analyze_with_llm(self, request: PlaceAgentRequest) -> Dict[str, List[str]]:
        """LLM을 활용한 지역 분석"""
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
        """Main Agent가 이해하기 쉬운 핵심 키워드 조합 (fallback용)"""
        keywords = []
        
        # 1. 지역 특성
        area_info = AREA_CENTERS.get(area_name, {})
        if area_info.get('signature_traits'):
            keywords.append(area_info['signature_traits'][0])
        
        # 2. 사용자 매칭
        demo = user_context.demographics
        if demo.age < 25:
            keywords.append("젊은층선호")
        elif demo.age > 30:
            keywords.append("성숙한분위기")
        else:
            keywords.append(f"{demo.age}세적합")
        
        # 3. 교통/접근성
        transport = user_context.requirements.transportation
        if transport == "지하철":
            keywords.append("지하철접근우수")
        elif transport == "도보":
            keywords.append("도보이동편리")
        else:
            keywords.append("교통편리")
        
        return ",".join(keywords[:3])

    async def get_coordinates_from_kakao(self, area_name: str) -> Optional[Dict]:
        """지역 좌표 검색 - 하드코딩된 데이터 우선 사용"""
        if area_name in AREA_CENTERS:
            return AREA_CENTERS[area_name]
        
        if not self.kakao_api_key:
            print(f"알 수 없는 지역: {area_name}, Kakao API 키도 없음")
            return None
            
        try:
            headers = {"Authorization": f"KakaoAK {self.kakao_api_key}"}
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://dapi.kakao.com/v2/local/search/keyword.json",
                    params={"query": area_name},
                    headers=headers
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get("documents"):
                        place = data["documents"][0]
                        return {
                            "lat": float(place["y"]),
                            "lng": float(place["x"]),
                            "signature_traits": ["일반적인지역"],
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
        """메인 요청 처리 - LLM + 룰 기반 결합"""
        
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
        
        # 좌표 변환 및 최종 응답 생성
        locations = []
        for i, area_name in enumerate(selected_areas, 1):
            area_info = await self.get_coordinates_from_kakao(area_name)
            
            if not area_info:
                print(f"지역 정보를 찾을 수 없음: {area_name}")
                continue
                
            # Main Agent가 이해하기 쉬운 간단한 reason
            reason = reasons[i-1] if i-1 < len(reasons) else self.generate_simple_reason(area_name, request.user_context)
            
            locations.append(LocationResponse(
                sequence=i,
                area_name=area_name,
                coordinates=Coordinates(
                    latitude=area_info["lat"],
                    longitude=area_info["lng"]
                ),
                reason=reason  # 핵심 키워드만
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
            locations=locations
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
    return {"status": "healthy", "service": "Place Agent v2.0"}

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)