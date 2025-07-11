# 데이터 폴더 설명
# 로컬 파일 기반 Qdrant 벡터 DB 관련 파일들

## 📁 폴더 구조

```
data/
├── qdrant_storage/          # Qdrant 벡터 DB 파일들 (자동 생성)
├── sample_places.json       # 샘플 장소 데이터
├── initialize_db.py         # DB 초기화 스크립트
└── README.md               # 이 파일
```

## 🚀 사용 방법

### 1. 벡터 DB 초기화
```bash
# 프로젝트 루트에서 실행
cd /Users/hwangjunho/Desktop/date-course-agent
python data/initialize_db.py
```

### 2. 실행 결과
- `data/qdrant_storage/` 폴더에 벡터 DB 파일들이 생성됩니다
- 샘플 장소 5개가 벡터화되어 저장됩니다
- 검색 테스트가 자동으로 실행됩니다

## 📊 포함된 샘플 데이터

1. **라 메종 블랑셰** (홍대 파인다이닝)
2. **더 바인 루프탑** (이태원 와인바) 
3. **아트센터 나비** (강남 미술관)
4. **힐링 스파 앤 사우나** (명동 스파)
5. **한강공원 여의도 구역** (야외활동)

## 🔧 실제 데이터 추가 방법

### sample_places.json 형식
```json
{
  "place_id": "unique_id",
  "place_name": "장소명",
  "latitude": 37.5519,
  "longitude": 126.9245,
  "description": "상세 설명 (8-10줄)",
  "category": "음식점|술집|문화시설|휴식시설|야외활동",
  "embedding_vector": []  // 자동 생성됨
}
```

### 새 데이터 추가 후 재초기화
```bash
python data/initialize_db.py
```

## 💡 장점

- **별도 서버 불필요**: Docker나 외부 DB 서버 설치 없이 바로 사용
- **포터블**: 프로젝트 폴더와 함께 이동 가능
- **백업 용이**: data/ 폴더만 복사하면 모든 데이터 백업
- **개발 친화적**: 로컬에서 즉시 테스트 가능

## ⚠️ 주의사항

- `qdrant_storage/` 폴더는 Git에 포함되지 않습니다 (.gitignore 처리)
- 실제 서비스에서는 더 많은 장소 데이터가 필요합니다
- 정기적인 데이터 업데이트를 위한 스케줄링 고려 필요
