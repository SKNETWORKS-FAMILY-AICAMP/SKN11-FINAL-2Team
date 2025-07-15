# GPT 기반 코스 선택기 (스마트 선택)
# - 적절한 수의 조합에서 최적의 코스 3개 선택
# - 조합 수에 따른 적응형 선택 전략

import asyncio
from typing import List, Dict, Any
from loguru import logger
import os
import sys
import json
import re

# 상위 디렉토리의 모듈들 import
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# OpenAI 클라이언트 import
try:
    from openai import AsyncOpenAI
except ImportError:
    logger.warning("OpenAI 라이브러리가 설치되지 않음. pip install openai")
    AsyncOpenAI = None

class SmartGPTSelector:
    """스마트 GPT 기반 코스 선택기"""
    
    def __init__(self):
        """초기화"""
        self.max_combinations_for_gpt = 10  # GPT에 전달할 최대 조합 수 (15초 최적화: 20→10)
        self.min_combinations_for_gpt = 6   # 🔥 추가: GPT에게 보낼 최소 조합 수
        
        # OpenAI 클라이언트 초기화
        self.openai_client = None
        if AsyncOpenAI:
            try:
                api_key = os.getenv("OPENAI_API_KEY")
                if api_key:
                    self.openai_client = AsyncOpenAI(api_key=api_key)
                    logger.info("✅ OpenAI GPT 클라이언트 초기화 완료")
                else:
                    logger.warning("OPENAI_API_KEY 환경변수가 설정되지 않음")
            except Exception as e:
                logger.error(f"OpenAI 클라이언트 초기화 실패: {e}")
        
        logger.info("✅ 스마트 GPT 선택기 초기화 완료")
    
    async def select_best_courses(
        self,
        combinations: List[Dict[str, Any]],
        user_context: Dict[str, Any],
        weather: str,
        attempt: str
    ) -> List[Dict[str, Any]]:
        """생성된 조합들 중 최적의 코스들을 선택"""
        try:
            if not combinations:
                logger.warning("선택할 조합이 없음")
                return []
            
            logger.info(f"🤖 스마트 GPT 코스 선택 시작 - {len(combinations)}개 조합, {weather} 날씨")
            
            # 조합 수에 따른 적응형 처리
            if len(combinations) > self.max_combinations_for_gpt:
                # 너무 많으면 사전 필터링 수행
                filtered_combinations = self._pre_filter_combinations(combinations, user_context)
                logger.info(f"사전 필터링: {len(combinations)} → {len(filtered_combinations)}개")
            else:
                filtered_combinations = combinations
            
            # 최종 3개 코스 선택 (관대한 기준)
            if len(filtered_combinations) <= 3:
                # 조합이 3개 이하면 모두 선택
                selected_combinations = filtered_combinations
            elif len(filtered_combinations) == 0:
                # 필터링 결과가 없으면 원본 조합 사용 (완화된 기준)
                logger.warning("🔄 필터링 결과 없음, 원본 조합 사용 (완화된 기준)")
                selected_combinations = combinations[:3] if len(combinations) >= 3 else combinations
            elif len(filtered_combinations) < 3 and weather in ["rainy", "비"]:
                # 비오는 날에 필터링 결과가 적으면 원본 조합도 추가
                logger.warning("🌧️ 비오는 날 조합 부족, 원본 조합 추가")
                additional_combinations = [c for c in combinations if c not in filtered_combinations]
                selected_combinations = filtered_combinations + additional_combinations[:3-len(filtered_combinations)]
            else:
                # 3개보다 많으면 GPT 또는 룰 기반 선택
                selected_combinations = await self._intelligent_selection(
                    filtered_combinations, user_context, weather
                )
            
            # 코스 형태로 변환 (관대한 검증)
            selected_courses = []
            category_count = len(user_context.get('search_targets', []))
            is_rainy = weather == "rainy" or weather == "비"
            is_very_complex = category_count >= 4
            
            for i, combo in enumerate(selected_combinations):
                course = self._convert_combination_to_course(combo, i + 1, weather)
                
                # 매우 복잡한 경우 검증을 더 관대하게
                validation_lenient = is_rainy or is_very_complex
                
                if await self.validate_course_quality(course, user_context, lenient=validation_lenient):
                    selected_courses.append(course)
                elif (is_rainy or is_very_complex) and len(selected_courses) < 3:
                    # 비오는 날이거나 복잡한 시나리오면 강제로 추가
                    logger.info(f"🌧️{'비오는 날' if is_rainy else ''} {'복잡한 시나리오' if is_very_complex else ''} 관대한 기준으로 코스 추가")
                    selected_courses.append(course)
            
            # 최종 안전장치: 코스가 부족하면 강제로 생성 (4개 이상 카테고리는 더 적극적으로)
            category_count = len(user_context.get('search_targets', []))
            is_complex = category_count >= 4 or weather in ["rainy", "비"]
            is_very_complex = category_count >= 4  # 4개 이상은 매우 복잡
            
            # 1단계: 0개 코스 응급처치 (매우 관대한 기준)
            if len(selected_courses) == 0 and selected_combinations:
                logger.warning(f"🆘 응급처치: {weather} 날씨 {category_count}개 카테고리 - 첫 번째 조합 무조건 선택")
                emergency_course = self._convert_combination_to_course(selected_combinations[0], 1, weather)
                selected_courses.append(emergency_course)
                
                # 4개 이상 카테고리면 무조건 3개까지 생성
                if is_very_complex and len(selected_combinations) >= 3:
                    for i in range(1, 3):
                        if i < len(selected_combinations):
                            additional_course = self._convert_combination_to_course(
                                selected_combinations[i], i + 1, weather
                            )
                            selected_courses.append(additional_course)
                    logger.warning(f"🆘 4개+ 카테고리 응급처치: 3개 코스 강제 생성 완료")
            
            # 2단계: 부족한 코스 보충 (복잡한 시나리오는 더 적극적으로)
            elif len(selected_courses) < 3 and is_complex and len(selected_combinations) > len(selected_courses):
                target_count = 3 if is_very_complex else max(2, len(selected_courses) + 1)
                needed = min(target_count - len(selected_courses), len(selected_combinations) - len(selected_courses))
                
                for i in range(needed):
                    if len(selected_courses) + i < len(selected_combinations):
                        additional_course = self._convert_combination_to_course(
                            selected_combinations[len(selected_courses) + i], 
                            len(selected_courses) + i + 1, 
                            weather
                        )
                        selected_courses.append(additional_course)
                
                logger.warning(f"🚨 {needed}개 코스 추가 생성 완료 (복잡도: {'매우높음' if is_very_complex else '높음'})")
            
            logger.info(f"✅ 스마트 GPT 코스 선택 완료 - {len(selected_courses)}개 선택")
            return selected_courses
            
        except Exception as e:
            logger.error(f"❌ 스마트 GPT 코스 선택 실패: {e}")
            return []
    
    def _pre_filter_combinations(
        self, 
        combinations: List[Dict[str, Any]], 
        user_context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """사전 필터링: 룰 기반으로 조합 수 줄이기"""
        try:
            # 1단계: 거리 기준 필터링
            max_distance = self._get_max_distance_from_context(user_context)
            distance_filtered = [
                combo for combo in combinations 
                if combo.get('total_distance_meters', 0) <= max_distance
            ]
            
            # 2단계: 품질 점수 기준 정렬
            quality_sorted = sorted(
                distance_filtered,
                key=lambda x: x.get('quality_score', 0),
                reverse=True
            )
            
            # 3단계: 다양성 고려 선택
            diverse_combinations = self._select_diverse_combinations(
                quality_sorted, self.max_combinations_for_gpt
            )
            
            return diverse_combinations
            
        except Exception as e:
            logger.error(f"사전 필터링 실패: {e}")
            return combinations[:self.max_combinations_for_gpt]
    
    def _get_max_distance_from_context(self, user_context: Dict[str, Any]) -> int:
        """사용자 컨텍스트에서 최대 허용 거리 추출"""
        try:
            # 교통수단 고려
            transportation = user_context.get('requirements', {}).get('transportation', '대중교통')
            
            if '자차' in transportation or '차' in transportation:
                return 15000  # 15km
            elif '택시' in transportation:
                return 12000  # 12km
            else:  # 대중교통, 도보
                return 8000   # 8km
                
        except Exception as e:
            logger.debug(f"최대 거리 추출 실패: {e}")
            return 10000  # 기본값 10km
    
    def _select_diverse_combinations(
        self, 
        combinations: List[Dict[str, Any]], 
        target_count: int
    ) -> List[Dict[str, Any]]:
        """다양성을 고려한 조합 선택"""
        try:
            if len(combinations) <= target_count:
                return combinations
            
            selected = []
            used_place_ids = set()
            
            # 1순위: 품질 점수가 높으면서 새로운 장소 포함
            for combo in combinations:
                if len(selected) >= target_count:
                    break
                
                combo_place_ids = {
                    place.get('place_id', '') 
                    for place in combo.get('course_sequence', [])
                }
                
                # 50% 이상 새로운 장소면 선택
                new_places = combo_place_ids - used_place_ids
                overlap_ratio = len(new_places) / len(combo_place_ids) if combo_place_ids else 0
                
                if overlap_ratio >= 0.5 or len(selected) < target_count // 2:
                    selected.append(combo)
                    used_place_ids.update(combo_place_ids)
            
            # 2순위: 남은 슬롯을 품질 순으로 채움
            remaining_count = target_count - len(selected)
            if remaining_count > 0:
                remaining_combos = [combo for combo in combinations if combo not in selected]
                selected.extend(remaining_combos[:remaining_count])
            
            return selected
            
        except Exception as e:
            logger.error(f"다양성 선택 실패: {e}")
            return combinations[:target_count]
    
    async def _intelligent_selection(
        self,
        combinations: List[Dict[str, Any]],
        user_context: Dict[str, Any],
        weather: str
    ) -> List[Dict[str, Any]]:
        """지능적 조합 선택 (GPT 또는 고급 룰) - 수정된 버전"""
        try:
            # 🔥 수정: 1개여도 GPT 호출하도록 변경
            # 기존: if len(combinations) <= 1: return combinations
            # 조합이 0개면 빈 리스트 반환, 1개 이상이면 무조건 GPT 호출
            if len(combinations) == 0:
                logger.warning("조합이 0개 - 빈 리스트 반환")
                return []
            
            # OpenAI 클라이언트가 없으면 룰 기반
            if self.openai_client is None:
                logger.warning("OpenAI 클라이언트가 없어서 룰 기반 선택")
                return self._rule_based_selection(combinations, user_context, weather)
            
            # 🔥 수정: 1개든 100개든 항상 GPT 호출 (카테고리 1개일 때도 GPT가 판단)
            # 하지만 조합이 너무 적으면 최소한 확보
            if len(combinations) < self.min_combinations_for_gpt:
                logger.warning(f"🚨 조합 수 부족: {len(combinations)}개 < 최소 {self.min_combinations_for_gpt}개")
                logger.warning("🚨 GPT가 제대로 선택할 수 있도록 최소 조합 수를 맞춰야 합니다!")
            
            logger.info(f"🤖 GPT-4o mini 지능적 선택 시작 - {len(combinations)}개 조합")
            return await self._call_gpt_for_course_selection(combinations, user_context, weather)
                
        except Exception as e:
            logger.error(f"지능적 선택 실패: {e}")
            return combinations[:3]
    
    async def _call_gpt_for_course_selection(
        self,
        combinations: List[Dict[str, Any]],
        user_context: Dict[str, Any],
        weather: str
    ) -> List[Dict[str, Any]]:
        """실제 GPT-4o mini를 호출하여 최적 코스 선택"""
        try:
            if not self.openai_client:
                logger.warning("OpenAI 클라이언트가 없어서 고급 룰 기반으로 대체")
                return self._advanced_rule_selection(combinations, user_context, weather)
            
            # 프롬프트 생성
            prompt = self._create_selection_prompt(combinations, user_context, weather)
            
            # GPT 호출
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "당신은 데이트 코스 추천 전문가입니다."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1500
            )
            
            # 응답 파싱
            gpt_response = response.choices[0].message.content
            selected_combinations = self._parse_gpt_response(gpt_response, combinations)
            
            logger.info(f"✅ GPT-4o mini 선택 완료: {len(selected_combinations)}개 조합")
            return selected_combinations[:3]  # 상위 3개만 반환
            
        except Exception as e:
            logger.error(f"GPT 호출 실패: {e}")
            # 실패시 기존 룰 기반으로 폴백
            return self._advanced_rule_selection(combinations, user_context, weather)
    
    def _create_selection_prompt(
        self, 
        combinations: List[Dict[str, Any]], 
        user_context: Dict[str, Any], 
        weather: str
    ) -> str:
        """GPT용 프롬프트 생성 - 완전한 개인화 정보 포함"""
        try:
            # 사용자 정보 요약 (user_context 완전 전달)
            demographics = user_context.get('demographics', {})
            preferences = user_context.get('preferences', [])
            requirements = user_context.get('requirements', {})
            
            # course_planning 정보 추출 (새로 추가)
            course_planning = user_context.get('course_planning', {})
            optimization_goals = course_planning.get('optimization_goals', [])
            route_constraints = course_planning.get('route_constraints', {})
            sequence_optimization = course_planning.get('sequence_optimization', {})
            
            user_info = f"""🎯 완전한 사용자 프로필

📋 기본 정보:
- 나이: {demographics.get('age', '미상')}세
- MBTI: {demographics.get('mbti', '미상')}
- 관계: {demographics.get('relationship_stage', '미상')}
- 데이트 경험: {demographics.get('dating_experience', '보통')}

💝 선호도 및 요구사항:
- 선호도: {', '.join(preferences) if preferences else '특별한 선호 없음'}
- 예산: {requirements.get('budget_range', '미상')}
- 시간대: {requirements.get('time_preference', '하루 종일')}
- 인원: {requirements.get('party_size', 2)}명
- 교통수단: {requirements.get('transportation', '대중교통')}
- 특별 요청: {requirements.get('special_requests', '없음')}

🎪 데이트 목표 및 제약사항:
- 최적화 목표: {', '.join(optimization_goals) if optimization_goals else '일반적인 데이트 경험'}
- 최대 이동시간: {route_constraints.get('max_travel_time_between', 30)}분
- 총 데이트 시간: {route_constraints.get('total_course_duration', 240)}분
- 일정 유연성: {route_constraints.get('flexibility', 'medium')}
- 순서 변경 허용: {'불가' if not sequence_optimization.get('allow_reordering', True) else '가능'}

🌤️ 상황 정보:
- 날씨: {'비오는 날' if weather == 'rainy' else '맑은 날'}"""
            
            # 조합 정보 (전체 전달 - 최대 20개)
            combinations_info = ""
            display_count = min(len(combinations), 10)  # 최대 10개 (15초 최적화)
            for i, combo in enumerate(combinations[:display_count]):
                places_info = []
                for place in combo.get('course_sequence', []):
                    description = place.get('description', '') or place.get('summary', '')
                    if description:
                        # description이 너무 길면 200자로 자르기
                        desc_text = description[:200] + '...' if len(description) > 200 else description
                        places_info.append(
                            f"- {place.get('place_name', '')} ({place.get('category', '')}): {desc_text}"
                        )
                    else:
                        places_info.append(
                            f"- {place.get('place_name', '')} ({place.get('category', '')})"
                        )
                
                combinations_info += f"""\n조합 {i+1}:
{chr(10).join(places_info)}
총 이동거리: {combo.get('total_distance_meters', 0)}m
품질 점수: {combo.get('quality_score', 0):.2f}\n"""
            
            prompt = f"""{user_info}

다음 {display_count} 개의 데이트 코스 조합 중에서 사용자에게 가장 적합한 3개를 선택해주세요.
{combinations_info}

선택 기준:
1. 사용자의 선호도와 일치도
2. 날씨 적합성 
3. 이동 편의성
4. 전체적인 데이트 경험 품질

중요: 반드시 3개를 선택해야 합니다. 조합이 적어도 최대한 다양한 3개를 골라주세요.

반드시 아래 형식을 정확하게 따라주세요:

선택된 조합: [1, 3, 5]
코스 제목:
- **조합 1**: "〔코스의 특성을 담은 매력적인 제목〕"
- **조합 3**: "〔코스의 특성을 담은 매력적인 제목〕"
- **조합 5**: "〔코스의 특성을 담은 매력적인 제목〕"
이유:
- **조합 1**: (선택한 이유를 장소별로 구체적으로 2-3문장으로 설명)
- **조합 3**: (선택한 이유를 장소별로 구체적으로 2-3문장으로 설명)
- **조합 5**: (선택한 이유를 장소별로 구체적으로 2-3문장으로 설명)"""
            
            return prompt
            
        except Exception as e:
            logger.error(f"GPT 프롬프트 생성 실패: {e}")
            return "기본 프롬프트"
    
    def _parse_gpt_response(
        self, 
        gpt_response: str, 
        combinations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """GPT 응답을 파싱하여 선택된 조합 반환 (코스 제목 포함)"""
        try:
            # "선택된 조합: [1, 3, 5]" 형식에서 숫자 추출
            pattern = r'\[(\d+(?:,\s*\d+)*)\]'
            match = re.search(pattern, gpt_response)
            
            if match:
                # 선택된 조합 번호들
                selected_indices = [int(x.strip()) - 1 for x in match.group(1).split(',')]
                selected_combinations = []
                
                for idx in selected_indices:
                    if 0 <= idx < len(combinations):
                        combo = combinations[idx].copy()
                        combo_number = idx + 1
                        
                        # 🔥 GPT가 생성한 코스 제목 추출
                        course_title = self._extract_course_title_from_response(gpt_response, combo_number)
                        combo['course_title'] = course_title
                        
                        # GPT 응답에서 추천 이유 추출
                        combo['gpt_reason'] = self._extract_reason_from_response(gpt_response, combo_number)
                        selected_combinations.append(combo)
                
                logger.info(f"✅ GPT 응답 파싱 성공: {len(selected_combinations)}개 조합 선택")
                return selected_combinations
            else:
                # 파싱 실패시 상위 3개 반환
                logger.warning("GPT 응답 파싱 실패, 상위 3개 조합 반환")
                return combinations[:3]
                
        except Exception as e:
            logger.error(f"GPT 응답 파싱 실패: {e}")
            return combinations[:3]
    
    def _extract_course_title_from_response(self, gpt_response: str, combo_number: int) -> str:
        """GPT 응답에서 특정 조합의 코스 제목 추출"""
        try:
            # "코스 제목:" 섹션 찾기
            title_section_start = gpt_response.find('코스 제목:')
            if title_section_start == -1:
                return f"매력적인 데이트 코스 {combo_number}"
            
            # "이유:" 섹션까지 추출
            reason_section_start = gpt_response.find('이유:', title_section_start)
            if reason_section_start == -1:
                title_section = gpt_response[title_section_start:]
            else:
                title_section = gpt_response[title_section_start:reason_section_start]
            
            # 해당 조합 번호의 제목 찾기
            lines = title_section.split('\n')
            for line in lines:
                if f'조합 {combo_number}' in line or f'**조합 {combo_number}**' in line:
                    # "조합 1": "제목" 형식에서 제목 추출
                    if '"' in line:
                        quotes = [i for i, char in enumerate(line) if char == '"']
                        if len(quotes) >= 2:
                            title = line[quotes[0]+1:quotes[1]]
                            return title.strip('〔〕"')
            
            # 찾지 못하면 기본 제목
            return f"특별한 데이트 코스 {combo_number}"
            
        except Exception as e:
            logger.debug(f"코스 제목 추출 실패: {e}")
            return f"데이트 코스 {combo_number}"
    
    def _extract_reason_from_response(self, gpt_response: str, combo_number: int) -> str:
        """GPT 응답에서 특정 조합의 추천 이유 추출"""
        try:
            # "이유:" 다음 텍스트에서 해당 조합 관련 내용 찾기
            reason_section = gpt_response.split('이유:')[-1] if '이유:' in gpt_response else gpt_response
            
            # 조합 번호 관련 문장 찾기
            lines = reason_section.split('\n')
            for line in lines:
                if f'조합 {combo_number}' in line or f'{combo_number}번' in line:
                    return line.strip()
            
            # 찾지 못하면 기본 메시지
            return f"GPT가 추천한 최적의 조합 {combo_number}"
            
        except Exception as e:
            logger.debug(f"이유 추출 실패: {e}")
            return f"추천 조합 {combo_number}"
    
    def _rule_based_selection(
        self,
        combinations: List[Dict[str, Any]],
        user_context: Dict[str, Any],
        weather: str
    ) -> List[Dict[str, Any]]:
        """룰 기반 선택 (10개 이하)"""
        try:
            scored_combinations = []
            
            for combo in combinations:
                score = self._calculate_selection_score(combo, user_context, weather)
                scored_combinations.append((combo, score))
            
            # 점수 순으로 정렬하여 상위 3개 선택
            scored_combinations.sort(key=lambda x: x[1], reverse=True)
            return [combo for combo, score in scored_combinations[:3]]
            
        except Exception as e:
            logger.error(f"룰 기반 선택 실패: {e}")
            return combinations[:3]
    
    def _advanced_rule_selection(
        self,
        combinations: List[Dict[str, Any]],
        user_context: Dict[str, Any],
        weather: str
    ) -> List[Dict[str, Any]]:
        """고급 룰 기반 선택 (10개 초과)"""
        try:
            # 1단계: 카테고리별 점수 계산
            categorized_scores = self._calculate_category_scores(combinations, user_context, weather)
            
            # 2단계: 균형 잡힌 선택
            selected = []
            
            # 거리별 그룹으로 나누기
            short_distance = [c for c in combinations if c.get('total_distance_meters', 0) < 3000]
            medium_distance = [c for c in combinations if 3000 <= c.get('total_distance_meters', 0) < 6000]
            long_distance = [c for c in combinations if c.get('total_distance_meters', 0) >= 6000]
            
            # 각 그룹에서 최고 점수 1개씩
            for group in [short_distance, medium_distance, long_distance]:
                if group and len(selected) < 3:
                    best_in_group = max(group, key=lambda x: categorized_scores.get(x['combination_id'], 0))
                    selected.append(best_in_group)
            
            # 부족하면 전체에서 보충
            if len(selected) < 3:
                remaining = [c for c in combinations if c not in selected]
                remaining_scored = sorted(
                    remaining, 
                    key=lambda x: categorized_scores.get(x['combination_id'], 0),
                    reverse=True
                )
                selected.extend(remaining_scored[:3-len(selected)])
            
            return selected[:3]
            
        except Exception as e:
            logger.error(f"고급 룰 선택 실패: {e}")
            return combinations[:3]
    
    def _calculate_selection_score(
        self, 
        combination: Dict[str, Any], 
        user_context: Dict[str, Any], 
        weather: str
    ) -> float:
        """조합 선택 점수 계산"""
        try:
            score = 0.0
            
            # 1. 기본 품질 점수 (40%)
            quality_score = combination.get('quality_score', 0.0)
            score += quality_score * 0.4
            
            # 2. 거리 점수 (30%)
            distance = combination.get('total_distance_meters', 0)
            preferred_distance = self._get_preferred_distance(user_context)
            distance_score = max(0, 1 - abs(distance - preferred_distance) / preferred_distance)
            score += distance_score * 0.3
            
            # 3. 날씨 적합성 (20%)
            weather_score = self._calculate_weather_compatibility(combination, weather)
            score += weather_score * 0.2
            
            # 4. 사용자 선호 매칭 (10%)
            preference_score = self._calculate_preference_match(combination, user_context)
            score += preference_score * 0.1
            
            return score
            
        except Exception as e:
            logger.debug(f"선택 점수 계산 실패: {e}")
            return 0.0
    
    def _calculate_category_scores(
        self, 
        combinations: List[Dict[str, Any]], 
        user_context: Dict[str, Any], 
        weather: str
    ) -> Dict[str, float]:
        """카테고리별 점수 계산"""
        scores = {}
        
        for combo in combinations:
            combo_id = combo.get('combination_id', '')
            score = self._calculate_selection_score(combo, user_context, weather)
            scores[combo_id] = score
        
        return scores
    
    def _get_preferred_distance(self, user_context: Dict[str, Any]) -> int:
        """사용자 선호 거리 추정"""
        try:
            # MBTI 고려
            mbti = user_context.get('demographics', {}).get('mbti', '')
            if 'E' in mbti:  # 외향적
                return 6000  # 더 활동적인 코스 선호
            else:  # 내향적
                return 3000  # 편안한 코스 선호
                
        except Exception as e:
            return 4000  # 기본값
    
    def _calculate_weather_compatibility(self, combination: Dict[str, Any], weather: str) -> float:
        """날씨 적합성 점수"""
        try:
            if weather == "rainy":
                # 비올 때는 실내 활동 선호
                indoor_categories = {'문화시설', '휴식시설', '카페', '음식점', '술집', '쇼핑'}
                
                places = combination.get('course_sequence', [])
                indoor_count = sum(1 for place in places if place.get('category') in indoor_categories)
                
                return indoor_count / len(places) if places else 0
            else:
                # 맑을 때는 모든 활동 가능
                return 1.0
                
        except Exception as e:
            return 0.5
    
    def _calculate_preference_match(self, combination: Dict[str, Any], user_context: Dict[str, Any]) -> float:
        """사용자 선호 매칭 점수"""
        try:
            preferences = user_context.get('preferences', [])
            if not preferences:
                return 0.5
            
            # 선호도 키워드 매칭
            preference_keywords = []
            for pref in preferences:
                if '로맨틱' in pref:
                    preference_keywords.extend(['로맨틱', '분위기', '특별한'])
                elif '활동적' in pref:
                    preference_keywords.extend(['활동', '체험', '재미'])
                elif '조용한' in pref:
                    preference_keywords.extend(['조용', '편안', '휴식'])
            
            # 조합의 장소 설명에서 키워드 매칭
            places = combination.get('course_sequence', [])
            total_matches = 0
            total_descriptions = 0
            
            for place in places:
                description = place.get('description', '')
                if description:
                    total_descriptions += 1
                    matches = sum(1 for keyword in preference_keywords if keyword in description)
                    total_matches += min(matches, 1)  # 장소당 최대 1점
            
            if total_descriptions == 0:
                return 0.5
            
            return total_matches / total_descriptions
            
        except Exception as e:
            return 0.5
    
    def _convert_combination_to_course(
        self, 
        combination: Dict[str, Any], 
        course_number: int, 
        weather: str
    ) -> Dict[str, Any]:
        """조합을 코스 형태로 변환 (🔥 GPT 생성 제목 포함)"""
        try:
            # 🔥 GPT가 생성한 제목 사용, 없으면 기본 제목
            course_title = combination.get('course_title', f"{weather}_course_{course_number}")
            course_id = f"{weather}_course_{course_number}"
            
            # 장소 정보 변환
            places = []
            for i, place in enumerate(combination.get('course_sequence', [])):
                place_info = {
                    'sequence': i + 1,
                    'place_id': place.get('place_id', ''),
                    'name': place.get('place_name', ''),
                    'category': place.get('category', ''),
                    'coordinates': {
                        'latitude': place.get('latitude', 0),
                        'longitude': place.get('longitude', 0)
                    },
                    'description': place.get('description', ''),
                    'similarity_score': place.get('similarity_score', 0.0)
                }
                places.append(place_info)
            
            # 이동 정보
            travel_info = combination.get('travel_distances', [])
            
            # 추천 이유 생성
            recommendation_reason = self._generate_smart_recommendation_reason(
                combination, weather, course_number
            )
            
            course = {
                'course_id': course_id,
                'course_title': course_title,  # 🔥 GPT 생성 제목 추가
                'places': places,
                'travel_info': travel_info,
                'total_distance_meters': combination.get('total_distance_meters', 0),
                'recommendation_reason': recommendation_reason,
                'quality_score': combination.get('quality_score', 0.0)
            }
            
            return course
            
        except Exception as e:
            logger.error(f"조합 변환 실패: {e}")
            return {}
    
    def _generate_smart_recommendation_reason(
        self, 
        combination: Dict[str, Any], 
        weather: str, 
        course_number: int
    ) -> str:
        """스마트 추천 이유 생성 (개선된 버전 - 다양화!)"""
        try:
            # GPT가 이미 이유를 제공했다면 그것 사용
            if 'gpt_reason' in combination:
                return combination['gpt_reason']
            total_distance = combination.get('total_distance_meters', 0)
            place_count = len(combination.get('course_sequence', []))
            quality_score = combination.get('quality_score', 0.0)
            places = combination.get('course_sequence', [])
            
            reasons = []
            
            # 거리 기준 평가 (더 세밀하게)
            if total_distance < 1500:
                reasons.append("걸어서 이동 가능한 최적의 근거리 코스")
            elif total_distance < 2500:
                reasons.append("효율적인 동선으로 편안한 데이트 가능")
            else:
                reasons.append("다양한 동네를 경험하는 풍성한 여행")
            
            # 장소별 특성 분석 (실제 장소 이름/카테고리 고려)
            categories = [place.get('category', '') for place in places]
            place_names = [place.get('place_name', '') for place in places]
            
            # 카테고리 조합에 따른 특징
            if '음식점' in categories and '카페' in categories:
                reasons.append("맛있는 식사와 여유로운 디저트 타임이 있는 코스")
            elif '문화시설' in categories:
                reasons.append("교양과 예술을 함께 즐길 수 있는 문화 데이트")
            elif '술집' in categories:
                reasons.append("로맨틱한 저녁 시간을 위한 특별한 코스")
            
            # 품질 기준 평가 (다양화)
            if quality_score >= 0.8:
                reasons.append("유명한 맛집과 명소들로 구성된 프리미엄 코스")
            elif quality_score >= 0.6:
                reasons.append("검증된 인기 장소들로 안정적인 만족도 보장")
            else:
                reasons.append("숨겨진 보석 같은 장소들을 발견하는 재미")
            
            # 날씨 고려 (더 구체적으로)
            if weather == "rainy":
                reasons.append("많은 비가 와도 실내에서 편안하게 즐기는 코스")
            else:
                reasons.append("맑은 하늘 아래에서 더욱 아름다운 추억 만들기")
            
            # 순위별 특징 (각각 다르게)
            if course_number == 1:
                reasons.append("가장 밸런스 있고 안전한 선택")
            elif course_number == 2:
                reasons.append("좀 더 모험적이고 색다른 매력의 대안")
            else:
                reasons.append("예상치 못한 즐거움을 주는 독특한 선택")
            
            return ". ".join(reasons) + "."
            
        except Exception as e:
            logger.error(f"추천 이유 생성 실패: {e}")
            return "사용자 맞춤 추천 코스입니다."
    
    async def validate_course_quality(
        self, 
        course: Dict[str, Any], 
        user_context: Dict[str, Any],
        lenient: bool = False
    ) -> bool:
        """코스 품질 검증 (관대한 기준 옵션 추가)"""
        try:
            # 기본 검증
            if not course.get('places'):
                return False
            
            # 카테고리 수에 따른 추가 완화
            category_count = len(user_context.get('search_targets', []))
            is_very_complex = category_count >= 4
            super_lenient = lenient or is_very_complex  # 4개+ 카테고리는 초관대
            
            # 거리 검증 (비오는 날은 오히려 더 엄격하게, 하지만 복잡한 경우는 완화)
            max_distance = self._get_max_distance_from_context(user_context)
            if lenient:
                max_distance = int(max_distance * 0.6)  # 비오는 날은 이동거리 최소화
            elif is_very_complex:
                max_distance = int(max_distance * 1.5)  # 복잡한 경우는 거리 완화
            
            if course.get('total_distance_meters', 0) > max_distance:
                if not super_lenient:
                    logger.debug(f"거리 초과로 코스 거절: {course.get('total_distance_meters')}m > {max_distance}m")
                    return False
            
            # 장소 수 검증
            place_count = len(course.get('places', []))
            if place_count < 1:
                return False
            
            # 품질 점수 검증 (관대한 기준에서는 더 낮은 점수도 허용)
            quality_score = course.get('quality_score', 0.0)
            if super_lenient:
                min_quality = 0.05  # 초관대: 거의 모든 코스 허용
            elif lenient:
                min_quality = 0.1   # 관대: 매우 낮은 품질도 허용
            else:
                min_quality = 0.3   # 기본: 적당한 품질 요구
                
            if quality_score < min_quality:
                if not super_lenient:
                    logger.debug(f"품질 점수 부족으로 코스 거절: {quality_score} < {min_quality}")
                    return False
            
            if super_lenient:
                logger.debug(f"🆘 초관대 기준으로 코스 승인: 거리={course.get('total_distance_meters')}m, 품질={quality_score}, 복잡도={category_count}")
            elif lenient:
                logger.debug(f"🌧️ 관대한 기준으로 코스 승인: 거리={course.get('total_distance_meters')}m, 품질={quality_score}")
            
            return True
            
        except Exception as e:
            logger.error(f"코스 품질 검증 실패: {e}")
            return False

# 하위 호환성을 위한 별칭
GPTSelector = SmartGPTSelector

if __name__ == "__main__":
    # 테스트 실행
    async def test_smart_gpt_selector():
        try:
            selector = SmartGPTSelector()
            
            # 테스트 조합 데이터 (많은 수)
            test_combinations = []
            for i in range(25):  # 25개 조합으로 테스트
                combo = {
                    'combination_id': f'combo_{i+1}',
                    'course_sequence': [
                        {
                            'place_id': f'place_{i+1}_1',
                            'place_name': f'테스트 장소 {i+1}-1',
                            'category': '음식점',
                            'latitude': 37.5519 + i * 0.001,
                            'longitude': 126.9245 + i * 0.001,
                            'description': f'테스트 설명 {i+1}',
                            'similarity_score': 0.9 - (i * 0.02)
                        }
                    ],
                    'travel_distances': [],
                    'total_distance_meters': 1000 + i * 200,
                    'quality_score': 0.9 - (i * 0.02)
                }
                test_combinations.append(combo)
            
            test_user_context = {
                'preferences': ['로맨틱한 분위기'],
                'requirements': {'party_size': 2, 'transportation': '대중교통'},
                'demographics': {'mbti': 'ENFJ'}
            }
            
            courses = await selector.select_best_courses(
                test_combinations, test_user_context, "sunny", "1차"
            )
            
            logger.info(f"✅ 스마트 GPT 선택기 테스트 성공")
            logger.info(f"   - 입력: {len(test_combinations)}개 조합")
            logger.info(f"   - 출력: {len(courses)}개 코스")
            logger.info(f"   - 조합 폭발 방지 및 품질 유지 성공! 🎉")
            
        except Exception as e:
            logger.error(f"❌ 스마트 GPT 선택기 테스트 실패: {e}")
    
    asyncio.run(test_smart_gpt_selector())
