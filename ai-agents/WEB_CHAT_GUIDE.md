# 🌐 웹 채팅 플로우 테스트 가이드

## 📋 개요

이 가이드는 웹 채팅 인터페이스를 통해 **Main Agent → Place Agent → RAG Agent** 전체 플로우를 테스트하는 방법을 설명합니다.

### 🎯 테스트 플로우
```
사용자 채팅 메시지
    ↓
Main Agent (프로필 추출)
    ↓
Place Agent (장소 추천)  
    ↓
RAG Agent (코스 생성)
    ↓
최종 결과를 채팅으로 출력
```

## 🚀 빠른 시작

### Option 1: 올인원 스크립트 (권장)

```bash
# 프로젝트 루트에서 실행
python test_complete_flow.py
```

이 스크립트는 자동으로:
1. 모든 서버 시작 (Main, Place, RAG Agent)
2. 웹 채팅 클라이언트 실행
3. 테스트 가이드 제공

### Option 2: 수동 실행

**1단계: 서버 시작**
```bash
python start_all_servers.py
```

**2단계: 채팅 클라이언트 실행** (별도 터미널)
```bash
cd agents/main-agent
python web_chat_client.py
```

## 💬 채팅 테스트 시나리오

### 기본 시나리오
```
29살 INTP 연인과 이촌동에서 로맨틱한 밤 데이트 3곳 추천해줘
```

### 추가 시나리오들
```
25살 ENFP 커플이에요. 홍대에서 트렌디하고 힙한 저녁 데이트 코스 만들어주세요!

30살 ISFJ 친구들과 강남에서 조용하고 세련된 오후 모임 장소 추천해주세요

27살 ESTP 썸남과 성수동에서 힙한 분위기 카페 2곳 추천부탁해요
```

## 📊 예상 결과

### 성공적인 플로우 출력 예시
```
💬 사용자: 29살 INTP 연인과 이촌동에서 로맨틱한 밤 데이트 3곳 추천해줘
🤖 처리 중...
✅ 성공: 전체 플로우 완료

📋 프로필 추출: completed
   추출된 정보:
   • age: 29
   • mbti: INTP
   • relationship_stage: 연인
   • atmosphere: 로맨틱

📍 장소 추천: completed
   추천된 장소 수: 3
   1. 이촌동 (37.5225, 126.9723)
   2. 한남동 (37.5357, 127.0002)
   3. 후암동 (37.5509, 126.9727)

🗓️ 코스 생성: completed
   생성된 코스 장소 수: 3
   1. [음식점] 한강 뷰 레스토랑 (이촌동)
      💬 한강의 야경을 감상하며 연인과 프라이빗하게...
   2. [카페] 감성 카페 (한남동)
      💬 조용하고 고급스러운 분위기가 감도는...
   3. [술집] 루프탑 바 (후암동)
      💬 남산의 야경을 바라보며 여유로운...

💡 최종 추천:
데이트 코스가 성공적으로 생성되었습니다! 위의 코스 정보를 확인해보세요.

⏱️ 처리 시간: 45.2초
```

## 🛠️ 기술적 세부사항

### 새로 추가된 API 엔드포인트

**Main Agent 서버 (포트 8000)**
```http
POST /api/v1/chat/complete_flow
Content-Type: application/json

{
  "session_id": "chat_12345678",
  "user_message": "사용자 채팅 메시지",
  "timestamp": "2025-07-03T10:30:00"
}
```

### API 응답 구조
```json
{
  "success": true,
  "message": "전체 플로우 완료",
  "flow_results": {
    "profile_extraction": {
      "status": "completed",
      "extracted_info": { "age": 29, "mbti": "INTP", ... }
    },
    "place_agent": {
      "status": "completed", 
      "success": true,
      "data": { "locations": [...] }
    },
    "rag_agent": {
      "status": "completed",
      "success": true,
      "data": { "course": { "places": [...] } }
    }
  },
  "final_recommendation": "데이트 코스가 성공적으로 생성되었습니다!"
}
```

### 백엔드 플로우 처리

**1. 프로필 추출**
- 기존 `main_agent.py`의 `process_request_with_file_save()` 사용
- 채팅에서 나이, MBTI, 관계, 분위기, 지역 등 추출

**2. Place Agent 호출**
- 기존 `build_place_agent_json()` 함수로 요청 생성
- `POST http://localhost:8001/place-agent` API 호출

**3. RAG Agent 호출**
- 기존 `build_rag_agent_json()` 함수로 요청 생성
- `POST http://localhost:8002/recommend-course` API 호출

## 🧪 테스트 기능

### 웹 채팅 클라이언트 명령어
```
/info     - 세션 정보 조회
/history  - 대화 히스토리 보기
/clear    - 세션 초기화
/quit     - 종료
```

### 실행 모드
```
1. 대화형 채팅      - 실시간 채팅 테스트
2. 빠른 테스트      - 샘플 메시지로 자동 테스트
3. 연결 테스트만    - 서버 연결 확인만
```

## 🔍 트러블슈팅

### 일반적인 문제들

**1. 서버 연결 실패**
```bash
# 서버 상태 확인
curl http://localhost:8000/api/v1/health
curl http://localhost:8001/health
curl http://localhost:8002/health

# 포트 사용 확인
lsof -i :8000
lsof -i :8001
lsof -i :8002
```

**2. API 키 설정 문제**
```bash
# .env 파일 확인
cat agents/main-agent/.env
cat agents/place_agent/.env

# 환경변수 확인
echo $OPENAI_API_KEY
```

**3. 의존성 문제**
```bash
# 각 에이전트 디렉토리에서
pip install -r requirements.txt
```

**4. 플로우 타임아웃**
- 전체 플로우는 최대 120초 소요 가능
- 특히 RAG Agent 처리가 오래 걸릴 수 있음
- OpenAI API 응답 속도에 따라 달라짐

### 로그 확인
```bash
# 서버 로그 확인 (start_all_servers.py 실행 중)
# 터미널에서 각 에이전트별 로그 실시간 확인 가능

# 개별 서버 로그 (있는 경우)
tail -f agents/main-agent/logs/app.log
tail -f agents/place_agent/logs/app.log
tail -f agents/rag-agent/logs/app.log
```

## 📈 성능 지표

### 예상 처리 시간
- **프로필 추출**: 3-10초
- **Place Agent**: 5-15초  
- **RAG Agent**: 20-60초
- **전체 플로우**: 30-90초

### 성공 지표
- [ ] 모든 서버 헬스체크 통과
- [ ] 채팅 메시지에서 프로필 추출 성공
- [ ] Place Agent에서 3개 장소 추천 성공
- [ ] RAG Agent에서 완전한 코스 생성 성공
- [ ] 최종 결과가 채팅 터미널에 출력

## 🎯 고급 활용

### 커스텀 테스트 시나리오
웹 채팅 클라이언트에서 다양한 시나리오 테스트:

```python
# 다양한 MBTI 타입
"25살 ENFP 썸녀와 홍대에서..."
"32살 ISFJ 부부가 압구정에서..."

# 다양한 시간대
"점심시간에 강남에서..."
"새벽에 24시간 카페..."

# 다양한 예산
"2만원 이하로 건대에서..."
"20만원으로 압구정에서..."

# 다양한 교통수단
"지하철로 이동 가능한..."
"차로 접근하기 좋은..."
```

### 세션 관리
- 각 채팅은 고유한 세션 ID로 관리
- `/clear` 명령으로 세션 초기화 가능
- 대화 히스토리 추적 가능

---

**마지막 업데이트:** 2025-07-03  
**버전:** 1.0 (웹 채팅 플로우 테스트)