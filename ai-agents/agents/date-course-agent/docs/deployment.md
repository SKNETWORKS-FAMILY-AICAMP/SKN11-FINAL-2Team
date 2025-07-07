# 배포 가이드

## 로컬 개발 환경 설정

### 1. Python 환경 설정
```bash
# Python 3.8+ 필요
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 환경변수 설정
```bash
# .env 파일 생성
cat > .env << EOF
OPENAI_API_KEY=your_openai_api_key_here
QDRANT_HOST=localhost
QDRANT_PORT=6333
LOG_LEVEL=INFO
EOF
```

### 3. Qdrant 설치 및 실행
```bash
# Docker로 Qdrant 실행
docker run -p 6333:6333 qdrant/qdrant

# 또는 직접 설치
pip install qdrant-client
```

### 4. 테스트 실행
```bash
python -m pytest tests/
```

## 프로덕션 배포

### Docker 배포

#### Dockerfile 작성
```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "src/main.py"]
```

#### Docker Compose
```yaml
version: '3.8'

services:
  date-course-agent:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - QDRANT_HOST=qdrant
      - QDRANT_PORT=6333
    depends_on:
      - qdrant

  qdrant:
    image: qdrant/qdrant
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage

volumes:
  qdrant_data:
```

### 클라우드 배포 (AWS)

#### AWS ECS 배포
```bash
# ECR에 이미지 푸시
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

docker build -t date-course-agent .
docker tag date-course-agent:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/date-course-agent:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/date-course-agent:latest

# ECS 서비스 생성
aws ecs create-service --cluster date-course-cluster --service-name date-course-agent --task-definition date-course-agent:1 --desired-count 2
```

## 모니터링 및 로깅

### 헬스 체크
```bash
curl http://localhost:8000/health
```

### 로그 모니터링
```bash
# 로그 확인
tail -f logs/app.log

# 도커 로그
docker logs date-course-agent
```

### 메트릭 수집
- 응답 시간
- 성공률
- 재시도 횟수
- 메모리/CPU 사용량

## 보안 설정

### API 키 보안
```bash
# AWS Secrets Manager 사용
aws secretsmanager create-secret --name date-course-agent/openai-key --secret-string '{"OPENAI_API_KEY":"your-key"}'
```

### 네트워크 보안
```bash
# VPC 내부 통신만 허용
# Security Group 설정
aws ec2 create-security-group --group-name date-course-sg --description "Date Course Agent Security Group"
```

## 성능 튜닝

### 메모리 최적화
```python
# 메모리 사용량 모니터링
import psutil
print(f"Memory usage: {psutil.Process().memory_info().rss / 1024 / 1024:.2f} MB")
```

### 동시성 설정
```python
# FastAPI 워커 수 조정
uvicorn.run(app, host="0.0.0.0", port=8000, workers=4)
```

## 백업 및 복구

### 벡터 DB 백업
```bash
# Qdrant 스냅샷 생성
curl -X POST "http://localhost:6333/collections/date_course_places/snapshots"
```

### 설정 백업
```bash
# 환경변수 백업
cp .env .env.backup
```

## 장애 대응

### 일반적인 문제 해결

#### OpenAI API 오류
```bash
# API 키 확인
curl -H "Authorization: Bearer $OPENAI_API_KEY" https://api.openai.com/v1/models
```

#### Qdrant 연결 오류
```bash
# Qdrant 상태 확인
curl http://localhost:6333/health
```

#### 메모리 부족
```bash
# 메모리 사용량 확인
free -h
```

### 롤백 절차
1. 이전 버전 Docker 이미지로 롤백
2. 데이터베이스 스냅샷 복구
3. 설정 파일 복원

## 업데이트 절차

### 무중단 배포
```bash
# Blue-Green 배포
docker-compose -f docker-compose.blue.yml up -d
# 헬스 체크 후
docker-compose -f docker-compose.green.yml down
```
