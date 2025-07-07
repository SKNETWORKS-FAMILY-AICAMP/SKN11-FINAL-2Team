# 데이트 코스 추천 서브 에이전트

A2A 메인 에이전트의 서브 에이전트로 동작하는 데이트 코스 추천시스템입니다.

## 📋 주요 기능

- **병렬 처리**: 맑을 때/비올 때 시나리오 동시 처리
- **지능적 검색**: 벡터 검색 + 3단계 재시도 전략
- **최적화**: GPT 기반 코스 선택 및 추천 이유 생성
- **예상 처리 시간**: 4-6초

## 🏗️ 시스템 아키텍처

```
├── src/
│   ├── core/           # 핵심 비즈니스 로직
│   ├── database/       # 벡터 DB 관련
│   ├── agents/         # AI 에이전트들
│   ├── utils/          # 유틸리티 함수들
│   ├── models/         # 데이터 모델
│   └── main.py         # 메인 엔트리포인트
├── config/             # 설정 파일
├── tests/              # 테스트 코드
└── docs/               # 문서
```

## 🔧 기술 스택

- **AI Framework**: LangChain, OpenAI GPT-4o mini
- **Vector DB**: Qdrant
- **Web Framework**: FastAPI
- **Async Processing**: asyncio
- **Data Validation**: Pydantic

## 🚀 설치 및 실행

### 1. 의존성 설치
```bash
pip install -r requirements.txt
```

### 2. 환경변수 설정
```bash
# .env 파일 생성
OPENAI_API_KEY=your_openai_api_key_here
QDRANT_HOST=localhost
QDRANT_PORT=6333
```

### 3. 실행 방법

#### API 서버로 실행
```bash
python src/main.py
```

#### 직접 함수 호출
```python
from src.main import DateCourseAgent

agent = DateCourseAgent()
result = await agent.process_request(request_data)
```

## 📊 처리 흐름

1. **요청 수신**: 메인 에이전트로부터 JSON 요청 받기
2. **병렬 분기**: 맑을 때/비올 때 시나리오 병렬 처리
3. **벡터 검색**: 3단계 재시도 전략 (Top3 → Top5 → 반경확대)
4. **조합 생성**: 모든 경우의 수 조합 생성 및 거리 계산
5. **GPT 선택**: 최적 코스 3개 선택 및 추천 이유 생성
6. **결과 통합**: 최종 응답 생성

## 📋 API 명세

### POST /recommend-course
데이트 코스 추천 요청

**Request:**
```json
{
  "request_id": "req-001",
  "timestamp": "2025-06-30T15:30:00Z",
  "search_targets": [...],
  "user_context": {...},
  "course_planning": {...}
}
```

**Response:**
```json
{
  "request_id": "req-001",
  "processing_time": "4.2초",
  "status": "success",
  "results": {
    "sunny_weather": [...],
    "rainy_weather": [...]
  }
}
```

## 🔄 메인 에이전트와 연동

### LangChain Tool로 등록
```python
from langchain.tools import Tool

date_course_tool = Tool(
    name="date_course_recommender",
    description="데이트 코스 추천 서브 에이전트",
    func=agent.process_request
)

# 메인 에이전트에 추가
main_agent.tools.append(date_course_tool)
```

### HTTP API로 호출
```python
import requests

response = requests.post(
    "http://localhost:8000/recommend-course",
    json=request_data
)
```

## 🧪 테스트

```bash
# 단위 테스트
pytest tests/unit/

# 통합 테스트
pytest tests/integration/

# 전체 테스트
pytest
```

## 📈 성능 최적화

- **병렬 처리**: 임베딩 생성과 반경 계산 동시 실행
- **재시도 전략**: 필요시에만 추가 검색 수행
- **캐싱**: 자주 사용되는 결과 캐싱 고려
- **직선거리**: Haversine 공식 사용

## 🚨 예외 처리

- **완전 실패**: 3차 시도까지 모두 실패 시 대안 제안
- **부분 성공**: 한 날씨 조건만 성공 시 부분 결과 제공
- **타임아웃**: 30초 내 응답 보장

## 📝 로그

- **처리 시간**: 각 단계별 소요 시간 추적
- **재시도**: 실패 원인 및 재시도 횟수 기록
- **성능**: 응답 시간 및 성공률 모니터링

## 🔐 보안

- **API 키**: 환경변수로 안전하게 관리
- **입력 검증**: Pydantic으로 엄격한 데이터 검증
- **에러 처리**: 민감한 정보 노출 방지

## 📚 참고 문서

- [설계 문서](docs/api_spec.md)
- [배포 가이드](docs/deployment.md)
- [프롬프트 엔지니어링](src/agents/prompt_templates.py)
