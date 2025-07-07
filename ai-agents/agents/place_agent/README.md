# Place Agent (모듈화 버전)

서울 지역 추천 및 좌표 반환 전문 서비스

## 📁 프로젝트 구조

```
place_agent/
├── config/
│   ├── __init__.py
│   └── settings.py          # 환경 설정
├── src/
│   ├── __init__.py
│   ├── main.py              # 메인 PlaceAgent 클래스
│   ├── models/
│   │   ├── __init__.py
│   │   ├── request_models.py    # 요청 모델
│   │   └── response_models.py   # 응답 모델
│   ├── core/
│   │   ├── __init__.py
│   │   ├── location_analyzer.py # LLM 기반 지역 분석
│   │   └── coordinates_service.py # 좌표 계산 서비스
│   ├── data/
│   │   ├── __init__.py
│   │   └── area_data.py         # 서울 지역 데이터
│   └── utils/
│       └── __init__.py
├── start_server.py          # FastAPI 서버
├── test_a2a.py             # A2A 테스트 스크립트
└── README.md
```

## 🚀 실행 방법

### 1. 환경 설정

```bash
# .env 파일 생성 (place_agent 폴더에)
OPENAI_API_KEY=your_openai_api_key
KAKAO_API_KEY=your_kakao_api_key_optional
SERVER_PORT=8002
```

### 2. 서버 실행

```bash
# Place Agent 서버 시작
python start_server.py
```

### 3. A2A 테스트

```bash
# 별도 터미널에서 A2A 테스트 실행
python test_a2a.py
```

## 📡 API 엔드포인트

### Health Check
```http
GET /health
```

### Place Agent 요청
```http
POST /place-agent
Content-Type: application/json

{
  "request_id": "test-001",
  "timestamp": "2024-01-01T12:00:00",
  "request_type": "proximity_based",
  "location_request": {
    "proximity_type": "near",
    "reference_areas": ["홍대"],
    "place_count": 3,
    "proximity_preference": "middle",
    "transportation": "지하철"
  },
  "user_context": {
    "demographics": {
      "age": 25,
      "mbti": "ENFP", 
      "relationship_stage": "연인"
    },
    "preferences": ["트렌디한", "감성적인"],
    "requirements": {
      "budget_level": "medium",
      "time_preference": "저녁",
      "transportation": "지하철",
      "max_travel_time": 30
    }
  },
  "selected_categories": ["카페", "레스토랑"]
}
```

### 테스트 엔드포인트
```http
GET /test
```

## 🔧 주요 기능

### 1. LLM 기반 지역 분석
- OpenAI GPT를 통한 지능적 지역 추천
- 사용자 MBTI, 관계 단계, 선호사항 고려
- 기존 정의된 지역 + 새로운 지역 하이브리드 지원

### 2. 좌표 서비스
- 기존 정의된 지역 좌표 우선 조회
- 카카오 API를 통한 새 지역 좌표 검색
- 좌표 유효성 검증 및 다양성 확보

### 3. 모듈화된 구조
- 관심사 분리 (SoC) 원칙 적용
- 서비스 지향 아키텍처
- 독립적인 모듈 테스트 가능

## 🧪 테스트 시나리오

1. **홍대 근처 3곳 (ENFP 연인)**
   - 트렌디하고 감성적인 장소 추천
   - 지하철 접근성 고려

2. **강남 근처 2곳 (INTJ 썸)**
   - 조용하고 세련된 장소 추천
   - 도보 거리 내 위치

3. **성수 근처 4곳 (ESFP 친구)**
   - 힙하고 트렌디한 장소 추천
   - 대중교통 이용 가능

## 🔗 연동 정보

- **포트**: 8002 (기본값)
- **프로토콜**: HTTP/JSON
- **메인 에이전트 연동**: `/place-agent` 엔드포인트 사용

## 📝 변경사항 (v2.0.0)

- ✅ 모노리스 구조에서 모듈화 구조로 전환
- ✅ 관심사 분리 및 코드 가독성 향상
- ✅ A2A 테스트 환경 구축
- ✅ 하이브리드 지역 지원 (기존 + 새 지역)
- ✅ 비동기 처리 및 성능 최적화