# 날씨별 병렬 처리 관리자 (스마트 버전)
# - 맑을 때/비올 때 시나리오를 병렬로 처리
# - 각 날씨별 임베딩 생성과 반경 계산 동시 실행
# - 조합 폭발 방지를 위한 스마트 처리

import asyncio
from typing import Dict, Any, List, Union
from loguru import logger
import copy
import os
import sys

# 상위 디렉토리의 모듈들 import
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from src.core.embedding_service import EmbeddingService
from src.core.radius_calculator import RadiusCalculator
from src.database.vector_search import SmartVectorSearchEngine  # 스마트 버전 사용
from src.core.course_optimizer import SmartCourseOptimizer      # 스마트 버전 사용
from src.agents.gpt_selector import SmartGPTSelector           # 스마트 버전 사용
from src.models.internal_models import WeatherScenarioResult
from src.models.request_models import SearchTargetModel
from src.utils.location_analyzer import location_analyzer # location_analyzer 임포트 추가

class SmartWeatherProcessor:
    """스마트 날씨별 데이트 코스 처리를 담당하는 클래스"""
    
    def __init__(self):
        """초기화"""
        # 스마트 서비스들을 즉시 초기화 (조합 폭발 방지)
        try:
            self.embedding_service = EmbeddingService()
            self.radius_calculator = RadiusCalculator()
            self.vector_search = SmartVectorSearchEngine()  # 다양성 보장 검색
            self.course_optimizer = SmartCourseOptimizer()  # 조합 폭발 방지
            self.gpt_selector = SmartGPTSelector()          # 적응형 선택
            self.location_analyzer = location_analyzer      # location_analyzer 초기화 추가
            logger.info("✅ 스마트 날씨 처리기 초기화 완료 - 조합 폭발 방지 기능 적용")
        except Exception as e:
            logger.error(f"❌ 서비스 초기화 실패: {e}")
            # 서비스들을 None으로 설정해두고 나중에 지연 초기화
            self.embedding_service = None
            self.radius_calculator = None
            self.vector_search = None
            self.course_optimizer = None
            self.gpt_selector = None
            self.location_analyzer = None # 오류 발생 시 함께 None으로 설정
            logger.info("✅ 스마트 날씨 처리기 초기화 완료 (지연 초기화)")
    
    async def _initialize_services(self):
        """서비스들을 지연 초기화"""
        try:
            if self.embedding_service is None:
                logger.info("🔧 스마트 서비스 초기화 시작...")
                self.embedding_service = EmbeddingService()
                self.radius_calculator = RadiusCalculator()
                self.vector_search = SmartVectorSearchEngine()
                self.course_optimizer = SmartCourseOptimizer()
                self.gpt_selector = SmartGPTSelector()
                logger.info("🔧 모든 스마트 서비스 초기화 완료")
        except Exception as e:
            logger.error(f"❌ 서비스 초기화 실패: {e}")
            raise
    
    async def process_both_weather_scenarios(
        self, 
        search_targets: List[Union[SearchTargetModel, Dict[str, Any]]], 
        user_context: Dict[str, Any], 
        course_planning: Dict[str, Any]
    ) -> Dict[str, WeatherScenarioResult]:
        """맑을 때와 비올 때 시나리오를 병렬로 처리 (스마트 버전 + 임베딩+위치분석 병렬화)"""
        try:
            category_count = len(search_targets)
            logger.info(f"🌤️ 스마트 날씨별 시나리오 병렬 처리 시작 - {category_count}개 카테고리")
            
            # 조합 수 예상 계산
            estimated_combinations = 3 ** category_count
            if estimated_combinations > 50:
                logger.info(f"⚡ 대량 조합 예상 ({estimated_combinations}개) - 스마트 처리 모드 활성화")
            
            # 서비스 초기화
            await self._initialize_services()
            
            # 병렬 실행 (임베딩+위치분석 병렬화 적용)
            sunny_task = self._process_scenario_parallel("sunny", search_targets, user_context, course_planning)
            rainy_task = self._process_scenario_parallel("rainy", search_targets, user_context, course_planning)
            
            sunny_result, rainy_result = await asyncio.gather(
                sunny_task, rainy_task, return_exceptions=True
            )
            
            # 예외 처리
            if isinstance(sunny_result, Exception):
                logger.error(f"❌ 맑은 날씨 처리 실패: {sunny_result}")
                sunny_result = self._create_failed_result("sunny", str(sunny_result))
            
            if isinstance(rainy_result, Exception):
                logger.error(f"❌ 비오는 날씨 처리 실패: {rainy_result}")
                rainy_result = self._create_failed_result("rainy", str(rainy_result))
            
            logger.info("✅ 스마트 날씨별 시나리오 병렬 처리 완료")
            return {
                'sunny': sunny_result,
                'rainy': rainy_result
            }
            
        except Exception as e:
            logger.error(f"❌ 스마트 날씨별 시나리오 처리 실패: {e}")
            return {
                'sunny': self._create_failed_result("sunny", str(e)),
                'rainy': self._create_failed_result("rainy", str(e))
            }
    
    async def _process_scenario_parallel(self, weather: str, search_targets: List[Dict], user_context: Dict, course_planning: Dict) -> WeatherScenarioResult:
        """특정 날씨 시나리오를 처리하는 병렬 최적화 로직 (임베딩+위치분석 병렬)"""
        try:
            logger.info(f"⚡ {weather.upper()} 시나리오 병렬 처리 시작")

            # 0. 카테고리 변환 내역 초기화 (모든 날씨에 대해)
            category_conversions = []
            original_targets = search_targets.copy()

            # 1. (필요시) 날씨에 따라 검색 타겟 수정
            if weather == "rainy":
                search_targets = self._convert_outdoor_categories_for_rainy(search_targets)
                category_conversions = self._get_category_conversions(original_targets, search_targets)

            # 2. 임베딩 생성과 위치분석을 병렬로 실행 ⚡
            embeddings_task = self._create_embeddings_for_targets(search_targets)
            location_task = self.location_analyzer.analyze_search_targets(search_targets, weather)
            
            # 병렬 실행으로 시간 단축
            embeddings, location_analysis = await asyncio.gather(
                embeddings_task, location_task
            )
            logger.info(f"✅ {weather.upper()} 임베딩+위치분석 병렬 완료")

            # 3. 수립된 전략에 따라 벡터 검색 수행 (재시도 로직 포함)
            search_result = await self.vector_search.search_with_retry_logic(
                search_targets=search_targets,
                embeddings=embeddings,
                location_analysis=location_analysis
            )
            
            # 4. 스마트 코스 조합 생성
            combinations = self.course_optimizer.generate_combinations(
                places=search_result.places,
                search_targets=search_targets,
                weather=weather,
                location_analysis=location_analysis
            )

            # 5. GPT를 통해 최종 코스 선택
            selected_courses = await self.gpt_selector.select_best_courses(
                combinations, user_context, weather, search_result.attempt
            )

            # 6. 최종 결과 생성
            result = WeatherScenarioResult(
                weather=weather,
                status="success" if selected_courses else "failed",
                attempt=search_result.attempt,
                radius_used=search_result.radius_used,
                courses=selected_courses,
                total_combinations=len(combinations),
                category_conversions=category_conversions
            )
            logger.info(f"✅ {weather.upper()} 시나리오 병렬 처리 완료")
            return result

        except Exception as e:
            logger.error(f"❌ {weather.upper()} 시나리오 병렬 처리 실패: {e}")
            return self._create_failed_result(weather, str(e))

    async def _process_scenario(self, weather: str, search_targets: List[Dict], user_context: Dict, course_planning: Dict) -> WeatherScenarioResult:
        """특정 날씨 시나리오를 처리하는 통합 로직"""
        try:
            logger.info(f"▶️  {weather.upper()} 시나리오 처리 시작")

            # 0. 카테고리 변환 내역 초기화 (모든 날씨에 대해)
            category_conversions = []
            original_targets = search_targets.copy()

            # 1. (필요시) 날씨에 따라 검색 타겟 수정
            if weather == "rainy":
                search_targets = self._convert_outdoor_categories_for_rainy(search_targets)
                category_conversions = self._get_category_conversions(original_targets, search_targets)

            # 2. 임베딩 생성
            embeddings = await self._create_embeddings_for_targets(search_targets)

            # 3. 위치 분석을 통해 검색 전략 수립 (가장 중요!)
            location_analysis = self.location_analyzer.analyze_search_targets(search_targets, weather)
            logger.info(f"💡 {weather.upper()} 시나리오 전략: {location_analysis['analysis_summary']}")

            # 4. 수립된 전략에 따라 벡터 검색 수행 (재시도 로직 포함)
            search_result = await self.vector_search.search_with_retry_logic(
                search_targets=search_targets,
                embeddings=embeddings,
                location_analysis=location_analysis
            )
            
            # 5. 스마트 코스 조합 생성
            combinations = self.course_optimizer.generate_combinations(
                places=search_result.places,
                search_targets=search_targets,
                weather=weather,
                location_analysis=location_analysis # 조합 시에도 위치 분석 결과 활용
            )

            # 6. GPT를 통해 최종 코스 선택
            selected_courses = await self.gpt_selector.select_best_courses(
                combinations, user_context, weather, search_result.attempt
            )

            # 7. 최종 결과 생성
            result = WeatherScenarioResult(
                weather=weather,
                status="success" if selected_courses else "failed",
                attempt=search_result.attempt,
                radius_used=search_result.radius_used,
                courses=selected_courses,
                total_combinations=len(combinations),
                category_conversions=category_conversions  # 카테고리 변환 내역 추가
            )
            logger.info(f"✅ {weather.upper()} 시나리오 처리 완료")
            return result

        except Exception as e:
            logger.error(f"❌ {weather.upper()} 시나리오 처리 실패: {e}")
            return self._create_failed_result(weather, str(e))
    
    async def _create_embeddings_for_targets(self, search_targets: List[Union[SearchTargetModel, Dict[str, Any]]]) -> List[List[float]]:
        """검색 대상들에 대한 임베딩 생성"""
        try:
            # Pydantic 모델과 딕셔너리 모두 지원
            semantic_queries = []
            for target in search_targets:
                if isinstance(target, SearchTargetModel):
                    semantic_queries.append(target.semantic_query)
                else:
                    semantic_queries.append(target['semantic_query'])
            
            embeddings = await self.embedding_service.create_semantic_embeddings(semantic_queries)
            return embeddings
            
        except Exception as e:
            logger.error(f"❌ 임베딩 생성 실패: {e}")
            raise
    
    async def _perform_smart_vector_search_with_boost(
        self,
        search_targets: List[Union[SearchTargetModel, Dict[str, Any]]],
        embeddings: List[List[float]],
        radius: int,
        weather: str
    ):
        """🔥 조합 부족 시 자동으로 top_K를 늘려서 재검색하는 스마트 벡터 검색"""
        try:
            logger.info(f"🔍 스마트 벡터 검색 시작 (조합 부족 시 자동 부스트) - {weather} 날씨, 반경 {radius}m")
            
            # 🔥 조합 부족 시 자동으로 top_K를 늘려서 재검색
            search_result = await self.vector_search.search_with_boosted_top_k_if_needed(
                search_targets=search_targets,
                embeddings=embeddings, 
                radius=radius,
                weather=weather,
                min_combinations_needed=6  # 🔥 최소 6개 조합 필요
            )
            
            logger.info(f"✅ 스마트 벡터 검색 완료 - {len(search_result.places)}개 장소, {search_result.attempt}")
            return search_result
            
        except Exception as e:
            logger.error(f"❌ 스마트 벡터 검색 (부스트) 실패: {e}")
            # 실패시 기본 검색으로 폴백
            return await self._perform_smart_vector_search(search_targets, embeddings, radius, weather)
    
    async def _perform_smart_vector_search(
        self, 
        search_targets: List[Union[SearchTargetModel, Dict[str, Any]]], 
        embeddings: List[List[float]], 
        radius: int, 
        weather: str
    ):
        """스마트 벡터 검색 수행 (다양성 보장 + 3단계 재시도)"""
        try:
            logger.info(f"🔍 스마트 벡터 검색 시작 - {weather} 날씨, 반경 {radius}m")
            
            search_result = await self.vector_search.search_with_retry_logic(
                search_targets=search_targets,
                embeddings=embeddings,
                radius=radius,
                weather=weather
            )
            
            logger.info(f"🔍 스마트 벡터 검색 완료 - {len(search_result.places)}개 장소, {search_result.attempt} 시도")
            return search_result
            
        except Exception as e:
            logger.error(f"❌ 스마트 벡터 검색 실패: {e}")
            raise
    
    def _convert_outdoor_categories_for_rainy(self, search_targets: List[Union[SearchTargetModel, Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """비오는 날씨에 맞게 야외활동 카테고리를 실내 카테고리로 변환"""
        # Pydantic 모델을 딕셔너리로 변환
        dict_targets = []
        for target in search_targets:
            if isinstance(target, SearchTargetModel):
                dict_targets.append({
                    'sequence': target.sequence,
                    'category': target.category,
                    'location': target.location.dict() if hasattr(target.location, 'dict') else target.location,
                    'semantic_query': target.semantic_query
                })
            else:
                dict_targets.append(target)
        
        modified_targets = copy.deepcopy(dict_targets)
        
        conversion_map = {
            "야외활동": ["문화시설", "엔터테인먼트", "휴식시설", "카페"],  # 야외활동을 실내 활동으로 변환
            "주차장": ["쇼핑", "문화시설", "카페"],  # 주차장도 실내로 변환
        }
        
        for i, target in enumerate(modified_targets):
            original_category = target['category']
            
            if original_category in conversion_map:
                # 스마트 로직: 순서에 따라 다른 카테고리 선택 (다양성 확보)
                alternatives = conversion_map[original_category]
                new_category = alternatives[i % len(alternatives)]
                target['category'] = new_category
                
                # semantic_query도 더 구체적으로 수정
                original_query = target['semantic_query']
                if "야외" in original_query:
                    if new_category == "문화시설":
                        target['semantic_query'] = original_query.replace("야외", "실내 문화공간에서의").replace("공원", "박물관이나 갤러리")
                    elif new_category == "엔터테인먼트":
                        target['semantic_query'] = original_query.replace("야외", "실내 엔터테인먼트 공간에서의").replace("공원", "영화관이나 게임센터")
                    elif new_category == "휴식시설":
                        target['semantic_query'] = original_query.replace("야외", "실내 휴식공간에서의").replace("공원", "스파나 찜질방")
                    elif new_category == "카페":
                        target['semantic_query'] = original_query.replace("야외", "아늑한 카페에서의").replace("공원", "분위기 좋은 카페")
                
                logger.info(f"🔄 카테고리 변환 (다양성 확보): {original_category} → {new_category} (순서: {i})")
        
        return modified_targets
    
    def _get_category_conversions(
        self, 
        original_targets: List[Union[SearchTargetModel, Dict[str, Any]]], 
        modified_targets: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        """카테고리 변환 내역 반환"""
        conversions = []
        
        for i, (original, modified) in enumerate(zip(original_targets, modified_targets)):
            # original이 Pydantic 모델인 경우 처리
            if isinstance(original, SearchTargetModel):
                original_category = original.category
                original_sequence = original.sequence
            else:
                original_category = original['category']
                original_sequence = original['sequence']
            
            if original_category != modified['category']:
                conversions.append({
                    'sequence': str(original_sequence),  # 문자열로 변환
                    'from_category': original_category,
                    'to_category': modified['category'],
                    'reason': '비오는 날씨로 인한 실내 활동 변경'
                })
        
        return conversions
    
    def _create_failed_result(self, weather: str, error_message: str) -> WeatherScenarioResult:
        """실패한 결과 생성"""
        return WeatherScenarioResult(
            weather=weather,
            status="failed",
            attempt="none",
            radius_used=0,
            courses=[],
            total_combinations=0,
            error_message=error_message
        )

# 하위 호환성을 위한 별칭
WeatherProcessor = SmartWeatherProcessor
