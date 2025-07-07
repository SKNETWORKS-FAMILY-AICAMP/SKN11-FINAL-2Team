# 실제 장소 데이터를 벡터 DB에 로드하는 스크립트
# - data/places 디렉토리의 데이터를 읽어서 임베딩 생성 후 Qdrant에 저장

import asyncio
import json
import os
import sys
from typing import List, Dict, Any
from loguru import logger
import time

# 프로젝트 루트 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.core.embedding_service import EmbeddingService
from src.database.qdrant_client import get_qdrant_client
from config.settings import Settings

class VectorDBLoader:
    """data/places 디렉토리 데이터를 벡터 DB에 로드"""
    
    def __init__(self):
        """초기화"""
        self.embedding_service = None
        self.qdrant_client = get_qdrant_client()
        # 프로젝트 내부 places 디렉토리 사용
        self.places_data_path = os.path.join(os.path.dirname(__file__), "places")
        self.batch_size = 20  # 임베딩 배치 크기 (너무 크면 API 한도 초과)
        
        # 카테고리 파일 목록
        self.category_files = [
            "음식점.json", "카페.json", "술집.json", "문화시설.json", 
            "휴식시설.json", "야외활동.json", "엔터테인먼트.json", 
            "쇼핑.json", "주차장.json", "기타.json"
        ]
        
        logger.info(f"✅ 벡터 DB 로더 초기화 완료 - 데이터 경로: {self.places_data_path}")
    
    async def load_all_data(self):
        """모든 카테고리 데이터를 벡터 DB에 로드"""
        try:
            logger.info("🚀 벡터 DB 로딩 시작")
            start_time = time.time()
            
            # places 디렉토리 존재 확인
            if not os.path.exists(self.places_data_path):
                raise FileNotFoundError(f"❌ places 디렉토리가 없습니다: {self.places_data_path}")
            
            # 임베딩 서비스 초기화
            self.embedding_service = EmbeddingService()
            
            # 기존 컬렉션 초기화 (선택사항)
            logger.info("🗑️ 기존 컬렉션 초기화")
            self.qdrant_client.clear_collection()
            
            total_loaded = 0
            successful_categories = 0
            
            # 각 카테고리별로 처리
            for category_file in self.category_files:
                category_name = category_file.replace('.json', '')
                logger.info(f"📂 {category_name} 카테고리 처리 시작")
                
                loaded_count = await self.load_category_data(category_file, category_name)
                if loaded_count > 0:
                    successful_categories += 1
                    total_loaded += loaded_count
                    logger.info(f"✅ {category_name} 완료 - {loaded_count}개 로드")
                else:
                    logger.warning(f"⚠️ {category_name} - 로드된 데이터 없음")
                
                # 잠시 대기 (API 레이트 리밋 방지)
                await asyncio.sleep(1)
            
            end_time = time.time()
            duration = end_time - start_time
            
            logger.info(f"🎉 전체 로딩 완료!")
            logger.info(f"   성공한 카테고리: {successful_categories}/{len(self.category_files)}")
            logger.info(f"   총 {total_loaded}개 장소 로드")
            logger.info(f"   소요 시간: {duration:.1f}초")
            
            # 컬렉션 정보 확인
            collection_info = self.qdrant_client.get_collection_info()
            logger.info(f"📊 최종 컬렉션 정보: {collection_info}")
            
            if total_loaded == 0:
                logger.error("❌ 로드된 데이터가 없습니다!")
                logger.error("   다음을 확인해주세요:")
                logger.error(f"   1. 파일 경로: {self.places_data_path}")
                logger.error("   2. JSON 파일들이 올바른 위치에 있는지")
                logger.error("   3. 파일 내용이 올바른 형식인지")
            
        except Exception as e:
            logger.error(f"❌ 벡터 DB 로딩 실패: {e}")
            raise
    
    async def load_category_data(self, category_file: str, category_name: str) -> int:
        """특정 카테고리 데이터 로드"""
        try:
            file_path = os.path.join(self.places_data_path, category_file)
            
            # 파일 존재 확인
            if not os.path.exists(file_path):
                logger.warning(f"⚠️ 파일 없음: {file_path}")
                return 0
            
            # 파일 크기 확인
            file_size = os.path.getsize(file_path)
            logger.info(f"📄 {category_file} - 파일 크기: {file_size:,} bytes")
            
            # JSON 파일 읽기
            with open(file_path, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
            
            logger.info(f"📖 {category_file} 읽기 완료 - {len(raw_data)}개 항목")
            
            # 데이터 검증 및 필터링
            valid_data = self.validate_and_filter_data(raw_data, category_name)
            logger.info(f"✅ 유효한 데이터 - {len(valid_data)}개 항목")
            
            if not valid_data:
                logger.warning(f"⚠️ {category_name}에 유효한 데이터 없음")
                return 0
            
            # 배치별로 처리
            total_processed = 0
            batch_count = (len(valid_data) - 1) // self.batch_size + 1
            
            for i in range(0, len(valid_data), self.batch_size):
                batch = valid_data[i:i + self.batch_size]
                batch_num = i // self.batch_size + 1
                
                logger.info(f"🔄 {category_name} 배치 {batch_num}/{batch_count} 처리 중... ({len(batch)}개)")
                
                processed_count = await self.process_batch(batch, category_name)
                total_processed += processed_count
                
                # 진행률 표시
                progress = (batch_num / batch_count) * 100
                logger.info(f"   📈 {category_name} 진행률: {progress:.1f}% ({total_processed}/{len(valid_data)})")
                
                # 배치 간 대기 (API 레이트 리밋 방지)
                if i + self.batch_size < len(valid_data):
                    await asyncio.sleep(2)
            
            return total_processed
            
        except Exception as e:
            logger.error(f"❌ {category_file} 처리 실패: {e}")
            return 0
    
    def validate_and_filter_data(self, raw_data: List[Dict], category_name: str) -> List[Dict]:
        """데이터 검증 및 필터링"""
        valid_data = []
        skipped_count = 0
        
        for item in raw_data:
            try:
                # 필수 필드 확인 (새로운 JSON 구조에 맞게 수정)
                if not all(key in item for key in ['place_id', 'name', 'latitude', 'longitude', 'summary']):
                    skipped_count += 1
                    continue
                
                # place_id가 비어있지 않은지 확인
                if not item['place_id'] or len(item['place_id'].strip()) < 5:
                    skipped_count += 1
                    continue
                
                # summary가 비어있지 않은지 확인
                if not item['summary'] or len(item['summary'].strip()) < 10:
                    skipped_count += 1
                    continue
                
                # name이 비어있지 않은지 확인
                if not item['name'] or len(item['name'].strip()) < 1:
                    skipped_count += 1
                    continue
                
                # 위도 경도 유효성 확인
                try:
                    lat = float(item['latitude'])
                    lon = float(item['longitude'])
                    if not (33 <= lat <= 39 and 124 <= lon <= 132):  # 대한민국 범위
                        skipped_count += 1
                        continue
                except (ValueError, TypeError):
                    skipped_count += 1
                    continue
                
                # 유효한 데이터로 변환 (새로운 JSON 구조 지원)
                valid_item = {
                    'place_id': item['place_id'].strip(),  # 실제 place_id 사용
                    'place_name': item['name'].strip(),
                    'latitude': float(item['latitude']),
                    'longitude': float(item['longitude']),
                    'address': item.get('address', '').strip(),  # 새로 추가
                    'kakao_url': item.get('kakao_url', '').strip(),  # 새로 추가
                    'description': item.get('description', '').strip(),
                    'summary': item['summary'].strip(),
                    'category': category_name,
                    'price': item.get('price', [])
                    # 'original_id': item.get('id', 0)  # 기존 id는 optional
                }
                
                valid_data.append(valid_item)
                
            except Exception as e:
                skipped_count += 1
                logger.debug(f"데이터 검증 실패: {e}")
                continue
        
        if skipped_count > 0:
            logger.info(f"   ⚠️ 스킵된 항목: {skipped_count}개")
        
        return valid_data
    
    async def process_batch(self, batch: List[Dict], category_name: str) -> int:
        """배치 데이터 처리 (임베딩 생성 및 저장)"""
        try:
            # 임베딩할 텍스트 준비 (description + summary)
            embedding_texts = []
            for item in batch:
                # description과 summary 결합
                combined_text = f"{item['description']} {item['summary']}".strip()
                if not combined_text or combined_text == item['summary']:
                    combined_text = item['summary']  # description이 비어있으면 summary만 사용
                embedding_texts.append(combined_text)
            
            # 임베딩 생성
            logger.debug(f"🧠 임베딩 생성 중... ({len(embedding_texts)}개)")
            embeddings = await self.embedding_service.create_embeddings(embedding_texts)
            
            # 벡터 DB에 저장할 데이터 준비 (새로운 필드 추가)
            places_data = []
            for item, embedding in zip(batch, embeddings):
                place_data = {
                    'place_id': item['place_id'],  # 실제 place_id 사용
                    'place_name': item['place_name'],
                    'latitude': item['latitude'],
                    'longitude': item['longitude'],
                    'address': item['address'],  # 새로 추가
                    'kakao_url': item['kakao_url'],  # 새로 추가
                    'description': f"{item['description']} {item['summary']}".strip(),  # 벡터 생성용
                    'summary': item['summary'],  # 원본 summary 보관
                    'category': item['category'],
                    'embedding_vector': embedding,
                    # 추가 메타데이터
                    'price': item['price']
                    # 'original_id': item['original_id']
                }
                places_data.append(place_data)
            
            # Qdrant에 저장
            logger.debug(f"💾 벡터 DB에 저장 중... ({len(places_data)}개)")
            self.qdrant_client.add_places(places_data)
            
            logger.debug(f"✅ 배치 처리 완료 - {len(places_data)}개 저장")
            return len(places_data)
            
        except Exception as e:
            logger.error(f"❌ 배치 처리 실패: {e}")
            return 0
    
    async def test_search(self):
        """로딩 후 테스트 검색"""
        try:
            logger.info("🔍 테스트 검색 시작")
            
            # 테스트 쿼리들
            test_queries = [
                "로맨틱한 레스토랑에서 저녁 식사",
                "커피와 디저트를 즐길 수 있는 카페",
                "문화 활동을 할 수 있는 장소"
            ]
            
            for query in test_queries:
                logger.info(f"🔍 검색 쿼리: '{query}'")
                
                test_embedding = await self.embedding_service.create_single_embedding(query)
                
                # 검색 실행
                results = await self.qdrant_client.search_vectors(
                    query_vector=test_embedding,
                    limit=3
                )
                
                logger.info(f"   📋 결과 {len(results)}개:")
                for i, result in enumerate(results):
                    logger.info(f"      {i+1}. {result['place_name']} ({result['category']}) - 유사도: {result['similarity_score']:.3f}")
                logger.info("")
            
        except Exception as e:
            logger.error(f"❌ 테스트 검색 실패: {e}")
    
    def show_file_status(self):
        """파일 상태 확인"""
        logger.info("📋 파일 상태 확인:")
        logger.info(f"   📁 데이터 경로: {self.places_data_path}")
        
        for category_file in self.category_files:
            file_path = os.path.join(self.places_data_path, category_file)
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                logger.info(f"   ✅ {category_file} - {file_size:,} bytes")
            else:
                logger.info(f"   ❌ {category_file} - 파일 없음")

async def main():
    """메인 실행 함수"""
    try:
        loader = VectorDBLoader()
        
        # 파일 상태 확인
        loader.show_file_status()
        
        # 모든 데이터 로드
        await loader.load_all_data()
        
        # 테스트 검색
        await loader.test_search()
        
        logger.info("🎉 벡터 DB 구축 완료!")
        logger.info("이제 'python src/main.py'로 시스템을 실행할 수 있습니다.")
        
    except Exception as e:
        logger.error(f"❌ 실행 실패: {e}")
        raise

if __name__ == "__main__":
    # 로거 설정
    logger.add("vector_db_loading.log", rotation="1 day", level="INFO")
    
    # 실행
    asyncio.run(main())
