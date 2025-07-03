# DayToCourse Main Agent - Minimal Prototype

🚀 **빠른 프로토타입**: 모든 로직이 단일 파일에 통합된 여행 및 학습 추천 에이전트  
🧠 **LangChain 메모리**: 대화 맥락을 기억하는 스마트 에이전트  
⚡ **즉시 실행**: 최소 설정으로 바로 테스트 가능

## 🎯 주요 기능

- **🗣️ 대화형 메모리**: LangChain을 사용한 세션별 대화 기록
- **🏛️ 장소 추천**: Seoul, Tokyo, Paris 등 주요 도시 명소
- **📚 학습 코스**: 언어, 문화, 요리 등 다양한 학습 기회
- **⚡ 빠른 분석**: 패턴 매칭 기반 즉시 분석
- **🤖 AI 강화**: OpenAI API로 맥락적 추천 개선

## 🚀 빠른 시작

### 설치 및 실행

```bash
# 의존성 설치
pip install -r requirements.txt

# 환경 변수 설정 (선택사항)
cp .env.example .env
# .env 파일에서 OPENAI_API_KEY 설정

# CLI 실행
python cli.py --help
```

### 기본 사용법

```bash
# 간단한 질문
python cli.py ask "I want to visit Seoul"

# 세션별 대화 (메모리 사용)
python cli.py ask "I want to visit Seoul" --session mysession
python cli.py ask "What about food there?" --session mysession

# 대화형 모드
python cli.py chat

# 데모 실행
python cli.py demo
```

## 💬 대화 예시

```bash
# 첫 번째 질문
$ python cli.py ask "I want to visit Seoul" --session travel

💡 Recommendations:
• Explore Seoul - perfect for your travel interests!
• Visit Gyeongbokgung Palace for Korean culture
• Try Korean BBQ in Myeongdong

# 같은 세션에서 후속 질문 (메모리 활용)
$ python cli.py ask "What about learning Korean?" --session travel

💭 Conversation Context:
User: I want to visit Seoul
Assistant: Found 3 places and 2 courses for Seoul...

💡 Recommendations:
• Take a Korean language course before your Seoul trip
• Korean Language for Beginners - perfect for travelers
• Learn Hangul writing system basics
```

## 🎮 CLI 명령어

### 기본 명령어

```bash
# 질문하기
python cli.py ask "여행 질문" --session 세션ID

# 대화형 모드 시작
python cli.py chat --session 세션ID

# 특정 도시 탐색
python cli.py explore Seoul --session 세션ID

# 예시 쿼리 보기
python cli.py examples
```

### 메모리 관리

```bash
# 메모리 상태 확인
python cli.py memory

# 특정 세션 정보
python cli.py memory --session 세션ID

# 세션 메모리 삭제
python cli.py clear 세션ID

# 시스템 상태 확인
python cli.py health
```

### 데모 및 테스트

```bash
# 대화 메모리 데모
python cli.py demo

# JSON 출력으로 결과 확인
python cli.py ask "질문" --json-output
```

## 🧠 메모리 기능

### LangChain 통합
- **ConversationBufferWindowMemory**: 최근 10개 대화 기억
- **세션별 관리**: 각 session_id마다 독립적인 메모리
- **맥락적 추천**: 이전 대화를 바탕으로 개선된 추천

### 메모리 사용 예시

```python
from main_agent import MainAgent, AgentRequest
import asyncio

async def memory_example():
    agent = MainAgent()
    
    # 첫 번째 대화
    request1 = AgentRequest(
        user_input="I want to visit Seoul",
        session_id="user123"
    )
    response1 = await agent.process_request(request1)
    
    # 두 번째 대화 (메모리 활용)
    request2 = AgentRequest(
        user_input="What about traditional food?",
        session_id="user123"  # 같은 세션
    )
    response2 = await agent.process_request(request2)
    
    # 대화 맥락이 포함된 추천 제공
    print(response2.conversation_context)

asyncio.run(memory_example())
```

## 📚 프로그래밍 API

### 기본 사용법

```python
from main_agent import MainAgent, AgentRequest
import asyncio

# 에이전트 생성
agent = MainAgent(openai_api_key="your-key")  # 또는 환경변수 사용

# 요청 생성
request = AgentRequest(
    user_input="I want to learn Korean culture in Seoul",
    session_id="my_session",
    user_preferences={"budget": "medium"}
)

# 처리 및 응답
response = await agent.process_request(request)

# 결과 확인
print(f"Success: {response.success}")
print(f"Destinations: {response.destinations}")
print(f"Places: {len(response.places)}")
print(f"Courses: {len(response.courses)}")
print(f"Recommendations: {response.recommendations}")
```

### 백엔드 서버 통합

```python
# FastAPI 예시
from fastapi import FastAPI
from main_agent import MainAgent, AgentRequest

app = FastAPI()
agent = MainAgent()

@app.post("/recommend")
async def recommend(request: AgentRequest):
    response = await agent.process_request(request)
    return response.to_dict()

# Flask 예시  
from flask import Flask, request, jsonify
import asyncio

app = Flask(__name__)
agent = MainAgent()

@app.route('/recommend', methods=['POST'])
def recommend():
    data = request.get_json()
    agent_request = AgentRequest(**data)
    response = asyncio.run(agent.process_request(agent_request))
    return jsonify(response.to_dict())
```

### 편의 함수

```python
from main_agent import quick_recommend, create_agent

# 빠른 추천 (세션 없음)
response = await quick_recommend("I want to visit Tokyo")

# 커스텀 에이전트 생성
agent = create_agent(openai_api_key="custom-key")
```

## 📊 내장 데이터

### 지원 도시
- **Seoul**: 경복궁, 명동, 홍대, 북촌한옥마을
- **Tokyo**: 센소지, 시부야, 츠키지 시장, 하라주쿠  
- **Paris**: 에펠탑, 루브르, 샹젤리제, 몽마르트르

### 학습 카테고리
- **Language Learning**: 한국어, 일본어, 프랑스어 기초
- **Cultural Studies**: 전통문화, 예술사, 문학 개론

## 🔧 설정

### 환경변수
```bash
# .env 파일
OPENAI_API_KEY=your_openai_api_key_here
```

### 프로그래밍 설정
```python
# API 키 직접 제공
agent = MainAgent(openai_api_key="your-key")

# 환경변수 사용 (권장)
agent = MainAgent()  # .env 또는 환경변수에서 자동 로드
```

## 🎛️ 고급 사용법

### 세션 관리
```python
# 세션 정보 확인
info = agent.get_session_info("session_id")
print(f"Memory available: {info['has_memory']}")

# 세션 삭제
agent.clear_session("session_id")

# 상태 확인
health = agent.health_check()
print(f"Active sessions: {health['data']['active_sessions']}")
```

### 메모리 없는 모드
```python
# OpenAI API 키 없이 실행 (기본 분석만)
agent = MainAgent()  # 메모리 기능 비활성화, 패턴 매칭만 사용
```

## 🏗️ 아키텍처

### 단일 파일 구조
```
main_agent.py (600+ lines)
├── Data Models (AgentRequest, AgentResponse, PlaceRecommendation, etc.)
├── Hardcoded Data (PLACE_DATA, COURSE_DATA)  
├── QuickAnalyzer (Pattern matching analysis)
├── MemoryManager (LangChain integration)
├── MainAgent (Core orchestration)
└── Convenience Functions (quick_recommend, create_agent)
```

### 처리 흐름
1. **요청 수신** → AgentRequest 파싱
2. **빠른 분석** → 패턴 매칭으로 의도 파악
3. **메모리 조회** → 이전 대화 맥락 검색  
4. **AI 강화** → OpenAI로 맥락적 추천 생성
5. **데이터 매핑** → 하드코딩된 장소/코스 매칭
6. **응답 생성** → 통합 결과 반환
7. **메모리 저장** → 대화 기록 업데이트

## 🚀 성능

- **콜드 스타트**: ~100ms (메모리 없음)
- **웜 분석**: ~50ms (기본 분석)
- **메모리 강화**: +500-2000ms (OpenAI API 호출시)
- **메모리 사용량**: ~10MB (데이터 + 활성 세션)

## 🔮 확장 가능성

현재 프로토타입을 확장하려면:

1. **데이터 확장**: `PLACE_DATA`, `COURSE_DATA`에 더 많은 도시/코스 추가
2. **분석 고도화**: `QuickAnalyzer`에 더 정교한 패턴 추가  
3. **메모리 개선**: 다양한 LangChain 메모리 타입 실험
4. **API 통합**: 실제 여행/학습 데이터 API 연동
5. **멀티모달**: 이미지, 음성 입력 지원

## 🎯 사용 사례

### 개발자 테스트
```bash
python cli.py demo  # 기능 데모
python cli.py chat  # 대화형 테스트
```

### 프로덕션 통합
```python
# 웹 서버에 임베드
agent = MainAgent()
response = await agent.process_request(request)
return response.to_dict()
```

### 연구 및 실험
```python
# 메모리 실험
for session in ["A", "B", "C"]:
    response = await agent.process_request(
        AgentRequest("같은 질문", session_id=session)
    )
    # 각 세션별로 다른 추천 확인
```

---

**🎉 준비 완료!** `python cli.py chat`로 바로 시작하세요!