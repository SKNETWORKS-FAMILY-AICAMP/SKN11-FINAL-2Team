from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
import json
from typing import Dict, List, Any
from models.smart_models import CategoryRecommendation

class SmartCategoryRecommender:
    def __init__(self, openai_api_key: str):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2, openai_api_key=openai_api_key)
        self.categories = ["문화시설", "쇼핑", "술집", "야외활동",
                          "엔터테인먼트", "음식점", "카페", "휴식시설"]

    async def generate_personalized_categories(self, profile_data: Dict,
                                             place_count: int,
                                             conversation_context: str) -> List[CategoryRecommendation]:
        """개인화된 카테고리 추천 - 시간-장소 제약 검증 포함"""

        # 시간-장소 제약 검증 (자동 조정 제거)
        duration = profile_data.get("duration")
        if duration:
            constraint_result = self._check_time_place_constraints(duration, place_count)
            if constraint_result["needs_confirmation"]:
                # 제약 위반 시 예외 발생시켜서 사용자에게 선택권 제공
                raise ValueError(f"CONSTRAINT_VIOLATION:{constraint_result['message']}")

        # 필수 데이터만 추출 (빈 값 제거)
        essential_data = {}
        for key, value in profile_data.items():
            if value and value != '' and value != [] and value != None:
                essential_data[key] = value
        
        prompt = f"""
        당신은 전문 데이트 코스 추천사입니다. 
        사용자 프로필을 분석하여 {place_count}개 장소의 최적 조합을 추천해주세요.

        === 사용자 프로필 ===
        {essential_data}
        
        === 대화 맥락 ===
        {conversation_context}

        === 제약사항 ===
        - 방문할 장소 수: {place_count}개
        - 선택 가능한 카테고리: {self.categories}
        - 각 장소마다 구체적이고 개인화된 추천 이유 작성 필수

        === 출력 형식 (순수 JSON만 응답) ===
        {{
            "recommendations": [
                {{
                    "sequence": 1,
                    "category": "카페",
                    "reason": "23세 ENTJ 남성이 여자친구와 로맨틱한 저녁 데이트를 위해 편안한 대화 공간이 필요",
                    "alternatives": ["음식점", "휴식시설"]
                }}
            ],
            "overall_strategy": "전체적인 추천 전략 설명"
        }}
        
        중요: 코드 블록(```) 없이 순수 JSON만 반환하세요.
        """

        try:
            result = await self.llm.ainvoke([HumanMessage(content=prompt)])
            print(f"[SMART_CATEGORY] GPT 원본 응답: {result.content}")
            
            # JSON 추출 및 정제
            json_content = self._extract_json_from_response(result.content)
            data = json.loads(json_content)
            
            recommendations = [CategoryRecommendation(**rec) for rec in data["recommendations"]]
            print(f"[SMART_CATEGORY] 추천 생성 성공: {len(recommendations)}개")
            return recommendations
            
        except Exception as e:
            print(f"[ERROR] 스마트 카테고리 추천 실패: {e}")
            print(f"[ERROR] GPT 응답: {result.content if 'result' in locals() else 'API 호출 실패'}")
            # 기본 추천 반환
            return self._get_default_recommendations(place_count)
    
    def _check_time_place_constraints(self, duration: str, place_count: int) -> dict:
        """시간-장소 제약 검증 - GPT 기반 재확인 메시지 생성"""
        try:
            # 시간-장소 제약 맵
            TIME_PLACE_CONSTRAINTS = {
                "1시간": {"max_places": 1},
                "2시간": {"max_places": 2},
                "3시간": {"max_places": 3},
                "4시간": {"max_places": 3},
                "5시간": {"max_places": 4},
                "6시간": {"max_places": 5},
                "반나절": {"max_places": 4},
                "하루종일": {"max_places": 5}
            }
            
            # duration 정규화
            normalized_duration = duration.strip()
            if normalized_duration not in TIME_PLACE_CONSTRAINTS:
                # "X시간" 패턴 처리
                import re
                hour_match = re.search(r'(\d+)시간', normalized_duration)
                if hour_match:
                    hours = int(hour_match.group(1))
                    if hours <= 1:
                        max_places = 1
                    elif hours <= 2:
                        max_places = 2
                    elif hours <= 3:
                        max_places = 3
                    elif hours <= 4:
                        max_places = 3
                    else:
                        max_places = min(hours - 1, 5)
                else:
                    max_places = 3  # 기본값
            else:
                max_places = TIME_PLACE_CONSTRAINTS[normalized_duration]["max_places"]
            
            # 제약 위반 시 GPT 메시지 생성
            if place_count > max_places:
                gpt_message = self._generate_constraint_message(duration, place_count, max_places)
                return {
                    "needs_confirmation": True,
                    "message": gpt_message,
                    "max_places": max_places
                }
            
            return {"needs_confirmation": False}
            
        except Exception as e:
            print(f"[ERROR] 장소 개수 검증 실패: {e}")
            return {"needs_confirmation": False}
    
    def _generate_constraint_message(self, duration: str, requested: int, max_allowed: int) -> str:
        """제약 위반 시 GPT 기반 정중한 재확인 메시지 생성"""
        try:
            prompt = f"""
사용자가 {duration} 데이트에 {requested}개 장소를 원하지만, 실제로는 최대 {max_allowed}개까지만 가능합니다.

다음을 포함해서 정중하고 친근한 톤으로 재확인 메시지를 작성해주세요:
1. 왜 {requested}개가 어려운지 간단히 설명 (각 장소에서 충분히 즐기기 위해)
2. {max_allowed}개를 추천하는 이유
3. 사용자의 선택권 제시: "{max_allowed}개로 할래요? 아니면 시간을 늘리시겠어요?"

예시 톤: "아, {duration} 데이트에 {requested}개 장소는 조금 빡빡할 수 있어요! 각 장소에서 충분히 즐기시려면..."

단순한 텍스트로만 답변해주세요.
"""
            
            result = self.llm.invoke(prompt)
            return result.content.strip()
            
        except Exception as e:
            print(f"[ERROR] GPT 재확인 메시지 생성 실패: {e}")
            return f"⚠️ {duration} 데이트에 {requested}개 장소는 조금 빡빡할 수 있어요! 최대 {max_allowed}개를 추천드려요. {max_allowed}개로 하시겠어요? 아니면 시간을 늘리시겠어요?"

    async def handle_category_modification(self, user_request: str,
                                         current_recommendations: List[CategoryRecommendation]) -> Dict:
        """카테고리 수정 요청 처리"""

        current_data = [rec.dict() for rec in current_recommendations]

        prompt = f"""
        현재 카테고리 추천: {current_data}
        사용자 수정 요청: "{user_request}"

        사용자가 어떤 변경을 원하는지 파악하고,
        8개 카테고리 범위 내에서 수정해주세요: {self.categories}

        JSON으로 응답:
        {{
            "understood_request": "사용자 요청 이해 내용",
            "action": "modify",
            "target_sequence": 2,
            "new_category": "쇼핑",
            "reason": "변경 이유",
            "confidence": 0.9
        }}
        
        중요: 코드 블록(```)을 사용하지 말고 순수 JSON만 반환하세요.
        """

        try:
            result = await self.llm.ainvoke([HumanMessage(content=prompt)])
            print(f"[SMART_CATEGORY] GPT 응답: {result.content}")
            
            # JSON 추출
            import re
            json_content = self._extract_json_from_response(result.content)
            modification_data = json.loads(json_content)
            
            # 응답 검증
            if modification_data.get("confidence", 0) < 0.7:
                return {"action": "error", "message": "수정 요청을 명확히 이해하지 못했습니다."}
            
            # 실제 수정 적용
            updated_recommendations = []
            for rec in current_recommendations:
                rec_dict = rec.dict()
                
                # 타겟 시퀀스와 일치하는지 확인
                if rec_dict["sequence"] == modification_data.get("target_sequence"):
                    # 카테고리 수정
                    new_category = modification_data.get("new_category")
                    if new_category in self.categories:
                        rec_dict["category"] = new_category
                        rec_dict["reason"] = f"사용자 요청: {modification_data.get('reason', '카테고리 변경')}"
                        print(f"[SMART_CATEGORY] 수정 적용: {rec_dict['sequence']}번째 → {new_category}")
                
                updated_recommendations.append(rec_dict)
            
            return {
                "action": "modify",
                "understood_request": modification_data.get("understood_request", "카테고리 수정 완료"),
                "target_sequence": modification_data.get("target_sequence"),
                "new_category": modification_data.get("new_category"),
                "reason": modification_data.get("reason", "사용자 요청"),
                "updated_recommendations": updated_recommendations,
                "confidence": modification_data.get("confidence", 0.9)
            }
            
        except Exception as e:
            print(f"[ERROR] 카테고리 수정 실패: {e}")
            return {"action": "error", "message": "수정 요청을 이해하지 못했습니다."}
    
    def _extract_json_from_response(self, response_content: str) -> str:
        """GPT 응답에서 JSON 부분만 추출"""
        import re
        
        # 코드 블록 제거 (```json ... ``` 또는 ``` ... ```)
        if "```json" in response_content:
            match = re.search(r'```json\s*(.*?)\s*```', response_content, re.DOTALL)
            if match:
                return match.group(1).strip()
        elif "```" in response_content:
            match = re.search(r'```\s*(.*?)\s*```', response_content, re.DOTALL)
            if match:
                return match.group(1).strip()
        
        # JSON 객체 직접 추출 시도
        brace_count = 0
        start_idx = -1
        
        for i, char in enumerate(response_content):
            if char == '{':
                if start_idx == -1:
                    start_idx = i
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0 and start_idx != -1:
                    return response_content[start_idx:i+1]
        
        return response_content.strip()

    def _get_default_recommendations(self, place_count: int) -> List[CategoryRecommendation]:
        """스마트 추천 실패 시 최소한의 동적 기본 추천"""
        import datetime
        
        # 현재 시간 기반 동적 카테고리 선택
        current_hour = datetime.datetime.now().hour
        
        if 6 <= current_hour < 12:  # 오전
            time_slot = "오전"
            base_categories = ["카페", "문화시설", "야외활동", "쇼핑"]
        elif 12 <= current_hour < 18:  # 오후
            time_slot = "오후"
            base_categories = ["카페", "음식점", "쇼핑", "문화시설"]
        elif 18 <= current_hour < 22:  # 저녁
            time_slot = "저녁"
            base_categories = ["음식점", "카페", "문화시설", "술집"]
        else:  # 밤
            time_slot = "밤"
            base_categories = ["술집", "카페", "엔터테인먼트", "휴식시설"]
        
        recommendations = []
        for i in range(place_count):
            category = base_categories[i % len(base_categories)]
            reason = f"{time_slot} 시간대에 적합한 {category} 방문 추천"
            
            recommendations.append(CategoryRecommendation(
                sequence=i + 1,
                category=category,
                reason=reason,
                alternatives=["카페", "음식점"] if category not in ["카페", "음식점"] else ["문화시설", "쇼핑"]
            ))
        
        print(f"[SMART_RECOMMENDER] 현재 시간({current_hour}시) 기반 {time_slot} 추천 생성")
        return recommendations