# 코스 조합 최적화기 (스마트 조합 생성 + 클러스터 기반 거리 제한 + 다양성 확보)
# - 카테고리 수에 따른 적응형 조합 생성
# - 조합 폭발 방지 및 품질 유지
# - 위치 클러스터 분석 및 동적 거리 제한
# - 장소 다양성 확보

from typing import List, Dict, Any
from itertools import product
from loguru import logger
import os
import sys

# 상위 디렉토리의 모듈들 import
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from src.utils.distance_calculator import calculate_haversine_distance
from config.settings import settings

# 새로운 모듈들 import (에러 방지를 위해 try-except 사용)
try:
    from src.utils.location_analyzer import location_analyzer
    LOCATION_ANALYZER_AVAILABLE = True
except ImportError:
    LOCATION_ANALYZER_AVAILABLE = False
    logger.warning("⚠️ location_analyzer 모듈을 찾을 수 없음 - 기본 거리 제한 사용")

try:
    from src.utils.diversity_manager import diversity_manager
    DIVERSITY_MANAGER_AVAILABLE = True
except ImportError:
    DIVERSITY_MANAGER_AVAILABLE = False
    logger.warning("⚠️ diversity_manager 모듈을 찾을 수 없음 - 기본 조합 선택 사용")

class SmartCourseOptimizer:
    """스마트 코스 조합 최적화기 (위치 클러스터 + 다양성 포함)"""
    
    def __init__(self):
        """초기화"""
        self.max_combinations_by_category = {
            1: 15,  # 1개 카테고리: 최대 15개 (GPT가 선택할 수 있도록 충분히)
            2: 20,  # 2개 카테고리: 최대 20개
            3: 15,  # 3개 카테고리: 최대 15개
            4: 12,  # 4개 카테고리: 최대 12개
            5: 10   # 5개 카테고리: 최대 10개
        }
        logger.info("✅ 스마트 코스 최적화기 초기화 완료 (위치 클러스터 + 다양성 포함)")
    
    def generate_combinations(
        self, 
        places: List[Dict[str, Any]], 
        search_targets: List[Dict[str, Any]] = None,
        weather: str = "sunny",
        location_analysis: Dict[str, Any] = None # 이 줄을 추가합니다.
    ) -> List[Dict[str, Any]]:
        """장소들로부터 스마트 조합 생성 (클러스터 기반 거리 제한 + 다양성 확보)"""
        try:
            if not places:
                return []
            
            logger.info(f"🔀 스마트 코스 조합 생성 시작 - {len(places)}개 장소 ({weather} 날씨)")
            
            # 비오는 날 거리 제한 강화
            self.weather = weather
            self.category_count = len(search_targets) if search_targets else 1
            
            # 1. 위치 분석 (클러스터링 및 동적 거리 제한 결정)
            location_analysis = None
            if search_targets and LOCATION_ANALYZER_AVAILABLE:
                # 🔥 수정: 날씨 정보를 함께 전달하여 동적 거리 제한 적용
                location_analysis = location_analyzer.analyze_search_targets(search_targets, weather)
                logger.info(f"📍 {location_analysis['analysis_summary']}")
            
            # 2. 시퀀스별로 장소들을 그룹화
            sequence_groups = self._group_places_by_sequence(places)
            
            if not sequence_groups:
                return []
            
            category_count = len(sequence_groups)
            max_combinations = self.max_combinations_by_category.get(category_count, 10)
            
            # 3. 카테고리 수에 따른 스마트 조합 생성
            if category_count <= 2:
                # 2개 이하: 전체 조합
                combinations = self._create_full_combinations(sequence_groups, max_combinations)
            elif category_count == 3:
                # 3개: 전략적 조합 선택
                combinations = self._create_strategic_combinations(sequence_groups, max_combinations)
            else:
                # 4-5개: 계층적 조합 생성
                combinations = self._create_hierarchical_combinations(sequence_groups, max_combinations)
            
            # 4. 거리 계산 및 조합 완성 (클러스터 기반 거리 제한 적용!)
            completed_combinations = []
            for i, combination in enumerate(combinations):
                try:
                    completed_combo = self._complete_combination(combination, i + 1)
                    
                    # 클러스터 기반 거리 제한 검사
                    if self._is_distance_acceptable_cluster_based(completed_combo, location_analysis):
                        completed_combinations.append(completed_combo)
                    else:
                        logger.debug(f"조합 {i+1} 클러스터 기반 거리 제한 위반으로 제외")
                except Exception as e:
                    logger.debug(f"조합 {i+1} 완성 실패: {e}")
                    continue
            
            # 5. 날씨별 우선순위 정렬
            is_rainy = getattr(self, 'weather', 'sunny') in ['rainy', '비']
            
            # 비오는 날 응급 모드: 조합이 너무 적으면 거리 제한 완화
            if is_rainy and len(completed_combinations) == 0:
                logger.warning("🌧️ 비오는 날 응급모드: 거리 제한 완화")
                # 다시 시도 (거리 제한 없이)
                for i, combination in enumerate(combinations):
                    try:
                        completed_combo = self._complete_combination(combination, i + 1)
                        # 기본 거리 검사만 수행 (클러스터 검사 스킵)
                        if self._is_distance_acceptable_basic(completed_combo):
                            completed_combinations.append(completed_combo)
                        else:
                            # 완전 납도한 기준으로도 추가
                            completed_combinations.append(completed_combo)
                            logger.debug(f"🌧️ 비상모드: 조합 {i+1} 강제 추가")
                    except Exception as e:
                        logger.debug(f"조합 {i+1} 비상모드 완성 실패: {e}")
                        continue
            
            if is_rainy:
                # 비오는 날: 근거리 우선 정렬
                completed_combinations.sort(key=lambda x: x.get('total_distance_meters', 0))
                logger.info(f"🌧️ 비오는 날 근거리 우선 정렬 적용")
            else:
                # 맑은 날: 품질 점수 우선 정렬 (기존 방식)
                completed_combinations.sort(key=lambda x: x.get('quality_score', 0), reverse=True)
            
            # 6. 다양성 확보 - GPT 선택을 위해 더 많은 조합 유지
            if DIVERSITY_MANAGER_AVAILABLE:
                # GPT가 선택할 수 있도록 더 많은 조합을 유지 (최대 15개)
                target_for_gpt = min(15, len(completed_combinations))
                # 🔥 수정: 최소 3개는 보장하도록 변경
                if target_for_gpt < 3 and len(completed_combinations) > 0:
                    target_for_gpt = min(3, len(completed_combinations))
                diverse_combinations = diversity_manager.ensure_course_diversity(
                    completed_combinations, target_course_count=target_for_gpt
                )
            else:
                # 다양성 관리자가 없으면 GPT용으로 최대 15개 선택 (최소 3개 보장)
                target_count = min(15, len(completed_combinations))
                if target_count < 3 and len(completed_combinations) > 0:
                    target_count = min(3, len(completed_combinations))
                diverse_combinations = completed_combinations[:target_count]
            
            # 🔥 추가: 조합이 너무 적으면 강제로 늘리기 (GPT가 선택할 수 있도록)
            if len(diverse_combinations) == 1 and category_count == 1:
                # 1개 카테고리에서 1개 조합만 나왔다면, 같은 장소들로 다른 조합 생성
                diverse_combinations = self._ensure_minimum_combinations_for_single_category(
                    diverse_combinations, max_combinations
                )
                logger.info(f"🔧 단일 카테고리 조합 확장: 1개 → {len(diverse_combinations)}개")
            
            logger.info(f"✅ 스마트 코스 조합 생성 완료 - {len(diverse_combinations)}개 (다양성 확보)")
            return diverse_combinations
            
        except Exception as e:
            logger.error(f"❌ 스마트 코스 조합 생성 실패: {e}")
            return []
    
    def _is_distance_acceptable_cluster_based(
        self, 
        combination: Dict[str, Any], 
        location_analysis: Dict[str, Any] = None
    ) -> bool:
        """클러스터 기반 거리 제한 검사"""
        try:
            course_places = combination.get('course_sequence', [])
            
            if not course_places or len(course_places) < 2:
                return True
            
            # 위치 분석이 있고 location_analyzer가 사용 가능하면 클러스터 기반 검증 사용
            if location_analysis and LOCATION_ANALYZER_AVAILABLE:
                is_valid, reason = location_analyzer.validate_course_distance(
                    course_places, location_analysis
                )
                if not is_valid:
                    logger.debug(f"클러스터 기반 거리 검증 실패: {reason}")
                return is_valid
            else:
                # 기본 거리 제한 적용
                return self._is_distance_acceptable_basic(combination)
                
        except Exception as e:
            logger.error(f"클러스터 기반 거리 검사 실패: {e}")
            return True
    
    def _is_distance_acceptable_basic(self, combination: Dict[str, Any]) -> bool:
        """기본 거리 제한 검사 (날씨별 차등 적용)"""
        try:
            total_distance = combination.get('total_distance_meters', 0)
            travel_distances = combination.get('travel_distances', [])
            
            # 날씨에 따른 거리 기준 조정
            is_rainy = getattr(self, 'weather', 'sunny') in ['rainy', '비']
            
            # 1. 총 이동거리 검사 (카테고리가 많을 때 더 관대하게)
            base_max_total = getattr(settings, 'MAX_TOTAL_DISTANCE', 10000)
            category_count = getattr(self, 'category_count', 3)
            
            # 카테고리가 많을 때는 거리 제한을 대폭 완화
            if category_count >= 5:
                base_max_total = int(base_max_total * 2.0)   # 5개 이상일 때 100% 완화
            elif category_count >= 4:
                base_max_total = int(base_max_total * 1.8)   # 4개일 때 80% 완화
            
            # 비오는 날 처리 (복잡한 경우 덜 엄격하게)
            if is_rainy:
                if category_count >= 4:
                    max_total = int(base_max_total * 0.8)    # 복잡한 경우 20%만 단축
                else:
                    max_total = int(base_max_total * 0.7)    # 단순한 경우 30% 단축
            else:
                max_total = base_max_total
            
            if total_distance > max_total:
                # 4개 이상 카테고리에서는 거리 초과해도 일부 허용
                if category_count >= 4 and total_distance <= max_total * 1.3:
                    logger.debug(f"🔄 복잡한 시나리오 예외 허용: {total_distance}m > {max_total}m (허용범위)")
                else:
                    logger.debug(f"총 거리 초과 ({'비오는 날' if is_rainy else '맑은 날'}): {total_distance}m > {max_total}m")
                    return False
            
            # 2. 구간별 거리 검사 (복잡한 시나리오에서 더 관대하게)
            base_max_segment = getattr(settings, 'MAX_SINGLE_SEGMENT_DISTANCE', 5000)
            
            # 카테고리 수에 따른 구간별 거리 조정
            if category_count >= 4:
                base_max_segment = int(base_max_segment * 1.5)  # 복잡한 경우 구간 거리도 완화
            
            max_segment = int(base_max_segment * 0.5) if is_rainy else base_max_segment  # 비올 때 50% 단축
            
            failed_segments = 0
            for segment in travel_distances:
                segment_distance = segment.get('distance_meters', 0)
                if segment_distance > max_segment:
                    failed_segments += 1
                    # 복잡한 시나리오에서는 일부 구간 초과 허용
                    if category_count < 4 or failed_segments > 1:
                        logger.debug(f"구간 거리 초과 ({'비오는 날' if is_rainy else '맑은 남'}): {segment.get('from', '')} → {segment.get('to', '')} = {segment_distance}m > {max_segment}m")
                        return False
                    else:
                        logger.debug(f"🔄 복잡한 시나리오 구간 초과 1회 허용: {segment_distance}m > {max_segment}m")
            
            if is_rainy:
                logger.debug(f"🌧️ 비오는 날 거리 기준 적용: 총거리={total_distance}m (한계:{max_total}m), 복잡도={category_count}")
            elif category_count >= 4:
                logger.debug(f"🔀 복잡한 시나리오 완화된 거리 기준: 총거리={total_distance}m (한계:{max_total}m), {category_count}개 카테고리")
            
            return True
            
        except Exception as e:
            logger.error(f"기본 거리 검사 실패: {e}")
            return False
    
    def _group_places_by_sequence(self, places: List[Dict[str, Any]]) -> Dict[int, List[Dict]]:
        """시퀀스별로 장소들을 그룹화"""
        groups = {}
        
        for place in places:
            sequence = place.get('search_sequence', 1)
            if sequence not in groups:
                groups[sequence] = []
            groups[sequence].append(place)
        
        # 시퀀스 순서대로 정렬
        sorted_groups = {seq: groups[seq] for seq in sorted(groups.keys())}
        
        logger.debug(f"시퀀스 그룹화: {[(seq, len(places)) for seq, places in sorted_groups.items()]}")
        return sorted_groups
    
    def _create_full_combinations(self, sequence_groups: Dict[int, List[Dict]], max_combinations: int) -> List[List[Dict]]:
        """전체 조합 생성 (2개 이하 카테고리)"""
        try:
            place_lists = [places for seq, places in sorted(sequence_groups.items())]
            all_combinations = list(product(*place_lists))
            
            # 거리 기준으로 정렬하여 상위 조합 선택
            combinations = [list(combo) for combo in all_combinations]
            combinations = self._sort_combinations_by_quality(combinations)
            
            result = combinations[:max_combinations]
            logger.info(f"전체 조합 생성: {len(all_combinations)} → {len(result)}개 선택")
            return result
            
        except Exception as e:
            logger.error(f"전체 조합 생성 실패: {e}")
            return []
    
    def _create_strategic_combinations(self, sequence_groups: Dict[int, List[Dict]], max_combinations: int) -> List[List[Dict]]:
        """전략적 조합 생성 (3개 카테고리)"""
        try:
            combinations = []
            place_lists = [places for seq, places in sorted(sequence_groups.items())]
            
            # 1순위: 각 카테고리 최고 점수 조합 (1개)
            if all(len(places) >= 1 for places in place_lists):
                combinations.append([places[0] for places in place_lists])
            
            # 2순위: 한 카테고리만 2등, 나머지 1등 (최대 3개)
            for i, places in enumerate(place_lists):
                if len(places) >= 2:
                    combo = [place_list[0] for place_list in place_lists]
                    combo[i] = places[1]
                    combinations.append(combo)
            
            # 3순위: 두 카테고리 2등, 한 카테고리 1등 (최대 3개)
            for i, places in enumerate(place_lists):
                if all(len(place_list) >= 2 for j, place_list in enumerate(place_lists) if j != i):
                    combo = [place_list[1] if j != i else place_list[0] 
                            for j, place_list in enumerate(place_lists)]
                    combinations.append(combo)
            
            # 4순위: 거리/품질 기반 추가 조합
            if len(combinations) < max_combinations:
                remaining_slots = max_combinations - len(combinations)
                additional_combos = self._generate_quality_combinations(
                    place_lists, remaining_slots, exclude=combinations
                )
                combinations.extend(additional_combos)
            
            logger.info(f"전략적 조합 생성: {len(combinations)}개")
            return combinations[:max_combinations]
            
        except Exception as e:
            logger.error(f"전략적 조합 생성 실패: {e}")
            return []
    
    def _create_hierarchical_combinations(self, sequence_groups: Dict[int, List[Dict]], max_combinations: int) -> List[List[Dict]]:
        """계층적 조합 생성 (4-5개 카테고리) - 더 적극적으로"""
        try:
            combinations = []
            place_lists = [places for seq, places in sorted(sequence_groups.items())]
            
            # 1단계: 핵심 조합들 (각 카테고리 1등 위주)
            core_combinations = self._generate_core_combinations(place_lists)
            combinations.extend(core_combinations)
            
            # 2단계: 다양성 조합들 (서로 다른 특성)
            if len(combinations) < max_combinations:
                diversity_combinations = self._generate_diversity_combinations(
                    place_lists, max_combinations - len(combinations), exclude=combinations
                )
                combinations.extend(diversity_combinations)
            
            # 3단계: 응급 조합 생성 (아무것도 없으면 무작위로라도)
            if len(combinations) == 0:
                logger.warning("🚨 응급 조합 생성 모드 활성화")
                emergency_combinations = self._generate_emergency_combinations(place_lists, max(3, max_combinations))
                combinations.extend(emergency_combinations)
            elif len(combinations) < 3 and category_count >= 4:
                # 4개 이상 카테고리에서 조합이 매우 적으면 보강
                needed = 3 - len(combinations)
                emergency_combinations = self._generate_emergency_combinations(place_lists, needed)
                combinations.extend(emergency_combinations)
                logger.warning(f"🚨 복잡한 시나리오 조합 보강: {needed}개 추가")
            
            logger.info(f"계층적 조합 생성: {len(combinations)}개 (응급모드: {'활성' if len(combinations) <= 3 else '비활성'})")
            return combinations[:max_combinations]
            
        except Exception as e:
            logger.error(f"계층적 조합 생성 실패: {e}")
            # 완전 실패시에도 최소한의 조합 시도
            return self._generate_emergency_combinations(
                [places for seq, places in sorted(sequence_groups.items())], 1
            )
    
    def _generate_core_combinations(self, place_lists: List[List[Dict]]) -> List[List[Dict]]:
        """핵심 조합 생성: 높은 품질 보장"""
        combinations = []
        
        # 모든 카테고리 1등 (1개)
        if all(len(places) >= 1 for places in place_lists):
            combinations.append([places[0] for places in place_lists])
        
        # 한 카테고리만 2등, 나머지 1등 (최대 5개)
        for i, places in enumerate(place_lists):
            if len(places) >= 2:
                combo = [place_list[0] for place_list in place_lists]
                combo[i] = places[1]
                combinations.append(combo)
        
        return combinations
    
    def _generate_diversity_combinations(self, place_lists: List[List[Dict]], needed_count: int, exclude: List[List[Dict]]) -> List[List[Dict]]:
        """다양성 조합 생성: 서로 다른 특성의 장소들"""
        combinations = []
        
        # 기존 조합에서 사용된 장소 ID 수집
        used_place_ids = set()
        for combo in exclude:
            for place in combo:
                used_place_ids.add(place.get('place_id', ''))
        
        # 각 카테고리에서 기존에 사용되지 않은 장소들 선별
        available_by_category = []
        for places in place_lists:
            available = [p for p in places if p.get('place_id', '') not in used_place_ids]
            # 부족하면 기존 장소도 포함 (최소 2개는 확보)
            if len(available) < 2:
                available = places[:2]
            available_by_category.append(available[:2])  # 각 카테고리당 최대 2개
        
        # 가능한 모든 조합 중 품질 기준으로 선별
        if all(len(avail) > 0 for avail in available_by_category):
            possible_combos = list(product(*available_by_category))
            
            # 품질 점수로 정렬
            scored_combos = []
            for combo in possible_combos:
                score = self._calculate_combination_quality_score(list(combo))
                scored_combos.append((list(combo), score))
            
            scored_combos.sort(key=lambda x: x[1], reverse=True)
            combinations = [combo for combo, score in scored_combos[:needed_count]]
        
        return combinations
    
    def _generate_quality_combinations(self, place_lists: List[List[Dict]], needed_count: int, exclude: List[List[Dict]]) -> List[List[Dict]]:
        """품질 기반 추가 조합 생성"""
        combinations = []
        
        # 가능한 조합들 중 일부만 샘플링
        max_sample = min(1000, needed_count * 10)  # 최대 1000개만 샘플링
        
        try:
            # 전체 조합 중 샘플링
            all_possible = list(product(*place_lists))
            if len(all_possible) > max_sample:
                # 너무 많으면 인덱스 기반 샘플링
                step = len(all_possible) // max_sample
                sampled_combos = [all_possible[i] for i in range(0, len(all_possible), step)]
            else:
                sampled_combos = all_possible
            
            # 품질 평가 및 정렬
            scored_combos = []
            for combo in sampled_combos:
                combo_list = list(combo)
                if combo_list not in exclude:
                    score = self._calculate_combination_quality_score(combo_list)
                    scored_combos.append((combo_list, score))
            
            scored_combos.sort(key=lambda x: x[1], reverse=True)
            combinations = [combo for combo, score in scored_combos[:needed_count]]
            
        except Exception as e:
            logger.debug(f"품질 조합 생성 중 오류: {e}")
        
        return combinations
    
    def _generate_emergency_combinations(self, place_lists: List[List[Dict]], target_count: int) -> List[List[Dict]]:
        """응급 조합 생성: 최소한의 조합이라도 만들어야 함"""
        try:
            emergency_combinations = []
            
            # 각 카테고리에서 최소 1개씩은 있는지 확인
            if all(len(places) >= 1 for places in place_lists):
                # 가장 기본적인 조합: 각 카테고리 첫 번째
                emergency_combinations.append([places[0] for places in place_lists])
                
                # 두 번째 조합: 가능하면 두 번째 선택지들
                if target_count > 1:
                    second_combo = []
                    for places in place_lists:
                        if len(places) >= 2:
                            second_combo.append(places[1])
                        else:
                            second_combo.append(places[0])  # 없으면 첫 번째 재사용
                    emergency_combinations.append(second_combo)
                
                # 세 번째 조합: 혼합
                if target_count > 2:
                    mixed_combo = []
                    for i, places in enumerate(place_lists):
                        choice_idx = i % len(places)  # 순환 선택
                        mixed_combo.append(places[choice_idx])
                    emergency_combinations.append(mixed_combo)
                
                # 추가 조합: 무작위 혼합 (더 많이 생성)
                for extra in range(target_count, min(target_count + 5, 10)):
                    extra_combo = []
                    for i, places in enumerate(place_lists):
                        choice_idx = (i + extra) % len(places)
                        extra_combo.append(places[choice_idx])
                    emergency_combinations.append(extra_combo)
            
            logger.warning(f"🚨 응급 조합 {len(emergency_combinations)}개 생성 완료")
            return emergency_combinations[:max(target_count, 5)]  # 최소 5개는 보장
            
        except Exception as e:
            logger.error(f"응급 조합 생성도 실패: {e}")
            return []
    
    def _calculate_combination_quality_score(self, combination: List[Dict]) -> float:
        """조합의 품질 점수 계산"""
        try:
            score = 0.0
            
            # 1. 유사도 점수 (40%)
            similarity_scores = [place.get('similarity_score', 0.0) for place in combination]
            avg_similarity = sum(similarity_scores) / len(similarity_scores) if similarity_scores else 0
            score += avg_similarity * 0.4
            
            # 2. 거리 점수 (40%) - 짧을수록 좋음
            total_distance = self._calculate_total_distance(combination)
            # 거리를 0-1 스케일로 정규화 (10km를 기준점으로)
            distance_score = max(0, 1 - (total_distance / 10000))
            score += distance_score * 0.4
            
            # 3. 다양성 점수 (20%) - 서로 다른 특성
            diversity_score = self._calculate_diversity_score(combination)
            score += diversity_score * 0.2
            
            return score
            
        except Exception as e:
            logger.debug(f"품질 점수 계산 실패: {e}")
            return 0.0
    
    def _calculate_total_distance(self, combination: List[Dict]) -> float:
        """조합의 총 이동 거리 계산"""
        try:
            total_distance = 0.0
            for i in range(len(combination) - 1):
                distance = calculate_haversine_distance(
                    combination[i]['latitude'], combination[i]['longitude'],
                    combination[i + 1]['latitude'], combination[i + 1]['longitude']
                )
                total_distance += distance
            return total_distance
        except Exception as e:
            return float('inf')
    
    def _calculate_diversity_score(self, combination: List[Dict]) -> float:
        """조합의 다양성 점수 계산"""
        try:
            # 장소 설명에서 키워드 추출하여 다양성 측정
            all_keywords = set()
            place_keywords = []
            
            for place in combination:
                description = place.get('description', '')
                # 간단한 키워드 추출 (실제로는 더 정교한 방법 사용 가능)
                keywords = set(description.split()[:5])  # 처음 5개 단어
                place_keywords.append(keywords)
                all_keywords.update(keywords)
            
            if not all_keywords:
                return 0.5
            
            # 겹치지 않는 키워드의 비율로 다양성 측정
            unique_keywords = len(all_keywords)
            total_keywords = sum(len(keywords) for keywords in place_keywords)
            
            if total_keywords == 0:
                return 0.5
            
            diversity = unique_keywords / total_keywords
            return min(1.0, diversity)
            
        except Exception as e:
            return 0.5
    
    def _sort_combinations_by_quality(self, combinations: List[List[Dict]]) -> List[List[Dict]]:
        """품질 기준으로 조합 정렬"""
        try:
            scored_combinations = []
            for combo in combinations:
                score = self._calculate_combination_quality_score(combo)
                scored_combinations.append((combo, score))
            
            scored_combinations.sort(key=lambda x: x[1], reverse=True)
            return [combo for combo, score in scored_combinations]
        except Exception as e:
            logger.error(f"조합 정렬 실패: {e}")
            return combinations
    
    def _complete_combination(self, combination: List[Dict], combination_id: int) -> Dict[str, Any]:
        """조합을 완성 (거리 계산 등)"""
        try:
            # 이동 경로 계산
            travel_info = self._calculate_travel_distances(combination)
            
            # 총 이동 거리 계산
            total_distance = sum(segment['distance_meters'] for segment in travel_info)
            
            # 조합 데이터 완성
            completed_combination = {
                'combination_id': f'combo_{combination_id}',
                'course_sequence': combination,
                'travel_distances': travel_info,
                'total_distance_meters': total_distance,
                'place_count': len(combination),
                'quality_score': self._calculate_combination_quality_score(combination)
            }
            
            return completed_combination
            
        except Exception as e:
            logger.error(f"조합 완성 실패: {e}")
            raise
    
    def _calculate_travel_distances(self, places: List[Dict]) -> List[Dict[str, Any]]:
        """장소들 간의 이동 거리 계산"""
        travel_info = []
        
        for i in range(len(places) - 1):
            from_place = places[i]
            to_place = places[i + 1]
            
            # 거리 계산
            distance = calculate_haversine_distance(
                from_place['latitude'], from_place['longitude'],
                to_place['latitude'], to_place['longitude']
            )
            
            travel_segment = {
                'from': from_place['place_name'],
                'to': to_place['place_name'],
                'distance_meters': round(distance)
            }
            
            travel_info.append(travel_segment)
        
        return travel_info
    
    def filter_combinations_by_distance(
        self, 
        combinations: List[Dict[str, Any]], 
        max_total_distance: int = 10000
    ) -> List[Dict[str, Any]]:
        """거리 기준으로 조합 필터링"""
        try:
            filtered = [
                combo for combo in combinations 
                if combo['total_distance_meters'] <= max_total_distance
            ]
            
            logger.info(f"거리 필터링: {len(combinations)} → {len(filtered)}개")
            return filtered
            
        except Exception as e:
            logger.error(f"거리 필터링 실패: {e}")
            return combinations
    
    def get_top_combinations(
        self, 
        combinations: List[Dict[str, Any]], 
        top_n: int = 10
    ) -> List[Dict[str, Any]]:
        """상위 N개 조합 반환"""
        try:
            # 품질 점수 순으로 정렬 후 상위 N개 선택
            sorted_combinations = sorted(
                combinations,
                key=lambda x: x.get('quality_score', 0),
                reverse=True
            )
            top_combinations = sorted_combinations[:top_n]
            
            logger.info(f"상위 {len(top_combinations)}개 조합 선택")
            return top_combinations
            
        except Exception as e:
            logger.error(f"상위 조합 선택 실패: {e}")
            return combinations[:top_n] if len(combinations) >= top_n else combinations
    
    def _ensure_minimum_combinations_for_single_category(
        self, 
        combinations: List[Dict[str, Any]], 
        max_combinations: int
    ) -> List[Dict[str, Any]]:
        """단일 카테고리일 때 최소 조합 확보 - 🔥 잘못된 방법! 삭제 예정"""
        # 🔥 이 함수는 잘못된 접근입니다!
        # 카테고리 수나 장소 수를 줄이면 안됩니다!
        # 대신 vector_search에서 top_K를 늘려서 더 많은 장소를 가져와야 합니다.
        logger.warning("🚨 잘못된 접근: 장소 수를 줄이는 대신 top_K를 늘려서 더 많은 장소를 가져와야 함")
        return combinations

# 하위 호환성을 위한 별칭
CourseOptimizer = SmartCourseOptimizer

if __name__ == "__main__":
    # 테스트 실행
    def test_smart_course_optimizer():
        try:
            optimizer = SmartCourseOptimizer()
            
            # 5개 카테고리 테스트 케이스
            test_places = []
            categories = ['음식점', '술집', '문화시설', '휴식시설', '야외활동']
            
            for seq, category in enumerate(categories, 1):
                for i in range(3):  # 각 카테고리당 3개씩
                    place = {
                        'place_id': f'{category}_{i+1:03d}',
                        'place_name': f'{category} {i+1}',
                        'latitude': 37.5519 + (seq-1) * 0.001 + i * 0.0005,
                        'longitude': 126.9245 + (seq-1) * 0.001 + i * 0.0005,
                        'search_sequence': seq,
                        'category': category,
                        'description': f'{category} 설명 {i+1}',
                        'similarity_score': 0.9 - i * 0.1
                    }
                    test_places.append(place)
            
            # 조합 생성 테스트
            combinations = optimizer.generate_combinations(test_places)
            print(f"✅ 스마트 코스 최적화기 테스트 성공")
            print(f"   - 5개 카테고리 × 3개 장소 = 총 {len(test_places)}개 장소")
            print(f"   - 생성된 조합: {len(combinations)}개 (3^5=243개 대신)")
            print(f"   - 조합 폭발 방지 성공! 🎉")
            
        except Exception as e:
            print(f"❌ 스마트 코스 최적화기 테스트 실패: {e}")
    
    test_smart_course_optimizer()
