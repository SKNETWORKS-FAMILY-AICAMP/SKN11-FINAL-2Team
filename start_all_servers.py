#!/usr/bin/env python3
"""
모든 에이전트 서버를 한 번에 실행하는 스크립트
- Main Agent (포트 8000)
- Place Agent (포트 8001)  
- Date-Course Agent (포트 8002)
"""

import os
import sys
import time
import subprocess
import threading
import signal
from pathlib import Path

# 현재 스크립트의 디렉토리
SCRIPT_DIR = Path(__file__).parent.absolute()

# 각 에이전트 경로 및 설정
AGENTS = {
    "main-agent": {
        "path": SCRIPT_DIR / "agents" / "main-agent",
        "script": "run_server.py",
        "port": 8000,
        "name": "Main Agent"
    },
    "place-agent": {
        "path": SCRIPT_DIR / "agents" / "place_agent", 
        "script": "start_server.py",
        "port": 8001,
        "name": "Place Agent"
    },
    "date-course-agent": {
        "path": SCRIPT_DIR / "agents" / "date-course-agent",
        "script": "start_server.py", 
        "port": 8002,
        "name": "Date-Course Agent"
    }
}

# 실행 중인 프로세스들을 저장할 리스트
running_processes = []

def check_port_available(port):
    """포트가 사용 가능한지 확인"""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('localhost', port))
            return True
        except OSError:
            return False

def kill_port_process(port):
    """특정 포트를 사용하는 프로세스 종료"""
    try:
        if sys.platform == "darwin" or sys.platform == "linux":
            # macOS/Linux
            result = subprocess.run(['lsof', '-ti', f':{port}'], 
                                  capture_output=True, text=True)
            if result.stdout:
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    if pid:
                        subprocess.run(['kill', '-9', pid])
                        print(f"   ✅ 포트 {port} 프로세스 종료: PID {pid}")
        else:
            # Windows
            result = subprocess.run(['netstat', '-ano'], 
                                  capture_output=True, text=True)
            lines = result.stdout.split('\n')
            for line in lines:
                if f':{port}' in line and 'LISTENING' in line:
                    parts = line.split()
                    if len(parts) > 4:
                        pid = parts[-1]
                        subprocess.run(['taskkill', '/F', '/PID', pid])
                        print(f"   ✅ 포트 {port} 프로세스 종료: PID {pid}")
    except Exception as e:
        print(f"   ⚠️ 포트 {port} 정리 실패: {e}")

def start_agent(agent_key, agent_config):
    """개별 에이전트 서버 시작"""
    print(f"\n🚀 {agent_config['name']} 시작...")
    print(f"   - 경로: {agent_config['path']}")
    print(f"   - 포트: {agent_config['port']}")
    
    # 해당 디렉토리로 이동하여 서버 실행
    try:
        process = subprocess.Popen(
            [sys.executable, agent_config['script']],
            cwd=agent_config['path'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        running_processes.append({
            'name': agent_config['name'],
            'process': process,
            'port': agent_config['port']
        })
        
        print(f"   ✅ {agent_config['name']} 시작됨 (PID: {process.pid})")
        
        # 로그 출력을 위한 스레드
        def log_output():
            for line in iter(process.stdout.readline, ''):
                if line:
                    print(f"[{agent_config['name']}] {line.rstrip()}")
        
        log_thread = threading.Thread(target=log_output, daemon=True)
        log_thread.start()
        
        return process
        
    except Exception as e:
        print(f"   ❌ {agent_config['name']} 시작 실패: {e}")
        return None

def check_servers_health():
    """모든 서버의 헬스 체크"""
    import requests
    
    health_endpoints = {
        "Main Agent": "http://localhost:8000/api/health",
        "Place Agent": "http://localhost:8001/health", 
        "Date-Course Agent": "http://localhost:8002/health"
    }
    
    print("\n🔍 서버 헬스 체크...")
    all_healthy = True
    
    for name, url in health_endpoints.items():
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"   ✅ {name}: 정상")
            else:
                print(f"   ❌ {name}: HTTP {response.status_code}")
                all_healthy = False
        except Exception as e:
            print(f"   ❌ {name}: 연결 실패 ({e})")
            all_healthy = False
    
    return all_healthy

def cleanup_and_exit(signum=None, frame=None):
    """모든 프로세스 정리 후 종료"""
    print("\n\n🛑 서버 종료 중...")
    
    for proc_info in running_processes:
        try:
            proc_info['process'].terminate()
            proc_info['process'].wait(timeout=5)
            print(f"   ✅ {proc_info['name']} 종료됨")
        except subprocess.TimeoutExpired:
            proc_info['process'].kill()
            print(f"   ⚠️ {proc_info['name']} 강제 종료됨")
        except Exception as e:
            print(f"   ❌ {proc_info['name']} 종료 실패: {e}")
    
    print("🏁 모든 서버가 종료되었습니다.")
    sys.exit(0)

def main():
    """메인 실행 함수"""
    print("🎯 다중 에이전트 서버 시작")
    print("=" * 60)
    print("새로운 포트 구성:")
    print("  - Main Agent: 포트 8000")
    print("  - Place Agent: 포트 8001") 
    print("  - Date-Course Agent: 포트 8002")
    print("=" * 60)
    
    # 시그널 핸들러 등록 (Ctrl+C 처리)
    signal.signal(signal.SIGINT, cleanup_and_exit)
    signal.signal(signal.SIGTERM, cleanup_and_exit)
    
    # 1. 포트 정리
    print("\n📋 1단계: 포트 정리")
    for agent_key, agent_config in AGENTS.items():
        port = agent_config['port']
        if not check_port_available(port):
            print(f"   ⚠️ 포트 {port} 이미 사용 중 - 프로세스 정리")
            kill_port_process(port)
        else:
            print(f"   ✅ 포트 {port} 사용 가능")
    
    # 2. 각 에이전트 디렉토리 확인
    print("\n📋 2단계: 디렉토리 확인")
    for agent_key, agent_config in AGENTS.items():
        agent_path = agent_config['path']
        script_path = agent_path / agent_config['script']
        
        if not agent_path.exists():
            print(f"   ❌ {agent_config['name']} 디렉토리 없음: {agent_path}")
            return
        
        if not script_path.exists():
            print(f"   ❌ {agent_config['name']} 스크립트 없음: {script_path}")
            return
            
        print(f"   ✅ {agent_config['name']}: {agent_path}")
    
    # 3. 순차적으로 서버 시작
    print("\n📋 3단계: 서버 시작")
    failed_agents = []
    
    for agent_key, agent_config in AGENTS.items():
        process = start_agent(agent_key, agent_config)
        if process is None:
            failed_agents.append(agent_config['name'])
        else:
            # 서버가 시작되는 시간을 기다림
            time.sleep(3)
    
    if failed_agents:
        print(f"\n❌ 일부 에이전트 시작 실패: {', '.join(failed_agents)}")
        cleanup_and_exit()
        return
    
    # 4. 헬스 체크 대기
    print("\n📋 4단계: 서버 준비 대기")
    max_retries = 10
    retry_count = 0
    
    while retry_count < max_retries:
        time.sleep(2)
        retry_count += 1
        print(f"   🔄 헬스 체크 시도 {retry_count}/{max_retries}")
        
        if check_servers_health():
            print("\n🎉 모든 서버가 정상적으로 시작되었습니다!")
            break
    else:
        print(f"\n⚠️ {max_retries}회 시도 후에도 일부 서버가 준비되지 않았습니다.")
    
    # 5. 서버 정보 출력
    print("\n📊 서버 정보")
    print("=" * 60)
    print("🌐 API 엔드포인트:")
    print("  - Main Agent: http://localhost:8000/docs")
    print("  - Place Agent: http://localhost:8001/docs") 
    print("  - Date-Course Agent: http://localhost:8002/docs")
    print("\n💡 헬스 체크:")
    print("  - Main Agent: http://localhost:8000/api/health")
    print("  - Place Agent: http://localhost:8001/health")
    print("  - Date-Course Agent: http://localhost:8002/health")
    print("\n🧪 A2A 테스트 실행:")
    print("  cd agents/main-agent && python test_a2a.py")
    print("\n⏹️ 종료: Ctrl+C")
    print("=" * 60)
    
    # 6. 메인 루프 (서버들이 계속 실행되도록)
    try:
        while True:
            # 프로세스 상태 확인
            active_processes = []
            for proc_info in running_processes:
                if proc_info['process'].poll() is None:
                    active_processes.append(proc_info)
                else:
                    print(f"\n⚠️ {proc_info['name']} 프로세스가 종료되었습니다.")
            
            running_processes[:] = active_processes
            
            if not running_processes:
                print("\n❌ 모든 서버 프로세스가 종료되었습니다.")
                break
            
            time.sleep(5)  # 5초마다 상태 확인
            
    except KeyboardInterrupt:
        cleanup_and_exit()

if __name__ == "__main__":
    main()