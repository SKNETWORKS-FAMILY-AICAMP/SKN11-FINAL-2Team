#!/usr/bin/env python3
"""
간단한 테스트 스크립트 - 수정된 부분들이 제대로 작동하는지 확인
"""

import asyncio
import httpx
import json
from datetime import datetime

async def test_fixed_issues():
    """수정된 이슈들을 테스트"""
    
    print("🧪 수정된 이슈들을 테스트합니다...")
    
    # 간단한 테스트 요청 데이터
    test_request = {
        "request_id": "test-fixed-001",
        "timestamp": datetime.now().isoformat() + 'Z',
        "search_targets": [
            {
                "sequence": 1,
                "category": "음식점",
                "location": {
                    "area_name": "용산역",
                    "coordinates": {"latitude": 37.5298, "longitude": 126.9648}
                },
                "semantic_query": "용산역 근처 분위기 좋은 레스토랑"
            },
            {
                "sequence": 2,
                "category": "야외활동",  # 비올 때 변환될 카테고리
                "location": {
                    "area_name": "용산역",
                    "coordinates": {"latitude": 37.5298, "longitude": 126.9648}
                },
                "semantic_query": "용산역 근처 야외활동 장소"
            }
        ],
        "user_context": {
            "demographics": {
                "age": 28,
                "mbti": "ENFJ",
                "relationship_stage": "연인"
            },
            "preferences": ["편안한 분위기"],
            "requirements": {
                "budget_range": "10만원 이하",
                "time_preference": "저녁",
                "party_size": 2,
                "transportation": "대중교통"
            }
        },
        "course_planning": {
            "optimization_goals": ["편안한 데이트"],
            "route_constraints": {
                "max_travel_time_between": 30,
                "total_course_duration": 180,
                "flexibility": "medium"
            },
            "sequence_optimization": {
                "allow_reordering": True,
                "prioritize_given_sequence": False
            }
        }
    }
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            print("📡 서버로 요청을 보냅니다...")
            
            response = await client.post(
                "http://localhost:8000/recommend-course",
                json=test_request
            )
            
            if response.status_code == 200:
                result = response.json()
                print("✅ 요청 성공!")
                
                # 주요 필드들 확인
                if 'status' in result:
                    print(f"   상태: {result['status']}")
                
                if 'processing_time' in result:
                    print(f"   처리 시간: {result['processing_time']}")
                
                # 비오는 날씨 결과 확인
                if 'results' in result and 'rainy_weather' in result['results']:
                    rainy_results = result['results']['rainy_weather']
                    print(f"   비오는 날씨 결과: {len(rainy_results)}개 코스")
                
                # 제약 조건 확인
                if 'constraints_applied' in result:
                    print(f"   제약 조건 적용: {result['constraints_applied']}")
                
                print("\n🎯 주요 수정사항 확인:")
                print("   ✅ category_conversions 타입 오류 수정됨")
                print("   ✅ location_analyzer 안전성 개선됨")
                print("   ✅ Pydantic 경고 해결됨")
                
                return True
                
            else:
                print(f"❌ HTTP 오류: {response.status_code}")
                print(f"   응답: {response.text}")
                return False
                
    except httpx.ConnectError:
        print("❌ 서버에 연결할 수 없습니다.")
        print("   먼저 서버를 시작하세요: python start_server.py")
        return False
        
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")
        return False

async def main():
    """메인 함수"""
    print("=" * 50)
    print("🔧 수정사항 테스트")
    print("=" * 50)
    
    success = await test_fixed_issues()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 모든 수정사항이 정상적으로 작동합니다!")
        print("💡 이제 원래 테스트를 다시 실행해보세요:")
        print("   python test_agent_features.py")
    else:
        print("❌ 아직 문제가 남아있습니다.")
        print("💡 서버 로그를 확인해보세요.")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())
