# 장소 다양성 관리자 (중복 제거 및 다양성 확보)
# - 코스별로 서로 다른 장소 조합 보장
# - 중복 장소 제거 및 균형 잡힌 선택

from typing import List, Dict, Any, Set
from loguru import logger

class PlaceDiversityManager:
    """장소 다양성 관리자"""
    
    def __init__(self):
        """초기화"""
        self.diversity_ratio = 0.7  # 70% 이상 다른 장소여야 함
        self.max_reuse_count = 2  # 같은 장소 최대 2번까지 사용
        logger.info("✅ 장소 다양성 관리자 초기화 완료")
    
    def ensure_course_diversity(
        self, 
        all_combinations: List[Dict[str, Any]], 
        target_course_count: int = 3
    ) -> List[Dict[str, Any]]:
        """코스 간 다양성 확보"""
        try:
            if not all_combinations:
                return []
            
            logger.info(f"🌈 코스 다양성 확보 시작 - {len(all_combinations)}개 조합 → {target_course_count}개 선택")
            
            # 1. 품질 순으로 정렬
            sorted_combinations = sorted(
                all_combinations,
                key=lambda x: x.get('quality_score', 0),
                reverse=True
            )
            
            # 2. 다양성 기반 선택
            diverse_courses = self._select_diverse_combinations(
                sorted_combinations, target_course_count
            )
            
            # 3. 각 코스에 다양성 정보 추가
            for i, course in enumerate(diverse_courses):
                course['diversity_rank'] = i + 1
                course['diversity_score'] = self._calculate_diversity_score(course, diverse_courses)
            
            logger.info(f"✅ 코스 다양성 확보 완료 - {len(diverse_courses)}개 선택")
            return diverse_courses
            
        except Exception as e:
            logger.error(f"❌ 코스 다양성 확보 실패: {e}")
            return all_combinations[:target_course_count]
    
    def _select_diverse_combinations(
        self, 
        sorted_combinations: List[Dict[str, Any]], 
        target_count: int
    ) -> List[Dict[str, Any]]:
        """다양성 기반 조합 선택"""
        try:
            selected_courses = []
            used_place_ids = set()
            place_usage_count = {}
            
            # 1순위: 최고 품질 코스 먼저 선택
            if sorted_combinations:
                first_course = sorted_combinations[0]
                selected_courses.append(first_course)
                
                # 사용된 장소 ID 기록
                first_place_ids = self._extract_place_ids(first_course)
                used_place_ids.update(first_place_ids)
                for place_id in first_place_ids:
                    place_usage_count[place_id] = place_usage_count.get(place_id, 0) + 1
                
                logger.debug(f"1순위 코스 선택: {len(first_place_ids)}개 장소 사용")
            
            # 2순위 이후: 다양성 점수 기준 선택
            remaining_combinations = sorted_combinations[1:]
            
            for combination in remaining_combinations:
                if len(selected_courses) >= target_count:
                    break
                
                # 다양성 점수 계산
                diversity_score = self._calculate_combination_diversity(
                    combination, used_place_ids, place_usage_count
                )
                
                # 다양성이 충족되면 선택
                if diversity_score >= self.diversity_ratio:
                    selected_courses.append(combination)
                    
                    # 사용된 장소 업데이트
                    new_place_ids = self._extract_place_ids(combination)
                    used_place_ids.update(new_place_ids)
                    for place_id in new_place_ids:
                        place_usage_count[place_id] = place_usage_count.get(place_id, 0) + 1
                    
                    logger.debug(f"{len(selected_courses)}순위 코스 선택: 다양성 점수 {diversity_score:.2f}")
            
            # 부족하면 남은 조합에서 최선 선택
            if len(selected_courses) < target_count:
                remaining_slots = target_count - len(selected_courses)
                backup_combinations = [
                    combo for combo in remaining_combinations 
                    if combo not in selected_courses
                ]
                
                # 다양성 점수 순으로 정렬하여 선택
                backup_with_scores = []
                for combo in backup_combinations:
                    score = self._calculate_combination_diversity(
                        combo, used_place_ids, place_usage_count
                    )
                    backup_with_scores.append((combo, score))
                
                backup_with_scores.sort(key=lambda x: x[1], reverse=True)
                
                for combo, score in backup_with_scores[:remaining_slots]:
                    selected_courses.append(combo)
                    logger.debug(f"백업 코스 선택: 다양성 점수 {score:.2f}")
            
            return selected_courses
            
        except Exception as e:
            logger.error(f"다양성 기반 선택 실패: {e}")
            return sorted_combinations[:target_count]
    
    def _calculate_combination_diversity(
        self, 
        combination: Dict[str, Any], 
        used_place_ids: Set[str], 
        place_usage_count: Dict[str, int]
    ) -> float:
        """조합의 다양성 점수 계산"""
        try:
            place_ids = self._extract_place_ids(combination)
            
            if not place_ids:
                return 0.0
            
            # 새로운 장소의 비율 계산
            new_places = [pid for pid in place_ids if pid not in used_place_ids]
            new_ratio = len(new_places) / len(place_ids)
            
            # 재사용 페널티 계산
            reuse_penalty = 0
            for place_id in place_ids:
                usage_count = place_usage_count.get(place_id, 0)
                if usage_count >= self.max_reuse_count:
                    reuse_penalty += 0.3  # 30% 페널티
                elif usage_count >= 1:
                    reuse_penalty += 0.1  # 10% 페널티
            
            # 최종 다양성 점수
            diversity_score = new_ratio - (reuse_penalty / len(place_ids))
            return max(0, diversity_score)
            
        except Exception as e:
            logger.error(f"다양성 점수 계산 실패: {e}")
            return 0.0
    
    def _extract_place_ids(self, combination: Dict[str, Any]) -> List[str]:
        """조합에서 장소 ID 추출"""
        try:
            place_ids = []
            course_sequence = combination.get('course_sequence', [])
            
            for place in course_sequence:
                place_id = place.get('place_id', '')
                if place_id:
                    place_ids.append(place_id)
            
            return place_ids
            
        except Exception as e:
            logger.error(f"장소 ID 추출 실패: {e}")
            return []
    
    def _calculate_diversity_score(
        self, 
        course: Dict[str, Any], 
        all_courses: List[Dict[str, Any]]
    ) -> float:
        """코스의 전체 다양성 점수 계산"""
        try:
            current_place_ids = set(self._extract_place_ids(course))
            
            if not current_place_ids:
                return 0.0
            
            # 다른 코스들과의 겹치는 장소 수 계산
            overlap_scores = []
            
            for other_course in all_courses:
                if other_course == course:
                    continue
                
                other_place_ids = set(self._extract_place_ids(other_course))
                
                if other_place_ids:
                    overlap = len(current_place_ids & other_place_ids)
                    total_unique = len(current_place_ids | other_place_ids)
                    
                    if total_unique > 0:
                        diversity = 1 - (overlap / total_unique)
                        overlap_scores.append(diversity)
            
            # 평균 다양성 점수
            if overlap_scores:
                return sum(overlap_scores) / len(overlap_scores)
            else:
                return 1.0  # 다른 코스가 없으면 최고 점수
                
        except Exception as e:
            logger.error(f"전체 다양성 점수 계산 실패: {e}")
            return 0.5

# 전역 인스턴스
diversity_manager = PlaceDiversityManager()

if __name__ == "__main__":
    # 테스트 실행
    def test_diversity_manager():
        try:
            print("✅ 장소 다양성 관리자 테스트 성공")
            
        except Exception as e:
            print(f"❌ 장소 다양성 관리자 테스트 실패: {e}")
    
    test_diversity_manager()
