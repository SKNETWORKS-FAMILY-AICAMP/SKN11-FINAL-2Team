# A2A 테스트 스크립트
# - Main Agent에서 Place Agent로의 통신 테스트
# - 모듈화된 구조 검증

import asyncio
import httpx
import json
from datetime import datetime

class A2ATestClient:
    """A2A 통신 테스트 클라이언트"""
    
    def __init__(self, place_agent_url: str = "http://localhost:8002"):
        self.place_agent_url = place_agent_url
    
    async def test_health_check(self):
        """헬스 체크 테스트"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.place_agent_url}/health")
                
            if response.status_code == 200:
                result = response.json()
                print("✅ 헬스 체크 성공")
                print(f"   상태: {result.get('status')}")
                print(f"   서비스: {result.get('service')}")
                print(f"   버전: {result.get('version')}")
                return True
            else:
                print(f"❌ 헬스 체크 실패: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ 헬스 체크 연결 실패: {e}")
            return False
    
    async def test_place_request(self, test_name: str, request_data: dict):
        """Place Agent 요청 테스트"""
        try:
            print(f"\n🧪 테스트: {test_name}")
            print("-" * 40)
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.place_agent_url}/place-agent",
                    json=request_data
                )
            
            if response.status_code == 200:
                result = response.json()
                print("✅ 요청 처리 성공")
                print(f"   요청 ID: {result.get('request_id')}")
                print(f"   성공 여부: {result.get('success')}")
                
                if result.get('success'):
                    locations = result.get('locations', [])
                    print(f"   반환된 지역 수: {len(locations)}")
                    
                    for i, location in enumerate(locations, 1):
                        print(f"   {i}. {location.get('area_name')}")
                        coords = location.get('coordinates', {})
                        print(f"      좌표: {coords.get('latitude')}, {coords.get('longitude')}")
                        print(f"      이유: {location.get('reason', '')[:50]}...")
                else:
                    print(f"   오류 메시지: {result.get('error_message')}")
                
                return result
            else:
                print(f"❌ 요청 실패: {response.status_code}")
                print(f"   응답: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ 요청 처리 실패: {e}")
            return None

async def main():
    """A2A 테스트 메인 함수"""
    print("🚀 Place Agent A2A 테스트 시작")
    print("=" * 50)
    
    client = A2ATestClient()
    
    # 1. 헬스 체크
    health_ok = await client.test_health_check()
    if not health_ok:
        print("❌ 헬스 체크 실패 - 서버가 실행 중인지 확인하세요")
        return
    
    # 2. 기본 테스트 케이스들
    test_cases = [
        {
            "name": "홍대 근처 3곳 (ENFP 연인)",
            "data": {
                "request_id": "test-001",
                "timestamp": datetime.datetime.now().isoformat(),
                "request_type": "proximity_based",
                "location_request": {
                    "proximity_type": "near",
                    "reference_areas": ["홍대"],
                    "place_count": 3,
                    "proximity_preference": "middle",
                    "transportation": "지하철"
                },
                "user_context": {
                    "demographics": {
                        "age": 25,
                        "mbti": "ENFP",
                        "relationship_stage": "연인"
                    },
                    "preferences": ["트렌디한", "감성적인"],
                    "requirements": {
                        "budget_level": "medium",
                        "time_preference": "저녁",
                        "transportation": "지하철",
                        "max_travel_time": 30
                    }
                },
                "selected_categories": ["카페", "레스토랑"]
            }
        },
        {
            "name": "강남 근처 2곳 (INTJ 썸)",
            "data": {
                "request_id": "test-002", 
                "timestamp": datetime.datetime.now().isoformat(),
                "request_type": "proximity_based",
                "location_request": {
                    "proximity_type": "near",
                    "reference_areas": ["강남"],
                    "place_count": 2,
                    "proximity_preference": "close",
                    "transportation": "도보"
                },
                "user_context": {
                    "demographics": {
                        "age": 28,
                        "mbti": "INTJ",
                        "relationship_stage": "썸"
                    },
                    "preferences": ["조용한", "세련된"],
                    "requirements": {
                        "budget_level": "high",
                        "time_preference": "오후",
                        "transportation": "도보",
                        "max_travel_time": 15
                    }
                },
                "selected_categories": ["카페"]
            }
        },
        {
            "name": "성수 근처 4곳 (ESFP 친구)",
            "data": {
                "request_id": "test-003",
                "timestamp": datetime.datetime.now().isoformat(),
                "request_type": "proximity_based", 
                "location_request": {
                    "proximity_type": "near",
                    "reference_areas": ["성수"],
                    "place_count": 4,
                    "proximity_preference": "far",
                    "transportation": "대중교통"
                },
                "user_context": {
                    "demographics": {
                        "age": 23,
                        "mbti": "ESFP",
                        "relationship_stage": "친구"
                    },
                    "preferences": ["힙한", "트렌디한"],
                    "requirements": {
                        "budget_level": "low",
                        "time_preference": "낮",
                        "transportation": "대중교통",
                        "max_travel_time": 45
                    }
                },
                "selected_categories": ["카페", "레스토랑", "문화공간"]
            }
        }
    ]
    
    # 테스트 실행
    results = []
    for test_case in test_cases:
        result = await client.test_place_request(test_case["name"], test_case["data"])
        results.append(result)
        await asyncio.sleep(1)  # API 부하 방지
    
    # 결과 요약
    print("\n" + "=" * 50)
    print("📊 테스트 결과 요약")
    print("=" * 50)
    
    success_count = sum(1 for r in results if r and r.get('success'))
    total_count = len(results)
    
    print(f"성공: {success_count}/{total_count}")
    print(f"성공률: {(success_count/total_count)*100:.1f}%")
    
    if success_count == total_count:
        print("🎉 모든 A2A 테스트 성공! 모듈화 완료")
    else:
        print("⚠️ 일부 테스트 실패 - 로그를 확인하세요")

if __name__ == "__main__":
    asyncio.run(main())