# RAG Agent 설치 및 실행 가이드

## 🚀 빠른 시작 (3분 설정)

### 1. 환경변수 설정
```bash
# .env 파일 생성
cp .env.example .env

# .env 파일 편집
# OPENAI_API_KEY=sk-your-actual-api-key-here
```

### 2. 의존성 설치
```bash
pip install -r requirements.txt
```

### 3. 벡터 DB 초기화
```bash
cd data
python initialize_db.py
```

### 4. 서버 실행
```bash
python run_server.py
```

**끝!** 🎉 이제 http://localhost:8000 에서 RAG Agent가 실행됩니다.

---

## 📋 상세 설정 가이드

### ✅ 필수 요구사항
- **Python 3.8+**
- **OpenAI API 키** (유료 계정 권장)
- **인터넷 연결** (OpenAI API 호출용)

### 🔧 환경변수 설정

#### 필수 설정 (반드시 설정!)
```bash
OPENAI_API_KEY=sk-your-actual-api-key-here
```

#### 선택적 설정 (기본값 사용 가능)
```bash
# OpenAI 모델 (기본값 권장)
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_GPT_MODEL=gpt-4o-mini

# 검색 반경 (미터 단위)
DEFAULT_SEARCH_RADIUS=1000

# 서버 포트
SERVER_PORT=8000
```

### 📊 벡터 DB 설정

**Qdrant는 로컬 파일 모드로 실행** (별도 서버 불필요!)
```bash
# 자동으로 생성됨
data/qdrant_storage/
```

### 🧪 동작 테스트

#### 1. API 키 검증
```bash
python config/api_keys.py
# 출력: ✅ API 키가 올바르게 설정되었습니다.
```

#### 2. 설정 확인
```bash
python config/settings.py
# 출력: ✅ 모든 설정이 올바르게 구성되었습니다!
```

#### 3. 벡터 DB 확인
```bash
python data/initialize_db.py
# 출력: ✅ 벡터 DB 초기화 완료!
```

#### 4. 서버 테스트
```bash
curl -X POST http://localhost:8000/recommend-course \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "test",
    "timestamp": "2025-07-02T12:00:00Z",
    "search_targets": ["홍대", "맛집", "카페"],
    "user_context": {
      "age": 25,
      "gender": "남성",
      "mbti": "ENFP",
      "relationship_status": "연인"
    },
    "course_planning": {
      "duration": "3시간",
      "budget": "5만원",
      "preferences": ["로맨틱", "힙함"]
    }
  }'
```

---

## 🔍 문제 해결

### ❌ 자주 발생하는 오류

#### 1. "OPENAI_API_KEY가 설정되지 않았습니다"
```bash
# .env 파일 확인
cat .env

# API 키가 올바른지 확인
echo $OPENAI_API_KEY
```

#### 2. "모듈을 찾을 수 없습니다"
```bash
# 의존성 재설치
pip install -r requirements.txt

# Python 경로 확인
python -c "import sys; print(sys.path)"
```

#### 3. "벡터 DB 연결 실패"
```bash
# 벡터 DB 재초기화
rm -rf data/qdrant_storage
python data/initialize_db.py
```

#### 4. "포트가 이미 사용 중"
```bash
# 다른 포트 사용
export SERVER_PORT=8001
python run_server.py

# 또는 기존 프로세스 종료
lsof -ti:8000 | xargs kill -9
```

### 📱 서버 상태 확인

#### Health Check
```bash
curl http://localhost:8000/health
# 출력: {"status": "healthy"}
```

#### 로그 확인
```bash
# 서버 실행 시 실시간 로그 확인
python run_server.py --log-level DEBUG
```

---

## 🚀 성능 최적화

### 빠른 실행을 위한 팁

#### 1. 환경변수 최적화
```bash
# 더 빠른 처리를 위해
MAX_WORKERS=20
REQUEST_TIMEOUT=60.0
```

#### 2. 캐싱 활용
```bash
# OpenAI API 호출 최소화
OPENAI_TEMPERATURE=0.3  # 일관된 결과
```

#### 3. 검색 범위 조정
```bash
# 더 정확한 결과를 위해
DEFAULT_SEARCH_RADIUS=800  # 800m로 축소
MAX_TOTAL_DISTANCE=2500    # 2.5km로 축소
```

---

## 📞 지원

### 문제 발생 시
1. **로그 확인**: 서버 실행 시 출력되는 로그 확인
2. **설정 검증**: `python config/settings.py` 실행
3. **의존성 확인**: `pip list | grep -E "(openai|qdrant|fastapi)"`
4. **팀 슬랙**: #rag-agent 채널에 문의

### 개발자 연락처
- **GitHub**: @your-github-username
- **담당자**: RAG Agent 개발팀

---

## 📈 모니터링

### 서버 모니터링
```bash
# CPU/메모리 사용량
top -p $(pgrep -f "python.*run_server.py")

# 요청 응답시간 확인
curl -w "@curl-format.txt" -s -o /dev/null http://localhost:8000/health
```

### 성능 지표
- **평균 응답시간**: 4-6초
- **검색 성공률**: 95%+
- **메모리 사용량**: ~500MB
- **동시 요청 처리**: 10개+