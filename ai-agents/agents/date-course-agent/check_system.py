#!/usr/bin/env python3
"""
서버 상태 확인 및 디버깅 스크립트
"""

import sys
import os
import asyncio
import httpx

# 프로젝트 루트를 Python 경로에 추가
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

async def check_server_status():
    """서버 상태 확인"""
    print("🔍 서버 상태를 확인합니다...")
    
    try:
        async with httpx.AsyncClient() as client:
            # 헬스 체크 요청
            response = await client.get("http://localhost:8000/health", timeout=5.0)
            
            if response.status_code == 200:
                result = response.json()
                print("✅ 서버가 정상적으로 실행 중입니다!")
                print(f"   상태: {result.get('status', 'unknown')}")
                print(f"   서비스: {result.get('service', 'unknown')}")
                return True
            else:
                print(f"❌ 서버가 비정상 상태입니다 (HTTP {response.status_code})")
                return False
                
    except httpx.ConnectError:
        print("❌ 서버에 연결할 수 없습니다. 서버가 실행되지 않았을 가능성이 높습니다.")
        return False
    except httpx.TimeoutException:
        print("❌ 서버 응답 시간이 초과되었습니다.")
        return False
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")
        return False

def check_dependencies():
    """의존성 패키지 확인"""
    print("\n🔍 필수 패키지를 확인합니다...")
    
    required_packages = [
        'fastapi',
        'uvicorn',
        'httpx',
        'pydantic',
        'loguru',
        'aiohttp'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"   ✅ {package}")
        except ImportError:
            print(f"   ❌ {package} (설치 필요)")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n❌ 누락된 패키지: {', '.join(missing_packages)}")
        print("   다음 명령어로 설치하세요:")
        print(f"   pip install {' '.join(missing_packages)}")
        return False
    else:
        print("\n✅ 모든 필수 패키지가 설치되어 있습니다.")
        return True

def check_src_modules():
    """src 모듈 구조 확인"""
    print("\n🔍 프로젝트 모듈을 확인합니다...")
    
    try:
        from src.main import DateCourseAgent
        print("   ✅ src.main.DateCourseAgent")
        
        from src.utils.data_validator import DataValidator
        print("   ✅ src.utils.data_validator.DataValidator")
        
        from src.models.request_models import DateCourseRequestModel
        print("   ✅ src.models.request_models.DateCourseRequestModel")
        
        print("\n✅ 모든 필수 모듈을 성공적으로 로드했습니다.")
        return True
        
    except ImportError as e:
        print(f"\n❌ 모듈 로드 실패: {e}")
        return False

async def main():
    """메인 함수"""
    print("=" * 50)
    print("🚀 Date Course Agent 시스템 진단")
    print("=" * 50)
    
    # 1. 의존성 확인
    deps_ok = check_dependencies()
    
    # 2. 모듈 구조 확인
    modules_ok = check_src_modules()
    
    # 3. 서버 상태 확인
    server_ok = await check_server_status()
    
    # 4. 결과 요약
    print("\n" + "=" * 50)
    print("📊 진단 결과 요약")
    print("=" * 50)
    print(f"의존성 패키지: {'✅ OK' if deps_ok else '❌ 문제'}")
    print(f"프로젝트 모듈: {'✅ OK' if modules_ok else '❌ 문제'}")
    print(f"서버 상태: {'✅ 실행 중' if server_ok else '❌ 미실행'}")
    
    if not server_ok:
        print("\n💡 서버 시작 방법:")
        print("   python start_server.py")
        print("   또는")
        print("   python -m uvicorn src.main:app --host 0.0.0.0 --port 8000")

if __name__ == "__main__":
    asyncio.run(main())
