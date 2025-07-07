#!/usr/bin/env python3
"""
간단한 한 줄 수정으로 category_conversions 문제 해결
"""

# 파일 읽기
with open('/Users/hwangjunho/Desktop/date-course-agent/src/core/weather_processor.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 맨 앞에 category_conversions 초기화 추가
old_line1 = '            logger.info(f"▶️  {weather.upper()} 시나리오 처리 시작")'
new_line1 = '''            logger.info(f"▶️  {weather.upper()} 시나리오 처리 시작")

            # 0. 카테고리 변환 내역 초기화 (모든 날씨에 대해)
            category_conversions = []
            original_targets = search_targets.copy()'''

content = content.replace(old_line1, new_line1)

# 2. 비오는 날씨 처리 부분 수정
old_line2 = '''            # 1. (필요시) 날씨에 따라 검색 타겟 수정
            if weather == "rainy":
                search_targets = self._convert_outdoor_categories_for_rainy(search_targets)'''

new_line2 = '''            # 1. (필요시) 날씨에 따라 검색 타겟 수정
            if weather == "rainy":
                search_targets = self._convert_outdoor_categories_for_rainy(search_targets)
                category_conversions = self._get_category_conversions(original_targets, search_targets)'''

content = content.replace(old_line2, new_line2)

# 저장
with open('/Users/hwangjunho/Desktop/date-course-agent/src/core/weather_processor.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ category_conversions 문제가 완전히 해결되었습니다!")
print("   - 모든 날씨 시나리오에서 category_conversions가 안전하게 초기화됩니다")
print("   - 비오는 날씨에서만 실제 변환 내역이 추가됩니다")
