#!/usr/bin/env python3
"""
완전한 플로우 테스트 스크립트
서버 시작 → 웹 채팅 테스트를 위한 올인원 스크립트
"""

import subprocess
import time
import os
import sys
import signal
from pathlib import Path

def start_all_servers():
    """모든 서버 시작"""
    print("🚀 모든 서버 시작 중...")
    
    # start_all_servers.py 실행
    try:
        process = subprocess.Popen(
            [sys.executable, "start_all_servers.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        
        print("✅ 서버 시작 프로세스 실행됨")
        print("   PID:", process.pid)
        print("   서버가 준비될 때까지 잠시 기다려주세요...")
        
        return process
    except Exception as e:
        print(f"❌ 서버 시작 실패: {e}")
        return None

def start_chat_client():
    """웹 채팅 클라이언트 시작"""
    print("\n💬 웹 채팅 클라이언트 시작 중...")
    
    try:
        # 별도 터미널에서 채팅 클라이언트 실행
        if sys.platform == "darwin":  # macOS
            subprocess.run([
                "osascript", "-e", 
                f'tell app "Terminal" to do script "cd {os.getcwd()}/agents/main-agent && python web_chat_client.py"'
            ])
        elif sys.platform == "linux":  # Linux
            subprocess.run([
                "gnome-terminal", "--", "bash", "-c",
                f"cd {os.getcwd()}/agents/main-agent && python web_chat_client.py; read"
            ])
        else:  # Windows
            subprocess.run([
                "cmd", "/c", "start", "cmd", "/k",
                f"cd /d {os.getcwd()}\\agents\\main-agent && python web_chat_client.py"
            ])
            
        print("✅ 채팅 클라이언트가 새 터미널에서 시작되었습니다")
        
    except Exception as e:
        print(f"❌ 채팅 클라이언트 시작 실패: {e}")
        print("   수동으로 실행하세요:")
        print(f"   cd agents/main-agent && python web_chat_client.py")

def main():
    """메인 실행 함수"""
    print("🎯 완전한 플로우 테스트")
    print("=" * 50)
    print("이 스크립트는 다음을 수행합니다:")
    print("1. 모든 에이전트 서버 시작 (Main, Place, RAG)")
    print("2. 웹 채팅 클라이언트 실행")
    print("3. 완전한 채팅 → Place → RAG 플로우 테스트")
    print("=" * 50)
    
    # 현재 디렉토리 확인
    current_dir = Path.cwd()
    if not (current_dir / "start_all_servers.py").exists():
        print("❌ start_all_servers.py 파일을 찾을 수 없습니다.")
        print("   프로젝트 루트 디렉토리에서 실행하세요.")
        return
    
    try:
        # 1. 서버 시작
        server_process = start_all_servers()
        if not server_process:
            return
        
        # 서버 준비 대기
        print("\n⏳ 서버 준비 대기 중 (30초)...")
        time.sleep(30)
        
        # 2. 채팅 클라이언트 시작
        start_chat_client()
        
        # 3. 사용자 안내
        print("\n" + "=" * 50)
        print("🎉 설정 완료!")
        print("=" * 50)
        print("📋 다음 단계:")
        print("1. 새로 열린 터미널에서 채팅 클라이언트가 실행됩니다")
        print("2. 채팅 클라이언트에서 다음과 같은 메시지를 입력해보세요:")
        print('   "29살 INTP 연인과 이촌동에서 로맨틱한 밤 데이트 3곳 추천해줘"')
        print("3. 백엔드에서 자동으로 Place Agent → RAG Agent가 실행됩니다")
        print("4. 최종 결과가 채팅 터미널에 출력됩니다")
        print("\n🔗 서버 URL:")
        print("   - Main Agent: http://localhost:8000/docs")
        print("   - Place Agent: http://localhost:8001/docs")
        print("   - RAG Agent: http://localhost:8002/docs")
        print("\n⏹️ 종료: Ctrl+C")
        print("=" * 50)
        
        # 서버 프로세스 대기
        try:
            while True:
                if server_process.poll() is not None:
                    print("\n⚠️ 서버 프로세스가 종료되었습니다.")
                    break
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n🛑 종료 요청 받음...")
            
        # 정리
        print("🧹 정리 중...")
        if server_process and server_process.poll() is None:
            server_process.terminate()
            try:
                server_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server_process.kill()
        
        print("✅ 정리 완료")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
    except KeyboardInterrupt:
        print("\n\n👋 사용자가 종료했습니다.")

if __name__ == "__main__":
    main()