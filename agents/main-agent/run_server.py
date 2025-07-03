#!/usr/bin/env python3
"""
Main Agent Server 실행 스크립트
"""

import sys
import os
import subprocess
from pathlib import Path

def main():
    """Main Agent 서버 실행"""
    
    # 현재 디렉토리가 main-agent인지 확인
    current_dir = Path.cwd()
    if current_dir.name != "main-agent":
        print("❌ main-agent 디렉토리에서 실행해주세요.")
        sys.exit(1)
    
    # .env 파일 확인
    env_file = current_dir / ".env"
    if not env_file.exists():
        print("⚠️  .env 파일이 없습니다. OPENAI_API_KEY를 설정해주세요.")
        print("   예: echo 'OPENAI_API_KEY=your_key_here' > .env")
    
    # 포트 설정
    port = os.getenv("MAIN_AGENT_PORT", "8001")
    
    # 서버 실행
    print("🚀 Main Agent 서버를 시작합니다...")
    print("   - 서비스: Main Agent API")
    print(f"   - 포트: {port}")
    print("   - API 문서: http://localhost:{port}/docs")
    print("   - 헬스 체크: http://localhost:{port}/api/v1/health")
    print()
    
    try:
        # uvicorn으로 서버 실행
        subprocess.run([
            sys.executable, "-m", "uvicorn",
            "server:app",
            "--host", "0.0.0.0",
            "--port", port,
            "--reload",
            "--log-level", "info"
        ])
    except KeyboardInterrupt:
        print("\n🛑 서버를 종료합니다.")
    except Exception as e:
        print(f"❌ 서버 실행 중 오류 발생: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()