#!/usr/bin/env python3

import sys
import os
import asyncio
sys.path.append('/Users/hwangjunho/Desktop/date-course-agent/src')

from core.weather_processor import WeatherProcessor
from models.request_models import SearchTargetModel, LocationModel

async def simple_test():
    """간단한 테스트"""
    try:
        print("🧪 간단한 테스트 시작...")
        
        # WeatherProcessor 초기화
        processor = WeatherProcessor()
        print("✅ WeatherProcessor 생성")
        
        # 테스트 데이터 (용산구 좌표)
        search_targets = [
            SearchTargetModel(
                sequence=1,
                category="음식점",
                location=LocationModel(
                    area_name="이태원",
                    coordinates={"latitude": 37.5339, "longitude": 126.9956}
                ),
                semantic_query="이태원 로맨틱한 레스토랑"
            )
        ]
        
        user_context = {
            "demographics": {"age": 28, "relationship_stage": "연인"},
            "preferences": ["로맨틱한 분위기"],
            "requirements": {
                "budget_range": "15-20만원",
                "time_preference": "저녁",
                "party_size": 2,
                "transportation": "대중교통"
            }
        }
        
        course_planning = {
            "optimization_goals": ["로맨틱한 경험"],
            "route_constraints": {
                "max_travel_time_between": 30,
                "total_course_duration": 300,
                "flexibility": "low"
            },
            "sequence_optimization": {
                "allow_reordering": False,
                "prioritize_given_sequence": True
            }
        }
        
        print("✅ 테스트 데이터 준비")
        
        # 맑은 날씨 처리 테스트
        print("☀️ 맑은 날씨 처리 테스트...")
        result = await processor.process_sunny_weather(
            search_targets, user_context, course_planning
        )
        
        print(f"✅ 결과: {result.status}, 시도: {result.attempt}")
        print(f"   반경: {result.radius_used}m")
        print(f"   코스 수: {len(result.courses)}")
        
        if result.error_message:
            print(f"❌ 에러: {result.error_message}")
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(simple_test())
