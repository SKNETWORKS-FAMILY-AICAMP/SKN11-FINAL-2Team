# 테스트 목적 및 설명

## 단위 테스트 (unit/)
각 모듈의 개별 기능을 테스트합니다.

### 테스트 파일 구조
- `test_weather_processor.py` - 날씨별 처리 로직 테스트
- `test_embedding_service.py` - 임베딩 서비스 테스트
- `test_vector_search.py` - 벡터 검색 엔진 테스트
- `test_distance_calculator.py` - 거리 계산 테스트
- `test_gpt_selector.py` - GPT 선택기 테스트

## 통합 테스트 (integration/)
전체 시스템의 통합 동작을 테스트합니다.

### 테스트 시나리오
- 전체 요청 처리 플로우
- 외부 API 연동 테스트
- 데이터베이스 연동 테스트

## 모의 데이터 (mock_data/)
테스트에 사용할 샘플 데이터들입니다.

### 포함된 데이터
- `sample_request.json` - 샘플 요청 데이터
- `sample_places.json` - 샘플 장소 데이터
- `sample_embeddings.json` - 샘플 임베딩 데이터
