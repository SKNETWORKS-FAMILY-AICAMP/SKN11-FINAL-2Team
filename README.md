# 데이트 코스 추천 서비스

AI 기반 개인화 데이트 코스 추천 플랫폼입니다. 사용자의 MBTI, 관계단계, 선호도를 분석하여 최적의 데이트 코스를 추천합니다.

## 🏗️ 시스템 아키텍처

```
Frontend (React) ← → API Server (FastAPI) ← → AI Agents (3 Agents)
                        ↓
                   Database (SQLite)
```

## 📁 프로젝트 구조

```
├── api/                    # FastAPI 백엔드 서버
│   ├── models/            # SQLAlchemy 데이터베이스 모델
│   ├── schemas/           # Pydantic 스키마
│   ├── crud/              # 데이터베이스 CRUD 로직
│   ├── routers/           # API 엔드포인트
│   └── main.py            # FastAPI 애플리케이션 진입점
│
├── ai-agents/             # AI 에이전트 시스템
│   ├── agents/
│   │   ├── main-agent/    # 메인 오케스트레이터
│   │   ├── place-agent/   # 지역 분석 에이전트
│   │   └── date-course-agent/ # 코스 생성 에이전트
│   └── start_all_servers.py   # 모든 에이전트 서버 실행
│
└── README.md
```

## 🚀 주요 기능

### 🤖 AI 에이전트 시스템
- **Main Agent**: 사용자 프로필 추출 및 에이전트 오케스트레이션
- **Place Agent**: 카카오 API 연동 지역 분석 및 좌표 제공
- **Date-Course Agent**: Qdrant 벡터 DB 기반 개인화 코스 생성

### 🎯 개인화 추천
- **MBTI 기반**: 16가지 성격 유형별 맞춤 추천
- **관계 단계**: 연인/썸/친구별 차별화된 코스
- **예산 고려**: low/medium/high 예산 수준별 추천
- **날씨 대응**: 맑은 날/비오는 날 시나리오 분리

### 🔗 소셜 기능
- **커플 시스템**: 연인 신청/수락/관리
- **코스 공유**: 추천받은 코스 공유 및 저장
- **댓글 시스템**: 코스에 대한 피드백 및 후기
- **카카오 로그인**: 간편한 소셜 로그인

## 🛠️ 기술 스택

### 백엔드 (API)
- **FastAPI**: 비동기 웹 프레임워크
- **SQLAlchemy**: 비동기 ORM
- **SQLite**: 경량 데이터베이스
- **Pydantic**: 데이터 검증 및 직렬화

### AI 에이전트
- **OpenAI GPT-4**: 자연어 처리 및 생성
- **Qdrant**: 벡터 데이터베이스
- **LangChain**: AI 에이전트 프레임워크
- **Kakao API**: 지도 및 위치 서비스

## 🔧 설치 및 실행

### 1. 환경 설정
```bash
# 환경 변수 설정 (.env 파일 생성)
OPENAI_API_KEY=your_openai_api_key
KAKAO_API_KEY=your_kakao_api_key
KAKAO_CLIENT_ID=your_kakao_client_id
KAKAO_CLIENT_SECRET=your_kakao_client_secret
```

### 2. 백엔드 서버 실행
```bash
cd api
pip install -r requirements.txt
python main.py
```

### 3. AI 에이전트 서버 실행
```bash
cd ai-agents
python start_all_servers.py
```

## 📊 데이터베이스 스키마

### 핵심 테이블
- **users**: 사용자 정보 및 프로필
- **couples**: 커플 관계 관리
- **places**: 장소 정보
- **courses**: 데이트 코스
- **chat_sessions**: AI 채팅 세션

## 🌐 API 엔드포인트

### 사용자 관련
- `GET /users/me`: 사용자 정보 조회
- `POST /users/profile`: 프로필 설정
- `GET /users/check-nickname`: 닉네임 중복 확인

### 코스 관련
- `POST /courses/recommend`: AI 코스 추천
- `GET /courses/my`: 내 코스 목록
- `POST /courses/save`: 코스 저장

### 커플 관련
- `POST /couples/request`: 연인 신청
- `POST /couples/accept`: 연인 수락
- `GET /couples/status`: 연인 상태 조회

### 채팅 관련
- `POST /chat/sessions`: 새 채팅 세션 시작
- `POST /chat/message`: 메시지 전송
- `GET /chat/sessions`: 세션 목록 조회

## 🎨 사용 예시

### 1. 채팅을 통한 코스 추천
```python
# 새 채팅 세션 시작
POST /chat/sessions

# 메시지 전송
POST /chat/message
{
    "session_id": "uuid",
    "message": "강남에서 20대 INFP 연인과 저녁 데이트하고 싶어요"
}

# 코스 추천 받기
POST /chat/recommend
```

### 2. 직접 API 호출
```python
POST /courses/recommend
{
    "user_profile": {
        "age": 25,
        "mbti": "INFP",
        "relationship_stage": "연인",
        "budget": "medium"
    },
    "location": "강남구",
    "time_period": "저녁"
}
```

## 🔄 처리 플로우

1. **사용자 입력** → Main Agent에서 프로필 추출
2. **지역 분석** → Place Agent에서 좌표 및 지역 정보 제공
3. **코스 생성** → Date-Course Agent에서 벡터 검색 기반 코스 생성
4. **결과 반환** → 개인화된 데이트 코스 추천

## 📈 성능 특성

- **전체 추천 시간**: 30-90초 (평균 45초)
- **동시 처리**: 비동기 기반 다중 요청 처리
- **재시도 메커니즘**: 3단계 점진적 조건 완화
- **벡터 검색**: 의미적 유사성 기반 고품질 매칭

## 🛡️ 보안 및 인증

- **카카오 OAuth**: 안전한 소셜 로그인
- **세션 관리**: 사용자별 세션 격리
- **API 키 관리**: 환경변수를 통한 보안 키 관리

## 🔮 확장 계획

- **다른 도시 지원**: 부산, 대구 등 추가 지역
- **실시간 데이터**: 날씨, 교통, 혼잡도 연동
- **더 많은 카테고리**: 스포츠, 액티비티 등 확장
- **모바일 앱**: React Native 기반 모바일 버전

## 📄 라이선스

이 프로젝트는 MIT 라이선스를 따릅니다.