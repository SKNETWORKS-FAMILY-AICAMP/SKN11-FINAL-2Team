# 병렬 처리 헬퍼
# - 비동기 작업 병렬 실행
# - 타임아웃 처리

import asyncio
import time
from typing import List, Dict, Any, Callable, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from loguru import logger
import os
import sys

# 상위 디렉토리의 모듈들 import
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

class ParallelExecutor:
    """병렬 처리 작업을 관리하는 클래스"""
    
    def __init__(self):
        """초기화"""
        self.max_workers = int(os.getenv("MAX_WORKERS", "10"))
        self.default_timeout = float(os.getenv("REQUEST_TIMEOUT", "150.0"))
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        logger.info(f"✅ 병렬 실행기 초기화 완료 - 최대 워커: {self.max_workers}개")
    
    async def execute_weather_scenarios_parallel(
        self, 
        sunny_task: Callable, 
        rainy_task: Callable,
        timeout: float = None
    ) -> Dict[str, Any]:
        """맑은 날씨와 비오는 날씨 시나리오를 병렬로 실행"""
        try:
            logger.info("🌤️ 날씨 시나리오 병렬 실행 시작")
            start_time = time.time()
            
            timeout = timeout or self.default_timeout
            
            # 병렬 실행
            sunny_result, rainy_result = await asyncio.wait_for(
                asyncio.gather(sunny_task, rainy_task, return_exceptions=True),
                timeout=timeout
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            # 예외 처리
            if isinstance(sunny_result, Exception):
                logger.error(f"❌ 맑은 날씨 처리 실패: {sunny_result}")
                sunny_result = self._create_error_result("sunny", str(sunny_result))
            
            if isinstance(rainy_result, Exception):
                logger.error(f"❌ 비오는 날씨 처리 실패: {rainy_result}")
                rainy_result = self._create_error_result("rainy", str(rainy_result))
            
            logger.info(f"✅ 날씨 시나리오 병렬 실행 완료 - {duration:.2f}초")
            
            return {
                'sunny': sunny_result,
                'rainy': rainy_result,
                'execution_time': duration,
                'parallel_success': True
            }
            
        except asyncio.TimeoutError:
            logger.error(f"❌ 날씨 시나리오 병렬 실행 타임아웃 ({timeout}초)")
            return {
                'sunny': self._create_error_result("sunny", "타임아웃"),
                'rainy': self._create_error_result("rainy", "타임아웃"),
                'execution_time': timeout,
                'parallel_success': False,
                'error': "timeout"
            }
        except Exception as e:
            logger.error(f"❌ 날씨 시나리오 병렬 실행 실패: {e}")
            return {
                'sunny': self._create_error_result("sunny", str(e)),
                'rainy': self._create_error_result("rainy", str(e)),
                'execution_time': 0,
                'parallel_success': False,
                'error': str(e)
            }
    
    async def execute_embedding_and_radius_parallel(
        self, 
        embedding_task: Callable, 
        radius_task: Callable,
        timeout: float = None
    ) -> Tuple[Any, Any]:
        """임베딩 생성과 반경 계산을 병렬로 실행"""
        try:
            logger.info("🔄 임베딩 생성 & 반경 계산 병렬 실행 시작")
            start_time = time.time()
            
            timeout = timeout or self.default_timeout
            
            # 병렬 실행
            embedding_result, radius_result = await asyncio.wait_for(
                asyncio.gather(embedding_task, radius_task, return_exceptions=True),
                timeout=timeout
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            # 예외 처리
            if isinstance(embedding_result, Exception):
                logger.error(f"❌ 임베딩 생성 실패: {embedding_result}")
                raise embedding_result
            
            if isinstance(radius_result, Exception):
                logger.error(f"❌ 반경 계산 실패: {radius_result}")
                raise radius_result
            
            logger.info(f"✅ 임베딩 생성 & 반경 계산 병렬 실행 완료 - {duration:.2f}초")
            return embedding_result, radius_result
            
        except asyncio.TimeoutError:
            logger.error(f"❌ 임베딩 & 반경 계산 타임아웃 ({timeout}초)")
            raise asyncio.TimeoutError("임베딩 생성 및 반경 계산 타임아웃")
        except Exception as e:
            logger.error(f"❌ 임베딩 & 반경 계산 병렬 실행 실패: {e}")
            raise
    
    async def execute_multiple_tasks_parallel(
        self, 
        tasks: List[Callable], 
        task_names: List[str] = None,
        timeout: float = None,
        return_exceptions: bool = True
    ) -> List[Any]:
        """여러 비동기 작업을 병렬로 실행"""
        try:
            if not tasks:
                return []
            
            task_names = task_names or [f"Task_{i+1}" for i in range(len(tasks))]
            logger.info(f"🚀 {len(tasks)}개 작업 병렬 실행 시작: {', '.join(task_names)}")
            
            start_time = time.time()
            timeout = timeout or self.default_timeout
            
            # 병렬 실행
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=return_exceptions),
                timeout=timeout
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            # 결과 분석
            success_count = 0
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"❌ {task_names[i]} 실패: {result}")
                else:
                    success_count += 1
                    logger.debug(f"✅ {task_names[i]} 성공")
            
            logger.info(f"✅ 병렬 실행 완료 - {success_count}/{len(tasks)} 성공, {duration:.2f}초")
            return results
            
        except asyncio.TimeoutError:
            logger.error(f"❌ 병렬 작업 타임아웃 ({timeout}초)")
            if return_exceptions:
                return [asyncio.TimeoutError("타임아웃")] * len(tasks)
            else:
                raise
        except Exception as e:
            logger.error(f"❌ 병렬 작업 실행 실패: {e}")
            if return_exceptions:
                return [e] * len(tasks)
            else:
                raise
    
    async def execute_with_thread_pool(
        self, 
        sync_function: Callable, 
        *args, 
        timeout: float = None,
        **kwargs
    ) -> Any:
        """동기 함수를 스레드 풀에서 비동기로 실행"""
        try:
            logger.debug(f"🔧 스레드 풀에서 실행: {sync_function.__name__}")
            
            timeout = timeout or self.default_timeout
            loop = asyncio.get_event_loop()
            
            result = await asyncio.wait_for(
                loop.run_in_executor(self.executor, sync_function, *args),
                timeout=timeout
            )
            
            logger.debug(f"✅ 스레드 풀 실행 완료: {sync_function.__name__}")
            return result
            
        except asyncio.TimeoutError:
            logger.error(f"❌ 스레드 풀 실행 타임아웃: {sync_function.__name__}")
            raise
        except Exception as e:
            logger.error(f"❌ 스레드 풀 실행 실패: {sync_function.__name__} - {e}")
            raise
    
    async def execute_batch_operations(
        self, 
        operation_func: Callable, 
        batch_data: List[Any],
        batch_size: int = 5,
        timeout_per_batch: float = None
    ) -> List[Any]:
        """대량의 데이터를 배치로 나누어 병렬 처리"""
        try:
            if not batch_data:
                return []
            
            logger.info(f"📦 배치 처리 시작 - 총 {len(batch_data)}개, 배치 크기: {batch_size}")
            
            # 데이터를 배치로 분할
            batches = [
                batch_data[i:i + batch_size] 
                for i in range(0, len(batch_data), batch_size)
            ]
            
            all_results = []
            timeout_per_batch = timeout_per_batch or self.default_timeout
            
            for i, batch in enumerate(batches):
                logger.info(f"🔄 배치 {i+1}/{len(batches)} 처리 중...")
                
                # 배치 내 작업들을 병렬로 실행
                batch_tasks = [operation_func(item) for item in batch]
                batch_results = await self.execute_multiple_tasks_parallel(
                    batch_tasks,
                    task_names=[f"Batch{i+1}_Item{j+1}" for j in range(len(batch))],
                    timeout=timeout_per_batch
                )
                
                all_results.extend(batch_results)
            
            logger.info(f"✅ 배치 처리 완료 - {len(all_results)}개 결과")
            return all_results
            
        except Exception as e:
            logger.error(f"❌ 배치 처리 실패: {e}")
            raise
    
    def _create_error_result(self, weather: str, error_message: str) -> Dict[str, Any]:
        """에러 결과 객체 생성"""
        return {
            'weather': weather,
            'status': 'failed',
            'error_message': error_message,
            'courses': [],
            'attempt': 'error',
            'radius_used': 0,
            'total_combinations': 0
        }
    
    async def execute_with_semaphore(
        self, 
        tasks: List[Callable], 
        max_concurrent: int = 5,
        timeout: float = None
    ) -> List[Any]:
        """세마포어를 사용해 동시 실행 수를 제한하면서 병렬 처리"""
        try:
            if not tasks:
                return []
            
            logger.info(f"🚦 세마포어 병렬 실행 - 최대 동시 실행: {max_concurrent}개")
            
            semaphore = asyncio.Semaphore(max_concurrent)
            timeout = timeout or self.default_timeout
            
            async def semaphore_task(task):
                async with semaphore:
                    return await task
            
            # 세마포어로 제한된 병렬 실행
            semaphore_tasks = [semaphore_task(task) for task in tasks]
            
            results = await asyncio.wait_for(
                asyncio.gather(*semaphore_tasks, return_exceptions=True),
                timeout=timeout
            )
            
            logger.info(f"✅ 세마포어 병렬 실행 완료 - {len(results)}개 결과")
            return results
            
        except asyncio.TimeoutError:
            logger.error(f"❌ 세마포어 병렬 실행 타임아웃 ({timeout}초)")
            raise
        except Exception as e:
            logger.error(f"❌ 세마포어 병렬 실행 실패: {e}")
            raise
    
    async def execute_with_progress_tracking(
        self, 
        tasks: List[Callable], 
        progress_callback: Callable[[int, int], None] = None,
        timeout: float = None
    ) -> List[Any]:
        """진행 상황을 추적하면서 병렬 실행"""
        try:
            if not tasks:
                return []
            
            logger.info(f"📊 진행 추적 병렬 실행 시작 - {len(tasks)}개 작업")
            
            timeout = timeout or self.default_timeout
            completed_tasks = []
            
            # 작업들을 Future 객체로 변환
            pending_tasks = {asyncio.create_task(task): i for i, task in enumerate(tasks)}
            
            start_time = time.time()
            
            try:
                while pending_tasks:
                    # 완료된 작업들을 기다림 (타임아웃 적용)
                    done, pending = await asyncio.wait(
                        pending_tasks.keys(),
                        return_when=asyncio.FIRST_COMPLETED,
                        timeout=min(5.0, timeout - (time.time() - start_time))  # 최대 5초마다 체크
                    )
                    
                    # 완료된 작업들 처리
                    for task in done:
                        task_index = pending_tasks.pop(task)
                        try:
                            result = await task
                            completed_tasks.append((task_index, result))
                        except Exception as e:
                            completed_tasks.append((task_index, e))
                    
                    # 진행 상황 콜백 호출
                    if progress_callback:
                        progress_callback(len(completed_tasks), len(tasks))
                    
                    logger.info(f"📈 진행 상황: {len(completed_tasks)}/{len(tasks)} 완료")
                    
                    # 타임아웃 체크
                    if time.time() - start_time > timeout:
                        logger.warning(f"⏰ 타임아웃으로 인한 조기 종료")
                        # 남은 작업들 취소
                        for task in pending_tasks.keys():
                            task.cancel()
                        break
                
                # 결과 정렬 (원래 순서대로)
                completed_tasks.sort(key=lambda x: x[0])
                results = [result for _, result in completed_tasks]
                
                logger.info(f"✅ 진행 추적 병렬 실행 완료 - {len(results)}/{len(tasks)} 완료")
                return results
                
            except Exception as e:
                # 모든 남은 작업 취소
                for task in pending_tasks.keys():
                    task.cancel()
                raise
                
        except Exception as e:
            logger.error(f"❌ 진행 추적 병렬 실행 실패: {e}")
            raise
    
    def get_execution_statistics(self, results: List[Any]) -> Dict[str, Any]:
        """병렬 실행 결과 통계 생성"""
        try:
            if not results:
                return {}
            
            total_tasks = len(results)
            successful_tasks = sum(1 for result in results if not isinstance(result, Exception))
            failed_tasks = total_tasks - successful_tasks
            
            # 예외 타입별 분석
            exception_types = {}
            for result in results:
                if isinstance(result, Exception):
                    exc_type = type(result).__name__
                    exception_types[exc_type] = exception_types.get(exc_type, 0) + 1
            
            stats = {
                "total_tasks": total_tasks,
                "successful_tasks": successful_tasks,
                "failed_tasks": failed_tasks,
                "success_rate": successful_tasks / total_tasks if total_tasks > 0 else 0,
                "exception_types": exception_types
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ 실행 통계 생성 실패: {e}")
            return {}
    
    def __del__(self):
        """소멸자 - 스레드 풀 정리"""
        try:
            if hasattr(self, 'executor'):
                self.executor.shutdown(wait=False)
        except:
            pass

# 전역 인스턴스 (싱글톤)
_parallel_executor = None

def get_parallel_executor() -> ParallelExecutor:
    """병렬 실행기 싱글톤 인스턴스 반환"""
    global _parallel_executor
    if _parallel_executor is None:
        _parallel_executor = ParallelExecutor()
    return _parallel_executor

# 편의 함수들
async def execute_tasks_parallel(
    tasks: List[Callable], 
    timeout: float = None
) -> List[Any]:
    """작업들을 병렬로 실행하는 편의 함수"""
    executor = get_parallel_executor()
    return await executor.execute_multiple_tasks_parallel(tasks, timeout=timeout)

async def execute_weather_parallel(
    sunny_task: Callable, 
    rainy_task: Callable
) -> Dict[str, Any]:
    """날씨 시나리오를 병렬로 실행하는 편의 함수"""
    executor = get_parallel_executor()
    return await executor.execute_weather_scenarios_parallel(sunny_task, rainy_task)

if __name__ == "__main__":
    # 테스트 실행
    async def test_parallel_executor():
        try:
            executor = ParallelExecutor()
            
            # 가상의 비동기 작업들
            async def mock_task(delay: float, should_fail: bool = False):
                await asyncio.sleep(delay)
                if should_fail:
                    raise ValueError(f"Mock task failed after {delay}s")
                return f"Task completed after {delay}s"
            
            # 테스트 작업들 생성
            test_tasks = [
                mock_task(0.5),
                mock_task(1.0),
                mock_task(0.3),
                mock_task(0.8, should_fail=True),  # 실패하는 작업
                mock_task(0.2)
            ]
            
            # 병렬 실행 테스트
            results = await executor.execute_multiple_tasks_parallel(
                test_tasks,
                task_names=[f"MockTask_{i+1}" for i in range(len(test_tasks))],
                timeout=5.0
            )
            
            print(f"✅ 병렬 실행기 테스트 성공")
            print(f"   총 작업: {len(test_tasks)}개")
            print(f"   성공: {sum(1 for r in results if not isinstance(r, Exception))}개")
            print(f"   실패: {sum(1 for r in results if isinstance(r, Exception))}개")
            
            # 통계 생성 테스트
            stats = executor.get_execution_statistics(results)
            print(f"   통계: {stats}")
            
        except Exception as e:
            print(f"❌ 병렬 실행기 테스트 실패: {e}")
    
    asyncio.run(test_parallel_executor())
