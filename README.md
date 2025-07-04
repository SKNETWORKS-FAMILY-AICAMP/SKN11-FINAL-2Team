# Place Agent v3.0.0

지역 선정 및 좌표 반환 전문 서비스 - 데이트 코스 추천을 위한 AI 기반 장소 분석 API

## 🚀 주요 기능

- **4가지 지역 선정 모드**: exact, near, between, multi
- **Kakao Map API 연동**: 실시간 지역 정보 및 좌표 조회
- **GPT-4o-mini 기반 LLM 분석**: 사용자 컨텍스트를 고려한 최적 장소 추천
- **좌표 정확도 관리**: 소수점 4자리 정규화 및 중복 방지 (최소 200m 간격)
- **다양한 카테고리 지원**: 카페, 음식점, 공원, 문화시설, 관광명소

## 📦 설치 및 실행

### 1. 의존성 설치
```bash
cd place_agent
pip install -r requirements.txt
```

### 2. 환경변수 설정
`.env` 파일 생성:
```env
OPENAI_API_KEY=your-openai-api-key
KAKAO_API_KEY=your-kakao-api-key
```

### 3. 서버 실행
```bash
python place_agent.py
```

서버가 `http://localhost:8001`에서 실행되며, API 문서는 `http://localhost:8001/docs`에서 확인 가능합니다.

## 🎯 API 엔드포인트

### POST /analyze
메인 지역 분석 및 좌표 반환 API

#### 4가지 proximity_type 지원:

#### 1. exact 모드 - 지정 지역 내 세부 장소들
```json
{
  "request_id": "req-001",
  "timestamp": "2025-01-01T12:00:00",
  "location_request": {
    "proximity_type": "exact",
    "reference_areas": ["홍대"],
    "place_count": 3
  },
  "user_context": {
    "demographics": {
      "age": 25,
      "mbti": "ENFP",
      "relationship_stage": "연인"
    },
    "preferences": ["조용한 분위기", "트렌디한"],
    "requirements": {
      "budget_level": "medium",
      "time_preference": "오후",
      "transportation": "지하철"
    }
  }
}
```

#### 2. near 모드 - 기준 지역 주변 추천
```json
{
  "request_id": "req-002",
  "timestamp": "2025-01-01T12:00:00",
  "location_request": {
    "proximity_type": "near",
    "reference_areas": ["강남역"],
    "place_count": 3
  },
  "user_context": {
    "demographics": {
      "age": 28,
      "mbti": "ISFJ",
      "relationship_stage": "썸"
    },
    "preferences": ["분위기 좋은", "사진 찍기 좋은"],
    "requirements": {
      "budget_level": "high",
      "time_preference": "저녁",
      "transportation": "차"
    }
  }
}
```

#### 3. between 모드 - 두 지역 중간점
```json
{
  "request_id": "req-003",
  "timestamp": "2025-01-01T12:00:00",
  "location_request": {
    "proximity_type": "between",
    "reference_areas": ["홍대", "강남"],
    "place_count": 2
  },
  "user_context": {
    "demographics": {
      "age": 24,
      "mbti": "ENTP",
      "relationship_stage": "친구"
    },
    "preferences": ["접근성 좋은"],
    "requirements": {
      "time_preference": "오전",
      "transportation": "지하철"
    }
  }
}
```

#### 4. multi 모드 - 일반 추천
```json
{
  "request_id": "req-004",
  "timestamp": "2025-01-01T12:00:00",
  "location_request": {
    "proximity_type": "multi",
    "reference_areas": [],
    "place_count": 3
  },
  "user_context": {
    "demographics": {
      "age": 22,
      "mbti": "INFP",
      "relationship_stage": "연인"
    },
    "preferences": ["힙한 곳", "인스타 감성"],
    "requirements": {
      "budget_level": "low",
      "time_preference": "오후",
      "max_travel_time": 30
    }
  },
  "selected_categories": ["카페", "레스토랑"]
}
```

#### 응답 형식:
```json
{
  "request_id": "req-001",
  "success": true,
  "locations": [
    {
      "sequence": 1,
      "area_name": "홍대 걷고싶은거리",
      "coordinates": {
        "latitude": 37.5519,
        "longitude": 126.9245
      },
      "reason": "홍대의 대표적인 거리로 다양한 카페와 맛집이 모여있어 젊은 연인들에게 인기가 높습니다."
    },
    {
      "sequence": 2,
      "area_name": "홍대 클럽거리",
      "coordinates": {
        "latitude": 37.5512,
        "longitude": 126.9235
      },
      "reason": "트렌디하고 활기찬 분위기를 원하시는 ENFP 성향에 잘 맞는 장소입니다."
    }
  ]
}
```

### GET /health
서비스 상태 및 API 키 설정 상태 확인

### GET /test-coordinates/{area_name}
특정 지역의 여러 좌표 테스트 (개발용)

### GET /test-nearby/{area_name}
특정 지역 주변 검색 테스트 (개발용)

### POST /test-request
전체 요청 처리 테스트 (개발용)

## 🔧 기술 스택

- **Backend**: FastAPI 3.0
- **AI/ML**: OpenAI GPT-4o-mini
- **지도 API**: Kakao Map API
- **좌표 계산**: Haversine 공식
- **비동기 처리**: asyncio, httpx

## 📍 좌표 정확도 및 중복 방지

- **좌표 정규화**: 소수점 4자리로 고정
- **최소 거리**: 200미터 이상 간격 보장
- **중복 제거**: 동일 카테고리 및 유사 장소명 필터링
- **거리 계산**: Haversine 공식 사용

## 🎨 사용자 컨텍스트 고려사항

### 인구통계학적 정보
- **나이**: 연령대별 선호 장소 반영
- **MBTI**: 성격 유형별 맞춤 추천
- **관계 단계**: 연인/썸/친구별 적합한 장소

### 선호사항 및 요구사항
- **예산 수준**: low/medium/high
- **시간대**: 오전/오후/저녁/밤
- **교통수단**: 도보/차/지하철
- **최대 이동시간**: 분 단위

## 🌟 특징

### LLM 기반 지능형 분석
- 사용자의 나이, MBTI, 관계 단계를 종합 고려
- 자연스러운 문장 형태의 추천 이유 제공
- 다양한 카테고리 균형 배치

### Kakao API 연동
- 실시간 장소 정보 조회
- 반경 기반 주변 지역 검색
- 카테고리별 장소 필터링 (카페, 음식점, 문화시설 등)

### 고도화된 좌표 관리
- 좌표 정규화로 일관성 보장
- 거리 기반 중복 방지
- 지역별 세부 위치 생성

## 🔍 지원 지역

서울 전체 지역을 동적으로 지원하며, 특히 다음 지역에 최적화:
- 홍대, 강남, 이태원, 성수, 연남동
- 신촌, 명동, 인사동, 압구정, 건대입구
- 그 외 서울 모든 구/동/주요 상권

## 🚨 에러 처리

- API 키 미설정 시 graceful degradation
- Kakao API 장애 시 fallback 메커니즘
- 좌표 조회 실패 시 대체 생성 로직
- 상세한 에러 메시지 및 로깅

## 🔄 개발 로드맵

- [x] 4가지 proximity_type 모드 구현
- [x] Kakao API 연동 및 실시간 검색
- [x] LLM 기반 지능형 장소 분석
- [x] 좌표 정확도 및 중복 방지 시스템
- [ ] 사용자 피드백 학습 시스템
- [ ] 대중교통 연계 최적화
- [ ] 실시간 혼잡도 반영

## 📝 라이선스

이 프로젝트는 SKN11 Final Project의 일부입니다.