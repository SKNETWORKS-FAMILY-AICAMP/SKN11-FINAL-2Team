"""
Place Agent Implementation
지역 선정 및 좌표 반환 전문 서비스
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
app = FastAPI(title="Place Agent", description="지역 분석 및 좌표 반환 서비스", version="3.0.0")

# OpenAI 클라이언트 초기화
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 좌표 정확도 설정
COORDINATE_PRECISION = 4  # 소수점 4자리로 고정
MIN_DISTANCE_METERS = 200  # 최소 거리 200미터

# 좌표 정규화 함수
def normalize_coordinates(lat: float, lng: float) -> tuple:
    """좌표를 지정된 정확도로 정규화"""
    return (
        round(float(lat), COORDINATE_PRECISION),
        round(float(lng), COORDINATE_PRECISION)
    )

def calculate_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """두 좌표 간 거리 계산 (미터 단위)"""
    # Haversine 공식 사용
    R = 6371000  # 지구 반지름 (미터)
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lng = math.radians(lng2 - lng1)
    
    a = (math.sin(delta_lat / 2) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c

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

class PlaceAgent:
    def __init__(self):
        self.kakao_api_key = os.getenv("KAKAO_API_KEY")
        if not self.kakao_api_key:
            print("⚠️ KAKAO_API_KEY가 설정되지 않았습니다. Kakao API 기능이 제한됩니다.")

    async def get_coordinates_from_kakao(self, area_name: str) -> Optional[Dict]:
        """Kakao API로 지역 정보 조회"""
        if not self.kakao_api_key:
            print(f"Kakao API 키가 없어 지역 조회 불가: {area_name}")
            return None
            
        try:
            headers = {"Authorization": f"KakaoAK {self.kakao_api_key}"}
            async with httpx.AsyncClient() as client_session:
                response = await client_session.get(
                    "https://dapi.kakao.com/v2/local/search/keyword.json",
                    params={
                        "query": f"{area_name} 서울",
                        "size": 1
                    },
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("documents"):
                        place = data["documents"][0]
                        
                        # 좌표 정규화
                        lat, lng = normalize_coordinates(
                            float(place["y"]), float(place["x"])
                        )
                        
                        return {
                            "lat": lat,
                            "lng": lng,
                            "address": place.get("address_name", ""),
                            "place_name": place.get("place_name", area_name)
                        }
                        
        except Exception as e:
            print(f"Kakao API 요청 실패: {e}")
        
        return None

    async def find_nearby_areas(self, center_lat: float, center_lng: float, radius_km: float = 3.0) -> List[Dict]:
        """중심 좌표 주변 지역들 검색"""
        if not self.kakao_api_key:
            return []
            
        try:
            headers = {"Authorization": f"KakaoAK {self.kakao_api_key}"}
            nearby_areas = []
            
            async with httpx.AsyncClient() as client_session:
                # 반경 내 장소들 검색 (여러 카테고리)
                categories = ["CE7", "FD6", "CT1", "AT4", "PK6", "SW8"]
                
                for category in categories[:5]:  # 상위 5개 카테고리만
                    response = await client_session.get(
                        "https://dapi.kakao.com/v2/local/search/category.json",
                        params={
                            "category_group_code": category,
                            "x": center_lng,
                            "y": center_lat,
                            "radius": int(radius_km * 1000),  # 미터 단위
                            "size": 15,
                            "sort": "distance"
                        },
                        headers=headers
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        for place in data.get("documents", []):
                            place_lat, place_lng = normalize_coordinates(
                                float(place["y"]), float(place["x"])
                            )
                            
                            # 중복 체크
                            is_duplicate = False
                            for existing in nearby_areas:
                                if calculate_distance(
                                    place_lat, place_lng,
                                    existing["lat"], existing["lng"]
                                ) < MIN_DISTANCE_METERS:
                                    is_duplicate = True
                                    break
                            
                            if not is_duplicate:
                                # 지역명 추출 (주소에서)
                                address_parts = place.get("address_name", "").split()
                                area_name = ""
                                if len(address_parts) >= 3:
                                    area_name = address_parts[2]  # 동/면 단위
                                elif len(address_parts) >= 2:
                                    area_name = address_parts[1]  # 구 단위
                                else:
                                    area_name = place.get("place_name", "알 수 없는 지역")
                                
                                nearby_areas.append({
                                    "lat": place_lat,
                                    "lng": place_lng,
                                    "area_name": area_name,
                                    "place_name": place.get("place_name", ""),
                                    "category": place.get("category_name", ""),
                                    "address": place.get("address_name", ""),
                                    "distance": calculate_distance(center_lat, center_lng, place_lat, place_lng)
                                })
                        
                        if len(nearby_areas) >= 20:  # 충분한 후보 확보시 중단
                            break
            
            # 거리순 정렬
            nearby_areas.sort(key=lambda x: x["distance"])
            return nearby_areas[:15]  # 상위 15개 반환
            
        except Exception as e:
            print(f"주변 지역 검색 실패: {e}")
            return []

    def create_prompt_area_selection(self, request: PlaceAgentRequest, candidate_areas: List[Dict] = None, mode: str = "general") -> str:
        """지역 선정을 위한 통합 LLM 프롬프트 생성"""
        user_ctx = request.user_context
        loc_req = request.location_request

        # null 값 처리
        budget = user_ctx.requirements.budget_level or "제한없음"
        transportation = user_ctx.requirements.transportation or loc_req.transportation or "제한없음"

        # 후보 지역 정보 정리
        if candidate_areas:
            candidates_text = "\n".join([
                f"- {area['area_name']} (유형: {area.get('category', '일반')}, 거리: {area['distance']:.0f}m)"
                for area in candidate_areas
            ])
            target_text = "위 후보 장소들"
        else:
            candidates_text = "서울 전체 지역 (모든 구, 동, 주요 상권 포함)"
            target_text = "서울 지역"

        prompt = f"""서울 지역/장소 추천 전문가로서 사용자에게 최적의 {"장소" if mode == "exact" else "지역"} {loc_req.place_count}곳을 추천해주세요.

    사용자 정보:
    - 나이: {user_ctx.demographics.age}세
    - MBTI: {user_ctx.demographics.mbti}
    - 관계: {user_ctx.demographics.relationship_stage}
    - 선호사항: {', '.join(user_ctx.preferences) if user_ctx.preferences else '특별한 선호 없음'}
    - 예산: {budget}
    - 시간대: {user_ctx.requirements.time_preference}
    - 교통수단: {transportation}

    요청 모드: {mode}
    - exact: 사용자 지정 지역 내 구체적 장소들
    - near: 사용자 지정 지역 주변 지역들
    - between: 두 지역 중간 지점 지역들
    - multi: 사용자 요구사항에 맞는 서울 지역들

    기준 지역: {loc_req.reference_areas if loc_req.reference_areas else "없음"}

    추천 대상:
    {candidates_text}

    선호 장소: 카페, 음식점, 공원, 문화시설, 관광명소, 쇼핑 지역
    제외 장소: 은행, 안내센터, 공공기관, 주유소, 마트

    요청 사항:
    1. {target_text} 중에서 사용자에게 가장 적합한 {loc_req.place_count}곳 선정
    2. 각각에 대한 추천 이유를 자연스럽게 1-2문장으로 설명
    3. 사용자의 나이, MBTI, 관계, 선호사항, 시간대, 예산 모두 고려
    4. 후보를 반환할때 똑같은 카테고리나 장소명이 겹치는 부분이 있다면 뒤에 출력되는 항목은 제외하고 다른 카테고리에서 후보 찾아서
    5. 요청 모드를 꼭 준수할 것

    응답 규칙 (반드시 준수):
    1. 형식: "장소명|이유" (번호나 다른 기호 절대 사용 금지)
    2. 다양성: 카페, 음식점, 공원, 문화시설 등 서로 다른 카테고리에서 선정
    3. 중복 방지: 같은 브랜드나 비슷한 이름의 장소 금지"""

        return prompt

    def parse_llm_response(self, llm_text: str) -> Dict[str, List[str]]:
        """LLM 응답을 파싱하여 지역명과 이유 추출"""
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
                        areas.append(area)
                        reasons.append(reason)
            
            return {"areas": areas, "reasons": reasons}
        
        except Exception as e:
            print(f"LLM 응답 파싱 실패: {e}")
            return {"areas": [], "reasons": []}

    async def analyze_with_llm(self, prompt: str) -> Dict[str, List[str]]:
        """LLM을 활용한 지역 분석"""
        try:
            response = await asyncio.to_thread(
                client.chat.completions.create,
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=600
            )
            
            llm_text = response.choices[0].message.content
            print(f"LLM 응답: {llm_text}")
            
            return self.parse_llm_response(llm_text)
            
        except Exception as e:
            print(f"LLM 분석 실패: {e}")
            return {"areas": [], "reasons": []}

    def generate_area_coordinates(self, area_name: str, count: int, base_lat: float, base_lng: float) -> List[Dict]:
        """지역 내 여러 좌표 생성"""
        coordinates = []
        
        # 첫 번째는 기본 좌표
        norm_lat, norm_lng = normalize_coordinates(base_lat, base_lng)
        coordinates.append({
            "lat": norm_lat,
            "lng": norm_lng,
            "sub_location": area_name,
            "detail": "메인 지역"
        })
        
        if count <= 1:
            return coordinates
        
        # 나머지는 반경 500m 내에서 생성
        import random
        random.seed(hash(area_name))  # 일관성 유지
        
        attempt = 0
        max_attempts = 50
        
        while len(coordinates) < count and attempt < max_attempts:
            attempt += 1
            
            # 반경 500m 내에서 랜덤 좌표 생성
            angle = random.uniform(0, 2 * math.pi)
            distance = random.uniform(100, 500)  # 100m~500m
            
            # 좌표 변환
            lat_offset = (distance * math.cos(angle)) / 111000
            lng_offset = (distance * math.sin(angle)) / (111000 * math.cos(math.radians(base_lat)))
            
            new_lat = base_lat + lat_offset
            new_lng = base_lng + lng_offset
            
            norm_new_lat, norm_new_lng = normalize_coordinates(new_lat, new_lng)
            
            # 중복 체크
            is_duplicate = False
            for existing in coordinates:
                distance_check = calculate_distance(
                    norm_new_lat, norm_new_lng, 
                    existing["lat"], existing["lng"]
                )
                if distance_check < MIN_DISTANCE_METERS:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                coordinates.append({
                    "lat": norm_new_lat,
                    "lng": norm_new_lng,
                    "sub_location": f"{area_name} {len(coordinates)}",
                    "detail": f"{area_name} 주변"
                })
        
        return coordinates

    async def get_multiple_coordinates_for_area(self, area_name: str, count: int) -> List[Dict]:
        """같은 지역 내에서 여러 세부 위치 좌표 조회"""
        results = []
        
        # 기본 지역 정보 조회
        base_info = await self.get_coordinates_from_kakao(area_name)
        if not base_info:
            print(f"지역 정보를 찾을 수 없음: {area_name}")
            return results
        
        base_lat, base_lng = base_info["lat"], base_info["lng"]
        
        # Kakao API로 해당 지역 장소들 검색
        if self.kakao_api_key:
            try:
                headers = {"Authorization": f"KakaoAK {self.kakao_api_key}"}
                async with httpx.AsyncClient() as client_session:
                    search_queries = [
                        f"서울 {area_name} 맛집",
                        f"서울 {area_name}",
                        f"서울 {area_name} 카페"
                    ]
                    
                    all_places = []
                    for query in search_queries:
                        if len(all_places) >= count * 2:
                            break
                            
                        response = await client_session.get(
                            "https://dapi.kakao.com/v2/local/search/keyword.json",
                            params={
                                "query": query,
                                "size": 15
                            },
                            headers=headers
                        )
                        
                        if response.status_code == 200:
                            data = response.json()
                            places = data.get("documents", [])
                            all_places.extend(places)
                    
                    # 중복 제거 및 거리 기반 필터링
                    unique_places = []
                    for place in all_places:
                        place_lat, place_lng = normalize_coordinates(float(place["y"]), float(place["x"]))
                        
                        # 기본 지역에서 1km 이내인지 확인
                        distance_from_base = calculate_distance(
                            place_lat, place_lng, base_lat, base_lng
                        )
                        
                        if distance_from_base > 1000:  # 1km 초과시 제외
                            continue
                        
                        # 기존 장소와 중복 체크
                        is_duplicate = False
                        for existing in unique_places:
                            if calculate_distance(
                                place_lat, place_lng,
                                existing["lat"], existing["lng"]
                            ) < MIN_DISTANCE_METERS:
                                is_duplicate = True
                                break
                        
                        if not is_duplicate:
                            unique_places.append({
                                "lat": place_lat,
                                "lng": place_lng,
                                "place_name": place.get("place_name", f"{area_name} 장소"),
                                "category": place.get("category_name", "일반"),
                                "address": place.get("address_name", "")
                            })
                            
                            if len(unique_places) >= count:
                                break
                    
                    # 결과 구성
                    for place_info in unique_places[:count]:
                        results.append({
                            "lat": place_info["lat"],
                            "lng": place_info["lng"],
                            "sub_location": place_info["place_name"],
                            "detail": place_info["category"],
                            "address": place_info.get("address", "")
                        })
                    
            except Exception as e:
                print(f"Kakao API 장소 검색 실패: {e}")
        
        # 부족한 경우 지역 내 좌표 생성으로 보충
        if len(results) < count:
            remaining = count - len(results)
            generated_coords = self.generate_area_coordinates(area_name, remaining, base_lat, base_lng)
            
            for coord_info in generated_coords:
                # 기존 결과와 중복 체크
                is_duplicate = False
                for existing in results:
                    if calculate_distance(
                        coord_info["lat"], coord_info["lng"],
                        existing["lat"], existing["lng"]
                    ) < MIN_DISTANCE_METERS:
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    results.append(coord_info)
        
        return results[:count]

    async def process_request(self, request: PlaceAgentRequest) -> List[LocationResponse]:
        """메인 요청 처리"""
        
        proximity_type = request.location_request.proximity_type
        reference_areas = request.location_request.reference_areas
        place_count = request.location_request.place_count
        
        # 1. Exact 모드: reference_areas 내 여러 위치 제공
        if proximity_type == "exact":
            print("Exact 모드: reference_areas 내 여러 위치 제공")
            locations = []
            
            for area_name in reference_areas:
                remaining_count = place_count - len(locations)
                if remaining_count <= 0:
                    break
                
                area_locations = await self.get_multiple_coordinates_for_area(area_name, remaining_count)
                
                # area_locations를 candidate_areas 형태로 변환
                candidate_areas = []
                for area_info in area_locations:
                    candidate_areas.append({
                        "area_name": area_info.get("sub_location", area_name),
                        "lat": area_info["lat"],
                        "lng": area_info["lng"],
                        "distance": 0,  # exact 모드라서 거리는 0
                        "place_name": area_info.get("sub_location", area_name),
                        "category": area_info.get("detail", "")
                    })
                
                # 기존 LLM 프롬프트 함수 재활용
                prompt = self.create_prompt_area_selection(request, candidate_areas, "exact")
                llm_result = await self.analyze_with_llm(prompt)
                
                # LLM 결과가 있으면 사용, 없으면 fallback
                if llm_result["areas"] and llm_result["reasons"]:
                    for i, (area_info, reason) in enumerate(zip(area_locations, llm_result["reasons"]), len(locations) + 1):
                        locations.append(LocationResponse(
                            sequence=i,
                            area_name=area_name,
                            coordinates=Coordinates(
                                latitude=area_info["lat"],
                                longitude=area_info["lng"]
                            ),
                            reason=reason
                        ))
                else:
                    # Fallback: 간단한 이유
                    for i, area_info in enumerate(area_locations, len(locations) + 1):
                        sub_location = area_info.get("sub_location", area_name)
                        detail = area_info.get("detail", "")
                        
                        if detail and detail != "메인 지역":
                            reason = f"이곳은 {sub_location}({detail})로 {area_name} 지역 내 요청하신 정확한 위치에 해당하여 추천합니다."
                        else:
                            reason = f"이곳은 {sub_location}로 {area_name} 지역 내 요청하신 정확한 위치에 해당하여 추천합니다."
                        
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
        
        # 2. Near 모드: 기준 지역 주변 검색
        elif proximity_type == "near" and reference_areas:
            print(f"Near 모드: {reference_areas[0]} 주변 지역 분석")
            
            # 기준 지역 좌표 획득
            base_coord = await self.get_coordinates_from_kakao(reference_areas[0])
            if not base_coord:
                return []
            
            # 주변 지역들 검색
            nearby_areas = await self.find_nearby_areas(base_coord["lat"], base_coord["lng"])
            
            if not nearby_areas:
                return []
            
            # LLM으로 최적 지역 선정
            prompt = self.create_prompt_area_selection(request, nearby_areas, "near")
            llm_result = await self.analyze_with_llm(prompt)
            
            if not llm_result["areas"]:
                return []
            
            # 선정된 지역들의 좌표 정보 매칭
            locations = []
            for i, (area_name, reason) in enumerate(zip(llm_result["areas"][:place_count], 
                                                       llm_result["reasons"][:place_count]), 1):
                # nearby_areas에서 해당 지역 찾기
                matched_area = None
                for area in nearby_areas:
                    if area_name in area["area_name"] or area["area_name"] in area_name:
                        matched_area = area
                        break
                
                if not matched_area:
                    # 직접 검색
                    coord = await self.get_coordinates_from_kakao(area_name)
                    if coord:
                        matched_area = coord
                
                if matched_area:
                    locations.append(LocationResponse(
                        sequence=i,
                        area_name=area_name,
                        coordinates=Coordinates(
                            latitude=matched_area["lat"],
                            longitude=matched_area["lng"]
                        ),
                        reason=reason
                    ))
            
            return locations
        
        # 3. Between 모드: 두 지역 중간점 분석
        elif proximity_type == "between" and len(reference_areas) >= 2:
            print(f"Between 모드: {reference_areas[0]}과 {reference_areas[1]} 중간 지점 분석")
            
            # 두 지역 좌표 획득
            coord1 = await self.get_coordinates_from_kakao(reference_areas[0])
            coord2 = await self.get_coordinates_from_kakao(reference_areas[1])
            
            if not coord1 or not coord2:
                return []
            
            # 중간점 계산
            mid_lat = (coord1["lat"] + coord2["lat"]) / 2
            mid_lng = (coord1["lng"] + coord2["lng"]) / 2
            
            # 중간점 주변 지역들 검색
            nearby_areas = await self.find_nearby_areas(mid_lat, mid_lng, radius_km=2.0)
            
            if not nearby_areas:
                return []
            
            # LLM으로 최적 중간 지역 선정
            prompt = self.create_prompt_area_selection(request, nearby_areas, "between")
            llm_result = await self.analyze_with_llm(prompt)
            
            if not llm_result["areas"]:
                return []
            
            # 선정된 지역들의 좌표 정보 매칭
            locations = []
            for i, (area_name, reason) in enumerate(zip(llm_result["areas"][:place_count], 
                                                       llm_result["reasons"][:place_count]), 1):
                # nearby_areas에서 해당 지역 찾기
                matched_area = None
                for area in nearby_areas:
                    if area_name in area["area_name"] or area["area_name"] in area_name:
                        matched_area = area
                        break
                
                if not matched_area:
                    # 직접 검색
                    coord = await self.get_coordinates_from_kakao(area_name)
                    if coord:
                        matched_area = coord
                
                if matched_area:
                    locations.append(LocationResponse(
                        sequence=i,
                        area_name=area_name,
                        coordinates=Coordinates(
                            latitude=matched_area["lat"],
                            longitude=matched_area["lng"]
                        ),
                        reason=reason
                    ))
            
            return locations
        
        # 4. Multi 모드 또는 기타: 일반 LLM 추천
        else:
            print("Multi/기타 모드: 일반 LLM 추천")
            
            # 일반적인 LLM 추천
            prompt = self.create_prompt_area_selection(request, None, "multi")
            llm_result = await self.analyze_with_llm(prompt)
            
            if not llm_result["areas"]:
                return []
            
            # 선정된 지역들의 좌표 획득
            locations = []
            for i, (area_name, reason) in enumerate(zip(llm_result["areas"][:place_count], 
                                                       llm_result["reasons"][:place_count]), 1):
                coord = await self.get_coordinates_from_kakao(area_name)
                
                if coord:
                    locations.append(LocationResponse(
                        sequence=i,
                        area_name=area_name,
                        coordinates=Coordinates(
                            latitude=coord["lat"],
                            longitude=coord["lng"]
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
        print(f"처리 중 오류 발생: {e}")
        return PlaceAgentResponse(
            request_id=request.request_id,
            success=False,
            locations=[],
            error_message=str(e)
        )

@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {
        "status": "healthy", 
        "service": "Place Agent v3.0.0 (No Hardcoding - Full LLM/API)",
        "kakao_api": "available" if place_agent.kakao_api_key else "not configured"
    }

@app.get("/test-coordinates/{area_name}")
async def test_coordinates(area_name: str, count: int = 3):
    """특정 지역의 좌표 테스트용 엔드포인트"""
    try:
        coords = await place_agent.get_multiple_coordinates_for_area(area_name, count)
        return {
            "area": area_name,
            "coordinates": coords,
            "count": len(coords)
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/test-nearby/{area_name}")
async def test_nearby_areas(area_name: str, radius: float = 3.0):
    """특정 지역 주변 검색 테스트용 엔드포인트"""
    try:
        base_coord = await place_agent.get_coordinates_from_kakao(area_name)
        if not base_coord:
            return {"error": f"지역을 찾을 수 없음: {area_name}"}
        
        nearby_areas = await place_agent.find_nearby_areas(
            base_coord["lat"], base_coord["lng"], radius
        )
        
        return {
            "base_area": area_name,
            "base_coordinates": base_coord,
            "nearby_areas": nearby_areas,
            "count": len(nearby_areas)
        }
    except Exception as e:
        return {"error": str(e)}

@app.post("/test-request")
async def test_full_request():
    """전체 요청 처리 테스트용 엔드포인트"""
    # 테스트용 더미 요청
    dummy_request = PlaceAgentRequest(
        request_id="test-001",
        timestamp="2025-01-01T12:00:00",
        location_request=LocationRequest(
            proximity_type="near",
            reference_areas=["홍대"],
            place_count=3
        ),
        user_context=UserContext(
            demographics=Demographics(age=25, mbti="ENFP", relationship_stage="연인"),
            preferences=["조용한 분위기", "트렌디한"],
            requirements=Requirements(
                budget_level="medium",
                time_preference="오후",
                transportation="지하철"
            )
        )
    )
    
    try:
        locations = await place_agent.process_request(dummy_request)
        return {
            "request": dummy_request.dict(),
            "response": locations,
            "count": len(locations)
        }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)