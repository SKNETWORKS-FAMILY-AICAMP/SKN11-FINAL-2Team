# A2A 통신 테스트 가이드

## 🚀 테스트 실행 순서

### 1. 서버 시작 (권장: 한 번에 실행)

**Option A: 모든 서버 한 번에 시작 (권장)**
```bash
# 프로젝트 루트에서 실행
python start_all_servers.py
```

**Option B: 개별 서버 시작**
```bash
# 터미널 1 - Main Agent (포트 8000)
cd agents/main-agent
python run_server.py

# 터미널 2 - Place Agent (포트 8001) 
cd agents/place_agent
python start_server.py

# 터미널 3 - Date-Course Agent (포트 8002)
cd agents/date-course-agent  
python start_server.py
```

### 2. A2A 테스트 실행

```bash
# 터미널 4 - 테스트 실행
cd agents/main-agent
python test_a2a.py
```

## 📋 테스트 모드

### 1. 개별 에이전트 테스트 (직접 호출)
- Place Agent 직접 테스트
- Date-Course Agent 직접 테스트
- 각 에이전트의 기본 기능 검증

### 2. Main → Place Agent 플로우 테스트
- Main Agent를 통한 Place Agent 호출
- 응답 데이터 구조 검증
- 통신 상태 확인

### 3. Main → Date-Course Agent 플로우 테스트
- Main Agent를 통한 Date-Course Agent 호출
- 코스 생성 결과 검증
- A2A 통신 성공률 확인

### 4. 전체 A2A 플로우 테스트
- Main → Place → Main → Date-Course 전체 플로우
- 각 단계별 성공/실패 분석
- 직접 호출과 A2A 통신 결과 비교

### 5. 종합 테스트
- 모든 테스트 자동 실행
- 전체 시스템 안정성 검증
- 성능 및 연결성 종합 분석

## 📁 테스트 데이터

### Place Agent 요청 데이터
```json
파일: requests/place/place_agent_request_from_chat.json
- request_type: "proximity_based"
- reference_areas: ["남산"]
- place_count: 3
- user_context: ISTP, 친구, 조용한 분위기
```

### Date-Course Agent 요청 데이터
```json
파일: requests/rag/rag_agent_request_from_chat.json
- search_targets: 3개 장소 (이촌동, 한남동, 후암동)
- user_context: ENFP, 연인, 조용한 분위기
- course_planning: 최적화 목표 및 제약사항
```

## 🔍 확인사항

### ✅ 성공 지표
- 모든 서버 헬스체크 통과 (200 상태)
- A2A 통신 응답 시간 < 30초
- 응답 데이터 구조 정확성
- 에러 없는 전체 플로우 완료

### ❌ 실패 대응
- 서버 연결 실패: 각 서버 실행 상태 확인
- 타임아웃 에러: 네트워크 및 서버 부하 확인
- 응답 구조 오류: API 스펙 및 데이터 형식 검토
- A2A 통신 실패: 포트 충돌 및 방화벽 설정 확인

## 📊 결과 분석

### 개별 테스트 결과
- Place Agent: 지역 추천 결과 수 및 좌표 정확성
- Date-Course Agent: 코스 생성 성공률 및 최적화 결과

### A2A 통신 결과  
- Main → Place Agent: 통신 성공률 및 응답 시간
- Main → Date-Course Agent: 데이터 전달 정확성
- 전체 플로우: 각 단계별 성공/실패 분석

### 성능 지표
- 응답 시간: 각 에이전트별 평균 응답 시간
- 성공률: A2A 통신 성공률 (목표: 100%)
- 데이터 정합성: 요청/응답 데이터 일치율

## 🐛 트러블슈팅

### 포트 충돌
```bash
# 포트 사용 확인
lsof -i :8000
lsof -i :8001  
lsof -i :8002

# 프로세스 종료
kill -9 <PID>
```

### 환경 변수 설정
```bash
# OpenAI API 키 확인
echo $OPENAI_API_KEY

# 각 에이전트 .env 파일 확인
cat agents/main-agent/.env
cat agents/place_agent/.env
cat agents/date-course-agent/.env
```

### 로그 확인
```bash
# 각 에이전트 로그 확인
tail -f agents/main-agent/logs/app.log
tail -f agents/place_agent/logs/app.log  
tail -f agents/date-course-agent/logs/app.log
```