"""
지능형 카테고리 생성기 - 완전한 동적 추천 시스템
하드코딩 제거하고 GPT 기반으로 상황별 맞춤 카테고리 추천
"""

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
import json
from typing import Dict, List, Any, Optional
from models.smart_models import CategoryRecommendation
import re

class IntelligentCategoryGenerator:
    def __init__(self, openai_api_key: str):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3, openai_api_key=openai_api_key)
        
        # 시간대별 카테고리 적합성 가이드
        self.time_compatibility = {
            "오전": {
                "highly_suitable": ["카페", "야외활동", "문화시설"],
                "moderately_suitable": ["쇼핑", "휴식시설"],
                "not_suitable": ["술집"]
            },
            "오후": {
                "highly_suitable": ["카페", "음식점", "쇼핑", "문화시설", "야외활동"],
                "moderately_suitable": ["엔터테인먼트", "휴식시설"],
                "not_suitable": []
            },
            "저녁": {
                "highly_suitable": ["음식점", "카페", "문화시설", "술집"],
                "moderately_suitable": ["쇼핑", "엔터테인먼트"],
                "not_suitable": ["야외활동"]
            },
            "밤": {
                "highly_suitable": ["술집", "엔터테인먼트"],
                "moderately_suitable": ["카페", "휴식시설"],
                "not_suitable": ["야외활동", "쇼핑"]
            }
        }
        
        # 논리적 흐름 규칙 (강화)
        self.flow_rules = {
            "after_alcohol": {
                "good_next": ["휴식시설"],  # 술집 후에는 휴식시설만
                "bad_next": ["문화시설", "야외활동", "쇼핑", "카페"]  # 카페도 금지
            },
            "before_meal": {
                "good_next": ["음식점"],
                "preparation": ["카페", "쇼핑"]
            },
            "end_activities": ["음식점", "술집", "휴식시설"],  # 적절한 마무리 장소
            "evening_ending_preference": ["휴식시설", "술집"],  # 저녁 데이트 마무리 선호
            "logical_sequences": {
                "good": [
                    ["카페", "음식점", "문화시설", "휴식시설"],
                    ["음식점", "문화시설", "쇼핑", "카페"],
                    ["카페", "쇼핑", "음식점", "술집"],
                    ["음식점", "카페", "술집"]
                ],
                "bad": [
                    ["술집", "문화시설"],
                    ["술집", "카페"], 
                    ["술집", "쇼핑"],
                    ["술집", "야외활동"]
                ]
            }
        }

    async def generate_contextual_categories(self, 
                                           profile_data: Dict,
                                           place_count: int,
                                           conversation_context: str) -> List[CategoryRecommendation]:
        """상황 인식 카테고리 추천 - 완전 동적 생성"""
        
        # 시간-장소 제약 검증 (사용자 선택권 존중)
        duration = profile_data.get("duration")
        if duration:
            constraint_result = self._check_time_place_constraints(duration, place_count)
            if constraint_result["needs_confirmation"]:
                # 사용자에게 선택권 제공 (자동 조정 안함)
                raise ValueError(f"CONSTRAINT_VIOLATION:{constraint_result['message']}")
        
        # 필수 데이터 추출
        essential_data = self._extract_essential_data(profile_data)
        time_slot = essential_data.get("time_slot", "저녁")
        duration = essential_data.get("duration", "3시간")
        
        # 시간대별 가이드라인 생성
        time_guidelines = self._generate_time_guidelines(time_slot, duration)
        
        prompt = f"""
당신은 전문 데이트 코스 기획자입니다. 하드코딩된 패턴 없이 상황에 맞는 최적 카테고리를 추천해주세요.

=== 사용자 프로필 ===
{essential_data}

=== 대화 맥락 ===
{conversation_context}

=== 추천 조건 ===
- 방문할 장소 수: {place_count}개
- 데이트 시간: {duration}
- 시간대: {time_slot}

=== 시간대별 가이드라인 ===
{time_guidelines}

=== 논리적 흐름 규칙 (엄격히 준수) ===
1. 술집 다음에는 절대로 카페, 문화시설, 쇼핑, 야외활동 불가 → 오직 휴식시설만 가능
2. 술집은 가능하면 마지막 장소로 배치 (술 마신 후 다른 활동은 비현실적)
3. 저녁/밤 시간대 마지막은 휴식시설 또는 술집으로 마무리
4. 식사 시간대에는 음식점을 자연스럽게 배치
5. 예시 좋은 순서: [음식점 → 문화시설 → 카페 → 휴식시설], [카페 → 음식점 → 술집]
6. 예시 나쁜 순서: [술집 → 카페], [술집 → 문화시설], [술집 → 쇼핑]

=== 개인화 요구사항 ===
- 각 카테고리마다 자연스럽고 간결한 추천 이유 작성
- 일반적인 이유 금지 ("편안한 시작을 위한 추천" 같은 뻔한 표현 절대 금지)
- 과도한 개인화 금지 ("ENTJ 성향의 23세가..." 같은 부자연스러운 표현 절대 금지)
- 대신 데이트 흐름과 시간대, 분위기를 고려한 자연스러운 이유 작성

선택 가능한 카테고리: ["문화시설", "쇼핑", "술집", "야외활동", "엔터테인먼트", "음식점", "카페", "휴식시설"]

=== 엄격한 제약 조건 ===
1. category는 반드시 위 8개 중 하나여야 함
2. alternatives도 반드시 위 8개 중에서만 선택 (절대 "이탈리안 레스토랑" 같은 세부 카테고리 금지)
3. 술집 다음에는 절대로 카페, 문화시설, 쇼핑 배치 금지
4. 저녁 시간대 마지막 장소는 휴식시설 또는 술집 권장

=== 출력 형식 (순수 JSON만 응답) ===
{{
    "recommendations": [
        {{
            "sequence": 1,
            "category": "적절한_카테고리",
            "reason": "{essential_data.get('mbti', '')} 성향의 {essential_data.get('age', '')}세가 {essential_data.get('relationship_stage', '')}와 {essential_data.get('atmosphere', '')} 분위기에서 [구체적이고 개인화된 이유]",
            "alternatives": ["대안1", "대안2"],
            "time_rationale": "이 시간대({time_slot})에 적합한 이유"
        }}
    ],
    "overall_strategy": "전체 코스의 논리적 흐름과 개인화 전략",
    "flow_validation": "시간순 논리성 검증 결과"
}}

중요: 코드 블록(```) 없이 순수 JSON만 반환하세요.
"""

        try:
            result = await self.llm.ainvoke([HumanMessage(content=prompt)])
            print(f"[INTELLIGENT_CATEGORY] GPT 원본 응답: {result.content}")
            
            # JSON 추출 및 검증
            json_content = self._extract_json_from_response(result.content)
            data = json.loads(json_content)
            
            # 응답 검증
            if not self._validate_response(data, place_count):
                print("[WARNING] GPT 응답 검증 실패, 재시도")
                return await self._retry_generation(essential_data, place_count, conversation_context)
            
            # 흐름 검증 수행
            recommendations = [CategoryRecommendation(**rec) for rec in data["recommendations"]]
            flow_issues = self._validate_category_flow(recommendations, time_slot)
            
            if flow_issues:
                print(f"[WARNING] 흐름 검증 실패: {flow_issues}")
                return await self._fix_flow_issues(recommendations, flow_issues, essential_data)
            
            print(f"[INTELLIGENT_CATEGORY] 동적 추천 생성 성공: {len(recommendations)}개")
            return recommendations
            
        except Exception as e:
            print(f"[ERROR] 지능형 카테고리 생성 실패: {e}")
            # 완전한 실패 시에만 emergency fallback 사용
            return await self._emergency_fallback(essential_data, place_count)

    def _extract_essential_data(self, profile_data: Dict) -> Dict:
        """유효한 데이터만 추출"""
        essential = {}
        for key, value in profile_data.items():
            if value and value != '' and value != [] and value != None:
                essential[key] = value
        return essential

    def _generate_time_guidelines(self, time_slot: str, duration: str) -> str:
        """시간대별 가이드라인 동적 생성"""
        compatibility = self.time_compatibility.get(time_slot, self.time_compatibility["저녁"])
        
        guidelines = f"""
시간대: {time_slot}
- 매우 적합: {compatibility['highly_suitable']}
- 보통 적합: {compatibility['moderately_suitable']}
- 부적합: {compatibility['not_suitable']}

지속시간: {duration}
"""
        
        # 시간별 특별 지침
        duration_hours = self._extract_hours_from_duration(duration)
        if duration_hours >= 4:
            guidelines += "- 긴 데이트이므로 다양한 경험 포함 가능\n"
        elif duration_hours <= 2:
            guidelines += "- 짧은 데이트이므로 핵심 활동 위주로 구성\n"
        
        return guidelines

    def _extract_hours_from_duration(self, duration: str) -> int:
        """지속시간에서 시간 추출"""
        if "시간" in duration:
            match = re.search(r'(\d+)시간', duration)
            return int(match.group(1)) if match else 3
        elif "반나절" in duration:
            return 4
        elif "하루" in duration:
            return 8
        return 3

    def _validate_response(self, data: Dict, expected_count: int) -> bool:
        """GPT 응답 검증 (강화)"""
        if "recommendations" not in data:
            return False
        
        recommendations = data["recommendations"]
        if len(recommendations) != expected_count:
            return False
        
        # 유효한 카테고리 목록
        valid_categories = ["문화시설", "쇼핑", "술집", "야외활동", "엔터테인먼트", "음식점", "카페", "휴식시설"]
        
        # 각 추천의 필수 필드 확인
        for rec in recommendations:
            if not all(key in rec for key in ["sequence", "category", "reason"]):
                return False
            
            # 카테고리 유효성 확인
            if rec["category"] not in valid_categories:
                print(f"[VALIDATION_FAIL] 유효하지 않은 카테고리: {rec['category']}")
                return False
            
            # alternatives 검증 (있는 경우)
            if "alternatives" in rec:
                for alt in rec["alternatives"]:
                    if alt not in valid_categories:
                        print(f"[VALIDATION_FAIL] 유효하지 않은 대안 카테고리: {alt}")
                        return False
            
            # 이유가 너무 일반적인지 확인
            generic_phrases = [
                "편안한 시작을 위한", "맛있는 식사를 위한", "다양한 경험을 위한",
                "즐거운 쇼핑을 위한", "좋은 분위기를 위한"
            ]
            if any(generic in rec["reason"] for generic in generic_phrases):
                print(f"[VALIDATION_FAIL] 일반적인 이유 감지: {rec['reason'][:50]}...")
                return False
        
        return True

    def _validate_category_flow(self, recommendations: List[CategoryRecommendation], time_slot: str) -> List[str]:
        """카테고리 순서의 논리적 흐름 검증 (강화)"""
        issues = []
        categories = [rec.category for rec in recommendations]
        
        # 1. 술집 후 부적절한 활동 체크 (강화)
        for i in range(len(recommendations) - 1):
            current = recommendations[i].category
            next_cat = recommendations[i + 1].category
            
            if current == "술집":
                bad_next = self.flow_rules["after_alcohol"]["bad_next"]
                if next_cat in bad_next:
                    issues.append(f"순서 {i+1}-{i+2}: 술집 후 {next_cat}은 비현실적")
        
        # 2. 시간대별 부적절한 활동 체크
        for i, rec in enumerate(recommendations):
            if time_slot in ["저녁", "밤"] and rec.category == "야외활동":
                issues.append(f"순서 {i+1}: {time_slot} 시간대에 야외활동 부적절")
        
        # 3. 마지막 장소 적절성 체크
        if len(recommendations) > 0:
            last_category = recommendations[-1].category
            if time_slot in ["저녁", "밤"]:
                if last_category not in self.flow_rules["evening_ending_preference"] and last_category not in ["카페"]:
                    issues.append(f"마지막 장소: {time_slot} 시간대에 {last_category}로 마무리는 부적절")
        
        # 4. 알려진 나쁜 조합 패턴 체크
        bad_sequences = self.flow_rules["logical_sequences"]["bad"]
        for bad_seq in bad_sequences:
            if len(bad_seq) <= len(categories):
                for i in range(len(categories) - len(bad_seq) + 1):
                    if categories[i:i+len(bad_seq)] == bad_seq:
                        issues.append(f"순서 {i+1}-{i+len(bad_seq)}: {' → '.join(bad_seq)} 조합은 비논리적")
        
        return issues

    async def _fix_flow_issues(self, recommendations: List[CategoryRecommendation], 
                              issues: List[str], essential_data: Dict) -> List[CategoryRecommendation]:
        """흐름 문제 자동 수정 (강화)"""
        fixed_recommendations = recommendations.copy()
        time_slot = essential_data.get("time_slot", "저녁")
        
        # 1. 술집 후 부적절한 카테고리 수정
        for i in range(len(fixed_recommendations) - 1):
            if fixed_recommendations[i].category == "술집":
                next_cat = fixed_recommendations[i + 1].category
                bad_next = self.flow_rules["after_alcohol"]["bad_next"]
                
                if next_cat in bad_next:
                    print(f"[AUTO_FIX] 술집 후 {next_cat} 문제 감지, 휴식시설로 변경")
                    # 다음 카테고리를 휴식시설로 변경
                    fixed_recommendations[i + 1].category = "휴식시설"
                    fixed_recommendations[i + 1].reason = f"술집 방문 후 편안하게 마무리할 수 있는 휴식시설 추천"
                    fixed_recommendations[i + 1].alternatives = ["카페", "음식점"]
        
        # 2. 술집을 마지막으로 이동 (가능한 경우)
        alcohol_idx = -1
        for i, rec in enumerate(fixed_recommendations):
            if rec.category == "술집":
                alcohol_idx = i
                break
        
        if alcohol_idx != -1 and alcohol_idx < len(fixed_recommendations) - 1:
            # 술집이 중간에 있으면 마지막으로 이동
            alcohol_rec = fixed_recommendations.pop(alcohol_idx)
            fixed_recommendations.append(alcohol_rec)
            
            # 시퀀스 번호 재조정
            for i, rec in enumerate(fixed_recommendations):
                rec.sequence = i + 1
            
            print(f"[AUTO_FIX] 술집을 마지막 순서로 이동")
        
        # 3. 저녁 시간대 마지막 장소 적절성 체크
        if len(fixed_recommendations) > 0 and time_slot in ["저녁", "밤"]:
            last_rec = fixed_recommendations[-1]
            suitable_endings = self.flow_rules["evening_ending_preference"] + ["카페"]
            
            if last_rec.category not in suitable_endings:
                print(f"[AUTO_FIX] {time_slot} 마무리 부적절, 휴식시설로 변경")
                last_rec.category = "휴식시설"
                last_rec.reason = f"{time_slot} 데이트의 여운을 남기며 편안하게 마무리할 수 있는 휴식시설"
                last_rec.alternatives = ["카페", "술집"]
        
        return fixed_recommendations

    async def _retry_generation(self, essential_data: Dict, place_count: int, 
                               conversation_context: str) -> List[CategoryRecommendation]:
        """재시도 생성 (더 엄격한 프롬프트)"""
        simplified_prompt = f"""
사용자 정보: {essential_data}
장소 개수: {place_count}개

개인화된 카테고리 {place_count}개를 추천하고, 각각에 대해 구체적인 이유를 작성하세요.
일반적인 이유 금지. 사용자의 특성을 반영한 구체적 이유만 작성.

JSON만 응답:
{{
    "recommendations": [
        {{"sequence": 1, "category": "카테고리", "reason": "구체적 개인화 이유", "alternatives": ["대안"]}}
    ]
}}
"""
        
        try:
            result = await self.llm.ainvoke([HumanMessage(content=simplified_prompt)])
            json_content = self._extract_json_from_response(result.content)
            data = json.loads(json_content)
            return [CategoryRecommendation(**rec) for rec in data["recommendations"]]
        except:
            return await self._emergency_fallback(essential_data, place_count)

    async def _emergency_fallback(self, essential_data: Dict, place_count: int) -> List[CategoryRecommendation]:
        """완전 실패 시 최소한의 동적 추천"""
        time_slot = essential_data.get("time_slot", "저녁")
        compatibility = self.time_compatibility.get(time_slot, self.time_compatibility["저녁"])
        
        # 시간대에 맞는 카테고리 선택
        suitable_categories = compatibility["highly_suitable"] + compatibility["moderately_suitable"]
        
        recommendations = []
        for i in range(place_count):
            category = suitable_categories[i % len(suitable_categories)]
            reason = f"{essential_data.get('time_slot', '저녁')} 시간대 {essential_data.get('atmosphere', '로맨틱')} 분위기에 적합한 {category} 추천"
            
            recommendations.append(CategoryRecommendation(
                sequence=i + 1,
                category=category,
                reason=reason,
                alternatives=["카페", "음식점"]
            ))
        
        return recommendations

    def _extract_json_from_response(self, response_content: str) -> str:
        """GPT 응답에서 JSON 부분만 추출"""
        import re
        
        # 코드 블록 제거
        if "```json" in response_content:
            match = re.search(r'```json\s*(.*?)\s*```', response_content, re.DOTALL)
            if match:
                return match.group(1).strip()
        elif "```" in response_content:
            match = re.search(r'```\s*(.*?)\s*```', response_content, re.DOTALL)
            if match:
                return match.group(1).strip()
        
        # JSON 객체 직접 추출
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
3. 사용자의 선택권 제시: "{max_allowed}개로 할래요? 아니면 시간을 늘리시겴래요?"

예시 톤: "아, {duration} 데이트에 {requested}개 장소는 조금 빡빡할 수 있어요! 각 장소에서 충분히 즐기시려면..."

단순한 텍스트로만 답변해주세요.
"""
            
            result = self.llm.invoke(prompt)
            return result.content.strip()
            
        except Exception as e:
            print(f"[ERROR] GPT 재확인 메시지 생성 실패: {e}")
            return f"⚠️ {duration} 데이트에 {requested}개 장소는 조금 빡빡할 수 있어요! 최대 {max_allowed}개를 추천드려요. {max_allowed}개로 하시겠어요? 아니면 시간을 늘리시겴래요?"
    
