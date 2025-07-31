# SKN11-FINAL-2Team
- SK네트웍스 Family AI 캠프 11기 2팀 Ofcourse
- 개발기간: 25.06.11 - 25.08.01

# 목차



# 팀원 소개
### 👤 팀원
<table>
  <tr>
    <td align="center">
      <img src="https://github.com/user-attachments/assets/a5dbdb16-ecc3-430a-9909-0b5dc8bbf79a" width="120" />
    </td>
    <td align="center">
      <img src="https://github.com/user-attachments/assets/7249aadb-96df-4a98-9af0-ca3c9038c844" width="120" />
    </td>
    <td align="center">
      <img src="https://github.com/user-attachments/assets/b048ec2c-193b-46d2-8d19-2d34f15a2001" width="120" />
    </td>
    <td align="center">
      <img src="https://github.com/user-attachments/assets/45531234-f60c-46ab-9a37-f040ffbbe177" width="120" />
    </td>
    <td align="center">
      <img src="https://github.com/user-attachments/assets/31560ea0-f0c6-4a43-a76a-2b46124da082" width="120" />
    </td>
  </tr>
  <tr>
    <td align="center">
      <a href="https://github.com/misong-hub">백미송</a>
    </td>
    <td align="center">
      <a href="https://github.com/HybuKimo">신준희</a>
    </td>
    <td align="center">
      <a href="https://github.com/Seonh0">이선호</a>
    </td>
    <td align="center">
      <a href="https://github.com/Minor1862">정민호</a>
    </td>
    <td align="center">
      <a href="https://github.com/junoaplus">황준호</a>
    </td>
  </tr>
</table>
<br/>


# 프로젝틑 소개

데이트 코스를 계획할 때의 번거로움과 정보 탐색의 불편함을 해결하기 위한 AI 기반 추천 서비스입니다. 사용자의 MBTI, 관계단계, 선호도를 분석하여 최적의 데이트 코스를 추천합니다.


## 🏗️ 시스템 아키텍처

```
Frontend (React) ← → API Server (FastAPI) ← → AI Services (3 Services)
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
├── ai-Services/             # AI Service 시스템
│   ├── Services/
│   │   ├── main-Service/    # 메인 오케스트레이터
│   │   ├── place-Service/   # 지역 분석 Service
│   │   └── date-course-Service/ # 코스 생성 Service
│   └── start_all_servers.py   # 모든 Service 서버 실행
│
└── README.md
```

## 🚀 주요 기능

### 🤖 AI Service 시스템
- **Main Service**: 사용자 프로필 추출 및 Service 오케스트레이션
- **Place Service**: 카카오 API 연동 지역 분석 및 좌표 제공
- **Date-Course Service**: Qdrant 벡터 DB 기반 개인화 코스 생성

### 🎯 개인화 추천
- **MBTI 기반**: 16가지 성격 유형별 맞춤 추천
- **관계 단계**: 연인/썸/소개팅 차별화된 코스
- **예산 고려**: 금액대별 예산 수준별 추천
- **날씨 대응**: 맑은 날/비오는 날 시나리오 분리

### 🔗 소셜 기능
- **커플 시스템**: 연인 신청/수락/관리
- **코스 공유**: 추천받은 코스를 연인 또는 커뮤니티에 공유 가능
- **댓글 시스템**: 코스에 대한 피드백 및 후기
- **후기 및 별점**: 장소 및 코스에 대한 후기 작성 및 별점 평가
- **카카오 로그인**: 간편한 소셜 로그인

## 🛠️ 기술 스택

| Backend | FastAPI, WebSocket |
| Frontend | next.js, Tailwind |
| AI Model | GPT-4 |
| DB | PostgreSQL |
| Vector DB | Qdrant |
| Infra | Docker, RunPod, Vercel |
| Collaboration Tool | Git, Github |

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

### 3. AI Service 서버 실행
```bash
cd ai-Services
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

1. **사용자 입력** → Main Service에서 프로필 추출
2. **지역 분석** → Place Service에서 좌표 및 지역 정보 제공
3. **코스 생성** → Date-Course Service에서 벡터 검색 기반 코스 생성
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

## 🚀 향후 계획

- **AI 서비스 고도화**: 사용자 피드백 및 데이터 분석 바탕으로 서비스 고도화
- **서비스 지역 확장**: 경기, 부산 등 주요 지역 데이터 구축
- **UI/UX 개선**: 채팅 UI/UX 및 로딩 속도 개선
- **비즈니스 모델 추가**: 구독형 상품 및 제휴 광고 추가

