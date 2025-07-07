# 🌐 Main Agent API 명세서

## 📋 개요

Main Agent는 채팅 기반 데이트 코스 추천 시스템의 중심 역할을 하며, 다음과 같은 API를 제공합니다:

### 🎯 주요 API 분류

1. **채팅 API**: 일반적인 대화 및 프로필 추출
2. **추천 API**: 전체 플로우 실행 (Place → RAG Agent)  
3. **세션 API**: 세션 관리 및 복원
4. **지원 API**: 헬스체크, 직접 에이전트 호출

---

## 🔗 Base URL
```
http://localhost:8000
```

---

## 💬 채팅 API

### POST /chat
일반 채팅을 통한 프로필 추출 및 맥락 유지

**Request Body:**
```json
{
  "session_id": "chat_12345678",
  "user_message": "29살 INTP 연인과 이촌동에서 로맨틱한 밤 데이트 3곳 추천해줘",
  "timestamp": "2025-07-03T10:30:00Z"
}
```

**Response (성공):**
```json
{
  "session_id": "chat_12345678",
  "success": true,
  "message": "프로필 정보가 추출되었습니다",
  "profile_status": "completed",
  "needs_recommendation": true,
  "recommendation_ready": true,
  "next_action": "추천을 시작하려면 /recommend 엔드포인트를 호출하세요",
  "extracted_info": {
    "age": "29",
    "mbti": "INTP",
    "relationship_stage": "연인",
    "atmosphere": "로맨틱",
    "time_slot": "밤",
    "reference_areas": ["이촌동"],
    "place_count": 3,
    "transportation": "도보"
  },
  "suggestions": ["추천을 시작할 준비가 되었습니다"]
}
```

**Response (프로필 미완성):**
```json
{
  "session_id": "chat_12345678", 
  "success": true,
  "message": "더 많은 정보가 필요합니다",
  "profile_status": "incomplete",
  "needs_recommendation": false,
  "extracted_info": {
    "age": "29",
    "mbti": "INTP"
  },
  "suggestions": ["어떤 지역에서 데이트하고 싶으신가요?", "몇 곳 정도 추천받고 싶으신가요?"]
}
```

---

## 🎯 추천 API

### POST /recommend
프로필이 완성된 후 전체 추천 플로우 실행

**Request Body:**
```json
{
  "session_id": "chat_12345678"
}
```

**Response (성공):**
```json
{
  "success": true,
  "message": "추천 완료",
  "session_id": "chat_12345678",
  "flow_results": {
    "place_agent": {
      "status": "completed",
      "success": true,
      "data": {
        "request_id": "req-12345678",
        "success": true,
        "locations": [
          {
            "sequence": 1,
            "area_name": "이촌동",
            "coordinates": {
              "latitude": 37.5225,
              "longitude": 126.9723
            },
            "reason": "한강뷰와 함께 로맨틱한 분위기를 즐길 수 있어 추천합니다"
          }
        ]
      }
    },
    "rag_agent": {
      "status": "completed",
      "success": true,
      "data": {
        "course": {
          "places": [
            {
              "name": "한강뷰 레스토랑",
              "category": "음식점", 
              "area_name": "이촌동",
              "coordinates": {
                "latitude": 37.5225,
                "longitude": 126.9723
              },
              "description": "한강의 야경을 감상하며 연인과 프라이빗하게..."
            }
          ],
          "total_duration": "3시간",
          "total_distance": "1.2km"
        }
      }
    }
  },
  "recommendation": {
    "places": [...],
    "course": {...},
    "created_at": "2025-07-03T10:45:00Z"
  }
}
```

**Response (실패):**
```json
{
  "success": false,
  "message": "Place Agent 호출 실패",
  "flow_results": {
    "place_agent": {
      "status": "failed",
      "error": "HTTP 500"
    }
  }
}
```

---

## 🔄 세션 API

### GET /session/{session_id}
세션 복원 및 상태 조회

**Response (세션 존재):**
```json
{
  "session_id": "chat_12345678",
  "exists": true,
  "session_memory": "사용자가 29살 INTP이고 연인과 이촌동에서...",
  "profile_status": "completed",
  "extracted_info": {
    "age": "29",
    "mbti": "INTP",
    "relationship_stage": "연인"
  },
  "needs_recommendation": true,
  "last_activity": "2025-07-03T10:30:00Z"
}
```

**Response (세션 없음):**
```json
{
  "session_id": "chat_12345678",
  "exists": false,
  "message": "세션을 찾을 수 없습니다"
}
```

### DELETE /session/{session_id}
세션 삭제

**Response:**
```json
{
  "session_id": "chat_12345678",
  "cleared": true
}
```

### GET /profile/{session_id}
세션별 프로필 상세 조회

**Response:**
```json
{
  "session_id": "chat_12345678",
  "memory": "사용자 프로필 정보...",
  "status": "found"
}
```

---

## 🛠️ 지원 API

### GET /health
헬스 체크

**Response:**
```json
{
  "status": "healthy",
  "service": "main-agent", 
  "port": 8000,
  "version": "1.0.0"
}
```

### POST /place/request
Place Agent 직접 호출 (A2A)

**Request Body:**
```json
{
  "request_id": "req-12345678",
  "timestamp": "2025-07-03T10:30:00Z",
  "request_type": "proximity_based",
  "location_request": {
    "proximity_type": "exact",
    "reference_areas": ["이촌동"],
    "place_count": 3
  },
  "user_context": {
    "demographics": {
      "age": 29,
      "mbti": "INTP",
      "relationship_stage": "연인"
    }
  }
}
```

### POST /course/request
RAG Agent 직접 호출 (A2A)

**Request Body:**
```json
{
  "request_id": "req-12345678",
  "search_targets": [
    {
      "sequence": 1,
      "category": "음식점",
      "location": {
        "area_name": "이촌동",
        "coordinates": {
          "latitude": 37.5225,
          "longitude": 126.9723
        }
      },
      "semantic_query": "로맨틱한 분위기의 음식점..."
    }
  ],
  "user_context": {...},
  "course_planning": {...}
}
```

---

## 🎯 사용 시나리오

### 시나리오 1: 새로운 채팅 세션

```bash
# 1. 초기 채팅
POST /chat
{
  "session_id": "chat_new001",
  "user_message": "안녕하세요!"
}

# 2. 정보 수집
POST /chat  
{
  "session_id": "chat_new001",
  "user_message": "29살 INTP 연인과 데이트하고 싶어요"
}

# 3. 상세 정보 수집
POST /chat
{
  "session_id": "chat_new001", 
  "user_message": "이촌동에서 로맨틱한 밤 데이트 3곳 추천해주세요"
}

# 4. 추천 시작
POST /recommend
{
  "session_id": "chat_new001"
}
```

### 시나리오 2: 세션 복원

```bash
# 1. 세션 복원
GET /session/chat_old123

# 2. 바로 추천 (프로필이 완성된 경우)
POST /recommend
{
  "session_id": "chat_old123"
}
```

---

## 📊 응답 상태 코드

| 상태 코드 | 의미 | 설명 |
|----------|------|------|
| 200 | 성공 | 요청이 성공적으로 처리됨 |
| 400 | 잘못된 요청 | 필수 파라미터 누락 또는 잘못된 형식 |
| 404 | 찾을 수 없음 | 세션이 존재하지 않음 |
| 500 | 서버 오류 | 내부 서버 오류 또는 에이전트 호출 실패 |

---

## 🔧 에러 처리

### 일반적인 에러 응답 형식
```json
{
  "detail": "에러 메시지",
  "status_code": 400
}
```

### 추천 플로우 에러 (일부 성공 시)
```json
{
  "success": false,
  "message": "RAG Agent 호출 실패",
  "flow_results": {
    "place_agent": {
      "status": "completed",
      "success": true,
      "data": {...}
    },
    "rag_agent": {
      "status": "failed", 
      "error": "HTTP 500"
    }
  }
}
```

---

## 💡 클라이언트 구현 가이드

### 기본 플로우
1. **건강상태 확인**: `GET /health`
2. **채팅 시작**: `POST /chat` (반복)
3. **추천 준비 확인**: `needs_recommendation: true` 대기
4. **추천 실행**: `POST /recommend`
5. **결과 처리**: 응답 데이터 파싱

### 세션 관리
- 세션 ID는 클라이언트가 생성 (`chat_` + 8자리 랜덤)
- 세션 복원: `GET /session/{session_id}`로 상태 확인
- 세션 삭제: `DELETE /session/{session_id}`

### 오류 처리
- 네트워크 타임아웃: 채팅 30초, 추천 120초
- 에이전트 오류: `flow_results`에서 상세 오류 확인
- 세션 오류: 404 시 새 세션 생성

---

**버전:** 2.0 (v1 제거)  
**마지막 업데이트:** 2025-07-03