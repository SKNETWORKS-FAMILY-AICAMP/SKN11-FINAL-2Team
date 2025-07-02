# Place Agent

데이트 코스 추천을 위한 지역 분석 및 좌표 반환 서비스

## 설치 및 실행

### 1. 의존성 설치
```bash
pip install -r requirements.txt
```

### 2. 환경변수 설정
`.env` 파일에서 API 키를 설정하세요:
```
OPENAI_API_KEY=your-openai-api-key
KAKAO_API_KEY=your-kakao-api-key  # 선택사항
```

### 3. 서버 실행
```bash
python place_agent.py
```

서버는 `http://localhost:8001/docs`에서 실행됩니다.

## API 엔드포인트

### POST /analyze
지역 분석 및 좌표 반환 메인 API

**요청 예시 (케이스 1: 명확한 지역)**:
```json
{
  "request_id": "req-001",
  "timestamp": "2025-06-30T15:30:00Z",
  "request_type": "exact_locations",
  "areas": [
    {"sequence": 1, "area_name": "홍대"},
    {"sequence": 2, "area_name": "강남"}
  ]
}
```

**요청 예시 (케이스 2: 애매한 지역)**:
```json
{
  "request_id": "req-002",
  "timestamp": "2025-06-30T16:15:00Z",
  "request_type": "area_recommendation",
  "location_request": {
    "vague_location": "서울",
    "place_count": 3,
    "distribution_style": "diverse"
  },
  "user_context": {
    "demographics": {
      "age": 25,
      "mbti": "ENFP",
      "relationship_stage": "썸"
    },
    "preferences": ["분위기 있는 곳", "사진 찍기 좋은"],
    "requirements": {
      "budget_level": "low-medium",
      "time_preference": "오후",
      "transportation": "대중교통"
    }
  },
  "selected_categories": ["브런치카페", "갤러리카페"]
}
```

**응답 예시**:
```json
{
  "request_id": "req-001",
  "success": true,
  "locations": [
    {
      "sequence": 1,
      "area_name": "홍대",
      "coordinates": {
        "latitude": 37.5519,
        "longitude": 126.9245
      },
      "reason": "젊고 활기찬 문화 중심지로 다양한 카페와 클럽이 있어 데이트하기 좋습니다."
    }
  ]
}
```

### GET /health
서비스 상태 확인

### GET /areas
사용 가능한 지역 목록 조회

## 지원하는 케이스

1. **exact_locations**: 명확한 지역 지정
2. **area_recommendation**: 애매한 위치 추천
3. **proximity_based**: 중간지점/근처 지역

## 현재 지원 지역

홍대, 강남, 이태원, 성수, 연남, 신촌, 명동, 인사동, 압구정, 건대

## 개발 중인 기능

- Kakao Map API 연동으로 동적 지역 검색
- 사용자 피드백 기반 좌표 정교화
- 지하철역 기반 중간지점 계산
