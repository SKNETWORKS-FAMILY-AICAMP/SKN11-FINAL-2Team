#!/usr/bin/env python3
"""
weather_processor.py 파일의 _process_scenario 메소드를 완전히 수정하는 스크립트
"""

import re

def fix_process_scenario_method():
    """_process_scenario 메소드의 category_conversions 문제를 완전히 수정"""
    
    # 읽기
    with open('/Users/hwangjunho/Desktop/date-course-agent/src/core/weather_processor.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 기존 _process_scenario 메소드를 찾아서 교체
    old_method_pattern = r'(    async def _process_scenario\(self, weather: str, search_targets: List\[Dict\], user_context: Dict, course_planning: Dict\) -> WeatherScenarioResult:.*?)(    def _create_embeddings_for_targets|    async def _create_embeddings_for_targets|    def _convert_outdoor_categories_for_rainy|$)'
    
    new_method = '''    async def _process_scenario(self, weather: str, search_targets: List[Dict], user_context: Dict, course_planning: Dict) -> WeatherScenarioResult:
        """특정 날씨 시나리오를 처리하는 통합 로직"""
        try:
            logger.info(f"▶️  {weather.upper()} 시나리오 처리 시작")

            # 1. 카테고리 변환 내역 초기화 (모든 날씨에 대해 안전하게)
            category_conversions = []
            original_targets = search_targets.copy()
            
            # 2. (필요시) 날씨에 따라 검색 타겟 수정
            if weather == "rainy":
                search_targets = self._convert_outdoor_categories_for_rainy(search_targets)
                category_conversions = self._get_category_conversions(original_targets, search_targets)

            # 3. 임베딩 생성
            embeddings = await self._create_embeddings_for_targets(search_targets)

            # 4. 위치 분석을 통해 검색 전략 수립 (가장 중요!)
            location_analysis = self.location_analyzer.analyze_search_targets(search_targets, weather)
            logger.info(f"💡 {weather.upper()} 시나리오 전략: {location_analysis['analysis_summary']}")

            # 5. 수립된 전략에 따라 벡터 검색 수행 (재시도 로직 포함)
            search_result = await self.vector_search.search_with_retry_logic(
                search_targets=search_targets,
                embeddings=embeddings,
                location_analysis=location_analysis
            )
            
            # 6. 스마트 코스 조합 생성
            combinations = self.course_optimizer.generate_combinations(
                places=search_result.places,
                search_targets=search_targets,
                weather=weather,
                location_analysis=location_analysis # 조합 시에도 위치 분석 결과 활용
            )

            # 7. GPT를 통해 최종 코스 선택
            selected_courses = await self.gpt_selector.select_best_courses(
                combinations, user_context, weather, search_result.attempt
            )

            # 8. 최종 결과 생성 (모든 날씨에 대해 category_conversions 안전하게 전달)
            result = WeatherScenarioResult(
                weather=weather,
                status="success" if selected_courses else "failed",
                attempt=search_result.attempt,
                radius_used=search_result.radius_used,
                courses=selected_courses,
                total_combinations=len(combinations),
                category_conversions=category_conversions  # 안전하게 전달
            )
            logger.info(f"✅ {weather.upper()} 시나리오 처리 완료")
            return result

        except Exception as e:
            logger.error(f"❌ {weather.upper()} 시나리오 처리 실패: {e}")
            return self._create_failed_result(weather, str(e))
    
    '''
    
    # 정규식으로 교체
    updated_content = re.sub(
        old_method_pattern, 
        new_method + r'\\2',
        content, 
        flags=re.DOTALL
    )
    
    if updated_content == content:
        print("❌ 메소드를 찾지 못했습니다. 수동으로 수정해야 합니다.")
        return False
    
    # 저장
    with open('/Users/hwangjunho/Desktop/date-course-agent/src/core/weather_processor.py', 'w', encoding='utf-8') as f:
        f.write(updated_content)
    
    print("✅ _process_scenario 메소드가 완전히 수정되었습니다!")
    return True

if __name__ == "__main__":
    print("🔧 weather_processor.py 수정 시작...")
    if fix_process_scenario_method():
        print("✅ 수정 완료!")
    else:
        print("❌ 수정 실패!")
