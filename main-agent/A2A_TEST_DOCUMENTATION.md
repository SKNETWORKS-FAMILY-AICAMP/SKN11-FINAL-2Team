# A2A 통신 테스트 가이드

## 개요
`test_a2a.py` 파일은 전체 에이전트 간 통신 플로우를 테스트하는 스크립트입니다.

## 테스트 플로우
1. **Main Agent** → **Place Agent** (장소 추천)
2. **Place Agent** → **Main Agent** (장소 결과 반환)
3. **Main Agent** → **Date-Course Agent** (최종 코스 생성)
4. **Date-Course Agent** → **Main Agent** (최종 코스 반환)

## 필요한 서버들
- **Main Agent**: http://localhost:8001
- **Place Agent**: http://localhost:8002
- **Date-Course Agent**: http://localhost:8000

## 사용법

### 1. 서버 시작
각 터미널에서 다음 명령어를 실행하여 서버들을 시작합니다:

```bash
# Terminal 1: Main Agent
cd agents/main-agent
python run_server.py

# Terminal 2: Place Agent
cd agents/place_agent
python start_server.py

# Terminal 3: Date-Course Agent
cd agents/date-course-agent
python start_server.py
```

### 2. 테스트 실행
```bash
cd agents/main-agent
python test_a2a.py
```

### 3. 테스트 모드 선택
스크립트 실행 시 다음 3가지 모드 중 선택할 수 있습니다:

1. **개별 에이전트 테스트**: 각 에이전트를 개별적으로 테스트
2. **전체 A2A 플로우 테스트**: 전체 통신 플로우를 순차적으로 테스트
3. **전체 테스트**: 개별 테스트 + 플로우 테스트

## 테스트 파일 구조

### 요청 데이터 파일
- `requests/rag/rag_agent_request_from_chat.json`: Date-Course Agent 요청 데이터
- `requests/place/place_agent_request_from_chat.json`: Place Agent 요청 데이터

### 주요 함수들

#### `check_servers()`
모든 서버의 상태를 확인합니다.

#### `test_direct_place_agent(request_data)`
Place Agent를 직접 테스트합니다.

#### `test_direct_date_course_agent(request_data)`
Date-Course Agent를 직접 테스트합니다.

#### `test_a2a_communication(request_data)`
Main Agent를 통한 A2A 통신을 테스트합니다.

#### `test_comprehensive_a2a_flow(place_request_data, date_course_request_data)`
전체 A2A 플로우를 테스트합니다.

## 예상 결과

### 성공적인 테스트 결과
```
🚀 전체 A2A 통신 테스트 시작
Main Agent: http://localhost:8001
Place Agent: http://localhost:8002
Date-Course Agent: http://localhost:8000

✅ Main Agent: {'status': 'healthy', 'service': 'main-agent', 'port': 8001}
✅ Place Agent: {'status': 'healthy', 'service': 'place-agent', 'port': 8002}
✅ Date-Course Agent: {'status': 'healthy', 'service': 'date-course-agent', 'port': 8000}

🎉 전체 A2A 플로우 테스트 완료!
```

### 실패 시 확인사항
1. 모든 서버가 정상적으로 실행되고 있는지 확인
2. 요청 데이터 파일이 존재하는지 확인
3. 네트워크 연결 상태 확인
4. 각 에이전트의 로그 파일 확인

## 로그 확인
테스트 완료 후 다음 위치에서 로그를 확인할 수 있습니다:
- Main Agent: `agents/main-agent/logs/`
- Place Agent: `agents/place_agent/logs/`
- Date-Course Agent: `agents/date-course-agent/logs/`

## 문제 해결

### 서버 연결 실패
- 해당 서버가 실행 중인지 확인
- 포트 번호가 올바른지 확인
- 방화벽 설정 확인

### 요청 데이터 파일 누락
- `requests/rag/rag_agent_request_from_chat.json` 파일 존재 확인
- `requests/place/place_agent_request_from_chat.json` 파일 존재 확인

### 응답 데이터 오류
- 각 에이전트의 로그 파일 확인
- 요청 데이터 형식 확인
- API 엔드포인트 확인

## 추가 기능

### 커스텀 요청 데이터 사용
테스트 파일의 REQUEST_FILE 또는 PLACE_REQUEST_FILE 변수를 수정하여 다른 요청 데이터를 사용할 수 있습니다.

### 타임아웃 설정
각 요청의 타임아웃은 30초로 설정되어 있으며, 필요에 따라 조정할 수 있습니다.

### 디버깅 모드
더 자세한 로그를 원하는 경우 각 함수의 출력 부분을 수정하여 더 많은 정보를 출력할 수 있습니다.