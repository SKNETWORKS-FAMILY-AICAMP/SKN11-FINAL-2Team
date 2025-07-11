# 서버 실행 스크립트
# 프로젝트 루트에서 실행하여 모듈 경로 문제 해결

import sys
import os

# 프로젝트 루트를 Python 경로에 추가
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# 이제 src 모듈을 찾을 수 있음
from src.main import DateCourseAgent, main
import asyncio

if __name__ == "__main__":
    # 직접 실행 시 테스트 함수 호출
    asyncio.run(main())
