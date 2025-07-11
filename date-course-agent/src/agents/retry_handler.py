# 재시도 로직 관리
# - 3단계 검색 전략 관리
# - 실패 시 제약 조건 완화

import asyncio
from typing import Dict, Any, List, Optional
from loguru import logger
import os
import sys

# 상위 디렉토리의 모듈들 import
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from src.models.internal_models import RetryResult, FailureReason

class RetryHandler:
    """재시도 로직 관리자"""
    
    def __init__(self):
        """초기화"""
        self.max_attempts = int(os.getenv("MAX_SEARCH_ATTEMPTS", "3"))
        self.radius_expansion_factor = float(os.getenv("RADIUS_EXPANSION_FACTOR", "1.5"))
        self.top_k_expansion_factor = 1.67  # 3 -> 5
        
        logger.info(f"✅ 재시도 핸들러 초기화 완료 - 최대 시도: {self.max_attempts}회")
    
    async def execute_with_retry(
        self, 
        search_function, 
        initial_params: Dict[str, Any],
        validation_function = None
    ) -> RetryResult:
        """재시도 로직으로 검색 함수 실행"""
        try:
            logger.info("🔄 재시도 로직 실행 시작")
            
            attempts = []
            current_params = initial_params.copy()
            
            for attempt in range(1, self.max_attempts + 1):
                logger.info(f"🎯 {attempt}차 시도 시작")
                
                # 시도별 파라미터 조정
                if attempt == 1:
                    # 1차: 원본 파라미터
                    current_params = self._prepare_first_attempt_params(initial_params)
                elif attempt == 2:
                    # 2차: Top K 확대
                    current_params = self._prepare_second_attempt_params(initial_params)
                elif attempt == 3:
                    # 3차: 반경 확대
                    current_params = self._prepare_third_attempt_params(initial_params)
                
                # 검색 실행
                try:
                    start_time = asyncio.get_event_loop().time()
                    result = await search_function(**current_params)
                    end_time = asyncio.get_event_loop().time()
                    
                    # 시도 기록
                    attempt_record = {
                        'attempt': attempt,
                        'params': current_params.copy(),
                        'result': result,
                        'duration': end_time - start_time,
                        'success': self._is_successful_result(result, validation_function)
                    }
                    attempts.append(attempt_record)
                    
                    # 성공 시 종료
                    if attempt_record['success']:
                        logger.info(f"✅ {attempt}차 시도 성공")
                        return RetryResult(
                            success=True,
                            final_attempt=attempt,
                            final_result=result,
                            attempts_history=attempts,
                            constraints_relaxed=self._get_relaxed_constraints(attempt, initial_params, current_params)
                        )
                    else:
                        logger.warning(f"❌ {attempt}차 시도 실패")
                        
                except Exception as e:
                    logger.error(f"❌ {attempt}차 시도 중 오류: {e}")
                    attempt_record = {
                        'attempt': attempt,
                        'params': current_params.copy(),
                        'result': None,
                        'duration': 0,
                        'success': False,
                        'error': str(e)
                    }
                    attempts.append(attempt_record)
            
            # 모든 시도 실패
            logger.error(f"❌ 모든 재시도 실패 ({self.max_attempts}회)")
            return RetryResult(
                success=False,
                final_attempt=self.max_attempts,
                final_result=None,
                attempts_history=attempts,
                failure_reason=self._analyze_failure_reason(attempts)
            )
            
        except Exception as e:
            logger.error(f"❌ 재시도 로직 실행 실패: {e}")
            return RetryResult(
                success=False,
                final_attempt=0,
                final_result=None,
                attempts_history=[],
                failure_reason=FailureReason(
                    type="system_error",
                    message=str(e),
                    suggestions=["시스템을 재시작해보세요", "네트워크 연결을 확인해보세요"]
                )
            )
    
    def _prepare_first_attempt_params(self, initial_params: Dict[str, Any]) -> Dict[str, Any]:
        """1차 시도 파라미터 준비 (원본)"""
        params = initial_params.copy()
        params['top_k'] = int(os.getenv("FIRST_ATTEMPT_TOP_K", "3"))
        params['attempt_type'] = "first"
        return params
    
    def _prepare_second_attempt_params(self, initial_params: Dict[str, Any]) -> Dict[str, Any]:
        """2차 시도 파라미터 준비 (Top K 확대)"""
        params = initial_params.copy()
        params['top_k'] = int(os.getenv("SECOND_ATTEMPT_TOP_K", "5"))
        params['attempt_type'] = "second"
        return params
    
    def _prepare_third_attempt_params(self, initial_params: Dict[str, Any]) -> Dict[str, Any]:
        """3차 시도 파라미터 준비 (반경 확대)"""
        params = initial_params.copy()
        
        # 반경 확대
        if 'radius' in params:
            params['radius'] = int(params['radius'] * self.radius_expansion_factor)
        
        # Top K는 다시 기본값으로
        params['top_k'] = int(os.getenv("FIRST_ATTEMPT_TOP_K", "3"))
        params['attempt_type'] = "third"
        
        return params
    
    def _is_successful_result(self, result: Any, validation_function = None) -> bool:
        """결과가 성공적인지 판단"""
        try:
            # 커스텀 검증 함수가 있으면 사용
            if validation_function:
                return validation_function(result)
            
            # 기본 검증 로직
            if result is None:
                return False
            
            # 딕셔너리 형태의 결과
            if isinstance(result, dict):
                if result.get('status') == 'failed':
                    return False
                if result.get('total_found', 0) == 0:
                    return False
                return True
            
            # 리스트 형태의 결과
            if isinstance(result, list):
                return len(result) > 0
            
            # 기타 객체
            if hasattr(result, 'status'):
                return result.status != 'failed'
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 결과 검증 실패: {e}")
            return False
    
    def _get_relaxed_constraints(
        self, 
        attempt: int, 
        initial_params: Dict[str, Any], 
        final_params: Dict[str, Any]
    ) -> List[str]:
        """완화된 제약 조건 목록 반환"""
        relaxed = []
        
        if attempt == 2:
            relaxed.append("검색 결과 수 확대 (Top 3 → Top 5)")
        elif attempt == 3:
            initial_radius = initial_params.get('radius', 0)
            final_radius = final_params.get('radius', 0)
            if final_radius > initial_radius:
                relaxed.append(f"검색 반경 확대 ({initial_radius}m → {final_radius}m)")
            relaxed.append("검색 결과 수 확대 (Top 3 → Top 5)")
        
        return relaxed
    
    def _analyze_failure_reason(self, attempts: List[Dict]) -> FailureReason:
        """실패 원인 분석"""
        try:
            # 모든 시도에서 오류가 발생한 경우
            if all(attempt.get('error') for attempt in attempts):
                return FailureReason(
                    type="system_error",
                    message="모든 시도에서 시스템 오류가 발생했습니다.",
                    suggestions=[
                        "네트워크 연결을 확인해보세요",
                        "API 키가 올바른지 확인해보세요",
                        "잠시 후 다시 시도해보세요"
                    ]
                )
            
            # 결과는 받았지만 조건에 맞지 않는 경우
            if all(not attempt.get('success', False) for attempt in attempts):
                return FailureReason(
                    type="no_suitable_results",
                    message="조건에 맞는 적절한 장소를 찾을 수 없습니다.",
                    suggestions=[
                        "검색 지역을 변경해보세요",
                        "예산 범위를 조정해보세요",
                        "카테고리를 다양화해보세요",
                        "시간 제약을 완화해보세요"
                    ]
                )
            
            # 부분적 성공이 있었던 경우
            return FailureReason(
                type="partial_failure",
                message="일부 조건에서만 결과를 찾을 수 있었습니다.",
                suggestions=[
                    "선호도를 조정해보세요",
                    "이동 거리 제한을 완화해보세요",
                    "대안 카테고리를 고려해보세요"
                ]
            )
            
        except Exception as e:
            logger.error(f"❌ 실패 원인 분석 실패: {e}")
            return FailureReason(
                type="unknown",
                message="알 수 없는 오류가 발생했습니다.",
                suggestions=["잠시 후 다시 시도해보세요"]
            )
    
    def create_retry_strategy(self, strategy_type: str = "default") -> Dict[str, Any]:
        """재시도 전략 설정 생성"""
        strategies = {
            "default": {
                "max_attempts": 3,
                "backoff_factor": 1.5,
                "timeout_per_attempt": 30,
                "retry_on_errors": ["timeout", "connection_error", "rate_limit"]
            },
            "aggressive": {
                "max_attempts": 5,
                "backoff_factor": 2.0,
                "timeout_per_attempt": 60,
                "retry_on_errors": ["timeout", "connection_error", "rate_limit", "server_error"]
            },
            "conservative": {
                "max_attempts": 2,
                "backoff_factor": 1.2,
                "timeout_per_attempt": 20,
                "retry_on_errors": ["timeout", "connection_error"]
            }
        }
        
        return strategies.get(strategy_type, strategies["default"])
    
    async def execute_parallel_retries(
        self, 
        search_functions: List[callable], 
        params_list: List[Dict[str, Any]]
    ) -> List[RetryResult]:
        """여러 검색을 병렬로 재시도 실행"""
        try:
            logger.info(f"🚀 병렬 재시도 실행 시작 - {len(search_functions)}개 작업")
            
            # 각 검색에 대해 재시도 로직 적용
            retry_tasks = []
            for search_func, params in zip(search_functions, params_list):
                task = self.execute_with_retry(search_func, params)
                retry_tasks.append(task)
            
            # 병렬 실행
            results = await asyncio.gather(*retry_tasks, return_exceptions=True)
            
            # 예외 처리
            final_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"❌ 병렬 작업 {i+1} 실패: {result}")
                    final_results.append(RetryResult(
                        success=False,
                        final_attempt=0,
                        final_result=None,
                        attempts_history=[],
                        failure_reason=FailureReason(
                            type="parallel_execution_error",
                            message=str(result),
                            suggestions=["개별 실행을 시도해보세요"]
                        )
                    ))
                else:
                    final_results.append(result)
            
            logger.info(f"✅ 병렬 재시도 실행 완료 - {len(final_results)}개 결과")
            return final_results
            
        except Exception as e:
            logger.error(f"❌ 병렬 재시도 실행 실패: {e}")
            return []
    
    def get_retry_statistics(self, retry_results: List[RetryResult]) -> Dict[str, Any]:
        """재시도 결과 통계 생성"""
        try:
            if not retry_results:
                return {}
            
            total_attempts = sum(len(result.attempts_history) for result in retry_results)
            successful_results = sum(1 for result in retry_results if result.success)
            
            # 시도별 성공률
            attempt_success_rates = {}
            for i in range(1, self.max_attempts + 1):
                attempts_at_level = [
                    result for result in retry_results 
                    if result.final_attempt >= i
                ]
                successes_at_level = [
                    result for result in attempts_at_level
                    if any(attempt.get('success', False) and attempt.get('attempt') == i 
                          for attempt in result.attempts_history)
                ]
                
                if attempts_at_level:
                    attempt_success_rates[f"{i}차"] = len(successes_at_level) / len(attempts_at_level)
            
            stats = {
                "total_retry_executions": len(retry_results),
                "total_attempts": total_attempts,
                "overall_success_rate": successful_results / len(retry_results),
                "attempt_success_rates": attempt_success_rates,
                "average_attempts_per_execution": total_attempts / len(retry_results),
                "constraints_relaxed_frequency": sum(
                    1 for result in retry_results 
                    if result.constraints_relaxed
                ) / len(retry_results)
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ 재시도 통계 생성 실패: {e}")
            return {}

# 편의 함수
async def retry_search_operation(
    search_function, 
    initial_params: Dict[str, Any],
    validation_function = None
) -> RetryResult:
    """검색 작업 재시도 편의 함수"""
    handler = RetryHandler()
    return await handler.execute_with_retry(search_function, initial_params, validation_function)

if __name__ == "__main__":
    # 테스트 실행
    async def test_retry_handler():
        try:
            handler = RetryHandler()
            
            # 가상의 검색 함수 (실패하다가 마지막에 성공)
            attempt_count = 0
            async def mock_search_function(**params):
                nonlocal attempt_count
                attempt_count += 1
                
                if attempt_count < 3:
                    # 처음 2번은 실패
                    return {"status": "failed", "total_found": 0}
                else:
                    # 3번째는 성공
                    return {"status": "success", "total_found": 5, "results": ["place1", "place2"]}
            
            # 테스트 파라미터
            test_params = {
                "radius": 2000,
                "category": "음식점",
                "top_k": 3
            }
            
            # 재시도 로직 테스트
            result = await handler.execute_with_retry(mock_search_function, test_params)
            
            print(f"✅ 재시도 핸들러 테스트 성공")
            print(f"   최종 성공: {result.success}")
            print(f"   최종 시도: {result.final_attempt}차")
            print(f"   완화된 제약: {result.constraints_relaxed}")
            print(f"   총 시도 횟수: {len(result.attempts_history)}")
            
            # 통계 생성 테스트
            stats = handler.get_retry_statistics([result])
            print(f"   통계: {stats}")
            
        except Exception as e:
            print(f"❌ 재시도 핸들러 테스트 실패: {e}")
    
    asyncio.run(test_retry_handler())
