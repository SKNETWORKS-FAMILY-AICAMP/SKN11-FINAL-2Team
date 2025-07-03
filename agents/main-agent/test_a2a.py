#!/usr/bin/env python3
"""
A2A 통신 테스트 - Main Agent → Place Agent → Main Agent → RAG Agent
전체 에이전트 통신 플로우 테스트
"""

import requests
import json
import time
import os
import sys
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# main-agent 모듈 import를 위한 경로 추가
sys.path.append(os.path.dirname(__file__))

# .env 파일 로드 (main-agent 디렉토리의 .env 파일)
load_dotenv()

# 기존 main-agent 함수들 import
from core.agent_builders import build_rag_agent_json

# 설정 (새로운 포트 구성)
MAIN_AGENT_URL = "http://localhost:8000"
PLACE_AGENT_URL = "http://localhost:8001"
RAG_AGENT_URL = "http://localhost:8002"  # RAG Agent 포트
REQUEST_FILE = "requests/rag/rag_agent_request_from_chat.json"
PLACE_REQUEST_FILE = "requests/place/place_agent_request_from_chat.json"

def load_test_request():
    """RAG Agent 테스트 요청 데이터 로드"""
    file_path = Path(REQUEST_FILE)
    
    if not file_path.exists():
        print(f"❌ RAG 요청 파일을 찾을 수 없습니다: {file_path}")
        return None
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"✅ RAG 요청 파일 로드 성공: {file_path}")
        print(f"   - Search targets: {len(data.get('search_targets', []))}")
        print(f"   - User age: {data.get('user_context', {}).get('demographics', {}).get('age')}")
        return data
    except Exception as e:
        print(f"❌ RAG 요청 파일 로드 실패: {e}")
        return None

def load_place_request():
    """Place Agent 테스트 요청 데이터 로드"""
    file_path = Path(PLACE_REQUEST_FILE)
    
    if not file_path.exists():
        print(f"❌ Place Agent 요청 파일을 찾을 수 없습니다: {file_path}")
        return None
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"✅ Place Agent 요청 파일 로드 성공: {file_path}")
        print(f"   - Request type: {data.get('request_type')}")
        print(f"   - Reference areas: {data.get('location_request', {}).get('reference_areas', [])}")
        print(f"   - Place count: {data.get('location_request', {}).get('place_count')}")
        return data
    except Exception as e:
        print(f"❌ Place Agent 요청 파일 로드 실패: {e}")
        return None

def check_servers():
    """모든 서버 상태 확인"""
    print("🔍 서버 상태 확인...")
    all_healthy = True
    
    # Main Agent 확인
    try:
        response = requests.get(f"{MAIN_AGENT_URL}/health", timeout=5)
        if response.status_code == 200:
            print(f"✅ Main Agent: {response.json()}")
        else:
            print(f"❌ Main Agent 응답 오류: {response.status_code}")
            all_healthy = False
    except Exception as e:
        print(f"❌ Main Agent 연결 실패: {e}")
        print("   → 'python start_all_servers.py' 또는 'cd agents/main-agent && python run_server.py'로 서버를 시작하세요.")
        all_healthy = False
    
    # Place Agent 확인
    try:
        response = requests.get(f"{PLACE_AGENT_URL}/health", timeout=5)
        if response.status_code == 200:
            print(f"✅ Place Agent: {response.json()}")
        else:
            print(f"❌ Place Agent 응답 오류: {response.status_code}")
            all_healthy = False
    except Exception as e:
        print(f"❌ Place Agent 연결 실패: {e}")
        print("   → 'python start_all_servers.py' 또는 'cd agents/place_agent && python start_server.py'로 서버를 시작하세요.")
        all_healthy = False
    
    # RAG Agent 확인
    try:
        response = requests.get(f"{RAG_AGENT_URL}/health", timeout=5)
        if response.status_code == 200:
            print(f"✅ RAG Agent: {response.json()}")
        else:
            print(f"❌ RAG Agent 응답 오류: {response.status_code}")
            all_healthy = False
    except Exception as e:
        print(f"❌ RAG Agent 연결 실패: {e}")
        print("   → 'python start_all_servers.py' 또는 'cd agents/rag-agent && python start_server.py'로 서버를 시작하세요.")
        all_healthy = False
    
    return all_healthy

def test_direct_place_agent(request_data):
    """Place Agent 직접 테스트"""
    print("\n🎯 Place Agent 직접 요청 테스트...")
    print("[Place Agent 요청 데이터]")
    print(json.dumps(request_data, ensure_ascii=False, indent=2))
    try:
        response = requests.post(
            f"{PLACE_AGENT_URL}/place-agent",
            json=request_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print("✅ Place Agent 직접 요청 성공!")
            print(f"   - Success: {result.get('success')}")
            print(f"   - Request ID: {result.get('request_id')}")
            if result.get('success'):
                locations = result.get('locations', [])
                print(f"   - 반환된 지역 수: {len(locations)}")
                for i, loc in enumerate(locations[:3], 1):  # 처음 3개만 출력
                    print(f"   {i}. {loc.get('area_name')} ({loc.get('coordinates', {}).get('latitude')}, {loc.get('coordinates', {}).get('longitude')})")
            print("[Place Agent 응답 요약]")
            print(json.dumps({k: v for k, v in result.items() if k != 'locations'}, ensure_ascii=False, indent=2))
            return True, result
        else:
            print(f"❌ Place Agent 오류: {response.text}")
            return False, None
    except Exception as e:
        print(f"❌ Place Agent 직접 요청 실패: {e}")
        return False, None

def test_direct_rag_agent(request_data):
    """RAG Agent 직접 테스트"""
    print("\n🎯 RAG Agent 직접 요청 테스트...")
    print("[RAG Agent 요청 데이터]")
    print(json.dumps(request_data, ensure_ascii=False, indent=2))
    try:
        response = requests.post(
            f"{RAG_AGENT_URL}/recommend-course",
            json=request_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print("✅ RAG Agent 직접 요청 성공!")
            print(f"   - Response keys: {list(result.keys())}")
            print("[RAG Agent 응답 전체]")
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return True, result
        else:
            print(f"❌ RAG Agent 오류: {response.text}")
            return False, None
    except Exception as e:
        print(f"❌ RAG Agent 직접 요청 실패: {e}")
        return False, None

def test_main_to_place_agent_flow(place_request_data):
    """
    Main → Place Agent 플로우 테스트
    Main Agent를 통해 Place Agent에 요청 전달
    """
    print("\n🔄 Main → Place Agent 플로우 테스트...")
    print("[Main Agent를 통한 Place Agent 요청]")
    
    try:
        # Main Agent의 place 요청 엔드포인트 사용
        response = requests.post(
            f"{MAIN_AGENT_URL}/place/request",
            json=place_request_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print("✅ Main → Place Agent 플로우 성공!")
            print(f"   - Success: {result.get('success')}")
            print(f"   - Request ID: {result.get('request_id')}")
            
            if result.get('success') and result.get('data'):
                data = result['data']
                locations = data.get('locations', [])
                print(f"   - 반환된 지역 수: {len(locations)}")
                for i, loc in enumerate(locations[:3], 1):
                    print(f"   {i}. {loc.get('area_name')} ({loc.get('coordinates', {}).get('latitude')}, {loc.get('coordinates', {}).get('longitude')})")
            
            print("[Main → Place Agent 응답 전체]")
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return True, result
        else:
            print(f"❌ Main → Place Agent 플로우 실패: {response.text}")
            return False, None
            
    except Exception as e:
        print(f"❌ Main → Place Agent 플로우 오류: {e}")
        return False, None

def test_main_to_rag_agent_flow(rag_request_data):
    """
    Main → RAG Agent 플로우 테스트
    Main Agent를 통해 RAG Agent에 요청 전달
    """
    print("\n🔄 Main → RAG Agent 플로우 테스트...")
    print("[Main Agent를 통한 RAG Agent 요청]")
    
    try:
        # Main Agent의 course 요청 엔드포인트 사용
        response = requests.post(
            f"{MAIN_AGENT_URL}/course/request",
            json=rag_request_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print("✅ Main → RAG Agent 플로우 성공!")
            print(f"   - Success: {result.get('success')}")
            print(f"   - Message: {result.get('message')}")
            
            if result.get('success') and result.get('data'):
                data = result['data']
                print(f"   - Response keys: {list(data.keys())}")
                # 코스 정보가 있다면 출력
                if 'course' in data:
                    course = data['course']
                    print(f"   - Course places: {len(course.get('places', []))}")
                    print(f"   - Total distance: {course.get('total_distance', 'N/A')}")
            
            print("[Main → RAG Agent 응답 전체]")
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return True, result
        else:
            print(f"❌ Main → RAG Agent 플로우 실패: {response.text}")
            return False, None
            
    except Exception as e:
        print(f"❌ Main → RAG Agent 플로우 오류: {e}")
        return False, None

def build_rag_request_from_place_response_using_existing_function(place_response, place_request_data):
    """
    기존 main-agent의 build_rag_agent_json 함수를 사용하여 RAG Agent 요청 생성
    """
    print("\n🔧 기존 main-agent 함수를 사용하여 RAG Agent 요청 생성...")
    
    try:
        # Place Agent 응답에서 필요한 정보 추출
        if not place_response.get('success') or not place_response.get('data'):
            print("❌ Place Agent 응답이 성공적이지 않습니다.")
            return None
        
        place_data = place_response['data']
        locations = place_data.get('locations', [])
        
        if not locations:
            print("❌ Place Agent 응답에 지역 정보가 없습니다.")
            return None
        
        # Place Agent 요청에서 프로필 정보 추출
        user_context = place_request_data.get('user_context', {})
        demographics = user_context.get('demographics', {})
        requirements = user_context.get('requirements', {})
        
        # 프로필 정보 구성
        profile = {
            "age": demographics.get('age'),
            "mbti": demographics.get('mbti'),
            "relationship_stage": demographics.get('relationship_stage'),
            "atmosphere": user_context.get('preferences', [None])[0] if user_context.get('preferences') else None,
            "budget": requirements.get('budget_level'),
            "time_slot": requirements.get('time_preference')
        }
        
        # 위치 요청 정보 구성
        location_request = place_request_data.get('location_request', {})
        
        # OpenAI API 키 가져오기
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            print("❌ OpenAI API 키가 설정되지 않았습니다.")
            return None
        
        # 기존 main-agent 함수 사용
        rag_request = build_rag_agent_json(
            place_response=place_data,
            profile=profile,
            location_request=location_request,
            openai_api_key=openai_api_key
        )
        
        print("✅ 기존 main-agent 함수로 RAG Agent 요청 생성 완료!")
        print(f"   - 지역 수: {len(locations)}")
        print(f"   - 검색 타겟: {len(rag_request.get('search_targets', []))}")
        print(f"   - 사용자 나이: {profile.get('age')}")
        print(f"   - 분위기: {profile.get('atmosphere')}")
        
        return rag_request
        
    except Exception as e:
        print(f"❌ RAG Agent 요청 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_comprehensive_a2a_flow(place_request_data):
    """
    전체 A2A 플로우 테스트
    1. Main → Place Agent (장소 추천)
    2. Place Agent → Main (장소 결과 반환)
    3. Main → RAG Agent (최종 코스 생성)
    4. RAG Agent → Main (최종 코스 반환)
    """
    print("\n🎯 전체 A2A 플로우 테스트 시작...")
    print("=" * 60)
    
    # Step 1: Main → Place Agent 플로우 테스트
    print("\n📍 STEP 1: Main → Place Agent 플로우")
    main_place_success, main_place_result = test_main_to_place_agent_flow(place_request_data)
    
    if not main_place_success:
        print("❌ Main → Place Agent 플로우 실패 - 전체 플로우 중단")
        return False
    
    # Step 2: Place Agent 직접 테스트 (비교용)
    print("\n📍 STEP 2: Place Agent 직접 테스트 (비교용)")
    direct_place_success, direct_place_result = test_direct_place_agent(place_request_data)
    
    # Step 3: 기존 main-agent 함수를 사용하여 RAG Agent 요청 생성
    print("\n🔧 STEP 3: 기존 main-agent 함수를 사용하여 RAG Agent 요청 생성")
    rag_request_data = build_rag_request_from_place_response_using_existing_function(main_place_result, place_request_data)
    
    if not rag_request_data:
        print("❌ RAG Agent 요청 생성 실패 - 전체 플로우 중단")
        return False
    
    # Step 4: Main → RAG Agent 플로우 테스트
    print("\n🗓️ STEP 4: Main → RAG Agent 플로우")
    main_rag_success, main_rag_result = test_main_to_rag_agent_flow(rag_request_data)
    
    if not main_rag_success:
        print("❌ Main → RAG Agent 플로우 실패 - 전체 플로우 중단")
        return False
    
    # Step 5: RAG Agent 직접 테스트 (비교용)
    print("\n🗓️ STEP 5: RAG Agent 직접 테스트 (비교용)")
    direct_rag_success, direct_rag_result = test_direct_rag_agent(rag_request_data)
    
    # Step 6: 결과 통합 및 검증
    print("\n✅ STEP 6: 결과 통합 및 검증")
    print("=" * 60)
    print("📋 전체 플로우 결과:")
    print(f"   - Main → Place Agent 성공: {main_place_success}")
    print(f"   - Place Agent (직접) 성공: {direct_place_success}")
    print(f"   - Main → RAG Agent 성공: {main_rag_success}")
    print(f"   - RAG Agent (직접) 성공: {direct_rag_success}")
    
    # 상세 결과 분석
    if main_place_result and main_place_result.get('success'):
        data = main_place_result.get('data', {})
        if data.get('locations'):
            print(f"   - Main을 통한 장소 추천 수: {len(data['locations'])}")
    
    if direct_place_result and direct_place_result.get('success'):
        print(f"   - 직접 장소 추천 수: {len(direct_place_result.get('locations', []))}")
    
    if main_rag_result and main_rag_result.get('success'):
        print(f"   - Main을 통한 코스 생성 성공: {main_rag_result.get('message', 'N/A')}")
    
    if direct_rag_result:
        print(f"   - 직접 코스 생성 결과: {list(direct_rag_result.keys())}")
    
    # 성공률 계산
    success_count = sum([main_place_success, main_rag_success])
    total_tests = 2
    success_rate = (success_count / total_tests) * 100
    
    print(f"\n📊 A2A 플로우 성공률: {success_rate:.1f}% ({success_count}/{total_tests})")
    
    if success_rate == 100:
        print("🎉 전체 A2A 플로우 테스트 완료! 모든 통신이 성공했습니다.")
        return True
    else:
        print("⚠️ 일부 A2A 플로우에서 문제가 발생했습니다. 로그를 확인하세요.")
        return False

def main():
    """메인 테스트 함수"""
    print("🚀 전체 A2A 통신 테스트 시작")
    print("새로운 포트 구성:")
    print(f"  Main Agent: {MAIN_AGENT_URL}")
    print(f"  Place Agent: {PLACE_AGENT_URL}")
    print(f"  RAG Agent: {RAG_AGENT_URL}")
    print("=" * 60)
    
    # 1. 테스트 데이터 로드
    print("\n📂 테스트 데이터 로드...")
    place_request_data = load_place_request()
    
    if not place_request_data:
        print("❌ Place Agent 요청 데이터 로드 실패")
        return
    
    # 2. 서버 상태 확인
    print("\n🔍 서버 상태 확인...")
    if not check_servers():
        print("❌ 일부 서버가 실행되지 않음 - 모든 서버를 시작하세요")
        return
    
    # 3. 테스트 모드 선택
    print("\n" + "=" * 60)
    print("테스트 모드를 선택하세요:")
    print("1. 개별 에이전트 테스트 (직접 호출)")
    print("2. Main → Place Agent 플로우 테스트")
    print("3. Main → RAG Agent 플로우 테스트")
    print("4. 전체 A2A 플로우 테스트 (Main → Place → Main → RAG)")
    print("5. 종합 테스트 (모든 테스트 실행)")
    
    try:
        choice = input("선택 (1/2/3/4/5): ").strip()
    except KeyboardInterrupt:
        print("\n❌ 사용자가 테스트를 중단했습니다.")
        return
    
    if choice == "1":
        # 개별 에이전트 테스트 (직접 호출)
        print("\n📋 개별 에이전트 테스트 (직접 호출)")
        
        # Place Agent 테스트
        print("\n" + "=" * 60)
        place_test = input("Place Agent 직접 테스트를 진행하시겠습니까? (y/N): ").lower()
        if place_test == 'y':
            test_direct_place_agent(place_request_data)
        
        # RAG Agent 테스트 (샘플 데이터 사용)
        print("\n" + "=" * 60)
        rag_test = input("RAG Agent 직접 테스트를 진행하시겠습니까? (y/N): ").lower()
        if rag_test == 'y':
            # 샘플 RAG 요청 데이터 생성
            sample_rag_request = {
                "request_id": "test-rag-001",
                "timestamp": datetime.datetime.now().isoformat(),
                "search_targets": [
                    {
                        "sequence": 1,
                        "category": "음식점",
                        "location": {
                            "area_name": "이촌동",
                            "coordinates": {"latitude": 37.5225, "longitude": 126.9723}
                        },
                        "semantic_query": "맛있는 음식점을 찾고 싶어요."
                    }
                ],
                "user_context": place_request_data.get('user_context', {}),
                "course_planning": {
                    "optimization_goals": ["사용자 선호와 동선 최적화"],
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
            test_direct_rag_agent(sample_rag_request)
            
    elif choice == "2":
        # Main → Place Agent 플로우 테스트
        print("\n🔄 Main → Place Agent 플로우 테스트")
        test_main_to_place_agent_flow(place_request_data)
        
    elif choice == "3":
        # Main → RAG Agent 플로우 테스트
        print("\n🔄 Main → RAG Agent 플로우 테스트")
        # 샘플 RAG 요청 데이터 생성
        sample_rag_request = {
            "request_id": "test-rag-002",
            "timestamp": datetime.datetime.now().isoformat(),
            "search_targets": [
                {
                    "sequence": 1,
                    "category": "음식점",
                    "location": {
                        "area_name": "이촌동",
                        "coordinates": {"latitude": 37.5225, "longitude": 126.9723}
                    },
                    "semantic_query": "맛있는 음식점을 찾고 싶어요."
                }
            ],
            "user_context": place_request_data.get('user_context', {}),
            "course_planning": {
                "optimization_goals": ["사용자 선호와 동선 최적화"],
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
        test_main_to_rag_agent_flow(sample_rag_request)
        
    elif choice == "4":
        # 전체 A2A 플로우 테스트
        print("\n🎯 전체 A2A 플로우 테스트")
        test_comprehensive_a2a_flow(place_request_data)
        
    elif choice == "5":
        # 종합 테스트 (모든 테스트 실행)
        print("\n🎯 종합 테스트 실행")
        
        # 1. 개별 에이전트 직접 테스트
        print("\n📋 1. 개별 에이전트 직접 테스트")
        print("=" * 60)
        test_direct_place_agent(place_request_data)
        time.sleep(2)
        
        # 샘플 RAG 요청 데이터 생성
        sample_rag_request = {
            "request_id": "test-rag-003",
            "timestamp": datetime.datetime.now().isoformat(),
            "search_targets": [
                {
                    "sequence": 1,
                    "category": "음식점",
                    "location": {
                        "area_name": "이촌동",
                        "coordinates": {"latitude": 37.5225, "longitude": 126.9723}
                    },
                    "semantic_query": "맛있는 음식점을 찾고 싶어요."
                }
            ],
            "user_context": place_request_data.get('user_context', {}),
            "course_planning": {
                "optimization_goals": ["사용자 선호와 동선 최적화"],
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
        test_direct_rag_agent(sample_rag_request)
        
        # 2. Main → Place Agent 플로우 테스트
        print("\n🔄 2. Main → Place Agent 플로우 테스트")
        print("=" * 60)
        test_main_to_place_agent_flow(place_request_data)
        time.sleep(2)
        
        # 3. Main → RAG Agent 플로우 테스트
        print("\n🔄 3. Main → RAG Agent 플로우 테스트")
        print("=" * 60)
        test_main_to_rag_agent_flow(sample_rag_request)
        time.sleep(2)
        
        # 4. 전체 A2A 플로우 테스트
        print("\n🎯 4. 전체 A2A 플로우 테스트")
        print("=" * 60)
        test_comprehensive_a2a_flow(place_request_data)
        
    else:
        print("❌ 잘못된 선택입니다. 1, 2, 3, 4, 5 중에서 선택하세요.")
        return
    
    print("\n" + "=" * 60)
    print("✅ 테스트 완료!")
    print("\n📊 결과 분석:")
    print("   1. 모든 에이전트의 응답 상태 코드 확인")
    print("   2. A2A 통신 플로우 연결 상태 검증")
    print("   3. Main Agent를 통한 요청과 직접 요청 결과 비교")
    print("   4. 응답 데이터 구조 및 내용 검증")
    print("\n💡 추가 확인사항:")
    print("   - 각 에이전트 서버 로그에서 요청/응답 기록 확인")
    print("   - 네트워크 지연시간 및 타임아웃 설정 검토")
    print("   - 에러 발생 시 에러 메시지 상세 분석")
    print("\n🔗 서버 포트 정보:")
    print(f"   - Main Agent: {MAIN_AGENT_URL}")
    print(f"   - Place Agent: {PLACE_AGENT_URL}")
    print(f"   - RAG Agent: {RAG_AGENT_URL}")

if __name__ == "__main__":
    main()