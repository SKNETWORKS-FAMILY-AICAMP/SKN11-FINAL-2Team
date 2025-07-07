#!/usr/bin/env python3
"""
메인 에이전트에서 보내는 소문자 JSON boolean 테스트
HTTP API를 통해 true/false (소문자)로 요청을 보내서 정상 처리되는지 확인
"""

import asyncio
import aiohttp
import json

# 메인 에이전트가 보낼 실제 JSON 데이터 (소문자 boolean)
test_request_with_lowercase_boolean = {
  "request_id": "boolean-test-001",
  "timestamp": "2025-07-02T12:00:00Z",
  "search_targets": [
    {
      "sequence": 1,
      "category": "음식점",
      "location": {
        "area_name": "홍대",
        "coordinates": {
          "latitude": 37.5519,
          "longitude": 126.9245
        }
      },
      "semantic_query": "홍대에서 커플이 가기 좋은 로맨틱한 레스토랑"
    },
    {
      "sequence": 2,
      "category": "카페",
      "location": {
        "area_name": "홍대",
        "coordinates": {
          "latitude": 37.5519,
          "longitude": 126.9245
        }
      },
      "semantic_query": "분위기 좋은 카페"
    }
  ],
  "user_context": {
    "demographics": {
      "age": 25,
      "mbti": "ENFP",
      "relationship_stage": "연인"
    },
    "preferences": ["로맨틱한 분위기", "힙한 장소"],
    "requirements": {
      "budget_range": "5만원",
      "time_preference": "저녁",
      "party_size": 2,
      "transportation": "대중교통"
    }
  },
  "course_planning": {
    "optimization_goals": ["로맨틱한 저녁 데이트"],
    "route_constraints": {
      "max_travel_time_between": 30,
      "total_course_duration": 240,
      "flexibility": "medium"
    },
    "sequence_optimization": {
      "allow_reordering": "true",         # 문자열 형태
      "prioritize_given_sequence": "false"  # 문자열 형태
    }
  }
}

async def test_json_boolean_api():
    """HTTP API로 소문자 boolean 테스트"""
    
    print("🧪 JSON Boolean API 테스트 시작")
    print("=" * 60)
    
    # JSON 문자열로 변환 (이때 Python boolean이 JSON boolean으로 변환됨)
    json_string = json.dumps(test_request_with_lowercase_boolean)
    print("📤 전송할 JSON:")
    print(json_string[:200] + "..." if len(json_string) > 200 else json_string)
    print()
    
    # 소문자 boolean 확인
    if '"true"' in json_string and '"false"' in json_string:
        print("✅ JSON에 소문자 boolean (문자열) 포함됨")
    else:
        print("❌ JSON에 소문자 boolean (문자열) 없음")
    print()
    
    try:
        async with aiohttp.ClientSession() as session:
            print("🚀 HTTP POST 요청 전송 중...")
            async with session.post(
                "http://localhost:8000/recommend-course",
                json=test_request_with_lowercase_boolean,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                
                print(f"📊 응답 상태: {response.status}")
                
                if response.status == 200:
                    result = await response.json()
                    print("✅ 요청 성공!")
                    print(f"📋 Request ID: {result.get('request_id', 'N/A')}")
                    print(f"⏱️  처리 시간: {result.get('processing_time', 'N/A')}")
                    print(f"🎯 상태: {result.get('status', 'N/A')}")
                    
                    # 결과 코스 개수 확인
                    results = result.get('results', {})
                    sunny_count = len(results.get('sunny_weather', []))
                    rainy_count = len(results.get('rainy_weather', []))
                    print(f"☀️ 맑은 날 코스: {sunny_count}개")
                    print(f"🌧️ 비 오는 날 코스: {rainy_count}개")
                    
                    print()
                    print("🎉 소문자 JSON boolean 처리 성공!")
                    
                else:
                    error_text = await response.text()
                    print(f"❌ 요청 실패: {response.status}")
                    print(f"오류 내용: {error_text}")
                    
    except aiohttp.ClientConnectorError:
        print("❌ 서버 연결 실패!")
        print("💡 먼저 서버를 실행해주세요: python run_server.py")
        
    except asyncio.TimeoutError:
        print("⏰ 요청 시간 초과 (60초)")
        
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")

async def test_direct_function_call():
    """직접 함수 호출로도 테스트"""
    print("\n" + "=" * 60)
    print("🔧 직접 함수 호출 테스트")
    print("=" * 60)
    
    try:
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
        
        from main import DateCourseAgent
        
        agent = DateCourseAgent()
        print("🚀 RAG Agent 직접 호출 중...")
        
        result = await agent.process_request(test_request_with_lowercase_boolean)
        
        print("✅ 직접 호출 성공!")
        print(f"📋 Request ID: {result.get('request_id', 'N/A')}")
        print(f"⏱️  처리 시간: {result.get('processing_time', 'N/A')}")
        print(f"🎯 상태: {result.get('status', 'N/A')}")
        
        print("\n🎉 직접 함수 호출로도 소문자 boolean 처리 성공!")
        
    except Exception as e:
        print(f"❌ 직접 호출 실패: {e}")

if __name__ == "__main__":
    asyncio.run(test_json_boolean_api())
    asyncio.run(test_direct_function_call())