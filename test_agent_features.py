import asyncio
import json
import sys
import os
import httpx # HTTP 요청을 위한 라이브러리
from loguru import logger
from datetime import datetime # datetime 모듈 추가

# 로거 설정: 상세한 분석을 위해 DEBUG 레벨까지 출력
logger.remove()
logger.add(sys.stderr, level="DEBUG")

# FastAPI 서버의 기본 URL
BASE_URL = "http://localhost:8000"

async def run_feature_tests_via_http():
    """HTTP 요청을 통해 서버의 기능을 테스트하는 함수"""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=120.0) as client:
        # --- 테스트 시나리오 1: 맑은 날, 용산에서의 데이트 --- #
        print("\n" + "="*50)
        print("🚀 테스트 1: 맑은 날, 용산에서의 데이트 (HTTP 요청)")
        print("="*50)

        test_request_sunny ={
  "request_id": "req-xxx",
  "timestamp": "2025-07-02T12:46:46",
  "search_targets": [
    {
      "sequence": 1,
      "category": "음식점",
      "location": {
        "area_name": "이촌동",
        "coordinates": {
          "latitude": 37.5225,
          "longitude": 126.9723
        }
      },
      "semantic_query": "조용한 저녁 시간, 한강의 부드러운 물결을 배경으로 사랑하는 이와 함께하는 완벽한 데이트 장소가 이촌동에 있습니다. 고급스러운 분위기의 음식점들은 연인과의 특별한 순간을 더욱 특별하게 만들어 주며, 아늑한 조명 아래 정성스럽게 준비된 요리와 함께하는 저녁은 깊은 대화를 나누기에 안성맞춤입니다. 산책 후, 따뜻한 마음을 나누며 6만원 이하의 예산으로도 충분히 품격 있는 경험을 할 수 있는 이곳은, 사랑하는 사람과의 소중한 추억을 쌓기에 최적의 환경을 제공합니다."
    },
    {
      "sequence": 2,
      "category": "카페",
      "location": {
        "area_name": "한남동",
        "coordinates": {
          "latitude": 37.5357,
          "longitude": 127.0002
        }
      },
      "semantic_query": "조용하고 고급스러운 분위기가 감도는 한남동의 카페는 연인과 함께 특별한 저녁 시간을 보내기에 최적의 장소입니다. 세련된 인테리어와 아늑한 조명이 어우러져 감성적인 데이트를 즐길 수 있으며, 다양한 커피와 디저트 메뉴가 예산 6만원 이하에서 충분히 만족스러운 경험을 선사합니다. 특히, 이곳은 저녁에 방문하면 더욱 로맨틱한 분위기가 연출되어 소중한 사람과의 대화가 더욱 깊어지는 곳입니다."
    },
    {
      "sequence": 3,
      "category": "술집",
      "location": {
        "area_name": "후암동",
        "coordinates": {
          "latitude": 37.5509,
          "longitude": 126.9727
        }
      },
      "semantic_query": "조용한 저녁, 사랑하는 이와 함께 남산의 야경을 바라보며 여유로운 시간을 보내기에 안성맞춤인 술집. 편안한 분위기 속에서 다양한 주류를 즐기며 소소한 대화를 나누기에 더할 나위 없이 좋은 장소로, 예산도 부담 없이 6만원 이하로 즐길 수 있어 데이트 마무리 장소로 추천합니다. 후암동의 숨겨진 보석 같은 이곳은 연인과의 특별한 순간을 더욱 빛나게 해 줄 것입니다."
    }
  ],
  "user_context": {
    "demographics": {
      "age": 27,
      "mbti": "ENFP",
      "relationship_stage": "연인"
    },
    "preferences": [
      "조용한 분위기"
    ],
    "requirements": {
      "budget_range": "6만원 이하",
      "time_preference": "저녁",
      "party_size": 2,
      "transportation": ""
    }
  },
  "course_planning": {
    "optimization_goals": [
      "사용자 선호와 동선 최적화",
      "각 장소별 적절한 머무름 시간 제안"
    ],
    "route_constraints": {
      "max_travel_time_between": 30,
      "total_course_duration": 240,
      "flexibility": "medium"
    },
    "sequence_optimization": {
      "allow_reordering": True,
      "prioritize_given_sequence": True
    }
  }
}

        try:
            response_sunny = await client.post("/recommend-course", json=test_request_sunny, timeout=120.0)
            response_sunny.raise_for_status() # HTTP 에러 발생 시 예외 처리
            result_sunny = response_sunny.json()
            
            print("\n--- ☀️ 맑은 날 시나리오 최종 결과 ---")
            print(json.dumps(result_sunny['results']['sunny_weather'], indent=2, ensure_ascii=False))
            print("\n--- ☔️ 비 오는 날 시나리오 최종 결과 (참고용) ---")
            print(json.dumps(result_sunny['results']['rainy_weather'], indent=2, ensure_ascii=False))
            print("\n--- ⚙️ 적용된 제약 조건 상세 ---")
            print(json.dumps(result_sunny['constraints_applied'], indent=2, ensure_ascii=False))

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP 오류 발생: {e.response.status_code} - {e.response.text}")
            print(f"❌ HTTP 오류: {e.response.status_code}")
            print(f"   응답 내용: {e.response.text}")
        except httpx.RequestError as e:
            logger.error(f"요청 중 오류 발생: {e}")
            print(f"❌ 연결 오류: {e}")
        except Exception as e:
            logger.error(f"예상치 못한 오류 발생: {e}")
            print(f"❌ 예상치 못한 오류: {e}")


        # --- 테스트 시나리오 2: 비 오는 날, 용산에서의 데이트 --- #
        print("\n" + "="*50)
        print("🚀 테스트 2: 비 오는 날, 용산에서의 데이트 (HTTP 요청)")
        print("="*50)

        test_request_rainy = test_request_sunny.copy()
        test_request_rainy["request_id"] = "test-rainy-yongsan-002"
        test_request_rainy["timestamp"] = datetime.now().isoformat() + 'Z' # 현재 시간 timestamp 추가

        try:
            response_rainy = await client.post("/recommend-course", json=test_request_rainy, )
            response_rainy.raise_for_status()
            result_rainy = response_rainy.json()

            print("\n--- ☀️ 맑은 날 시나리오 최종 결과 (참고용) ---")
            print(json.dumps(result_rainy['results']['sunny_weather'], indent=2, ensure_ascii=False))
            print("\n--- ☔️ 비 오는 날 시나리오 최종 결과 ---")
            print(json.dumps(result_rainy['results']['rainy_weather'], indent=2, ensure_ascii=False))
            print("\n--- ⚙️ 적용된 제약 조건 상세 ---")
            print(json.dumps(result_rainy['constraints_applied'], indent=2, ensure_ascii=False))

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP 오류 발생: {e.response.status_code} - {e.response.text}")
            print(f"❌ HTTP 오류: {e.response.status_code}")
            print(f"   응답 내용: {e.response.text}")
        except httpx.RequestError as e:
            logger.error(f"요청 중 오류 발생: {e}")
            print(f"❌ 연결 오류: {e}")
        except Exception as e:
            logger.error(f"예상치 못한 오류 발생: {e}")
            print(f"❌ 예상치 못한 오류: {e}")


        # --- 테스트 시나리오 3: 용산 내 '다중 지역' 데이트 (용산역 → 이태원) --- #
        print("\n" + "="*50)
        print("🚀 테스트 3: 용산 내 '다중 지역' 데이트 (HTTP 요청)")
        print("="*50)

        test_request_multi_region = {
  "request_id": "req-xxx",
  "timestamp": "2025-07-02T12:46:46",
  "search_targets": [
    {
      "sequence": 1,
      "category": "음식점",
      "location": {
        "area_name": "이촌동",
        "coordinates": {
          "latitude": 37.5225,
          "longitude": 126.9723
        }
      },
      "semantic_query": "조용한 저녁 시간, 한강의 부드러운 물결을 배경으로 사랑하는 이와 함께하는 완벽한 데이트 장소가 이촌동에 있습니다. 고급스러운 분위기의 음식점들은 연인과의 특별한 순간을 더욱 특별하게 만들어 주며, 아늑한 조명 아래 정성스럽게 준비된 요리와 함께하는 저녁은 깊은 대화를 나누기에 안성맞춤입니다. 산책 후, 따뜻한 마음을 나누며 6만원 이하의 예산으로도 충분히 품격 있는 경험을 할 수 있는 이곳은, 사랑하는 사람과의 소중한 추억을 쌓기에 최적의 환경을 제공합니다."
    },
    {
      "sequence": 2,
      "category": "카페",
      "location": {
        "area_name": "한남동",
        "coordinates": {
          "latitude": 37.5357,
          "longitude": 127.0002
        }
      },
      "semantic_query": "조용하고 고급스러운 분위기가 감도는 한남동의 카페는 연인과 함께 특별한 저녁 시간을 보내기에 최적의 장소입니다. 세련된 인테리어와 아늑한 조명이 어우러져 감성적인 데이트를 즐길 수 있으며, 다양한 커피와 디저트 메뉴가 예산 6만원 이하에서 충분히 만족스러운 경험을 선사합니다. 특히, 이곳은 저녁에 방문하면 더욱 로맨틱한 분위기가 연출되어 소중한 사람과의 대화가 더욱 깊어지는 곳입니다."
    },
    {
      "sequence": 3,
      "category": "술집",
      "location": {
        "area_name": "후암동",
        "coordinates": {
          "latitude": 37.5509,
          "longitude": 126.9727
        }
      },
      "semantic_query": "조용한 저녁, 사랑하는 이와 함께 남산의 야경을 바라보며 여유로운 시간을 보내기에 안성맞춤인 술집. 편안한 분위기 속에서 다양한 주류를 즐기며 소소한 대화를 나누기에 더할 나위 없이 좋은 장소로, 예산도 부담 없이 6만원 이하로 즐길 수 있어 데이트 마무리 장소로 추천합니다. 후암동의 숨겨진 보석 같은 이곳은 연인과의 특별한 순간을 더욱 빛나게 해 줄 것입니다."
    }
  ],
  "user_context": {
    "demographics": {
      "age": 27,
      "mbti": "ENFP",
      "relationship_stage": "연인"
    },
    "preferences": [
      "조용한 분위기"
    ],
    "requirements": {
      "budget_range": "6만원 이하",
      "time_preference": "저녁",
      "party_size": 2,
      "transportation": ""
    }
  },
  "course_planning": {
    "optimization_goals": [
      "사용자 선호와 동선 최적화",
      "각 장소별 적절한 머무름 시간 제안"
    ],
    "route_constraints": {
      "max_travel_time_between": 30,
      "total_course_duration": 240,
      "flexibility": "medium"
    },
    "sequence_optimization": {
      "allow_reordering": True,
      "prioritize_given_sequence": True
    }
  }
}

        try:
            response_multi_region = await client.post("/recommend-course", json=test_request_multi_region, timeout=10.0)
            response_multi_region.raise_for_status()
            result_multi_region = response_multi_region.json()

            print("\n--- ☀️ 맑은 날 시나리오 최종 결과 (다중 지역) ---")
            print(json.dumps(result_multi_region['results']['sunny_weather'], indent=2, ensure_ascii=False))
            print("\n--- ⚙️ 적용된 제약 조건 상세 (다중 지역) ---")
            print(json.dumps(result_multi_region['constraints_applied'], indent=2, ensure_ascii=False))

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP 오류 발생: {e.response.status_code} - {e.response.text}")
            print(f"❌ HTTP 오류: {e.response.status_code}")
            print(f"   응답 내용: {e.response.text}")
        except httpx.RequestError as e:
            logger.error(f"요청 중 오류 발생: {e}")
            print(f"❌ 연결 오류: {e}")
        except Exception as e:
            logger.error(f"예상치 못한 오류 발생: {e}")
            print(f"❌ 예상치 못한 오류: {e}")

        print("\n" + "="*50)
        print("✅ 모든 HTTP 테스트 완료")
        print("="*50)

if __name__ == "__main__":
    # httpx 라이브러리가 설치되어 있는지 확인
    try:
        import httpx
    except ImportError:
        print("오류: 'httpx' 라이브러리가 설치되어 있지 않습니다.")
        print("pip install httpx 명령어로 설치해주세요.")
        sys.exit(1)

    asyncio.run(run_feature_tests_via_http())