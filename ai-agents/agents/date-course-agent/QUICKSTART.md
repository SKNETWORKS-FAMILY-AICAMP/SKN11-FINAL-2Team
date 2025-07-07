# 빠른 시작 가이드 (로컬 파일 기반 Qdrant)

## 🚀 5분만에 시작하기

### 1단계: API 키 설정
```bash
# .env 파일 열기
code /Users/hwangjunho/Desktop/date-course-agent/.env

# OPENAI_API_KEY= 여기에 실제 키 입력
OPENAI_API_KEY=sk-proj-your-actual-key-here
```

### 2단계: 의존성 설치
```bash
cd /Users/hwangjunho/Desktop/date-course-agent
pip install -r requirements.txt
```

### 3단계: 벡터 DB 초기화 (별도 서버 불필요!)
```bash
python data/initialize_db.py
```

### 4단계: 테스트 실행
```bash
python src/main.py
```

## ✅ 성공 확인 방법

### 벡터 DB 초기화 성공 시
```
🚀 벡터 DB 초기화 시작...
✅ Qdrant 클라이언트 생성 완료
✅ 샘플 데이터 로드 완료: 5개 장소
✅ 임베딩 서비스 초기화 완료
✅ 임베딩 생성 완료
✅ 벡터 DB에 데이터 추가 완료
🎉 벡터 DB 초기화 완료!
```

### API 서버 실행 성공 시
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

## 🔧 주요 차이점 (기존 방식 vs 새 방식)

### 기존 방식 (서버 기반)
```bash
# Docker 설치 필요
docker run -p 6333:6333 qdrant/qdrant
# 별도 서버 관리 필요
# 네트워크 설정 복잡
```

### 새 방식 (파일 기반)
```bash
# 설치 불필요!
python data/initialize_db.py
# 파일로 자동 관리
# 즉시 사용 가능
```

## 📁 생성되는 파일들

```
data/
├── qdrant_storage/           # 🆕 자동 생성되는 벡터 DB 파일들
│   ├── collection/
│   ├── meta.json
│   └── storage.json
├── sample_places.json        # 샘플 장소 데이터
└── initialize_db.py          # 초기화 스크립트
```

## 🎯 다음 단계

1. **API 테스트**: http://localhost:8000/health
2. **코스 추천 테스트**: Postman이나 curl로 API 호출
3. **실제 데이터 추가**: sample_places.json에 더 많은 장소 추가
4. **메인 에이전트 연동**: LangChain Tool로 등록

## 💡 팁

- **백업**: `data/` 폴더만 복사하면 모든 데이터 백업
- **이동**: 프로젝트 폴더 통째로 이동 가능
- **공유**: 팀원에게 전체 폴더 공유하면 즉시 사용 가능
- **테스트**: 로컬에서 모든 기능 테스트 가능

별도 DB 서버 설치나 Docker 없이도 바로 사용할 수 있어요! 🎉