# GPT 프롬프트 템플릿 모음
# - 반경 계산용 프롬프트
# - 코스 선택용 프롬프트

import json
from typing import List, Dict, Any
from src.models.internal_models import CourseCombination

class GPTPromptTemplates:
    """GPT 프롬프트 템플릿 관리 클래스"""
    
    def create_course_selection_prompt(
        self, 
        combinations: List[CourseCombination], 
        user_context: Dict[str, Any], 
        weather: str, 
        search_attempt: str
    ) -> str:
        """코스 선택용 프롬프트 생성"""
        
        # 사용자 컨텍스트 요약
        user_summary = self._summarize_user_context(user_context)
        
        # 조합 정보 요약
        combinations_summary = self._summarize_combinations(combinations)
        
        # 날씨별 프롬프트
        weather_instruction = self._get_weather_instruction(weather)
        
        prompt = f"""당신은 데이트 코스 추천 전문가입니다. 다음 조건을 분석하여 최적의 데이트 코스 3개를 선택해주세요.

## 사용자 정보
{user_summary}

## 날씨 조건
{weather_instruction}

## 검색 시도
현재 {search_attempt} 시도 결과입니다.

## 코스 조합들
{combinations_summary}

## 선택 기준
1. 사용자의 나이, 관계 단계, 선호도에 적합한지
2. {weather} 날씨에 적절한지
3. 이동 거리와 동선이 합리적인지
4. 각 장소의 분위기와 컨셉이 조화로운지
5. 전체적인 데이트 경험의 완성도

## 응답 형식
다음 JSON 형식으로 상위 3개 코스를 선택하고 각각의 추천 이유를 작성해주세요:

```json
[
  {{
    "combination_id": "combination_1",
    "rank": 1,
    "reason": "이 코스를 1순위로 추천하는 구체적인 이유..."
  }},
  {{
    "combination_id": "combination_2", 
    "rank": 2,
    "reason": "이 코스를 2순위로 추천하는 구체적인 이유..."
  }},
  {{
    "combination_id": "combination_3",
    "rank": 3, 
    "reason": "이 코스를 3순위로 추천하는 구체적인 이유..."
  }}
]
```

만약 모든 조합이 사용자 조건에 부적절하다면 "부적절"이라고만 답변해주세요.

추천 이유는 구체적이고 개인화된 내용으로 작성해주세요. 단순한 나열보다는 왜 이 사용자에게 특별히 적합한지 설명해주세요."""

        return prompt
    
    def _summarize_user_context(self, user_context: Dict[str, Any]) -> str:
        """사용자 컨텍스트 요약"""
        try:
            demographics = user_context.get('demographics', {})
            preferences = user_context.get('preferences', [])
            requirements = user_context.get('requirements', {})
            
            summary = f"""
- 나이: {demographics.get('age', '알 수 없음')}세
- 관계: {demographics.get('relationship_stage', '알 수 없음')}
- MBTI: {demographics.get('mbti', '알 수 없음')}
- 선호도: {', '.join(preferences) if preferences else '없음'}
- 예산: {requirements.get('budget_range', '알 수 없음')}
- 시간대: {requirements.get('time_preference', '알 수 없음')}
- 인원: {requirements.get('party_size', 2)}명
- 교통수단: {requirements.get('transportation', '알 수 없음')}
"""
            return summary.strip()
            
        except Exception as e:
            return "사용자 정보를 파싱할 수 없습니다."
    
    def _summarize_combinations(self, combinations: List[CourseCombination]) -> str:
        """조합들 요약"""
        try:
            if not combinations:
                return "사용 가능한 조합이 없습니다."
            
            summary_lines = []
            
            for i, combo in enumerate(combinations[:10]):  # 최대 10개만 표시
                places_info = []
                for place in combo.course_sequence:
                    description = place.get('description', '') or place.get('summary', '')
                    if description:
                        # description이 너무 길면 150자로 자르기
                        desc_text = description[:150] + '...' if len(description) > 150 else description
                        places_info.append(f"{place['name']}({place['category']}): {desc_text}")
                    else:
                        places_info.append(f"{place['name']}({place['category']})")

                
                combo_summary = f"""
### {combo.combination_id}
- 장소들: {' → '.join(places_info)}
- 총 거리: {combo.total_distance_meters}m
- 평균 유사도: {combo.average_similarity_score:.2f}
- 구간별 거리: {', '.join([f"{seg['distance_meters']}m" for seg in combo.travel_distances])}
"""
                summary_lines.append(combo_summary.strip())
            
            if len(combinations) > 10:
                summary_lines.append(f"\n... 외 {len(combinations) - 10}개 조합")
            
            return '\n\n'.join(summary_lines)
            
        except Exception as e:
            return "조합 정보를 파싱할 수 없습니다."
    
    def _get_weather_instruction(self, weather: str) -> str:
        """날씨별 지시사항"""
        if weather.lower() in ['rainy', '비', '비오는']:
            return """
🌧️ 비오는 날씨입니다.
- 실내 위주의 활동을 우선시해주세요
- 이동 거리를 최소화해주세요
- 대중교통 접근성이 좋은 곳을 선택해주세요
- 야외 활동은 피해주세요
"""
        else:
            return """
☀️ 맑은 날씨입니다.
- 실내외 활동 모두 고려 가능합니다
- 도보 이동도 고려할 수 있습니다
- 야외에서의 낭만적인 시간도 좋습니다
"""
    
    def create_radius_calculation_prompt(
        self, 
        user_context: Dict[str, Any], 
        course_planning: Dict[str, Any], 
        weather: str = "sunny"
    ) -> str:
        """반경 계산용 프롬프트 생성"""
        
        # 사용자 정보 추출
        demographics = user_context.get('demographics', {})
        requirements = user_context.get('requirements', {})
        
        # 제약 조건 추출
        route_constraints = course_planning.get('route_constraints', {})
        
        age = demographics.get('age', '알 수 없음')
        relationship = demographics.get('relationship_stage', '알 수 없음')
        transportation = requirements.get('transportation', '알 수 없음')
        party_size = requirements.get('party_size', 2)
        max_travel_time = route_constraints.get('max_travel_time_between', 30)
        flexibility = route_constraints.get('flexibility', 'medium')
        
        weather_context = "비오는 날씨에는 실내 위주로 이동하고 도보 거리를 최소화해야 합니다." if weather == "rainy" else "맑은 날씨에는 도보 이동이 가능하고 야외 활동도 고려할 수 있습니다."
        
        prompt = f"""다음과 같은 사용자 성향과 요구사항을 가진 사람이 {weather} 날 데이트 코스를 이용할 때, 각 장소를 중심으로 몇 미터 반경 내에서 장소를 찾는 것이 적절할까요?

사용자 정보:
- 나이: {age}세
- 관계: {relationship}
- 인원: {party_size}명
- 교통수단: {transportation}

제약 조건:
- 장소 간 최대 이동시간: {max_travel_time}분
- 일정 유연성: {flexibility}

날씨 조건:
{weather_context}

위 조건을 종합적으로 고려하여 적절한 검색 반경을 미터 단위 숫자로만 답변해주세요.

예시: 2000"""
        
        return prompt
    
    def create_validation_prompt(self, courses: List[Dict], user_context: Dict[str, Any]) -> str:
        """코스 검증용 프롬프트 생성"""
        
        user_summary = self._summarize_user_context(user_context)
        
        courses_summary = ""
        for i, course in enumerate(courses):
            places = [place['name'] for place in course.get('places', [])]
            courses_summary += f"{i+1}. {' → '.join(places)}\n"
        
        prompt = f"""다음 데이트 코스들이 사용자에게 적합한지 검증해주세요.

## 사용자 정보
{user_summary}

## 제안된 코스들
{courses_summary}

각 코스에 대해 다음 기준으로 평가해주세요:
1. 사용자 연령대에 적합한가?
2. 관계 단계에 맞는 분위기인가?
3. 예산 범위에 적절한가?
4. 이동 동선이 합리적인가?
5. 전체적인 흐름이 자연스러운가?

각 코스에 대해 1-10점으로 점수를 매기고 간단한 평가 이유를 작성해주세요."""
        
        return prompt
    
    def create_improvement_suggestion_prompt(
        self, 
        failed_combinations: List[CourseCombination], 
        user_context: Dict[str, Any]
    ) -> str:
        """개선 제안용 프롬프트 생성"""
        
        user_summary = self._summarize_user_context(user_context)
        
        prompt = f"""현재 조건으로는 적절한 데이트 코스를 찾을 수 없었습니다. 

## 사용자 정보
{user_summary}

사용자가 원하는 데이트 코스를 찾기 위해 다음 중 어떤 조건을 조정하면 좋을지 3가지 구체적인 제안을 해주세요:

1. 지역 범위 확대
2. 예산 조정
3. 시간대 변경
4. 카테고리 다양화
5. 이동 거리 허용 범위 증가

각 제안에 대해 구체적인 이유와 함께 설명해주세요."""
        
        return prompt

# 전역 인스턴스
prompt_templates = GPTPromptTemplates()

# 편의 함수들
def get_course_selection_prompt(
    combinations: List[CourseCombination], 
    user_context: Dict[str, Any], 
    weather: str, 
    search_attempt: str
) -> str:
    """코스 선택 프롬프트 생성 편의 함수"""
    return prompt_templates.create_course_selection_prompt(combinations, user_context, weather, search_attempt)

def get_radius_calculation_prompt(
    user_context: Dict[str, Any], 
    course_planning: Dict[str, Any], 
    weather: str = "sunny"
) -> str:
    """반경 계산 프롬프트 생성 편의 함수"""
    return prompt_templates.create_radius_calculation_prompt(user_context, course_planning, weather)

if __name__ == "__main__":
    # 테스트 실행
    def test_prompt_templates():
        try:
            templates = GPTPromptTemplates()
            
            # 테스트 데이터
            test_user_context = {
                "demographics": {"age": 28, "mbti": "ENFJ", "relationship_stage": "연인"},
                "preferences": ["로맨틱한 분위기", "저녁 데이트"],
                "requirements": {
                    "budget_range": "커플 기준 15-20만원",
                    "time_preference": "저녁",
                    "party_size": 2,
                    "transportation": "대중교통"
                }
            }
            
            test_course_planning = {
                "route_constraints": {
                    "max_travel_time_between": 30,
                    "total_course_duration": 300,
                    "flexibility": "low"
                }
            }
            
            # 반경 계산 프롬프트 테스트
            radius_prompt = templates.create_radius_calculation_prompt(
                test_user_context, test_course_planning, "sunny"
            )
            
            print("✅ 프롬프트 템플릿 테스트 성공")
            print(f"반경 계산 프롬프트 길이: {len(radius_prompt)} 글자")
            print("첫 100글자:", radius_prompt[:100])
            
            # 코스 선택 프롬프트도 테스트 (빈 조합으로)
            selection_prompt = templates.create_course_selection_prompt(
                [], test_user_context, "sunny", "1차"
            )
            print(f"코스 선택 프롬프트 길이: {len(selection_prompt)} 글자")
            
        except Exception as e:
            print(f"❌ 프롬프트 템플릿 테스트 실패: {e}")
    
    test_prompt_templates()
