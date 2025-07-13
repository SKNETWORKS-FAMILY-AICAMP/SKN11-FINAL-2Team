# LLM 기반 지역 분석 서비스
# - 사용자 요청에 맞는 최적 지역 추천
# - 기존 정의된 지역 + 새로운 지역 하이브리드 지원

import asyncio
from typing import Dict, List
from openai import OpenAI
import os
import sys

# 상위 디렉토리의 모듈들 import
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from src.models.request_models import PlaceAgentRequest, UserContext
from src.data.area_data import get_predefined_areas
from config.settings import settings

class LocationAnalyzer:
    """LLM 기반 지역 분석 서비스"""
    
    def __init__(self):
        """초기화"""
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
    
    def create_analysis_prompt(self, request: PlaceAgentRequest) -> str:
        """LLM을 위한 지역 분석 프롬프트 생성 (하이브리드 - 기존지역 + 새지역)"""
        user_ctx = request.user_context
        loc_req = request.location_request
        
        # 기존 정의된 지역들
        predefined_areas = get_predefined_areas()
        
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
                self.client.chat.completions.create,
                model=settings.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=settings.LLM_MAX_TOKENS
            )
            
            llm_text = response.choices[0].message.content.strip()
            print(f"새 지역 '{area_name}' 특성 분석: {llm_text}")
            
            # 응답 파싱
            result = {"signature_traits": ["일반지역"], "vibe": "특별한", "reason": f"{area_name} 지역 추천"}
            
            lines = llm_text.split('\n')
            for line in lines:
                if '특성:' in line:
                    traits_part = line.split('|')[1] if '|' in line else ""
                    result["signature_traits"] = [t.strip() for t in traits_part.split(',')]
                elif '분위기:' in line:
                    vibe_part = line.split('|')[1] if '|' in line else "특별한"
                    result["vibe"] = vibe_part.strip()
                elif '이유:' in line:
                    reason_part = line.split('|')[1] if '|' in line else f"{area_name} 지역 추천"
                    result["reason"] = reason_part.strip()
            
            return result
            
        except Exception as e:
            print(f"새 지역 특성 분석 실패: {e}")
            return {
                "signature_traits": ["일반지역"],
                "vibe": "특별한",
                "reason": f"{area_name} 지역은 사용자 요청에 적합한 선택입니다."
            }

    async def analyze_locations(self, request: PlaceAgentRequest) -> Dict[str, List[str]]:
        """요청에 맞는 최적 지역들을 분석하여 반환"""
        try:
            # LLM 프롬프트 생성
            prompt = self.create_analysis_prompt(request)
            
            # LLM 호출
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=settings.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=settings.LLM_MAX_TOKENS
            )
            
            llm_text = response.choices[0].message.content
            print(f"LLM 지역 분석 결과: {llm_text}")
            
            # 응답 파싱
            return self.parse_llm_response(llm_text)
            
        except Exception as e:
            print(f"지역 분석 실패: {e}")
            return {"areas": [], "reasons": []}