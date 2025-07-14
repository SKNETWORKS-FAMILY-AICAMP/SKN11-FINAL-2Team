# .env 파일 사용 가이드

## 📋 환경변수 설정 가이드

### 1. 필수 설정
`.env` 파일에서 다음 값들을 반드시 설정해야 합니다:

#### OpenAI API 키 (필수)
```bash
OPENAI_API_KEY=sk-proj-your-actual-openai-api-key-here
```
- [OpenAI API 키 발급받기](https://platform.openai.com/api-keys)
- 계정 생성 → API Keys → Create new secret key

#### Qdrant 설정
```bash
QDRANT_HOST=localhost        # Qdrant 서버 주소
QDRANT_PORT=6333            # Qdrant 서버 포트
QDRANT_API_KEY=             # Qdrant Cloud 사용시에만 필요
```

### 2. 설정 파일 종류

#### `.env.example`
- 템플릿 파일 (Git에 포함됨)
- 실제 값 없이 구조만 보여줌
- 새로운 개발자가 참고용으로 사용

#### `.env`
- 실제 사용 파일 (Git에서 제외됨)
- 실제 API 키와 설정값 포함
- 이 파일에 실제 값을 입력하세요

### 3. 사용 방법

#### 단계 1: API 키 발급
1. OpenAI 계정 생성: https://platform.openai.com
2. API Keys 메뉴에서 새 키 생성
3. 생성된 키를 복사 (다시 볼 수 없으니 주의!)

#### 단계 2: .env 파일 수정
```bash
# .env 파일 열기
nano .env

# 또는 텍스트 에디터로
code .env
```

#### 단계 3: API 키 입력
```bash
# 이렇게 변경
OPENAI_API_KEY=sk-proj-abcd1234your-real-key-here
```

### 4. 보안 주의사항

#### ⚠️ 중요: API 키 보안
- `.env` 파일을 절대 Git에 커밋하지 마세요
- API 키를 코드에 직접 하드코딩하지 마세요
- 팀원과 공유 시 별도 안전한 방법 사용

#### .gitignore 설정
```bash
# 이미 .gitignore에 추가되어 있어야 함
.env
*.env
```

### 5. 테스트 방법

#### API 키 검증
```python
python -c "
from config.api_keys import api_keys
try:
    print('OpenAI API Key:', api_keys.openai_api_key[:10] + '...')
    print('✅ API 키가 올바르게 설정되었습니다.')
except Exception as e:
    print('❌ API 키 설정 오류:', e)
"
```

#### 환경변수 확인
```bash
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
print('OPENAI_API_KEY:', os.getenv('OPENAI_API_KEY', 'NOT SET')[:10] + '...')
print('QDRANT_HOST:', os.getenv('QDRANT_HOST'))
print('QDRANT_PORT:', os.getenv('QDRANT_PORT'))
"
```

### 6. 문제 해결

#### 환경변수가 로드되지 않는 경우
```bash
# python-dotenv 설치 확인
pip install python-dotenv

# .env 파일 위치 확인 (프로젝트 루트에 있어야 함)
ls -la .env
```

#### API 키가 작동하지 않는 경우
```bash
# OpenAI API 키 테스트
curl -H "Authorization: Bearer YOUR_API_KEY" https://api.openai.com/v1/models
```

### 7. 팀 협업 시

#### 새 팀원 온보딩
1. `.env.example` 파일을 `.env`로 복사
2. 실제 API 키 값 입력
3. 테스트 실행으로 검증

```bash
cp .env.example .env
# .env 파일 수정 후
python config/api_keys.py  # 검증 실행
```
