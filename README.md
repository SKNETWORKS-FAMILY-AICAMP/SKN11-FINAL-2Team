# SKN11-FINAL-2Team
- SK네트웍스 Family AI 캠프 11기 2팀 Ofcourse
- 개발기간: 25.06.11 - 25.08.01

## 목차
1. 프로젝트 개요
2. 팅원소개
3. 주요 기능


## 프로젝트 소개

데이트 코스를 계획할 때의 번거로움과 정보 탐색의 불편함을 해결하기 위한 AI 기반 추천 서비스입니다. 사용자의 MBTI, 관계 단계, 선호도를 분석하여 최적의 데이트 코스를 추천합니다.

## 팀원 소개
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

| 항목                | 내용 |
|---------------------|------|
| Backend | <img src="https://img.shields.io/badge/fastapi-009688?style=for-the-badge&logo=fastapi&logoColor=white"> |
| Frontend | <img src="https://img.shields.io/badge/Next.js-000000?style=for-the-badge&logo=Next.js&logoColor=white"/> |
| AI Model | <img src="https://img.shields.io/badge/gpt4o-412991?style=for-the-badge&logo=openai&logoColor=white"> |
| DB | <img src="https://img.shields.io/badge/postgresql-4169E1?style=for-the-badge&logo=postgresql&logoColor=white"> |
| Vector DB | <img src="https://img.shields.io/badge/qdrant-F74E68?style=for-the-badge&logo=qdrant&logoColor=white"> |
| Infra | <img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=Docker&logoColor=white"/> <img src="https://img.shields.io/badge/Runpod-6438B1?style=for-the-badge&logo=Runpod&logoColor=white"/> <img src="https://img.shields.io/badge/Vercel-000000?style=for-the-badge&logo=Vercel&logoColor=white"/> |
| Collaboration Tool | <img src="https://img.shields.io/badge/Git-F05032?style=for-the-badge&logo=git&logoColor=white"/> <img src="https://img.shields.io/badge/GitHub-181717?style=for-the-badge&logo=GitHub&logoColor=white"/> |



## 🏗️ 시스템 아키텍처

![miro](https://github.com/user-attachments/assets/92210054-7e5e-4b6c-9206-8d2867eae7c9)


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


## 🔄 시스템 워크플로우

![flow](https://github.com/user-attachments/assets/3f1cfd8a-d640-4940-990e-91ffe68c2b77)



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

