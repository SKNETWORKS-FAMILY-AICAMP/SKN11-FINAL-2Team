# GPT를 이용한 이동반경 계산기
# - 사용자 컨텍스트를 분석하여 적절한 검색 반경 결정
# - 맑을 때와 비올 때 다른 반경 제안

import asyncio
from typing import Dict, Any
from loguru import logger
import os
import sys

# 상위 디렉토리의 모듈들 import
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

class RadiusCalculator:
    """GPT 기반 이동반경 계산기"""
    
    def __init__(self):
        """초기화"""
        self.default_radius = int(os.getenv("DEFAULT_SEARCH_RADIUS", "2000"))
        logger.info("✅ 반경 계산기 초기화 완료")
    
    async def calculate_radius_for_sunny(
        self, 
        user_context: Dict[str, Any], 
        course_planning: Dict[str, Any]
    ) -> int:
        """맑을 때 적절한 검색 반경 계산"""
        try:
            logger.info("☀️ 맑은 날씨 반경 계산 시작")
            
            # 기본 반경 사용 (실제로는 GPT 호출 구현 예정)
            # TODO: GPT-4o mini를 사용한 지능적 반경 계산
            radius = self.default_radius
            
            # 간단한 로직으로 조정
            transportation = user_context.get('requirements', {}).get('transportation', '')
            if transportation == '자차':
                radius = int(radius * 1.5)  # 자차면 반경 확대
            elif transportation == '도보':
                radius = int(radius * 0.5)  # 도보면 반경 축소
            
            logger.info(f"✅ 맑은 날씨 반경 계산 완료: {radius}m")
            return radius
            
        except Exception as e:
            logger.error(f"❌ 맑은 날씨 반경 계산 실패: {e}")
            return self.default_radius
    
    async def calculate_radius_for_rainy(
        self, 
        user_context: Dict[str, Any], 
        course_planning: Dict[str, Any]
    ) -> int:
        """비올 때 적절한 검색 반경 계산 (개선된 버전)"""
        try:
            logger.info("🌧️ 비오는 날씨 반경 계산 시작")
            
            # 비올 때는 기본 반경을 동일하게 유지 (선택지 확보)
            radius = self.default_radius
            
            # 교통수단에 따른 조정
            transportation = user_context.get('requirements', {}).get('transportation', '')
            if transportation == '자차':
                radius = int(radius * 1.3)  # 자차면 오히려 확대 (편의성)
            elif transportation == '대중교통':
                radius = int(radius * 1.1)  # 대중교통도 약간 확대
            elif transportation == '도보':
                radius = int(radius * 0.8)  # 도보만 축소
            
            # 5개 이상 카테고리인 경우 추가 확대
            search_targets_count = len(user_context.get('search_targets', []))
            if search_targets_count >= 4:
                radius = int(radius * 1.2)  # 다중 카테고리 보정
                logger.info(f"🔄 다중 카테고리 ({search_targets_count}개) 보정 적용")
            
            logger.info(f"✅ 비오는 날씨 반경 계산 완료: {radius}m (개선된 로직)")
            return radius
            
        except Exception as e:
            logger.error(f"❌ 비오는 날씨 반경 계산 실패: {e}")
            return self.default_radius

if __name__ == "__main__":
    # 테스트 실행
    async def test_radius_calculator():
        try:
            calculator = RadiusCalculator()
            
            test_user_context = {
                "requirements": {
                    "transportation": "대중교통"
                }
            }
            
            test_course_planning = {
                "route_constraints": {
                    "flexibility": "low"
                }
            }
            
            sunny_radius = await calculator.calculate_radius_for_sunny(
                test_user_context, test_course_planning
            )
            rainy_radius = await calculator.calculate_radius_for_rainy(
                test_user_context, test_course_planning
            )
            
            print(f"✅ 반경 계산기 테스트 성공")
            print(f"맑을 때: {sunny_radius}m")
            print(f"비올 때: {rainy_radius}m")
            
        except Exception as e:
            print(f"❌ 반경 계산기 테스트 실패: {e}")
    
    asyncio.run(test_radius_calculator())
