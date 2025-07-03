# 🚀 다중 에이전트 서버 설정 가이드

## 📋 변경사항 요약

### 🔄 포트 재배치
기존 포트에서 새로운 포트로 변경되었습니다:

| 에이전트 | 기존 포트 | 새 포트 | 변경 파일 |
|---------|----------|---------|-----------|
| Main Agent | 8001 | **8000** | `agents/main-agent/run_server.py` |
| Place Agent | 8002 | **8001** | `agents/place_agent/config/settings.py` |
| Date-Course Agent | 8000 | **8002** | `agents/date-course-agent/start_server.py` |

### 📁 새로 생성된 파일
1. **`start_all_servers.py`** - 모든 서버를 한 번에 실행하는 스크립트
2. **`SERVER_SETUP_GUIDE.md`** - 이 가이드 문서

### 🔧 수정된 파일
1. **`agents/main-agent/test_a2a.py`** - 새로운 포트 구성에 맞게 URL 업데이트
2. **`agents/main-agent/A2A_TEST_GUIDE.md`** - 테스트 가이드 업데이트

## 🚀 실행 방법

### Option 1: 모든 서버 한 번에 실행 (권장)

```bash
# 프로젝트 루트 디렉토리에서
python start_all_servers.py
```

**장점:**
- 한 번의 명령으로 모든 서버 실행
- 자동 포트 충돌 해결
- 통합 로그 출력
- Ctrl+C로 모든 서버 동시 종료
- 자동 헬스 체크

### Option 2: 개별 서버 실행

```bash
# 터미널 1 - Main Agent
cd agents/main-agent
python run_server.py

# 터미널 2 - Place Agent  
cd agents/place_agent
python start_server.py

# 터미널 3 - Date-Course Agent
cd agents/date-course-agent
python start_server.py
```

## 🔍 서버 상태 확인

### 헬스 체크 URL
```bash
curl http://localhost:8000/api/v1/health  # Main Agent
curl http://localhost:8001/health         # Place Agent  
curl http://localhost:8002/health         # Date-Course Agent
```

### API 문서 (Swagger)
- Main Agent: http://localhost:8000/docs
- Place Agent: http://localhost:8001/docs
- Date-Course Agent: http://localhost:8002/docs

## 🧪 A2A 테스트 실행

```bash
# 서버들이 모두 실행된 후
cd agents/main-agent
python test_a2a.py
```

**테스트 모드:**
1. 개별 에이전트 테스트 (직접 호출)
2. Main → Place Agent 플로우 테스트  
3. Main → Date-Course Agent 플로우 테스트
4. **전체 A2A 플로우 테스트** (추천)
5. 종합 테스트 (모든 테스트 실행)

## 🔧 트러블슈팅

### 포트 충돌 해결
```bash
# 사용 중인 포트 확인
lsof -i :8000
lsof -i :8001  
lsof -i :8002

# 프로세스 종료 (macOS/Linux)
kill -9 <PID>
```

### 환경 변수 확인
각 에이전트 디렉토리에 `.env` 파일이 있는지 확인:
```bash
# OpenAI API 키 설정 확인
cat agents/main-agent/.env
cat agents/place_agent/.env  
cat agents/date-course-agent/.env
```

필요시 `.env` 파일 생성:
```bash
echo "OPENAI_API_KEY=your_api_key_here" > agents/main-agent/.env
echo "OPENAI_API_KEY=your_api_key_here" > agents/place_agent/.env
```

### 의존성 설치 확인
```bash
# 각 에이전트 디렉토리에서
pip install -r requirements.txt
```

## 📊 서버 상태 모니터링

### 실시간 로그 확인
`start_all_servers.py` 실행 시 모든 에이전트의 로그가 통합 출력됩니다:
```
[Main Agent] 서버 시작...
[Place Agent] Place Agent 초기화 완료
[Date-Course Agent] FastAPI 서버 시작...
```

### 개별 로그 확인
```bash
# 각 에이전트 로그 (파일이 있는 경우)
tail -f agents/main-agent/logs/app.log
tail -f agents/place_agent/logs/app.log
tail -f agents/date-course-agent/logs/app.log
```

## 🎯 A2A 통신 플로우

새로운 포트 구성에서의 A2A 통신:

```
1. Main Agent (8000) → Place Agent (8001)
   요청: 장소 추천
   
2. Place Agent (8001) → Main Agent (8000)  
   응답: 추천 장소 목록
   
3. Main Agent (8000) → Date-Course Agent (8002)
   요청: 코스 생성
   
4. Date-Course Agent (8002) → Main Agent (8000)
   응답: 최종 데이트 코스
```

## ✅ 성공 지표

### 서버 시작 성공
- [ ] 모든 서버가 각각의 포트에서 정상 실행
- [ ] 헬스 체크 API 모두 200 응답
- [ ] 포트 충돌 없음

### A2A 통신 성공  
- [ ] Main → Place Agent 통신 성공
- [ ] Main → Date-Course Agent 통신 성공
- [ ] 전체 플로우 테스트 100% 성공률
- [ ] 응답 시간 30초 이내

## 🆘 문제 해결 연락처

문제 발생시 다음을 확인하세요:
1. 모든 의존성 패키지 설치 완료
2. OpenAI API 키 정상 설정
3. 포트 충돌 여부
4. 네트워크 방화벽 설정
5. Python 버전 호환성 (3.8+)

---

**마지막 업데이트:** 2025-07-03  
**버전:** 2.0 (포트 재배치 및 통합 실행 스크립트 추가)