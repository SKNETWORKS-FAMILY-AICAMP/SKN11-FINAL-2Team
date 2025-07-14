# API 명세서

## 개요
데이트 코스 추천 서브 에이전트의 API 명세서입니다.

## 엔드포인트

### POST /recommend-course
데이트 코스 추천 요청

#### 요청 형식
```json
{
  "request_id": "req-001",
  "timestamp": "2025-06-30T15:30:00Z",
  "search_targets": [
    {
      "sequence": 1,
      "category": "음식점",
      "location": {
        "area_name": "홍대",
        "coordinates": {"latitude": 37.5519, "longitude": 126.9245}
      },
      "semantic_query": "홍대에서 커플이 가기 좋은 로맨틱한 파인다이닝 레스토랑"
    }
  ],
  "user_context": {
    "demographics": {
      "age": 28,
      "mbti": "ENFJ",
      "relationship_stage": "연인"
    },
    "preferences": ["로맨틱한 분위기", "저녁 데이트"],
    "requirements": {
      "budget_range": "커플 기준 15-20만원",
      "time_preference": "저녁",
      "party_size": 2,
      "transportation": "대중교통"
    }
  },
  "course_planning": {
    "optimization_goals": ["로맨틱한 저녁 데이트 경험 극대화"],
    "route_constraints": {
      "max_travel_time_between": 30,
      "total_course_duration": 300,
      "flexibility": "low"
    },
    "sequence_optimization": {
      "allow_reordering": false,
      "prioritize_given_sequence": true
    }
  }
}
```

#### 응답 형식

##### 성공 응답
```json
{
  "request_id": "req-001",
  "processing_time": "4.2초",
  "status": "success",
  "constraints_applied": {
    "sunny_weather": {"attempt": "1차", "radius_used": 2000},
    "rainy_weather": {"attempt": "2차", "radius_used": 2000}
  },
  "results": {
    "sunny_weather": [
      {
        "course_id": "sunny_course_1",
        "places": [
          {
            "sequence": 1,
            "place_info": {
              "place_id": "rest_001",
              "place_name": "로맨틱 파인다이닝 A",
              "latitude": 37.5519,
              "longitude": 126.9245,
              "category": "음식점"
            },
            "description": "홍대 중심가에 위치한 프리미엄 파인다이닝 레스토랑..."
          }
        ],
        "travel_info": [
          {
            "from": "로맨틱 파인다이닝 A",
            "to": "이태원 와인바 B",
            "distance_meters": 3200
          }
        ],
        "total_distance_meters": 7300,
        "recommendation_reason": "사용자의 로맨틱한 저녁 데이트 선호도에 맞는 고급스러운 분위기..."
      }
    ],
    "rainy_weather": [...]
  }
}
```

##### 실패 응답
```json
{
  "request_id": "req-001",
  "processing_time": "2.1초",
  "status": "failed",
  "message": "현재 조건으로는 적절한 데이트 코스를 찾을 수 없습니다.",
  "suggestions": [
    "지역을 변경해보세요",
    "예산 범위를 조정해보세요",
    "시간 제약을 완화해보세요"
  ]
}
```

### GET /health
서비스 상태 확인

#### 응답
```json
{
  "status": "healthy",
  "service": "date-course-agent",
  "version": "1.0.0"
}
```

## 상태 코드

- `200 OK`: 정상 처리
- `400 Bad Request`: 잘못된 요청 형식
- `500 Internal Server Error`: 서버 내부 오류
- `503 Service Unavailable`: 외부 서비스 오류

## 데이터 형식

### 카테고리 타입
- `음식점`: 레스토랑, 카페 등
- `술집`: 바, 펜, 와인바 등  
- `문화시설`: 미술관, 박물관, 영화관 등
- `휴식시설`: 스파, 찜질방 등
- `야외활동`: 공원, 산책로 등 (비올 때 자동 변환)

### 처리 상태
- `success`: 완전 성공 (맑을 때, 비올 때 모두 성공)
- `partial_success`: 부분 성공 (한 날씨 조건만 성공)
- `failed`: 완전 실패
