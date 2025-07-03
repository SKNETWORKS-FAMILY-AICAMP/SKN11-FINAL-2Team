# 🌐 웹 프론트엔드용 API 레퍼런스

## 📋 개요

데이트 코스 추천 웹 서비스를 위한 Main Agent API 가이드입니다.

**Base URL:** `http://localhost:8000`

---

## 🔑 핵심 API (웹에서 주로 사용)

### 1. 💬 채팅 API

#### `POST /chat`
사용자와의 일반적인 채팅을 통해 프로필을 점진적으로 수집합니다.

**요청:**
```javascript
fetch('http://localhost:8000/chat', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    session_id: "chat_" + Math.random().toString(36).substr(2, 8),
    user_message: "29살 INTP 연인과 이촌동에서 로맨틱한 밤 데이트 3곳 추천해줘",
    timestamp: new Date().toISOString()
  })
})
```

**응답 (프로필 완성):**
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
  "suggestions": []
}
```

**응답 (더 많은 정보 필요):**
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
  "suggestions": [
    "어떤 지역에서 데이트하고 싶으신가요?",
    "몇 곳 정도 추천받고 싶으신가요?"
  ]
}
```

---

### 2. 🎯 추천 시작 API

#### `POST /recommend`
프로필이 완성되면 Place Agent → RAG Agent 전체 플로우를 실행합니다.

**요청:**
```javascript
fetch('http://localhost:8000/recommend', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    session_id: "chat_12345678"
  })
})
```

**응답 (성공):**
```json
{
  "success": true,
  "message": "추천 완료",
  "session_id": "chat_12345678",
  "recommendation": {
    "places": [
      {
        "sequence": 1,
        "area_name": "이촌동",
        "coordinates": {
          "latitude": 37.5225,
          "longitude": 126.9723
        },
        "reason": "한강뷰와 함께 로맨틱한 분위기를 즐길 수 있어 추천합니다"
      },
      {
        "sequence": 2,
        "area_name": "한남동",
        "coordinates": {
          "latitude": 37.5357,
          "longitude": 127.0002
        },
        "reason": "세련된 카페와 갤러리가 많아 문화적인 데이트가 가능합니다"
      }
    ],
    "course": {
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
            "description": "한강의 야경을 감상하며 연인과 프라이빗하게 식사할 수 있는 고급스러운 레스토랑...",
            "recommended_duration": "90분",
            "price_range": "50,000-80,000원"
          },
          {
            "name": "감성 카페",
            "category": "카페", 
            "area_name": "한남동",
            "coordinates": {
              "latitude": 37.5357,
              "longitude": 127.0002
            },
            "description": "조용하고 고급스러운 분위기가 감도는 카페로 연인과의 깊은 대화를 즐기기에 완벽한 장소...",
            "recommended_duration": "60분",
            "price_range": "15,000-25,000원"
          }
        ],
        "total_duration": "4시간",
        "total_distance": "2.1km",
        "estimated_cost": "80,000-120,000원"
      }
    },
    "created_at": "2025-07-03T10:45:00Z"
  }
}
```

**응답 (실패):**
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

### 3. 🔄 세션 관리 API

#### `GET /session/{session_id}`
이전 채팅 세션을 복원합니다.

**요청:**
```javascript
fetch(`http://localhost:8000/session/chat_12345678`)
```

**응답 (세션 존재):**
```json
{
  "session_id": "chat_12345678",
  "exists": true,
  "session_memory": "사용자가 29살 INTP이고 연인과 이촌동에서 로맨틱한 밤 데이트를 원한다고 함",
  "profile_status": "completed",
  "extracted_info": {
    "age": "29",
    "mbti": "INTP",
    "relationship_stage": "연인",
    "atmosphere": "로맨틱"
  },
  "needs_recommendation": true,
  "last_activity": "2025-07-03T10:30:00Z"
}
```

#### `DELETE /session/{session_id}`
세션을 삭제합니다.

**요청:**
```javascript
fetch(`http://localhost:8000/session/chat_12345678`, {
  method: 'DELETE'
})
```

**응답:**
```json
{
  "session_id": "chat_12345678",
  "cleared": true
}
```

---

### 4. 💊 헬스체크 API

#### `GET /health`
서버 상태를 확인합니다.

**요청:**
```javascript
fetch('http://localhost:8000/health')
```

**응답:**
```json
{
  "status": "healthy",
  "service": "main-agent",
  "port": 8000,
  "version": "1.0.0"
}
```

---

## 🎨 프론트엔드 구현 가이드

### JavaScript 클라이언트 예시

```javascript
class DateCourseAPI {
  constructor(baseURL = 'http://localhost:8000') {
    this.baseURL = baseURL;
    this.sessionId = null;
  }

  // 새 세션 생성
  createSession() {
    this.sessionId = "chat_" + Math.random().toString(36).substr(2, 8);
    return this.sessionId;
  }

  // 채팅 메시지 전송
  async sendMessage(message) {
    if (!this.sessionId) {
      this.createSession();
    }

    const response = await fetch(`${this.baseURL}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        session_id: this.sessionId,
        user_message: message,
        timestamp: new Date().toISOString()
      })
    });

    return await response.json();
  }

  // 추천 시작
  async startRecommendation() {
    const response = await fetch(`${this.baseURL}/recommend`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        session_id: this.sessionId
      })
    });

    return await response.json();
  }

  // 세션 복원
  async restoreSession(sessionId) {
    const response = await fetch(`${this.baseURL}/session/${sessionId}`);
    const result = await response.json();
    
    if (result.exists) {
      this.sessionId = sessionId;
    }
    
    return result;
  }

  // 서버 상태 확인
  async checkHealth() {
    const response = await fetch(`${this.baseURL}/health`);
    return await response.json();
  }
}
```

### 사용 예시

```javascript
// API 클라이언트 생성
const api = new DateCourseAPI();

// 채팅 플로우
async function chatFlow() {
  try {
    // 1. 초기 메시지
    let result = await api.sendMessage("안녕하세요! 데이트 코스 추천을 받고 싶어요.");
    console.log("Bot:", result.message);

    // 2. 상세 정보 제공
    result = await api.sendMessage("29살 INTP 연인과 이촌동에서 로맨틱한 밤 데이트 3곳 추천해주세요.");
    console.log("Bot:", result.message);

    // 3. 추천 준비 확인
    if (result.needs_recommendation) {
      console.log("프로필 완성! 추천을 시작합니다...");
      
      // 4. 추천 시작
      const recommendation = await api.startRecommendation();
      
      if (recommendation.success) {
        console.log("추천 완료!", recommendation.recommendation);
      } else {
        console.log("추천 실패:", recommendation.message);
      }
    } else {
      console.log("더 많은 정보가 필요합니다:", result.suggestions);
    }

  } catch (error) {
    console.error("오류:", error);
  }
}
```

---

## 🎯 상태 관리 가이드

### 채팅 상태

```javascript
const ChatState = {
  INITIAL: 'initial',           // 처음 시작
  COLLECTING: 'collecting',     // 정보 수집 중
  READY: 'ready',              // 추천 준비 완료
  RECOMMENDING: 'recommending', // 추천 진행 중
  COMPLETED: 'completed'        // 추천 완료
};

// 상태 확인 함수
function getChatState(response) {
  if (response.profile_status === 'incomplete') {
    return ChatState.COLLECTING;
  } else if (response.needs_recommendation && !response.recommendation) {
    return ChatState.READY;
  } else if (response.recommendation) {
    return ChatState.COMPLETED;
  }
  return ChatState.INITIAL;
}
```

### UI 업데이트 예시

```javascript
function updateUI(chatResponse) {
  const state = getChatState(chatResponse);
  
  switch(state) {
    case ChatState.COLLECTING:
      // 정보 입력 폼 표시
      showInfoForm(chatResponse.suggestions);
      break;
      
    case ChatState.READY:
      // 추천 시작 버튼 표시
      showRecommendButton();
      break;
      
    case ChatState.COMPLETED:
      // 추천 결과 표시
      showRecommendation(chatResponse.recommendation);
      break;
  }
}
```

---

## 🚨 에러 처리

### HTTP 상태 코드

| 코드 | 의미 | 처리 방법 |
|------|------|-----------|
| 200 | 성공 | 정상 처리 |
| 400 | 잘못된 요청 | 요청 데이터 확인 |
| 404 | 세션 없음 | 새 세션 생성 |
| 500 | 서버 오류 | 에러 메시지 표시 |

### 에러 처리 예시

```javascript
async function handleAPICall(apiCall) {
  try {
    const response = await apiCall();
    
    if (!response.success && response.detail) {
      // API 레벨 에러
      throw new Error(response.detail);
    }
    
    return response;
    
  } catch (error) {
    if (error.message.includes('404')) {
      // 세션 만료 - 새 세션 생성
      api.createSession();
      return { error: 'session_expired', message: '새 세션이 생성되었습니다.' };
    } else if (error.message.includes('timeout')) {
      // 타임아웃
      return { error: 'timeout', message: '요청 시간이 초과되었습니다.' };
    } else {
      // 기타 오류
      return { error: 'unknown', message: error.message };
    }
  }
}
```

---

## 📱 반응형 웹 고려사항

### 모바일 최적화
- 채팅 인터페이스는 모바일 친화적
- 추천 결과는 카드 형태로 표시
- 지도 표시 시 터치 제스처 지원

### 로딩 상태 관리
```javascript
// 추천은 최대 2분 소요 가능
const RECOMMENDATION_TIMEOUT = 120000; // 120초

async function startRecommendationWithLoading() {
  showLoadingSpinner("추천을 생성하고 있습니다...");
  
  try {
    const result = await Promise.race([
      api.startRecommendation(),
      new Promise((_, reject) => 
        setTimeout(() => reject(new Error('timeout')), RECOMMENDATION_TIMEOUT)
      )
    ]);
    
    hideLoadingSpinner();
    return result;
    
  } catch (error) {
    hideLoadingSpinner();
    throw error;
  }
}
```

---

## 🔐 보안 고려사항

### CORS 설정
서버에서 이미 모든 Origin 허용으로 설정되어 있습니다.

### 데이터 검증
```javascript
function validateMessage(message) {
  if (!message || message.trim().length === 0) {
    throw new Error('메시지를 입력해주세요.');
  }
  
  if (message.length > 1000) {
    throw new Error('메시지가 너무 깁니다. (최대 1000자)');
  }
  
  return message.trim();
}
```

---

**마지막 업데이트:** 2025-07-03  
**API 버전:** 2.0 (버전 정보 제거)