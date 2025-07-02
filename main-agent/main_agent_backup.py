import asyncio
from typing import Dict, Any, List, Optional
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain
from langchain_openai import OpenAI
import re
import uuid
from datetime import datetime, timezone
import os
import time
import json
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.runnables import RunnableLambda
from langchain_core.messages import HumanMessage, AIMessage
from hanspell import spell_checker

# --- 확장된 UserProfile 및 UserRequest 데이터 클래스 ---
class UserProfile:
    def __init__(self, mbti=None, age=None, relationship_stage=None, 
                 budget_level=None, time_preference=None, transportation=None,
                 max_travel_time=None, atmosphere_preference=None, preferences=None):
        # 기본 프로필
        self.mbti = mbti
        self.age = age
        self.relationship_stage = relationship_stage
        
        # 상세 요구사항
        self.budget_level = budget_level  # "low", "medium", "high"
        self.time_preference = time_preference  # "아침", "점심", "저녁", "밤"
        self.transportation = transportation  # "도보", "대중교통", "자차", "택시"
        self.max_travel_time = max_travel_time  # 분 단위
        self.atmosphere_preference = atmosphere_preference  # "조용한", "활기찬", "로맨틱", "트렌디한" 등
        self.preferences = preferences or []  # 자유 형식 선호사항 리스트

    def is_complete_basic(self):
        """기본 프로필 완성도 체크"""
        return self.mbti is not None and self.age is not None and self.relationship_stage is not None

    def is_complete_detailed(self):
        """상세 정보 포함 완성도 체크"""
        basic_complete = self.is_complete_basic()
        detailed_complete = (
            self.budget_level is not None and 
            self.time_preference is not None and
            self.transportation is not None
        )
        return basic_complete and detailed_complete

    def missing_basic_fields(self):
        """누락된 기본 필드 반환"""
        missing = []
        if self.mbti is None:
            missing.append('mbti')
        if self.age is None:
            missing.append('age')
        if self.relationship_stage is None:
            missing.append('relationship_stage')
        return missing

    def missing_detailed_fields(self):
        """누락된 상세 필드 반환"""
        missing = []
        if self.budget_level is None:
            missing.append('budget_level')
        if self.time_preference is None:
            missing.append('time_preference')
        if self.transportation is None:
            missing.append('transportation')
        if self.max_travel_time is None:
            missing.append('max_travel_time')
        if self.atmosphere_preference is None:
            missing.append('atmosphere_preference')
        return missing

    def missing_fields(self):
        """모든 누락된 필드 반환 (하위 호환성)"""
        return self.missing_basic_fields() + self.missing_detailed_fields()

    def is_complete(self):
        """
        추천 가능한 최소 조건 체크 (채팅봇용)
        기본 정보가 있으면 추천 가능하도록 설정
        """
        # 최소 필수 정보: 나이, 관계 단계만 있으면 추천 가능
        return self.age is not None and self.relationship_stage is not None
    
    def is_ready_for_recommendation(self):
        """추천에 최적화된 정보 완성도 체크"""
        critical_info = self.age is not None and self.relationship_stage is not None
        location_info = hasattr(self, 'location') and getattr(self, 'location', None) is not None
        return critical_info and location_info
    
    def get_completion_score(self):
        """정보 완성도 점수 (0.0 ~ 1.0)"""
        total_fields = 9  # 기본 3개 + 상세 6개
        completed_fields = 0
        
        # 기본 프로필 체크
        if self.age is not None:
            completed_fields += 1
        if self.mbti is not None:
            completed_fields += 1
        if self.relationship_stage is not None:
            completed_fields += 1
            
        # 상세 요구사항 체크
        if self.budget_level is not None:
            completed_fields += 1
        if self.time_preference is not None:
            completed_fields += 1
        if self.transportation is not None:
            completed_fields += 1
        if self.max_travel_time is not None:
            completed_fields += 1
        if self.atmosphere_preference is not None:
            completed_fields += 1
        if self.preferences and len(self.preferences) > 0:
            completed_fields += 1
            
        return completed_fields / total_fields

    def to_dict(self):
        """JSON 변환용 딕셔너리 반환"""
        return {
            "demographics": {
                "age": self.age,
                "mbti": self.mbti,
                "relationship_stage": self.relationship_stage
            },
            "preferences": self.preferences,
            "requirements": {
                "budget_level": self.budget_level,
                "time_preference": self.time_preference,
                "transportation": self.transportation,
                "max_travel_time": self.max_travel_time,
                "atmosphere_preference": self.atmosphere_preference
            }
        }

class UserRequest:
    def __init__(self, message, location=None, concept=None, user_profile=None, budget=None, time=None, date=None):
        self.message = message
        self.location = location
        self.concept = concept
        self.user_profile = user_profile
        self.budget = budget
        self.time = time
        self.date = date

# --- 카테고리 매핑 샘플 ---
# 계획서 기준으로 구체화된 카테고리 매핑
LOCATION_CATEGORY_MAPPING = {
    "강남구": {
        "로맨틱": ["파인다이닝", "와인바", "루프탑카페", "갤러리"],
        "캐주얼": ["브런치카페", "일반카페", "캐주얼다이닝", "쇼핑몰"],
        "액티브": ["체험관", "스포츠바", "게임카페", "볼링장"]
    },
    "마포구": {  # 홍대
        "로맨틱": ["힙한바", "루프탑바", "감성카페", "소극장"],
        "캐주얼": ["브런치카페", "펍", "이자카야", "플리마켓"],
        "액티브": ["클럽", "노래방", "방탈출", "당구장"]
    },
    "용산구": {  # 이태원
        "로맨틱": ["이색레스토랑", "와인바", "루프탑바", "갤러리"],
        "캐주얼": ["세계음식", "브런치", "펍", "카페"],
        "액티브": ["클럽", "바", "외국인바", "쇼핑몰"]
    }
}

# --- 데이트 코스 추천 카테고리 목록 (vectorDB 기준) ---
CATEGORY_LIST = [
    "기타",        # 기타 장소들
    "쇼핑",        # 쇼핑 관련 장소들
    "문화시설",    # 문화 시설 및 전시 공간들
    "술집",        # 술집 및 바 관련 장소들
    "야외활동",    # 야외 활동 및 레저 시설들
    "엔터테인먼트",# 엔터테인먼트 및 놀이 시설들
    "음식점",      # 음식점 및 식당들
    "카페",        # 카페 및 디저트 전문점들
    "휴식시설"     # 휴식 및 숙박 시설들
]

def boost_categories(categories):
    # 샘플: 단순히 리스트에 추가 (실제 구현은 가중치 조정)
    return categories

def prioritize_categories(categories):
    # 샘플: 단순히 리스트 앞에 추가
    return categories

# --- 적응형 재질문 관리자 ---
class AdaptiveReaskManager:
    def __init__(self):
        # 정보 우선순위 점수
        self.INFO_PRIORITY = {
            "location": 95,        # 장소 추천에 절대 필요
            "concept": 85,         # 분위기/컨셉은 핵심
            "age": 70,            # 연령대별 선호도 차이
            "relationship": 65,    # 데이트 vs 친구 만남
            "budget": 60,         # 가격대 필터링
            "transportation": 40,  # 이동 수단
            "time_preference": 35, # 시간대 선호
            "max_travel_time": 30  # 최대 이동 시간
        }
        
        # 완성도 임계점 (상향 조정)
        self.THRESHOLDS = {
            "minimum": 0.7,     # 70% 완성도면 기본 추천 가능 (0.6에서 0.7로 상향)
            "optimal": 0.85,    # 85% 완성도면 고품질 추천 (0.8에서 0.85로 상향)
            "maximum": 1.0      # 100% 완성도
        }
        
        # 최대 질문 수 (증가)
        self.MAX_QUESTIONS = {
            "forced": 4,        # 강제 질문 최대 4개 (2에서 4로 증가)
            "total": 6          # 총 질문 최대 6개 (4에서 6으로 증가)
        }
        
        # 질문 유형별 필수 정보 (age를 essential로 승격)
        self.QUESTION_TYPE_REQUIREMENTS = {
            "simple_place": {"essential": ["location", "concept", "age"], "helpful": ["relationship", "budget"]},
            "date_planning": {"essential": ["location", "relationship", "concept", "age"], "helpful": ["budget"]},
            "activity_search": {"essential": ["location", "age", "concept"], "helpful": ["relationship", "budget"]},
            "general": {"essential": ["location", "concept", "relationship", "age"], "helpful": ["budget"]}
        }
    
    def analyze_question_complexity(self, user_input):
        """사용자 질문의 복잡도 분석"""
        simple_keywords = ["추천", "어디", "카페", "맛집", "가볼만한"]
        date_keywords = ["데이트", "썸", "연인", "커플", "만남"]
        activity_keywords = ["할거리", "체험", "활동", "놀거리"]
        
        if any(keyword in user_input for keyword in date_keywords):
            return "date_planning"
        elif any(keyword in user_input for keyword in activity_keywords):
            return "activity_search"
        elif any(keyword in user_input for keyword in simple_keywords):
            return "simple_place"
        else:
            return "general"
    
    def calculate_weighted_completion(self, current_info, question_type="general"):
        """가중치 기반 완성도 계산 (디버깅 강화)"""
        requirements = self.QUESTION_TYPE_REQUIREMENTS.get(question_type, self.QUESTION_TYPE_REQUIREMENTS["general"])
        essential_info = requirements["essential"]
        helpful_info = requirements["helpful"]
        
        # 디버깅을 위한 상세 정보 수집
        essential_status = {}
        helpful_status = {}
        
        # 필수 정보 점수 (70% 가중치)
        essential_score = 0
        essential_total = len(essential_info)
        for info in essential_info:
            has_info = self._has_info(current_info, info)
            essential_status[info] = has_info
            if has_info:
                essential_score += 1
        
        # 유용한 정보 점수 (30% 가중치)
        helpful_score = 0
        helpful_total = len(helpful_info)
        for info in helpful_info:
            has_info = self._has_info(current_info, info)
            helpful_status[info] = has_info
            if has_info:
                helpful_score += 1
        
        # 가중치 적용 완성도 계산
        if essential_total > 0 and helpful_total > 0:
            essential_ratio = essential_score / essential_total
            helpful_ratio = helpful_score / helpful_total
            completion = essential_ratio * 0.7 + helpful_ratio * 0.3
        elif essential_total > 0:
            completion = essential_score / essential_total
        else:
            completion = 0
        
        # 디버깅 출력
        print(f"\n🔍 [완성도 계산] 질문타입: {question_type}")
        print(f"   필수정보 ({essential_score}/{essential_total}): {essential_status}")
        print(f"   유용정보 ({helpful_score}/{helpful_total}): {helpful_status}")
        print(f"   최종 완성도: {completion:.2f}")
            
        return completion
    
    def _has_info(self, current_info, info_type):
        """특정 정보가 있는지 확인 (특별 맥락 고려)"""
        if info_type == "location":
            return current_info.get("location") is not None and current_info.get("location").strip() != ""
        elif info_type == "concept":
            concept = current_info.get("concept")
            return concept is not None and concept.strip() != ""
        elif info_type == "age":
            user_profile = current_info.get("user_profile")
            return user_profile and user_profile.age is not None
        elif info_type == "relationship":
            user_profile = current_info.get("user_profile")
            # "3주년", "여자친구" 등의 맥락에서 관계 정보 추출
            if user_profile and user_profile.relationship_stage is not None:
                return True
            # 특별 맥락 키워드 체크
            state = current_info.get("state", {})
            special_context = state.get("special_context", "")
            relationship_keywords = ["여자친구", "남자친구", "연인", "주년", "커플", "썸"]
            return any(keyword in special_context for keyword in relationship_keywords)
        elif info_type == "budget":
            user_profile = current_info.get("user_profile")
            # budget_level이 있거나, 추가 정보에서 예산 입력이 있으면 True
            if user_profile and user_profile.budget_level is not None:
                return True
            # 추가 정보에서 예산 정보 확인
            state = current_info.get("state", {})
            additional_info = state.get("additional_info_provided", {})
            return additional_info.get("budget") is not None
        elif info_type == "transportation":
            user_profile = current_info.get("user_profile")
            if user_profile and user_profile.transportation is not None:
                return True
            # 추가 정보에서 교통수단 정보 확인
            state = current_info.get("state", {})
            additional_info = state.get("additional_info_provided", {})
            return additional_info.get("transportation") is not None
        elif info_type == "time_preference":
            user_profile = current_info.get("user_profile")
            if user_profile and user_profile.time_preference is not None:
                return True
            # 추가 정보에서 시간 정보 확인
            state = current_info.get("state", {})
            additional_info = state.get("additional_info_provided", {})
            return additional_info.get("time_preference") is not None
        return False
    
    def extract_special_context(self, user_input):
        """특별한 맥락 정보 추출 (기념일, 관계 등)"""
        special_context = []
        
        # 기념일 키워드
        anniversary_keywords = ["주년", "기념일", "생일", "발렌타인", "화이트데이", "크리스마스"]
        relationship_keywords = ["여자친구", "남자친구", "연인", "커플", "썸", "소개팅", "미팅"]
        
        for keyword in anniversary_keywords:
            if keyword in user_input:
                special_context.append(f"특별한날_{keyword}")
        
        for keyword in relationship_keywords:
            if keyword in user_input:
                special_context.append(f"관계_{keyword}")
                
        return special_context
    
    def generate_followup_additional_question(self, additional_info_status):
        """추가 정보 입력 후 누락 정보에 대한 후속 질문"""
        provided = additional_info_status["provided"]
        missing = additional_info_status["missing"]
        
        if not missing:
            return {
                "type": "ready_to_recommend",
                "message": "완벽합니다! 모든 정보가 준비되었어요. 추천해드리겠습니다!"
            }
        
        # 한국어 필드명 매핑
        field_names = {
            "budget": "예산",
            "time_preference": "시간대", 
            "transportation": "교통수단",
            "special_requests": "특별 요청"
        }
        
        provided_text = ", ".join([field_names[field] for field in provided])
        missing_text = ", ".join([field_names[field] for field in missing])
        
        return {
            "type": "followup_additional",
            "message": f"""감사합니다! {provided_text}는 확인했어요 👍

{missing_text}도 추가로 알려주시면 더 정확한 추천이 가능해요!
아니면 "이대로 추천해줘"라고 하시면 지금 정보로 바로 추천드릴게요 😊""",
            "can_skip": True,
            "completion_ratio": additional_info_status["completion_ratio"]
        }
    
    def parse_additional_info(self, user_input):
        """추가 정보 입력에서 구체적 정보 추출"""
        additional_info = {
            "budget": None,
            "time_preference": None,
            "transportation": None,
            "special_requests": None
        }
        
        # 예산 추출
        budget_patterns = [
            r'예산.*?(\d+만?\s?원)',
            r'(\d+만?\s?원)',
            r'(저렴하게|비싸도\s?괜찮|적당히|가격\s?상관없|돈\s?상관없|예산\s?상관없|상관없)'
        ]
        for pattern in budget_patterns:
            match = re.search(pattern, user_input)
            if match:
                additional_info["budget"] = match.group(1)
                break
        
        # 시간대 추출
        time_keywords = ["오전", "점심", "오후", "저녁", "밤", "새벽", "아침", "낮"]
        for keyword in time_keywords:
            if keyword in user_input:
                additional_info["time_preference"] = keyword
                break
        
        # 교통수단 추출
        transport_keywords = ["지하철", "버스", "대중교통", "자차", "차", "도보", "걸어서", "택시", "따릉이"]
        for keyword in transport_keywords:
            if keyword in user_input:
                additional_info["transportation"] = keyword
                break
        
        # 특별 요청 추출
        special_keywords = [
            "프라이빗", "조용한", "로맨틱", "인스타", "야경", "실내", "야외", 
            "주차", "반려동물", "애완동물", "루프탑", "뷰", "전망", "분위기"
        ]
        found_special = []
        for keyword in special_keywords:
            if keyword in user_input:
                found_special.append(keyword)
        if found_special:
            additional_info["special_requests"] = ", ".join(found_special)
        
        # 추출된 정보 디버깅
        extracted = {k: v for k, v in additional_info.items() if v is not None}
        print(f"📝 [추가 정보 추출] 입력: '{user_input}'")
        print(f"📝 [추가 정보 추출] 결과: {extracted if extracted else '정보 없음'}")
        
        return additional_info
    
    def check_additional_info_completeness(self, additional_info):
        """추가 정보 완성도 체크 (인원수 제외)"""
        priority_fields = ["budget", "time_preference", "transportation", "special_requests"]
        provided = []
        missing = []
        
        for field in priority_fields:
            if additional_info.get(field):
                provided.append(field)
            else:
                missing.append(field)
        
        return {
            "provided": provided,
            "missing": missing,
            "completion_ratio": len(provided) / len(priority_fields)
        }
    
    def get_next_action(self, user_input, current_info, forced_questions_count=0, total_questions_count=0):
        """다음 행동 결정 (엄격한 임계점 적용)"""
        question_type = self.analyze_question_complexity(user_input)
        completion_score = self.calculate_weighted_completion(current_info, question_type)
        
        print(f"\n🎯 [행동 결정] 강제질문:{forced_questions_count}/{self.MAX_QUESTIONS['forced']}, 완성도:{completion_score:.2f}")
        
        # 최대 질문 수 초과 시에만 강제 추천
        if forced_questions_count >= self.MAX_QUESTIONS["forced"]:
            print(f"   → 최대 질문 수 도달! 강제 추천 진행")
            if completion_score >= self.THRESHOLDS["minimum"]:
                return "provide_recommendation_with_optional_details"
            else:
                return "provide_basic_recommendation"
        
        # 필수 정보가 모두 있는 경우에만 추천 제안
        missing_info = self.get_missing_info_by_priority(current_info, question_type)
        if missing_info["essential"]:
            print(f"   → 필수 정보 누락: {missing_info['essential']}")
            return "ask_highest_priority_missing"
        
        # 필수 정보는 있지만 완성도에 따른 차등 대응
        if completion_score >= self.THRESHOLDS["optimal"]:
            print(f"   → 완성도 우수! 선택권 제공")
            return "offer_recommendation_with_options"
        elif completion_score >= self.THRESHOLDS["minimum"]:
            print(f"   → 완성도 양호! 선택적 정보 수집 제안")
            return "offer_recommendation_with_optional_details"
        else:
            print(f"   → 완성도 부족! 추가 질문 필요")
            return "ask_highest_priority_missing"
    
    def get_missing_info_by_priority(self, current_info, question_type="general"):
        """우선순위에 따른 누락 정보 반환"""
        requirements = self.QUESTION_TYPE_REQUIREMENTS.get(question_type, self.QUESTION_TYPE_REQUIREMENTS["general"])
        essential_info = requirements["essential"]
        helpful_info = requirements["helpful"]
        
        missing_essential = []
        missing_helpful = []
        
        # 필수 정보 확인
        for info in essential_info:
            if not self._has_info(current_info, info):
                missing_essential.append(info)
        
        # 유용한 정보 확인
        for info in helpful_info:
            if not self._has_info(current_info, info):
                missing_helpful.append(info)
        
        # 우선순위 순으로 정렬
        all_missing = missing_essential + missing_helpful
        all_missing.sort(key=lambda x: self.INFO_PRIORITY.get(x, 0), reverse=True)
        
        return {
            "essential": missing_essential,
            "helpful": missing_helpful,
            "by_priority": all_missing
        }
    
    def generate_smart_question(self, missing_info_type, context):
        """맥락 기반 스마트 질문 생성"""
        questions = {
            "location": [
                "어느 지역에서 찾고 계신가요? (예: 홍대, 강남, 이태원)",
                "어디서 만나실 예정이신가요?"
            ],
            "concept": [
                "어떤 분위기를 원하시나요? (로맨틱/캐주얼/활기찬)",
                # "분위기 있는 곳을 찾으시나요, 아니면 편안한 곳을 원하시나요?"
            ],
            "age": [
                # "20대 핫플레이스를 찾고 계신가요, 아니면 좀 더 차분한 곳을 원하시나요?",
                "연령대를 알려주시면 더 맞는 곳을 추천드릴 수 있어요!"
            ],
            "relationship": [
                "연인분이신가요, 아니면 친구/지인과 가시는 건가요?",
                "어떤 분과 함께 가시는 건가요?"
            ],
            "budget": [
                "예산은 어느 정도로 생각하고 계신가요?",
                # "가격대가 어느 정도까지 괜찮으신가요?"
            ]
        }
        
        question_list = questions.get(missing_info_type, ["추가 정보를 알려주세요."])
        return question_list[0]  # 첫 번째 질문 반환
    
    def generate_recommendation_with_options(self, current_info):
        """추천과 함께 선택권 제공"""
        return {
            "type": "recommendation_with_options",
            "message": """🎯 현재 정보로 추천드릴 수 있어요!

💡 선택해주세요:
• "추천해줘" - 지금 바로 추천받기
• "더 자세히" - 맞춤 정보 추가 후 추천받기  
• "특별 요청" - 특별한 조건이나 요청사항 말씀해주세요

어떻게 하시겠어요?""",
            "options": ["추천해줘", "더 자세히", "특별 요청"]
        }
    
    def generate_optional_details_offer(self, current_info):
        """기본 추가 정보 수집 (인원수 제외, 커플 기준)"""
        state = current_info.get("state", {})
        special_context = state.get("special_context", "")
        
        # 기본 추가 정보 질문 (인원수 제외)
        questions = []
        
        # 기념일/특별한 날 고려
        if "생일" in special_context or "주년" in special_context or "기념일" in special_context:
            questions.extend([
                "💰 예산: (특별한 날이니 '비싸도 괜찮아요' 또는 구체적 금액)",
                "🕐 선호 시간대: (예시: 오후, 저녁, 밤)",
                "🚇 교통수단: (예시: 대중교통, 자차, 도보)",
                "🎉 특별 요청: (예시: 프라이빗한 곳, 인스타 감성, 야경 좋은 곳, 서프라이즈 가능한 곳)"
            ])
        else:
            questions.extend([
                "💰 예산: (예시: 3-5만원, 저렴하게, 비싸도 괜찮아요)",
                "🕐 선호 시간대: (예시: 오후, 저녁, 밤)", 
                "🚇 교통수단: (예시: 대중교통, 자차, 도보)",
                "🎉 특별 요청: (예시: 기념일, 주차 가능, 반려동물 동반, 실내만, 야외만, 프라이빗한 곳, 인스타 감성, 야경 좋은 곳 등)"
            ])
        
        questions_text = "\n• ".join(questions)
        return {
            "type": "optional_details",
            "message": f"""더 맞춤 추천을 원하시면 아래와 같은 정보를 자유롭게 입력해 주세요!

• {questions_text}

입력 예시: 예산은 5만원, 저녁에 대중교통으로 이동, 조용하고 프라이빗한 곳이면 좋아요
(건너뛰려면 '이대로 추천해줘'라고 입력하세요.)""",
            "can_skip": True
        }

def personalize_categories(base_categories, user_profile, user_message=None):
    prompt_text = (
        f"사용자 프로필: MBTI={user_profile.mbti}, 나이={user_profile.age}, 관계={user_profile.relationship_stage}\n"
        f"기본 카테고리: {base_categories}\n"
        f"사용자 요청: {user_message}\n"
        "위 정보를 참고해서, 이 사용자가 선호할 만한 데이트 카테고리 3~5개를 아래 리스트 중에서 골라 한글 리스트로 추천해줘.\n"
        f"카테고리 후보: {CATEGORY_LIST}\n"
        "리스트만 반환."
    )
    print("[LLM 프롬프트 - 개인화 카테고리]\n", prompt_text)
    try:
        result = simple_llm_call(prompt_text)
        if result:
            import ast
            categories = ast.literal_eval(result) if result.startswith('[') else [result.strip()]
            # base_categories와 LLM 결과를 적절히 조합(중복 제거, 우선순위 등)
            final = []
            for c in categories + base_categories:
                if c in CATEGORY_LIST and c not in final:
                    final.append(c)
                if len(final) >= 5:
                    break
            print(f"[LLM 추출 결과 - 개인화 카테고리] {final}")
            return final
    except Exception as e:
        print(f"[LLM 파싱 에러 - 개인화 카테고리] {e}")
    
    # 실패 시 기존 방식 fallback
    adjusted = list(base_categories)
    # 기존 rule-based fallback (간단화)
    seen = set()
    result = []
    for c in adjusted:
        if c not in seen:
            result.append(c)
            seen.add(c)
        if len(result) >= 5:
            break
    return result

# --- SubAgentCoordinator 샘플 ---
class AgentClient:
    def __init__(self, base_url):
        self.base_url = base_url
    
    async def request(self, endpoint, data):
        # 실제 구현에서는 httpx, aiohttp 등으로 비동기 요청
        await asyncio.sleep(0.1)  # 테스트용 딜레이
        return {"result": f"{self.base_url}{endpoint} 응답 (테스트)"}

async def call_place_agent(location_analysis, user_profile, user_message):
    """Place Agent에게 자연스러운 요청을 보내는 함수"""
    
    # 요청 타입에 따라 다른 JSON 구조 생성
    request_type = location_analysis["location_type"]
    request_id = f"req-{uuid.uuid4()}"
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    base_request = {
        "request_id": request_id,
        "timestamp": timestamp,
        "request_type": request_type,
        "original_message": user_message  # 사용자 원문 보존
    }
    
    if request_type == "exact_locations":
        # 명확한 장소 → 최소 정보만 전달
        place_request = {
            **base_request,
            "areas": [
                {
                    "sequence": i + 1,
                    "area_name": place
                } for i, place in enumerate(location_analysis["extracted_places"])
            ]
        }
    
    else:
        # 애매한 위치나 관계 기반 → 풍부한 맥락 전달
        place_request = {
            **base_request,
            "location_request": {
                "user_intent": location_analysis["user_intent"],
                "spatial_context": location_analysis["spatial_context"],
                "extracted_places": location_analysis["extracted_places"],
                "place_count": 3,  # 기본값
                "clarity_level": location_analysis["location_clarity"]
            },
            "user_context": {
                "demographics": {
                    "age": user_profile.age,
                    "mbti": user_profile.mbti, 
                    "relationship_stage": user_profile.relationship_stage
                },
                "preferences": user_profile.preferences or extract_natural_preferences(user_message),
                "requirements": {
                    "budget_level": user_profile.budget_level,
                    "time_preference": user_profile.time_preference,
                    "transportation": user_profile.transportation,
                    "max_travel_time": user_profile.max_travel_time,
                    "atmosphere_preference": user_profile.atmosphere_preference
                }
            },
            "conversation_context": {
                "tone": analyze_conversation_tone(user_message),
                "urgency": analyze_urgency(user_message),
                "specificity": location_analysis["location_clarity"]
            }
        }
    
    print(f"\n📍 [Place Agent 요청]\n{json.dumps(place_request, ensure_ascii=False, indent=2)}")
    
    # 실제 Place Agent 호출 (현재는 모의 응답)
    try:
        # await place_agent_client.request("/analyze-location", place_request)
        # 모의 응답
        mock_response = generate_mock_place_response(place_request)
        print(f"\n📍 [Place Agent 응답]\n{json.dumps(mock_response, ensure_ascii=False, indent=2)}")
        return mock_response
    except Exception as e:
        print(f"[Place Agent 에러] {e}")
        return {
            "request_id": request_id,
            "success": False,
            "error": "Place Agent 통신 실패",
            "fallback_locations": [
                {
                    "sequence": 1,
                    "area_name": "강남구",
                    "coordinates": {"latitude": 37.4979, "longitude": 127.0276}
                }
            ]
        }

def extract_natural_preferences(user_message):
    """사용자 메시지에서 자연스러운 선호사항 추출"""
    prompt = (
        f"다음 사용자 메시지에서 데이트 장소에 대한 선호사항을 자연스러운 표현으로 추출해줘.\n"
        f"키워드가 아닌 사용자가 실제로 표현한 감정이나 분위기를 그대로 보존해서.\n\n"
        f"메시지: {user_message}\n\n"
        f"예시: ['분위기 있는 곳이었으면 좋겠어', '너무 시끄럽지 않은 곳', '인스타에 올릴만한 예쁜 곳']\n"
        f"리스트 형태로만 반환해줘."
    )
    
    try:
        result = simple_llm_call(prompt)
        if result and result.startswith('['):
            import ast
            return ast.literal_eval(result)
    except:
        pass
    
    return ["좋은 분위기의 장소"]

def extract_contextual_needs(user_message, user_profile):
    """사용자 메시지와 프로필에서 맥락적 필요사항 추출"""  
    prompt = (
        f"사용자 메시지와 프로필을 보고 데이트에서 중요하게 고려해야 할 맥락적 요구사항을 추출해줘.\n\n"
        f"메시지: {user_message}\n"
        f"프로필: 나이 {user_profile.age}, MBTI {user_profile.mbti}, 관계 {user_profile.relationship_stage}\n\n"
        f"딕셔너리 형태로 반환:\n"
        f"예시: {{'budget_consideration': '대학생 수준 예산', 'time_context': '여유롭게 즐길 수 있는', 'privacy_level': '사람들 시선 부담스럽지 않은'}}\n"
    )
    
    try:
        result = simple_llm_call(prompt)
        if result and '{' in result:
            import ast
            match = re.search(r'\{.*\}', result, re.DOTALL)
            if match:
                return ast.literal_eval(match.group())
    except:
        pass
    
    return {
        "budget_consideration": "적당한 예산 수준",
        "time_context": "편안하게 즐길 수 있는",
        "social_context": f"{user_profile.relationship_stage} 단계에 적합한"
    }

def analyze_conversation_tone(user_message):
    """대화 톤 분석"""
    if any(word in user_message for word in ['급해', '빨리', '오늘', '지금']):
        return "urgent"
    elif any(word in user_message for word in ['좋겠어', '하고 싶어', '가볼까']):
        return "casual"
    elif any(word in user_message for word in ['추천해주세요', '도움을', '부탁']):
        return "formal"
    else:
        return "friendly"

def analyze_urgency(user_message):
    """긴급도 분석"""
    urgent_words = ['급해', '빨리', '오늘', '지금 당장', '내일']
    return "high" if any(word in user_message for word in urgent_words) else "normal"

def generate_mock_place_response(request):
    """Place Agent 모의 응답 생성"""
    return {
        "request_id": request["request_id"],
        "success": True,
        "locations": [
            {
                "sequence": 1,
                "area_name": "홍대입구역",
                "coordinates": {
                    "latitude": 37.5565,
                    "longitude": 126.9240
                },
                "selection_reason": "사용자의 '분위기 있는 곳' 요청에 적합한 젊고 활기찬 지역"
            },
            {
                "sequence": 2, 
                "area_name": "이태원역",
                "coordinates": {
                    "latitude": 37.5344,
                    "longitude": 126.9947
                },
                "selection_reason": "다양한 문화가 어우러진 특별한 데이트 경험 가능"
            },
            {
                "sequence": 3,
                "area_name": "강남역",
                "coordinates": {
                    "latitude": 37.4979,
                    "longitude": 127.0276
                },
                "selection_reason": "세련되고 트렌디한 분위기의 데이트 명소"
            }
        ],
        "analysis_summary": {
            "user_intent_understood": request.get("location_request", {}).get("user_intent", ""),
            "personalization_applied": True,
            "location_diversity": "서울 내 다양한 특색 지역으로 구성"
        }
    }

class SubAgentCoordinator:
    def __init__(self):
        self.agent_clients = {
            "place": AgentClient("http://place-agent:8001"),
            "weather": AgentClient("http://weather-agent:8002"),
            "context": AgentClient("http://context-agent:8003")
        }
        # 캐시된 기본 추천 데이터
        self.cached_recommendations = {
            "강남구": [{"name": "강남 추천 장소", "reason": "인기 있는 장소입니다"}],
            "마포구": [{"name": "홍대 추천 장소", "reason": "젊은 분위기의 장소입니다"}],
            "용산구": [{"name": "이태원 추천 장소", "reason": "다양한 문화가 있는 장소입니다"}]
        }
    
    def get_cached_recommendations(self, location=None):
        """캐시된 기본 추천 반환"""
        if location and location in self.cached_recommendations:
            return self.cached_recommendations[location]
        return [{"name": "기본 추천 장소", "reason": "안전한 선택입니다"}]
    
    def handle_sub_agent_failures(self, results):
        """Sub Agent 실패 시 대안 처리"""
        fallback_message = ""
        
        # Place Agent 실패 시
        if isinstance(results["place_recommendations"], Exception):
            results["place_recommendations"] = self.get_cached_recommendations()
            fallback_message += "기본 추천을 제공합니다. "
            print(f"[에러 처리] Place Agent 실패: {results['place_recommendations']}")
        
        # Weather Agent 실패 시  
        if isinstance(results["weather_considerations"], Exception):
            results["weather_considerations"] = "날씨를 확인하시고 방문해주세요."
            print(f"[에러 처리] Weather Agent 실패: {results['weather_considerations']}")
        
        # Context Agent 실패 시
        if isinstance(results["context_info"], Exception):
            results["context_info"] = "영업시간을 미리 확인해주세요."
            print(f"[에러 처리] Context Agent 실패: {results['context_info']}")
        
        if fallback_message:
            results["fallback_message"] = fallback_message
        
        return results
    
    async def coordinate_sub_agents(self, user_request, selected_categories):
        start_time = time.time()
        
        place_request = {
            "location": user_request.location,
            "categories": selected_categories,
            "user_profile": vars(user_request.user_profile),
            "budget": user_request.budget,
            "time": user_request.time
        }
        weather_request = {
            "location": user_request.location,
            "date": user_request.date,
            "time": user_request.time
        }
        context_request = {
            "location": user_request.location,
            "categories": selected_categories
        }
        
        # 타임아웃 설정으로 병렬 요청 실행
        try:
            tasks = [
                self.agent_clients["place"].request("/recommend", place_request),
                self.agent_clients["weather"].request("/analyze", weather_request),
                self.agent_clients["context"].request("/enrich", context_request)
            ]
            place_result, weather_result, context_result = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=1.5  # 1.5초 타임아웃
            )
        except asyncio.TimeoutError:
            print("[에러 처리] Sub Agent 호출 타임아웃")
            place_result = Exception("Timeout")
            weather_result = Exception("Timeout")
            context_result = Exception("Timeout")
        
        results = {
            "place_recommendations": place_result,
            "weather_considerations": weather_result,
            "context_info": context_result
        }
        
        # 에러 처리 적용
        results = self.handle_sub_agent_failures(results)
        
        elapsed_time = time.time() - start_time
        print(f"[성능] Sub Agent 조율 시간: {elapsed_time:.2f}초")
        
        return results

# --- ResponseIntegrator 샘플 ---
class ResponseIntegrator:
    def validate_response_quality(self, response):
        """응답 품질 검증"""
        quality_checks = {
            "has_recommendations": len(response.get("main_recommendations", "")) > 10,
            "has_explanation": len(response.get("greeting", "")) > 10,
            "has_practical_info": len(response.get("practical_info", "")) > 5,
            "appropriate_length": 50 <= len(response.get("full_text", "")) <= 500
        }
        
        quality_score = sum(quality_checks.values()) / len(quality_checks)
        print(f"[품질 검증] 점수: {quality_score:.2f}, 세부: {quality_checks}")
        
        return quality_score >= 0.7  # 70% 이상이면 통과
    
    def generate_fallback_response(self, user_request):
        """품질 검증 실패 시 대안 응답"""
        location = user_request.location or "해당 지역"
        return {
            "greeting": f"{location}에서의 데이트 코스를 추천드립니다.",
            "main_recommendations": "죄송합니다. 현재 시스템 점검 중입니다. 잠시 후 다시 시도해주세요.",
            "weather_advice": "날씨를 확인하고 방문하세요.",
            "practical_info": "영업시간을 미리 확인해주세요.",
            "call_to_action": "더 궁금한 점이 있으면 언제든 말씀해주세요!"
        }
    
    def integrate_sub_agent_results(self, user_request, sub_agent_results):
        recommendations = sub_agent_results["place_recommendations"]
        weather_info = sub_agent_results["weather_considerations"]
        context_info = sub_agent_results["context_info"]
        
        integrated_response = {
            "greeting": self.generate_personalized_greeting(user_request),
            "main_recommendations": self.format_recommendations(recommendations),
            "weather_advice": self.format_weather_advice(weather_info),
            "practical_info": self.format_practical_info(context_info),
            "call_to_action": self.generate_call_to_action()
        }
        
        # 품질 검증
        final_response = self.format_natural_response(integrated_response)
        integrated_response["full_text"] = final_response
        
        if not self.validate_response_quality(integrated_response):
            print("[품질 검증] 실패 - 대안 응답 생성")
            fallback = self.generate_fallback_response(user_request)
            return self.format_natural_response(fallback)
        
        # fallback 메시지가 있으면 추가
        if "fallback_message" in sub_agent_results:
            final_response = f"⚠️ {sub_agent_results['fallback_message']}\n\n{final_response}"
        
        return final_response
    
    def generate_personalized_greeting(self, user_request):
        location = user_request.location or "어딘가"
        concept = user_request.concept or "특별한"
        age_group = "20대" if user_request.user_profile and user_request.user_profile.age <= 25 else "30대"
        return f"{location}에서 {concept}한 데이트를 원하시는 {age_group} 커플분을 위한 특별한 코스를 준비했어요!"
    
    def format_recommendations(self, recommendations):
        if not recommendations or len(recommendations) == 0:
            return "죄송합니다. 현재 조건에 맞는 장소를 찾을 수 없어요. 다른 조건으로 다시 시도해볼까요?"
        
        if isinstance(recommendations, list):
            formatted = []
            for i, place in enumerate(recommendations[:3], 1):
                if isinstance(place, dict):
                    name = place.get('name', '장소명 없음')
                    reason = place.get('reason', '추천 이유 없음')
                    formatted.append(f"{i}. {name} - {reason}")
                else:
                    formatted.append(f"{i}. {str(place)}")
            return "\n".join(formatted)
        
        return str(recommendations)
    
    def format_weather_advice(self, weather_info):
        return str(weather_info)
    
    def format_practical_info(self, context_info):
        return str(context_info)
    
    def generate_call_to_action(self):
        return "더 궁금한 점이 있으면 언제든 말씀해주세요!"
    
    def format_natural_response(self, integrated_response):
        return (f"{integrated_response['greeting']}\n\n"
                f"🎯 추천 장소:\n{integrated_response['main_recommendations']}\n\n"
                f"🌤️ 날씨 참고: {integrated_response['weather_advice']}\n"
                f"📋 실용 정보: {integrated_response['practical_info']}\n\n"
                f"{integrated_response['call_to_action']}")

# --- 단순화된 LLM 설정 ---
load_dotenv()  # .env에서 환경변수 로드
llm = OpenAI(temperature=0.3, openai_api_key=os.environ['OPENAI_API_KEY'], model="gpt-4o-mini")

def is_valid_korean(text):
    """텍스트에 한글이 정상적으로 포함되어 있는지 검사"""
    import re
    # 한글 음절(가-힣) 또는 자모(ㄱ-ㅎ, ㅏ-ㅣ) 포함 여부
    return bool(re.search(r'[가-힣ㄱ-ㅎㅏ-ㅣ]', text))

def fix_common_korean_typos(text):
    """자주 발생하는 한글 오타/깨짐을 교정 (예: 조요안→조용한)"""
    typo_map = {
        '조요안': '조용한',
        '서울': '서울숲',
        '분위기여쓰면': '분위기였으면',
        # 필요시 추가
    }
    for wrong, right in typo_map.items():
        text = text.replace(wrong, right)
    return text

def simple_llm_call(prompt_text):
    """단순한 LLM 호출 함수 (속도 최우선, 재시도/오타교정 없음)"""
    try:
        if isinstance(prompt_text, bytes):
            prompt_text = prompt_text.decode('utf-8')
        response = llm.invoke(prompt_text)
        if hasattr(response, 'content'):
            content = response.content
        elif isinstance(response, str):
            content = response
        else:
            content = str(response)
        if isinstance(content, bytes):
            content = content.decode('utf-8', errors='replace')
        elif not isinstance(content, str):
            content = str(content)
        print(f"[LLM 응답 검증] 길이: {len(content)}, 한글포함: {'한글' in content or any(ord(c) > 127 for c in content)}")
        # 한글 정합성 체크 제거: 깨진 단어가 있더라도 응답을 그대로 반환
        return content
    except Exception as e:
        print(f"[LLM 호출 에러] {e}")
        return None

def extract_concept_info(user_message):
    """사용자 메시지에서 데이트 컨셉 추출 - 개선된 버전"""
    
    # 먼저 규칙 기반으로 명확한 키워드 체크
    romantic_keywords = ['로맨틱', '로맨틱한', '분위기', '분위기 있는', '조용한', '조용한 분위기', '차분한', '감성적', '낭만적', '예쁜', '인스타', '아늑한', '은은한']
    active_keywords = ['액티브', '활동적', '체험', '운동', '게임', '놀이', '재미있는', '신나는']
    casual_keywords = ['캐주얼', '편안한', '자연스러운', '일상적', '간단한']
    
    romantic_count = sum(1 for keyword in romantic_keywords if keyword in user_message)
    active_count = sum(1 for keyword in active_keywords if keyword in user_message)
    casual_count = sum(1 for keyword in casual_keywords if keyword in user_message)
    
    # 규칙 기반 판단
    if romantic_count > 0 and romantic_count >= active_count and romantic_count >= casual_count:
        concept_guess = "로맨틱"
    elif active_count > 0 and active_count > romantic_count and active_count >= casual_count:
        concept_guess = "액티브"
    else:
        concept_guess = "캐주얼"
    
    prompt = (
        "아래 사용자 메시지에서 데이트 컨셉을 분석해서\n"
        "['로맨틱', '캐주얼', '액티브'] 중 가장 적합한 것 1개를 반환해줘.\n\n"
        f"메시지: {user_message}\n"
        f"키워드 분석 결과: {concept_guess}\n\n"
        "판단 기준:\n"
        "- 로맨틱: 분위기, 조용한 분위기, 로맨틱한, 예쁜, 감성적, 낭만적, 아늑한, 차분한 등의 표현\n"
        "- 액티브: 활동적, 체험, 운동, 게임, 재미있는, 신나는 등의 표현\n"
        "- 캐주얼: 편안한, 자연스러운, 일상적이거나 특별한 키워드 없음\n\n"
        "단어 하나만 반환 (예: 로맨틱)"
    )
    
    try:
        result = simple_llm_call(prompt)
        if result:
            concept = result.strip()
            if concept in ["로맨틱", "캐주얼", "액티브"]:
                print(f"[LLM 추출 결과 - 컨셉] {concept} (규칙기반: {concept_guess})")
                return concept
    except Exception as e:
        print(f"[LLM 파싱 에러 - 컨셉] {e}")
    
    # LLM 실패 시 규칙 기반 결과 사용
    print(f"[규칙 기반 컨셉 결과] {concept_guess}")
    return concept_guess

def extract_comprehensive_requirements(user_message):
    """사용자 메시지에서 종합적인 요구사항 추출"""
    prompt = (
        "아래 사용자 메시지에서 데이트 관련 요구사항을 추출해서 JSON으로 반환해줘:\n"
        "{\n"
        '  "budget_info": "예산 관련 정보 (예: 5만원, 저렴하게, 비싸도 괜찮아)",\n'
        '  "time_info": "시간 관련 정보 (예: 저녁, 오후, 하루종일, 2-3시간)",\n'
        '  "transportation": "교통수단 (예: 지하철, 버스, 도보, 자차, 택시)",\n'
        '  "party_size": "인원수 (예: 2명, 둘이서, 커플)",\n'
        '  "duration": "예상 소요시간 (예: 2시간, 반나절, 하루종일)",\n'
        '  "special_needs": "특별 요구사항 (예: 주차가능, 실내전용, 반려동물동반)"\n'
        "}\n\n"
        f"메시지: {user_message}\n\n"
        "정보가 없으면 null 사용. JSON만 반환."
    )
    
    try:
        result = simple_llm_call(prompt)
        if result:
            match = re.search(r'\{.*\}', result, re.DOTALL)
            if match:
                info = json.loads(match.group())
                print(f"[종합 요구사항 추출] {info}")
                return info
    except Exception as e:
        print(f"[종합 요구사항 추출 에러] {e}")
    
    return {
        "budget_info": None,
        "time_info": None, 
        "transportation": None,
        "party_size": None,
        "duration": None,
        "special_needs": None
    }

def extract_budget_time_info(user_message):
    """사용자 메시지에서 예산/시간 정보 추출 - 호환성 유지"""
    comprehensive = extract_comprehensive_requirements(user_message)
    return {
        "budget": comprehensive.get("budget_info"),
        "time": comprehensive.get("time_info")
    }

def analyze_location_intent(user_message):
    """사용자의 위치 의도를 자연스럽게 분석 - LLM 중심 버전 (프롬프트 개선, location_request 구조 고정)"""
    # 1. 단순한 공간 관계 키워드 감지 (정규표현식 최소화)
    spatial_keywords = {
        "between": ["사이", "중간", "중간지점"],
        "nearby": ["근처", "주변", "인근", "쪽", "동네", "지역", "일대", "권", "가까운"]
    }
    # 2. 모호함 지시어 감지
    vague_indicators = ["어디든", "어느", "아무", "알아서", "적당히", "대충", "상관없어", "괜찮아", "어디가 좋을까", "어디 갈까"]
    conditional_indicators = ["이나", "또는", "아니면", "중에", "가운데"]
    # 3. 기본 공간 관계 감지
    detected_spatial_relationship = None
    for relationship, keywords in spatial_keywords.items():
        if any(keyword in user_message for keyword in keywords):
            detected_spatial_relationship = relationship
            break
    # 4. 모호함 레벨 판단
    vague_level = "clear"
    if any(indicator in user_message for indicator in vague_indicators):
        vague_level = "vague"
    elif any(indicator in user_message for indicator in conditional_indicators):
        vague_level = "conditional"
    # 5. 규칙 기반 지역 추출 먼저 시도 (속도 향상 및 정확도 개선)
    rule_based_places = []
    known_places = [
        "홍대", "홍익대", "강남", "강남역", "이태원", "명동", "건대", "신촌", "합정",
        "신논현", "한남동", "용산", "동대문", "종로", "연대", "서대문", "마포",
        "압구정", "청담", "잠실", "여의도", "영등포", "구로", "신림", "사당"
    ]
    
    for place in known_places:
        if place in user_message:
            rule_based_places.append(place)
    
    print(f"[지역 추출 디버깅] 입력: '{user_message}', 규칙기반 결과: {rule_based_places}")
    
    # 규칙 기반으로 찾았으면 LLM 호출 생략
    if rule_based_places:
        return {
            "extracted_places": rule_based_places,
            "location_request": {
                "proximity_type": "specific" if len(rule_based_places) == 1 else "general",
                "reference_areas": rule_based_places,
                "place_count": 3,
                "proximity_preference": "any"
            },
            "location_type": "area_recommendation",
            "location_clarity": "clear",
            "user_intent": user_message,
            "spatial_context": detected_spatial_relationship or "general",
            "place_agent_instruction": "",
            "needs_user_clarification": False
        }
    
    # 6. 규칙 기반으로 찾지 못한 경우만 LLM 사용
    try:
        # 프롬프트에 location_request 구조를 명확히 요구
        prompt = (
            "다음 사용자 메시지에서 데이트 장소로 활용할 수 있는 지역명, 역명, 동명, 구명 등을 모두 추출해서 'extracted_places' 리스트에 반드시 넣어줘.\n"
            "그리고 아래와 같은 location_request JSON 구조도 반드시 포함해서 반환해줘.\n"
            '{\n  "location_request": {\n    "proximity_type": "between|nearby|route|general|specific",\n    "reference_areas": ["장소1", "장소2", ...],\n    "place_count": 3,\n    "proximity_preference": "middle|close|any"\n  }\n}\n'
            "예시: '홍대와 강남 사이에서 데이트할 곳' → {\"extracted_places\": [\"홍대\", \"강남\"], \"location_request\": {\"proximity_type\": \"between\", \"reference_areas\": [\"홍대\", \"강남\"], \"place_count\": 3, \"proximity_preference\": \"middle\"}}\n"
            "장소명이 없으면 reference_areas는 빈 배열로, proximity_type은 general로, proximity_preference는 any로, place_count는 3으로 고정해줘.\n"
            "JSON만 반환. 예시: {\"extracted_places\": [\"강남\"], \"location_request\": { ... }}\n"
            f"메시지: {user_message}\n"
        )
        result = simple_llm_call(prompt)
        if result:
            # 한글 파싱 오류 방지를 위한 인코딩 처리
            if isinstance(result, bytes):
                result = result.decode('utf-8')
            elif not isinstance(result, str):
                result = str(result)
            
            # 유니코드 정규식으로 JSON 매칭
            match = re.search(r'\{.*\}', result, re.DOTALL | re.UNICODE)
            if match:
                json_str = match.group()
                # JSON 파싱 시 ensure_ascii=False로 한글 보존
                analysis = json.loads(json_str)
                # 필수 필드 보완
                required_fields = {
                    "location_type": "area_recommendation",
                    "location_clarity": "clear",
                    "extracted_places": [],
                    "user_intent": user_message,
                    "spatial_context": "general",
                    "place_agent_instruction": "",
                    "needs_user_clarification": False
                }
                for k, v in required_fields.items():
                    if k not in analysis:
                        analysis[k] = v
                # location_request 구조 보완
                loc_req = analysis.get("location_request", {})
                loc_req_required = {
                    "proximity_type": "general",
                    "reference_areas": analysis.get("extracted_places", []),
                    "place_count": 3,
                    "proximity_preference": "any"
                }
                for k, v in loc_req_required.items():
                    if k not in loc_req:
                        loc_req[k] = v
                analysis["location_request"] = loc_req
                # 기존 규칙 기반 힌트와 LLM 결과 융합
                extracted_places = analysis.get("extracted_places", [])
                if detected_spatial_relationship and analysis.get("spatial_context", "general") == "general":
                    analysis["spatial_context"] = detected_spatial_relationship
                if vague_level != "clear":
                    analysis["location_clarity"] = vague_level
                if detected_spatial_relationship and analysis.get("location_type", "") == "exact_locations":
                    route_keywords = ["갈 건데", "가는데", "까지", "에서", "거쳐서", "출발", "동안", "들를"]
                    if any(keyword in user_message for keyword in route_keywords):
                        analysis["location_type"] = "route_based"
                    else:
                        analysis["location_type"] = "proximity_based"
                pronoun_indicators = ["그", "이", "저", "거기", "여기"]
                if any(place in pronoun_indicators for place in extracted_places):
                    analysis["location_type"] = "needs_clarification"
                    analysis["needs_user_clarification"] = True
                elif not extracted_places or len(extracted_places) == 0:
                    analysis["location_type"] = "needs_clarification"
                    analysis["needs_user_clarification"] = True
                    analysis["extracted_places"] = []
                print(f"[LLM 중심 위치 의도 분석] {analysis}")
                return analysis
    except Exception as e:
        print(f"[위치 의도 분석 에러] {e}")
    # 7. LLM 실패 시 기본 규칙 기반 결과 (규칙 기반 결과 우선 사용)
    fallback_places = rule_based_places if rule_based_places else []
    print(f"[LLM 실패 시 기본값] 규칙기반: {rule_based_places}, 사용할 장소: {fallback_places}")
    
    return {
        "location_type": "needs_clarification" if not fallback_places else "area_recommendation",
        "location_clarity": vague_level,
        "extracted_places": fallback_places,
        "user_intent": user_message,
        "spatial_context": detected_spatial_relationship if detected_spatial_relationship else "general",
        "place_agent_instruction": "서울 내 사용자 프로필에 맞는 데이트 장소 추천" if not fallback_places else f"{', '.join(fallback_places)} 지역 데이트 장소 추천",
        "needs_user_clarification": len(fallback_places) == 0,
        "location_request": {
            "proximity_type": "general" if not fallback_places else ("specific" if len(fallback_places) == 1 else "general"),
            "reference_areas": fallback_places,
            "place_count": 3,
            "proximity_preference": "any"
        }
    }

def generate_place_instruction(detected_locations, spatial_relationship, vague_level):
    """Place Agent 지시사항 생성 함수"""
    if not detected_locations:
        return "서울 내 사용자 프로필에 맞는 데이트 장소 추천"
    
    location_str = ", ".join(detected_locations)
    
    if spatial_relationship == "between":
        return f"{location_str} 사이에서 접근성이 좋은 중간지점 3곳 추천"
    elif spatial_relationship == "nearby":
        return f"{location_str} 근처에서 도보/대중교통으로 접근 가능한 데이트 장소 추천"
    elif vague_level == "conditional":
        return f"{location_str} 지역에서 사용자 선호도에 맞는 데이트 장소 추천"
    elif vague_level == "clear":
        return f"{location_str} 지역의 구체적 데이트 장소 좌표 변환"
    else:
        return f"{location_str} 기준으로 개인화된 데이트 장소 추천"

def convert_place_to_district(place_name):
    """장소명을 행정구로 변환"""
    district_mapping = {
        "여의도": "영등포구",
        "강남": "강남구", "강남역": "강남구", "신논현": "강남구",
        "홍대": "마포구", "홍익대": "마포구", "합정": "마포구",
        "이태원": "용산구", "한남대": "용산구", "용산": "용산구",
        "명동": "중구", "동대문": "중구", "종로": "종로구",
        "건대": "광진구", "연대": "서대문구", "신촌": "강남구"
    }
    
    for keyword, district in district_mapping.items():
        if keyword in place_name:
            print(f"[장소 변환] {place_name} -> {district}")
            return district
    
    print(f"[장소 변환] {place_name} -> 강남구 (기본값)")
    return "강남구"  # 기본값

# --- 자연어 기반 사용자 정보 수집 및 파싱 ---
def extract_profile_fields_from_text(user_input, fields=None):
    """
    주어진 user_input에서 필수 정보만 LLM으로 추출 (age, relationship_stage, location, concept, budget, time_preference, atmosphere_preference)
    fields: 추출할 필드 리스트(기본값: 필수 정보)
    """
    if fields is None:
        fields = ['age', 'relationship_stage', 'location', 'concept', 'budget', 'time_preference', 'atmosphere_preference']
    field_kr = {
        'age': '나이',
        'relationship_stage': '관계',
        'location': '지역',
        'concept': '분위기/특성',
        'budget': '예산',
        'time_preference': '시간대',
        'atmosphere_preference': '장소 타입(실내/실외 등)'
    }
    # 분위기 예시 다양화
    prompt = (
        f"아래 사용자 답변에서 {', '.join([field_kr[f] for f in fields])} 정보를 추출해서 "
        '{' + ', '.join([f'"{f}": ...' for f in fields]) + '} 형태의 JSON으로 반환해줘.\n'
        "분위기(concept)는 아래 예시처럼 다양한 값을 그대로 추출해.\n"
        "예시: {'concept': '로맨틱'}\n"
        "예시: {'concept': '조용한'}\n"
        "예시: {'concept': '트렌디한'}\n"
        "예시: {'concept': '감성적'}\n"
        "예시: {'concept': '프라이빗'}\n"
        "예시: {'concept': '분위기 있는'}\n"
        "예시: {'concept': '힙한'}\n"
        "예시: {'concept': '모던'}\n"
        "예시: {'concept': '아늑한'}\n"
        "정보가 없으면 null로 반환. JSON만 반환.\n"
        f"답변: {user_input}\n"
    )
    try:
        result = simple_llm_call(prompt)
        if result:
            import json as _json
            import re
            match = re.search(r'\{.*\}', result, re.DOTALL)
            if match:
                info = _json.loads(match.group())
                # concept 값은 예시에 있는 값이면 그대로, 새로운 값이 오면 그대로 사용(별도 매핑X, fallbackX)
                return info
    except Exception as e:
        print(f"[프로필 파싱 에러] {e}")
    return {f: None for f in fields}

# ask_field 함수 제거됨 - Dynamic Chat에서는 사용하지 않음

# 정적 사용자 정보 수집 함수들 제거됨 - Dynamic Chat에서는 ChatMemoryManager 사용

def build_rag_agent_request(user_request, selected_categories):
    """RAG Agent 요청 구조 생성 (임시 구현)"""
    return {
        "user_context": user_request.user_profile.to_dict() if user_request.user_profile else {},
        "location_analysis": user_request.location,
        "categories": selected_categories,
        "timestamp": datetime.now().isoformat()
    }

# main_agent_flow 함수는 구 정적 방식 - Dynamic Chat에서는 사용하지 않음
# 향후 완전 삭제 예정
async def main_agent_flow_deprecated(user_message: str, user_profile: UserProfile):
    total_start_time = time.time()
    print("\n🧠 [Main Agent] 요청 분석 시작")
    # 1. 요청 분석 (Request Analyzer) - 새로운 위치 분석 적용
    start_time = time.time()
    # 위치 의도 분석 (개선된 버전)
    location_analysis = analyze_location_intent(user_message)
    # 재질문이 필요한 경우 처리
    if location_analysis.get("needs_user_clarification", False):
        print(f"\n🤔 원본 메시지: '{user_message}'")
        clarified_location = ask_location_clarification(user_message)
        # 재질문 결과로 location_analysis 업데이트
        location_analysis = {
            "location_type": "exact_locations",
            "location_clarity": "clear",
            "extracted_places": [clarified_location],
            "user_intent": f"{user_message} (위치: {clarified_location})",
            "spatial_context": "specific",
            "place_agent_instruction": f"{clarified_location} 지역의 구체적 데이트 장소 추천",
            "needs_user_clarification": False
        }
        print(f"✅ 위치 재질문 완료: {clarified_location}")
    # 기타 정보 추출
    concept_info = extract_concept_info(user_message)
    budget_time_info = extract_budget_time_info(user_message)
    print(f"[성능] Request Analyzer: {time.time() - start_time:.2f}초")
    # 2. 정보 수집 (Information Collector) - 자연어 기반 재질문 및 분위기/특성 질문
    start_time = time.time()
    # 프로필 정보 또는 컨셉이 부족하면 모두 필수로 수집
    if not user_profile.is_complete() or not concept_info or not concept_info.strip():
        user_profile, concept_info = await smart_collect_user_profile(user_profile, concept_info)
    print(f"[성능] Information Collector: {time.time() - start_time:.2f}초")
    # 3. 카테고리 선정 (Category Selector) - location_analysis 기반
    start_time = time.time()
    # 첫 번째 장소를 기준으로 카테고리 매핑 (향후 개선 가능)
    primary_location = location_analysis["extracted_places"][0] if location_analysis["extracted_places"] else "서울"
    district_location = convert_place_to_district(primary_location)
    
    base_categories = LOCATION_CATEGORY_MAPPING.get(district_location, {}).get(concept_info, [])
    if not base_categories:  # fallback
        base_categories = ["카페", "음식점", "문화시설"]
    selected_categories = personalize_categories(base_categories, user_profile, user_message)
    print(f"[성능] Category Selector: {time.time() - start_time:.2f}초")
    
    # UserRequest 객체 생성 (location_analysis 정보 포함)
    user_request = UserRequest(
        message=user_message,
        location=primary_location,  # location_analysis에서 추출된 장소
        concept=concept_info,
        user_profile=user_profile,
        budget=budget_time_info.get("budget"),
        time=budget_time_info.get("time"),
        date=datetime.now().strftime("%Y-%m-%d")
    )
    
    # 위치 분석 결과도 함께 출력
    print(f"\n📍 [위치 분석 결과]")
    print(f"- 위치 타입: {location_analysis['location_type']}")
    print(f"- 명확도: {location_analysis['location_clarity']}")
    print(f"- 추출 장소: {location_analysis['extracted_places']}")
    print(f"- 공간 맥락: {location_analysis['spatial_context']}")
    print(f"- Place Agent 지시: {location_analysis['place_agent_instruction']}")
    
    # RAG-Agent 요청 바디 생성
    rag_request_body = build_rag_agent_request(user_request, selected_categories)
    print("\n📋 [RAG-Agent 전달용 Request Body]")
    print(json.dumps(rag_request_body, ensure_ascii=False, indent=2))
    
    # 4. Sub Agent 조율 (병렬 호출) - 에러 처리 강화
    print("\n🤝 [Sub Agent 조율] 시작")
    sub_agent_coordinator = SubAgentCoordinator()
    sub_agent_results = await sub_agent_coordinator.coordinate_sub_agents(user_request, selected_categories)
    
    # 5. 응답 통합 - 품질 보장 시스템
    print("\n📝 [응답 통합] 시작")
    start_time = time.time()
    response_integrator = ResponseIntegrator()
    final_response = response_integrator.integrate_sub_agent_results(user_request, sub_agent_results)
    print(f"[성능] Response Integrator: {time.time() - start_time:.2f}초")
    
    total_elapsed = time.time() - total_start_time
    print(f"\n⏱️ [전체 성능] 총 소요시간: {total_elapsed:.2f}초 (목표: 2초)")
    
    if total_elapsed > 2.0:
        print("⚠️ 성능 목표 초과! 최적화 필요")
    else:
        print("✅ 성능 목표 달성!")
    
    return final_response

def ask_location_clarification(original_message, retry_count=0):
    """
    위치 정보가 불명확할 때 사용자에게 명확한 지역명을 재질문하는 함수
    최대 2회까지 재질문, 그래도 없으면 '서울'로 기본값 처리
    """
    print(f"\n📍 위치 정보가 명확하지 않습니다. (재질문 {retry_count + 1}회차)")
    print("어느 지역에서 데이트를 원하시나요?")
    print("1. 홍대 (젊고 힙한 분위기)")
    print("2. 강남 (세련되고 트렌디한 분위기)")  
    print("3. 이태원 (이색적이고 다양한 분위기)")
    print("4. 명동 (관광지 중심가)")
    print("5. 기타 (직접 입력)")
    
    choice = input("번호를 선택하거나 직접 입력해주세요: ")
    
    location_map = {
        "1": "홍대",
        "2": "강남", 
        "3": "이태원",
        "4": "명동"
    }
    
    if choice in location_map:
        selected_location = location_map[choice]
        print(f"✅ {selected_location}을(를) 선택하셨습니다.")
        return selected_location
    elif choice == "5" or not choice.isdigit():
        if choice == "5":
            custom_location = input("원하시는 지역을 입력해주세요: ")
        else:
            custom_location = choice
        
        if custom_location.strip():
            print(f"✅ {custom_location}을(를) 선택하셨습니다.")
            return custom_location.strip()
    # 재질문 최대 2회까지만
    if retry_count < 1:
        print("⚠️ 올바른 선택을 해주세요.")
        return ask_location_clarification(original_message, retry_count + 1)
    else:
        print("⚠️ 기본값으로 서울 전체를 대상으로 추천드리겠습니다.")
        return "서울"

def extract_profile_detail_from_text(user_input):
    """
    user_input에서 gender, address, car_owned, description만 LLM으로 추출 (profile_image_url 제외)
    """
    prompt = (
        "아래 사용자 답변에서 성별(gender), 거주지(address), 차량 소유 여부(car_owned), 자기소개(description) 정보를 추출해서 "
        '{"gender": ..., "address": ..., "car_owned": ..., "description": ...} 형태의 JSON으로 반환해줘.\n'
        "답변: " + user_input + "\n"
        "예시: {'gender': 'FEMALE', 'address': '강남구', 'car_owned': false, 'description': '카페 투어 좋아해요'}\n"
        "정보가 없으면 null로 반환. JSON만 반환."
    )
    try:
        result = simple_llm_call(prompt)
        if result:
            import json as _json
            match = re.search(r'\{.*\}', result, re.DOTALL)
            if match:
                info = _json.loads(match.group())
                # 불필요한 필드 제거, None/null만 남기지 않기
                return {k: v for k, v in info.items() if v is not None}
    except Exception as e:
        print(f"[profile_detail 파싱 에러] {e}")
    return {}

def extract_user_context_and_course_planning_from_text(user_input):
    """
    user_input에서 user_context, course_planning에 들어갈 수 있는 정보만 LLM으로 추출
    (age, mbti, relationship_stage, preferences, requirements, optimization_goals, special_needs, preferred_start_time, end_time 등)
    """
    prompt = (
        "아래 사용자 답변에서 데이트 추천에 필요한 정보를 추출해서 아래와 같은 JSON 구조로 반환해줘.\n"
        '{\n'
        '  "user_context": {\n'
        '    "demographics": {"age": ..., "mbti": ..., "relationship_stage": ...},\n'
        '    "preferences": [...],\n'
        '    "requirements": {\n'
        '      "budget_range": ..., "time_preference": ..., "party_size": ..., "transportation": ..., "special_needs": ...\n'
        '    }\n'
        '  },\n'
        '  "course_planning": {\n'
        '    "optimization_goals": [...],\n'
        '    "route_constraints": {\n'
        '      "max_travel_time_between": ..., "total_course_duration": ..., "flexibility": ..., "preferred_start_time": ..., "end_time": ...\n'
        '    }\n'
        '  }\n'
        '}\n'
        "답변: " + user_input + "\n"
        "예시: {\"user_context\": {\"demographics\": {\"age\": 25, \"mbti\": \"ENFP\", \"relationship_stage\": \"썸\"}, \"preferences\": [\"조용한 곳\", \"야외\"], \"requirements\": {\"budget_range\": \"3-6만원\", \"time_preference\": \"오후\", \"party_size\": 2, \"transportation\": \"대중교통\", \"special_needs\": \"주차 가능\"}}}, \"course_planning\": {\"optimization_goals\": [\"최소 이동\", \"최대 만족도\"], \"route_constraints\": {\"max_travel_time_between\": 30, \"total_course_duration\": 240, \"flexibility\": \"medium\", \"preferred_start_time\": \"14:00\", \"end_time\": \"20:00\"}}}"
        "정보가 없으면 null 또는 빈 배열로 반환. JSON만 반환."
    )
    try:
        result = simple_llm_call(prompt)
        if result:
            import json as _json
            match = re.search(r'\{.*\}', result, re.DOTALL)
            if match:
                info = _json.loads(match.group())
                return info
    except Exception as e:
        print(f"[user_context/course_planning 파싱 에러] {e}")
    return {}

def build_user_detail_json(user_profile, profile_detail, general_preferences=None):
    """
    DB 저장용 사용자 정보 JSON(profile_detail)
    general_preferences: 사용자의 일반 선호사항(리스트, 선택)
    """
    return {
        "gender": profile_detail.get("gender"),
        "age": user_profile.age,
        "mbti": user_profile.mbti,
        "address": profile_detail.get("address"),
        "car_owned": profile_detail.get("car_owned"),
        "description": profile_detail.get("description"),
        "relationship_stage": user_profile.relationship_stage,
        "general_preferences": general_preferences or []
    }

def build_course_request_json(user_profile, concept_info, user_context, course_planning):
    """
    코스 추천 요청용 JSON (매번 달라질 수 있는 정보)
    """
    return {
        "demographics": {
            "age": user_profile.age,
            "mbti": user_profile.mbti,
            "relationship_stage": user_profile.relationship_stage
        },
        "concept": concept_info,
        "preferences": user_context.get("preferences", []),
        "requirements": user_context.get("requirements", {}),
        "optimization_goals": course_planning.get("optimization_goals", []),
        "route_constraints": course_planning.get("route_constraints", {}),
        "sequence_optimization": course_planning.get("sequence_optimization", {})
    }

# === 구 정적 방식 함수들 (사용하지 않음) ===
# Dynamic Chat에서는 ChatMemoryManager와 interactive_dynamic_chat 사용
# 이 함수들은 향후 완전 삭제 예정

async def chat_collect_user_profile_with_detail_deprecated():
    CYAN = '\033[96m'
    YELLOW = '\033[93m'
    GREEN = '\033[92m'
    RED = '\033[91m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

    user_profile = UserProfile()
    concept_info = None
    while not user_profile.is_complete() or not concept_info or not concept_info.strip():
        print(f"{YELLOW}💡 아래 정보 중 입력 가능한 것을 자유롭게 말씀해 주세요!{RESET}")
        print(f"{YELLOW}예시: {BOLD}'27세 ENFP이고, 썸 단계입니다. 분위기는 조용한 곳이 좋아요.'{RESET}")
        print(f"{YELLOW}예시: {BOLD}'나이는 25, MBTI는 ISFJ, 연인이고 로맨틱한 분위기 원해요.'{RESET}")
        print(f"{YELLOW}예시: {BOLD}'ENFP, 24세, 썸, 트렌디한 곳'{RESET}")
        print(f"{YELLOW}예시: {BOLD}'나이 30, MBTI는 INFP, 관계는 장기연애, 분위기 좋은 곳'{RESET}")
        print(f"{CYAN}────────────────────────────────────{RESET}\n")
        user_profile, concept_info = await smart_collect_user_profile(user_profile, concept_info)
        print(f"\n{CYAN}👤 [현재 프로필] 나이: {user_profile.age}, MBTI: {user_profile.mbti}, 관계: {user_profile.relationship_stage}{RESET}")
        print(f"{CYAN}🎨 [현재 컨셉] {concept_info}{RESET}")
        if user_profile.is_complete() and concept_info and concept_info.strip():
            print(f"\n{GREEN}{BOLD}✅ 모든 정보가 정상적으로 수집되었습니다!{RESET}")
            break
        else:
            print(f"\n{RED}{BOLD}⚠️ 아직 정보가 부족합니다. 다시 입력해 주세요.{RESET}")
    print(f"\n{YELLOW}📝 더 자세한 프로필(성별, 거주지, 차량 소유, 자기소개 등)을 입력하시겠어요?{RESET}")
    print(f"{YELLOW}예시: {BOLD}'여자, 강남구, 차 없음, 카페 투어 좋아해요'{RESET}")
    print(f"{CYAN}건너뛰려면 Enter만 눌러주세요.{RESET}")
    detail_input = input(f"{CYAN}입력: {RESET}").strip()
    profile_detail = {}
    if detail_input:
        profile_detail = extract_profile_detail_from_text(detail_input)
        print(f"{GREEN}🟢 [profile_detail] {profile_detail}{RESET}")
    else:
        print(f"{RED}🔴 [profile_detail] 입력 없음 (건너뜀){RESET}")
    print(f"\n{YELLOW}💡 더 자세한 조건(선호사항, 예산, 시간, 인원, 교통, 특수 요구, 최적화 목표, 시작/종료 시간 등)을 입력하시겠어요?{RESET}")
    print(f"{YELLOW}예시: {BOLD}'야외, 조용한 곳, 3-6만원, 오후, 2명, 대중교통, 주차 가능, 이동 최소화, 오후 2시 시작, 저녁 8시 종료'{RESET}")
    print(f"{CYAN}건너뛰려면 Enter만 눌러주세요.{RESET}")
    detail_input2 = input(f"{CYAN}입력: {RESET}").strip()
    user_context = {}
    course_planning = {}
    if detail_input2:
        info = extract_user_context_and_course_planning_from_text(detail_input2)
        user_context = info.get('user_context', {})
        course_planning = info.get('course_planning', {})
        print(f"{GREEN}🟢 [user_context] {user_context}{RESET}")
        print(f"{GREEN}🟢 [course_planning] {course_planning}{RESET}")
    else:
        print(f"{RED}🔴 [user_context/course_planning] 입력 없음 (건너뜀){RESET}")
    general_preferences = user_context.get("preferences", [])
    user_detail = build_user_detail_json(user_profile, profile_detail, general_preferences)
    course_request = build_course_request_json(user_profile, concept_info, user_context, course_planning)
    print(f"\n{CYAN}{BOLD}=== DB 저장용 user_detail (profile_detail) ==={RESET}")
    import json as _json
    print(f"{CYAN}" + _json.dumps(user_detail, ensure_ascii=False, indent=2) + f"{RESET}")
    print(f"\n{CYAN}{BOLD}=== 코스 추천 요청용 course_request ==={RESET}")
    print(f"{CYAN}" + _json.dumps(course_request, ensure_ascii=False, indent=2) + f"{RESET}")
    return user_detail, course_request

def show_user_profile_summary(user_detail):
    # ANSI 컬러 코드
    CYAN = '\033[96m'
    YELLOW = '\033[93m'
    GREEN = '\033[92m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    print(f"{CYAN}{BOLD}\n┌───────────────────────────────┐")
    print("│      👤 현재 등록된 프로필      │")
    print(f"└───────────────────────────────┘{RESET}")
    print(f"{YELLOW}나이         : {user_detail.get('age', '미입력')}")
    print(f"성별         : {user_detail.get('gender', '미입력')}")
    print(f"MBTI         : {user_detail.get('mbti', '미입력')}")
    print(f"관계         : {user_detail.get('relationship_stage', '미입력')}")
    print(f"거주지       : {user_detail.get('address', '미입력')}")
    print(f"차량         : {user_detail.get('car_owned', '미입력')}")
    print(f"자기소개     : {user_detail.get('description', '미입력')}")
    print(f"일반 선호    : {', '.join(user_detail.get('general_preferences', [])) or '없음'}{RESET}")
    print(f"{GREEN}────────────────────────────────────{RESET}")
    print(f"{BOLD}정보가 다르다면 [프로필 페이지]에서 수정해 주세요!")
    print("여기서 바로 수정하려면 '수정'을 입력해 주세요.")
    cmd = input("계속 진행하려면 Enter, 수정하려면 '수정': ").strip()
    return cmd

async def chat_collect_with_existing_user_detail(user_detail):
    CYAN = '\033[96m'
    YELLOW = '\033[93m'
    GREEN = '\033[92m'
    RED = '\033[91m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

    cmd = show_user_profile_summary(user_detail)
    if cmd == '수정':
        print(f"\n{YELLOW}{BOLD}수정할 수 있는 항목: 나이, 성별, MBTI, 관계, 거주지, 차량, 자기소개, 일반 선호 등{RESET}")
        print(f"{YELLOW}예시: {BOLD}'29세, 남자, INFP, 썸, 마포구, 차 있음, 영화 좋아함, 선호: 조용한 곳, 야외'{RESET}")
        print(f"{CYAN}여러 항목을 한 번에 입력해도 됩니다!{RESET}")
        detail_input = input(f"{CYAN}수정할 내용 입력: {RESET}").strip()
        if detail_input:
            profile_detail = extract_profile_detail_from_text(detail_input)
            user_detail.update(profile_detail)
            print(f"{GREEN}🟢 [수정된 profile_detail] {profile_detail}{RESET}")
        else:
            print(f"{RED}🔴 [profile_detail] 입력 없음 (건너뜀){RESET}")
    # 바로 코스 요청사항 입력 단계로 진행
    print(f"\n{YELLOW}💡 더 자세한 조건(선호사항, 예산, 시간, 인원, 교통, 특수 요구, 최적화 목표, 시작/종료 시간 등)을 입력하시겠어요?{RESET}")
    print(f"{YELLOW}예시: {BOLD}'야외, 조용한 곳, 3-6만원, 오후, 2명, 대중교통, 주차 가능, 이동 최소화, 오후 2시 시작, 저녁 8시 종료'{RESET}")
    print(f"{CYAN}건너뛰려면 Enter만 눌러주세요.{RESET}")
    detail_input2 = input(f"{CYAN}입력: {RESET}").strip()
    user_context = {}
    course_planning = {}
    if detail_input2:
        info = extract_user_context_and_course_planning_from_text(detail_input2)
        user_context = info.get('user_context', {})
        course_planning = info.get('course_planning', {})
        print(f"{GREEN}🟢 [user_context] {user_context}{RESET}")
        print(f"{GREEN}🟢 [course_planning] {course_planning}{RESET}")
    else:
        print(f"{RED}🔴 [user_context/course_planning] 입력 없음 (건너뜀){RESET}")
    # 일반 선호사항 추출(있으면)
    general_preferences = user_context.get("preferences", [])
    # DB 저장용 user_detail (기존 정보 + 추가 입력 반영)
    merged_user_detail = user_detail.copy()
    if general_preferences:
        merged_user_detail["general_preferences"] = general_preferences
    # 코스 요청용 course_request
    class DummyUserProfile:
        def __init__(self, d):
            self.age = d.get("age")
            self.mbti = d.get("mbti")
            self.relationship_stage = d.get("relationship_stage")
    user_profile = DummyUserProfile(merged_user_detail)
    concept_info = None  # 기존 정보에 컨셉이 있으면 반영 가능
    course_request = build_course_request_json(user_profile, concept_info, user_context, course_planning)
    print(f"\n{CYAN}{BOLD}=== DB 저장용 user_detail (profile_detail) ==={RESET}")
    import json as _json
    print(f"{CYAN}" + _json.dumps(merged_user_detail, ensure_ascii=False, indent=2) + f"{RESET}")
    print(f"\n{CYAN}{BOLD}=== 코스 추천 요청용 course_request ==={RESET}")
    print(f"{CYAN}" + _json.dumps(course_request, ensure_ascii=False, indent=2) + f"{RESET}")
    return merged_user_detail, course_request

# --- 테스트 실행 샘플 ---
# === 구 테스트 시스템 (비활성화) ===
# Dynamic Chat을 위해 비활성화됨
def old_test_system():
    import asyncio
    import datetime
    import sys

    # 로그 저장 폴더 생성
    TEST_LOG_DIR = "test_logs"
    os.makedirs(TEST_LOG_DIR, exist_ok=True)

    # 장소 관련 테스트 케이스
    place_test_scenarios = [
        {
            "name": "프로필 정보 모두 있음",
            "profile": UserProfile(mbti="ENFP", age=25, relationship_stage="썸"),
            "message": "서울에서 분위기 있는 데이트 코스 추천해줘"
        },
        {
            "name": "구체적 장소 지정",
            "profile": UserProfile(mbti="ISFJ", age=27, relationship_stage="연인"),
            "message": "홍대, 이태원, 강남에서 로맨틱한 저녁 데이트 코스"
        },
        {
            "name": "중간지점 요청",
            "profile": UserProfile(mbti="ESTP", age=23, relationship_stage="썸"),
            "message": "홍대와 강남 사이에서 만나서 데이트하기 좋은 곳 3곳 추천"
        },
        {
            "name": "근처 지역 요청",
            "profile": UserProfile(mbti="INFP", age=24, relationship_stage="연인"),
            "message": "이태원 근처에서 조용하고 분위기 좋은 카페 추천해줘"
        },
        {
            "name": "명확한 로맨틱 컨셉",
            "profile": UserProfile(mbti="ISFJ", age=26, relationship_stage="연인"),
            "message": "강남에서 로맨틱하고 인스타에 올릴만한 예쁜 레스토랑 추천"
        },
        {
            "name": "유연한 표현 - 쪽에서",
            "profile": UserProfile(mbti="ENFP", age=24, relationship_stage="썸"),
            "message": "홍대 쪽에서 분위기 좋은 카페 추천해줘"
        },
        {
            "name": "유연한 표현 - 동네에서",
            "profile": UserProfile(mbti="ISFP", age=25, relationship_stage="연인"),
            "message": "그 동네에서 조용한 곳 찾고 있어"
        },
        {
            "name": "애매한 선택 표현",
            "profile": UserProfile(mbti="INTJ", age=28, relationship_stage="연인"),
            "message": "홍대나 이태원 중에서 어디든 괜찮아"
        },
        {
            "name": "매우 애매한 표현",
            "profile": UserProfile(mbti="ESFP", age=22, relationship_stage="썸"),
            "message": "서울에서 어디가 좋을까? 알아서 추천해줘"
        },
        {
            "name": "경로 기반 - 사이 이동",
            "profile": UserProfile(mbti="ISFJ", age=26, relationship_stage="연인"),
            "message": "홍대와 강남을 갈 건데 중간에 데이트 장소 추천해줘"
        },
        {
            "name": "경로 기반 - 여기서 여기까지",
            "profile": UserProfile(mbti="ENTJ", age=29, relationship_stage="연인"),
            "message": "명동에서 이태원까지 가는데 중간에 들를 만한 곳 있어?"
        },
        {
            "name": "경로 기반 - 복잡한 경로",
            "profile": UserProfile(mbti="INFP", age=24, relationship_stage="썸"),
            "message": "건대에서 출발해서 홍대 거쳐서 강남 가는 동안 데이트할 곳들 추천해줘"
        },
        {
            "name": "이동 중 들를 곳",
            "profile": UserProfile(mbti="ESTP", age=23, relationship_stage="썸"),
            "message": "신촌과 여의도 사이 어디든 들러서 커피 마실 곳 있을까?"
        }
    ]

    # 사용자 정보 관련 테스트 케이스
    userinfo_test_scenarios = [
        {
            "name": "MBTI 없음",
            "profile": UserProfile(mbti=None, age=25, relationship_stage="연인"),
            "message": "강남에서 분위기 좋은 데이트 코스 추천해줘"
        },
        {
            "name": "나이 없음",
            "profile": UserProfile(mbti="ENFP", age=None, relationship_stage="썸"),
            "message": "이태원에서 조용한 카페 추천해줘"
        },
        {
            "name": "관계 없음",
            "profile": UserProfile(mbti="ISFJ", age=27, relationship_stage=None),
            "message": "홍대에서 트렌디한 데이트 코스 추천해줘"
        },
        {
            "name": "모두 없음",
            "profile": UserProfile(mbti=None, age=None, relationship_stage=None),
            "message": "분위기 좋은 곳에서 데이트하고 싶어"
        },
        {
            "name": "컨셉 없음",
            "profile": UserProfile(mbti="ENFP", age=25, relationship_stage="썸"),
            "message": "서울에서 데이트할만한 곳 추천해줘"
        },
        {
            "name": "모두 있음",
            "profile": UserProfile(mbti="ENFP", age=25, relationship_stage="썸"),
            "message": "서울에서 분위기 좋은 카페 추천해줘"
        }
    ]

    print("\n=== 테스트 종류를 선택하세요 ===")
    print("1. 장소 관련 테스트 케이스")
    print("2. 사용자 정보 관련 테스트 케이스")
    print("3. 대화형 사용자 정보 수집 테스트 (챗봇 모드)")
    print("4. [4] 기존 유저 데이터 기반 챗봇형 정보 수집 테스트")
    test_type = input("번호를 입력하세요 (1/2/3/4): ").strip()

    if test_type == "3":
        print("\n=== 대화형 사용자 정보 수집 테스트 ===\n")
        print("아래 예시처럼 자연스럽게 입력해보세요!")
        print("예시: '저는 27살 ENFP이고, 썸 단계입니다. 분위기는 조용한 곳이 좋아요.'")
        print("예시: '나이는 25, MBTI는 ISFJ, 연인이고 로맨틱한 분위기 원해요.'")
        print("예시: 'ENFP, 24세, 썸, 트렌디한 곳'")
        print("예시: '나이 30, MBTI는 INFP, 관계는 장기연애, 분위기 좋은 곳'")
        print("---\n")
        # 대화형 프로필+상세정보+user_context 수집 및 JSON 출력
        print("❌ 구 정적 방식은 더 이상 지원하지 않습니다.")
        print("✅ 새로운 Dynamic Chat을 사용해주세요:")
        print("   python main_agent.py           - 동적 채팅 테스트")
        print("   python main_agent.py interactive - 실제 대화 모드")
        sys.exit(0)

    if test_type == "2":
        scenarios = userinfo_test_scenarios
        test_type_name = "userinfo"
    elif test_type == "4":
        print("\n=== [4] 기존 유저 데이터 기반 챗봇형 정보 수집 테스트 ===\n")
        # 예시 user_detail (DB에서 불러온 것처럼)
        user_detail = {
            "age": 28,
            "mbti": "ENFP",
            "relationship_stage": "연인",
            "address": "강남구",
            "car_owned": "없음",
            "description": "카페 투어 좋아해요",
            "general_preferences": ["조용한 곳", "야외"]
        }
        print("❌ 구 정적 방식은 더 이상 지원하지 않습니다.")
        print("✅ 새로운 Dynamic Chat을 사용해주세요:")
        sys.exit(0)
    else:
        scenarios = place_test_scenarios
        test_type_name = "place"

    print(f"\n=== {test_type_name.upper()} 테스트 케이스 실행 ===\n")

    for i, scenario in enumerate(scenarios, 1):
        print(f"{'='*50}")
        print(f"테스트 {i}: {scenario['name']}")
        print(f"메시지: {scenario['message']}")
        print(f"프로필: {scenario['profile'].age}세, {scenario['profile'].mbti}, {scenario['profile'].relationship_stage}")
        print(f"{'='*50}")
        # 로그 파일명
        log_filename = os.path.join(TEST_LOG_DIR, f"{test_type_name}_test_{i}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        with open(log_filename, "w", encoding="utf-8") as log_file:
            # 로그에 시나리오 정보 저장
            log_file.write(f"테스트명: {scenario['name']}\n")
            log_file.write(f"메시지: {scenario['message']}\n")
            log_file.write(f"프로필: {scenario['profile'].age}세, {scenario['profile'].mbti}, {scenario['profile'].relationship_stage}\n")
            log_file.write(f"실행시간: {datetime.datetime.now().isoformat()}\n")
            log_file.write(f"결과 로그:\n")
            # 표준 출력 로그를 파일에도 같이 저장
            import sys, json as _json
            class Tee:
                def __init__(self, *files):
                    self.files = files
                def write(self, obj):
                    for f in self.files:
                        f.write(obj)
                        f.flush()
                def flush(self):
                    for f in self.files:
                        f.flush()
            old_stdout = sys.stdout
            sys.stdout = Tee(sys.stdout, log_file)
            try:
                # 각 분석 함수들 개별 테스트
                print("\n1. 위치 의도 분석:")
                location_analysis = analyze_location_intent(scenario['message'])
                print(f"- 위치 타입: {location_analysis['location_type']}")
                print(f"- 명확도: {location_analysis['location_clarity']}")
                print(f"- 추출 장소: {location_analysis['extracted_places']}")
                print(f"- 공간 맥락: {location_analysis['spatial_context']}")
                print(f"- Place Agent 지시: {location_analysis['place_agent_instruction']}")
                log_file.write("\n[location_analysis JSON]\n")
                log_file.write(_json.dumps(location_analysis, ensure_ascii=False, indent=2) + "\n")

                print("\n2. 컨셉 추출:")
                concept = extract_concept_info(scenario['message'])
                print(f"추출된 컨셉: {concept}")
                log_file.write(f"\n[concept_info RAW]\n{concept}\n")

                print("\n3. 예산/시간 정보:")
                budget_time = extract_budget_time_info(scenario['message'])
                print(f"예산: {budget_time.get('budget')}, 시간: {budget_time.get('time')}")
                log_file.write("\n[budget_time_info JSON]\n")
                log_file.write(_json.dumps(budget_time, ensure_ascii=False, indent=2) + "\n")

                print("\n4. 자연스러운 선호사항:")
                preferences = extract_natural_preferences(scenario['message'])
                print(f"선호사항: {preferences}")
                log_file.write(f"\n[preferences RAW]\n{preferences}\n")

                print("\n5. 맥락적 필요사항:")
                contextual_needs = extract_contextual_needs(scenario['message'], scenario['profile'])
                print(f"맥락적 필요사항: {contextual_needs}")
                log_file.write("\n[contextual_needs JSON]\n")
                log_file.write(_json.dumps(contextual_needs, ensure_ascii=False, indent=2) + "\n")

                print("\n6. 대화 톤 & 긴급도:")
                tone = analyze_conversation_tone(scenario['message'])
                urgency = analyze_urgency(scenario['message'])
                print(f"톤: {tone}, 긴급도: {urgency}")
                log_file.write(f"\n[tone/urgency RAW]\n톤: {tone}, 긴급도: {urgency}\n")
            finally:
                sys.stdout = old_stdout
            # 테스트 요약/구현 현황/예시 user_context 등도 파일에 추가
            log_file.write("\n⏺ 📋 현재까지 구현 완료된 내용 요약\n\n")
            log_file.write("  🎯 위치 의도 분석 시스템 (완료)\n\n")
            log_file.write("  1. 지원하는 위치 타입들\n\n")
            log_file.write("  - ✅ exact_locations: '홍대, 이태원, 강남에서'\n")
            log_file.write("  - ✅ area_recommendation: '서울에서', '어디든 괜찮아'\n")
            log_file.write("  - ✅ proximity_based: '홍대와 강남 사이', '이태원 근처'\n")
            log_file.write("  - ✅ route_based: 'A에서 B까지', 'A 거쳐서 B', '중간에 들를'\n")
            log_file.write("  - ✅ needs_clarification: '그 동네에서', '어디가 좋을까?'\n\n")
            log_file.write("  2. 지원하는 공간 맥락들\n\n")
            log_file.write("  - ✅ between: A와 B 사이\n")
            log_file.write("  - ✅ nearby: A 근처/주변/쪽/동네\n")
            log_file.write("  - ✅ route: A에서 B로 가는 경로\n")
            log_file.write("  - ✅ stopover: 경로 중간에 들를 곳\n")
            log_file.write("  - ✅ multi_point: 여러 지점 거치는 복잡한 경로\n")
            log_file.write("  - ✅ general: 일반적 지역 내\n")
            log_file.write("  - ✅ specific: 특정 장소 지정\n\n")
            log_file.write("  3. 재질문 시스템\n\n")
            log_file.write("  - ✅ 대명사('그', '이', '저') 감지 시 재질문\n")
            log_file.write("  - ✅ 장소명 누락 시 재질문\n")
            log_file.write("  - ✅ 최대 2회 재질문 후 기본값('서울') 적용\n\n")
            log_file.write("  🎭 컨셉 추출 시스템 (완료)\n\n")
            log_file.write("  - ✅ 규칙 기반 + LLM 융합: 키워드 분석과 LLM 정확성 결합\n")
            log_file.write("  - ✅ 로맨틱/캐주얼/액티브 정확 분류\n")
            log_file.write("  - ✅ '분위기 있는', '로맨틱한', '인스타' 등 키워드 정확 감지\n\n")
            log_file.write("  📊 테스트된 시나리오들\n\n")
            log_file.write("  - ✅ 기본 지역 요청: '서울에서 분위기 있는'\n")
            log_file.write("  - ✅ 구체적 장소: '홍대, 이태원, 강남에서'\n")
            log_file.write("  - ✅ 중간지점: '홍대와 강남 사이에서'\n")
            log_file.write("  - ✅ 근처 지역: '이태원 근처에서'\n")
            log_file.write("  - ✅ 유연한 표현: '홍대 쪽에서', '그 동네에서'\n")
            log_file.write("  - ✅ 애매한 선택: '홍대나 이태원 중에서 어디든'\n")
            log_file.write("  - ✅ 경로 기반: '홍대와 강남을 갈 건데', '명동에서 이태원까지'\n")
            log_file.write("  - ✅ 복잡한 경로: '건대→홍대→강남 가는 동안'\n\n")
            log_file.write("  🔧 핵심 개선사항\n\n")
            log_file.write("  1. 키워드 의존성 최소화: 정규표현식 대신 LLM 중심 처리\n")
            log_file.write("  2. '사이' 패턴 파싱 문제 해결: '홍대와 강남 사이' → ['홍대', '강남'] 정확 추출\n")
            log_file.write("  3. 경로 기반 요청 지원: A→B 이동, 중간 경유지 등 복합 시나리오\n\n")

# --- 동적 채팅봇 시스템 ---

class ChatMemoryManager:
    """LangChain 기반 대화 메모리 관리"""
    
    def __init__(self):
        self.sessions = {}  # session_id: {"memory": ConversationBufferMemory, "user_profile": UserProfile, "state": dict}
        self.max_sessions = 50  # 최대 세션 수 제한
        self.adaptive_reask = AdaptiveReaskManager()  # 적응형 재질문 관리자
        print("ChatMemoryManager 초기화 완료")
    
    def get_or_create_session(self, session_id: str = None) -> str:
        """세션 가져오기 또는 생성"""
        if session_id is None:
            session_id = f"session_{uuid.uuid4().hex[:8]}"
        
        if session_id not in self.sessions:
            # 세션 수 제한 체크
            if len(self.sessions) >= self.max_sessions:
                # 가장 오래된 세션 삭제
                oldest_session = min(self.sessions.keys(), 
                                   key=lambda x: self.sessions[x]["created_at"])
                del self.sessions[oldest_session]
                print(f"세션 용량 초과로 {oldest_session} 삭제")
            
            # 새 세션 생성
            self.sessions[session_id] = {
                "memory": ConversationBufferMemory(
                    memory_key="chat_history",
                    return_messages=True
                ),
                "user_profile": UserProfile(),
                "state": {
                    "current_step": "greeting",  # greeting -> gathering -> ready -> recommending
                    "question_count": 0,
                    "forced_questions_count": 0,  # 강제 질문 횟수
                    "total_questions_count": 0,   # 총 질문 횟수
                    "last_question_field": None,
                    "user_engagement": "high",  # high/medium/low
                    "location": None,  # 위치 정보 별도 저장
                    "concept": None,   # 컨셉 정보 저장
                    "question_type": "general",  # 질문 유형
                    "completion_score": 0.0      # 완성도 점수
                },
                "created_at": datetime.now()
            }
            print(f"새 세션 생성: {session_id}")
        
        return session_id
    
    def add_message(self, session_id: str, role: str, content: str):
        """메시지 추가 및 정보 추출"""
        if session_id not in self.sessions:
            session_id = self.get_or_create_session(session_id)
        
        session = self.sessions[session_id]
        
        # 메모리에 메시지 추가
        if role == "user":
            session["memory"].chat_memory.add_user_message(content)
            # 사용자 메시지에서 정보 추출
            self._extract_and_update_info(session_id, content)
        else:
            session["memory"].chat_memory.add_ai_message(content)
    
    def _extract_and_update_info(self, session_id: str, user_message: str):
        """사용자 메시지에서 정보 추출 및 프로필 업데이트"""
        session = self.sessions[session_id]
        
        try:
            # 필수 정보만 추출
            fields = ['age', 'relationship_stage', 'location', 'concept', 'budget', 'time_preference', 'atmosphere_preference']
            extracted_info = extract_profile_fields_from_text(user_message, fields)
            
            # 지역 분석 수행 및 저장 (지역 정보가 없을 때만)
            current_location_analysis = session["state"].get("location_analysis", {})
            if not current_location_analysis.get("extracted_places"):
                location_analysis = analyze_location_intent(user_message)
                # 새로 추출된 지역이 있으면 저장
                if location_analysis.get("extracted_places"):
                    session["state"]["location_analysis"] = location_analysis
                    print(f"[지역 정보 저장] {location_analysis['extracted_places']}")
                else:
                    # 빈 결과면 기존 것 유지
                    location_analysis = current_location_analysis
            else:
                # 이미 지역 정보가 있으면 기존 것 사용
                location_analysis = current_location_analysis
                print(f"[기존 지역 정보 사용] {location_analysis.get('extracted_places', [])}")
            
            # 필수 정보 업데이트
            if extracted_info.get('age'):
                session["user_profile"].age = extracted_info['age']
            if extracted_info.get('relationship_stage'):
                session["user_profile"].relationship_stage = extracted_info['relationship_stage']
            if extracted_info.get('location') or location_analysis.get('extracted_places'):
                # 지역 분석 결과 우선 사용
                if location_analysis.get('extracted_places'):
                    session["state"]["location"] = location_analysis['extracted_places'][0]
                else:
                    session["state"]["location"] = extracted_info['location']
            if extracted_info.get('concept'):
                session["state"]["concept"] = extracted_info['concept']
            if extracted_info.get('budget'):
                session["user_profile"].budget_level = extracted_info['budget']
            if extracted_info.get('time_preference'):
                session["user_profile"].time_preference = extracted_info['time_preference']
            if extracted_info.get('atmosphere_preference'):
                session["user_profile"].atmosphere_preference = extracted_info['atmosphere_preference']
            print(f"정보 추출 완료 - 완성도: {session['user_profile'].get_completion_score():.2f}")
        except Exception as e:
            print(f"정보 추출 중 오류: {e}")
    
    def get_session_context(self, session_id: str) -> dict:
        """세션 컨텍스트 반환"""
        if session_id not in self.sessions:
            return {}
        
        session = self.sessions[session_id]
        chat_history = session["memory"].chat_memory.messages
        
        return {
            "session_id": session_id,
            "user_profile": session["user_profile"],
            "state": session["state"],
            "chat_history": chat_history[-10:],  # 최근 10개 메시지
            "conversation_length": len(chat_history),
            "completion_score": session["user_profile"].get_completion_score()
        }
    
    def get_current_info(self, session_id: str) -> dict:
        """현재 세션의 정보 상태 반환"""
        if session_id not in self.sessions:
            return {}
        
        session = self.sessions[session_id]
        return {
            "user_profile": session["user_profile"],
            "location": session["state"].get("location"),
            "concept": session["state"].get("concept"),
            "budget": session["user_profile"].budget_level,
            "time_preference": session["user_profile"].time_preference,
            "atmosphere_preference": session["user_profile"].atmosphere_preference,
            "location_analysis": session["state"].get("location_analysis", {}),  # 지역 분석 결과 추가
            "state": session["state"]
        }
    
    def update_completion_score(self, session_id: str, user_input: str):
        """완성도 점수 업데이트 (특별 맥락 포함)"""
        if session_id not in self.sessions:
            return
        
        session = self.sessions[session_id]
        
        # 특별 맥락 정보 추출 및 저장
        special_context = self.adaptive_reask.extract_special_context(user_input)
        if special_context:
            existing_context = session["state"].get("special_context", "")
            new_context = " ".join(special_context)
            session["state"]["special_context"] = f"{existing_context} {new_context}".strip()
            print(f"🎊 [특별 맥락 추출] {special_context}")
        
        current_info = self.get_current_info(session_id)
        
        # 질문 유형 분석 및 저장
        question_type = self.adaptive_reask.analyze_question_complexity(user_input)
        session["state"]["question_type"] = question_type
        
        # 완성도 점수 계산 및 저장
        completion_score = self.adaptive_reask.calculate_weighted_completion(current_info, question_type)
        session["state"]["completion_score"] = completion_score
    
    def get_smart_next_action(self, session_id: str, user_input: str) -> dict:
        """스마트 다음 행동 결정"""
        if session_id not in self.sessions:
            return {"action": "create_session"}
        
        current_info = self.get_current_info(session_id)
        session = self.sessions[session_id]
        
        # 완성도 업데이트
        self.update_completion_score(session_id, user_input)
        
        # 다음 행동 결정
        next_action = self.adaptive_reask.get_next_action(
            user_input=user_input,
            current_info=current_info,
            forced_questions_count=session["state"]["forced_questions_count"],
            total_questions_count=session["state"]["total_questions_count"]
        )
        
        return {
            "action": next_action,
            "completion_score": session["state"]["completion_score"],
            "question_type": session["state"]["question_type"]
        }
    
    def generate_smart_question(self, session_id: str, user_input: str) -> dict:
        """스마트 질문 생성 (AdaptiveReaskManager 사용)"""
        if session_id not in self.sessions:
            return {"error": "session_not_found"}
        
        current_info = self.get_current_info(session_id)
        session = self.sessions[session_id]
        question_type = session["state"]["question_type"]
        
        # AdaptiveReaskManager의 우선순위 기반 질문 생성 사용
        missing_info = self.adaptive_reask.get_missing_info_by_priority(current_info, question_type)
        
        if missing_info["by_priority"]:
            # 가장 우선순위 높은 누락 정보에 대한 질문
            highest_priority = missing_info["by_priority"][0]
            question = self.adaptive_reask.generate_smart_question(highest_priority, current_info)
            
            # 강제 질문 카운트 증가
            session["state"]["forced_questions_count"] += 1
            session["state"]["total_questions_count"] += 1
            session["state"]["last_question_field"] = highest_priority
            
            return {
                "type": "forced_question",
                "question": question,
                "missing_field": highest_priority,
                "is_essential": highest_priority in missing_info["essential"]
            }
        else:
            # 모든 정보가 있으면 추천 진행
            return {"type": "ready_to_recommend"}
    
    def generate_recommendation_options(self, session_id: str) -> dict:
        """추천 옵션 생성 (스마트 맥락별 질문 사용)"""
        if session_id not in self.sessions:
            return {"error": "session_not_found"}
        
        current_info = self.get_current_info(session_id)
        session = self.sessions[session_id]
        
        # AdaptiveReaskManager의 스마트 질문 시스템 사용
        if session["state"]["completion_score"] >= self.adaptive_reask.THRESHOLDS["optimal"]:
            return self.adaptive_reask.generate_recommendation_with_options(current_info)
        else:
            return self.adaptive_reask.generate_optional_details_offer(current_info)
    
    def is_ready_for_recommendation(self, session_id: str) -> bool:
        """추천 가능 여부 체크 (개선된 버전)"""
        if session_id not in self.sessions:
            return False
        
        session = self.sessions[session_id]
        missing = self.get_missing_critical_info(session_id)
        return len(missing) == 0
    
    def get_missing_critical_info(self, session_id: str) -> list:
        """부족한 핵심 정보 반환 (하위 호환성용)"""
        if session_id not in self.sessions:
            return ["session_not_found"]
        
        current_info = self.get_current_info(session_id)
        missing = []
        if not current_info.get("location"):
            missing.append("location")
        if not current_info["user_profile"].age:
            missing.append("age")
        if not current_info["user_profile"].relationship_stage:
            missing.append("relationship_stage")
        if not current_info.get("concept"):
            missing.append("concept")
        if not current_info.get("budget"):
            missing.append("budget")
        if not current_info.get("time_preference"):
            missing.append("time_preference")
        if not current_info.get("atmosphere_preference"):
            missing.append("atmosphere_preference")
        return missing
    
    def handle_additional_info_input(self, session_id: str, user_input: str) -> dict:
        """추가 정보 입력 처리 및 후속 질문 생성"""
        if session_id not in self.sessions:
            return {"error": "session_not_found"}
        
        session = self.sessions[session_id]
        
        # 추가 정보 파싱
        additional_info = self.adaptive_reask.parse_additional_info(user_input)
        
        # 파싱된 정보를 user_profile에 저장
        user_profile = session["user_profile"]
        if additional_info["budget"]:
            user_profile.budget_level = additional_info["budget"]
        if additional_info["time_preference"]:
            user_profile.time_preference = additional_info["time_preference"]
        if additional_info["transportation"]:
            user_profile.transportation = additional_info["transportation"]
        if additional_info["special_requests"]:
            # 특별 요청은 preferences에 추가
            if not user_profile.preferences:
                user_profile.preferences = []
            user_profile.preferences.append(additional_info["special_requests"])
        
        # 추가 정보 완성도 체크
        completeness = self.adaptive_reask.check_additional_info_completeness(additional_info)
        
        # 후속 질문 생성
        followup = self.adaptive_reask.generate_followup_additional_question(completeness)
        
        # 상태 업데이트
        session["state"]["additional_info_provided"] = additional_info
        session["state"]["additional_completion_ratio"] = completeness["completion_ratio"]
        
        return followup
    
    def clear_session(self, session_id: str):
        """세션 삭제"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            print(f"세션 {session_id} 삭제됨")

# 새로운 스마트 재질문 시스템 테스트 함수
async def test_smart_reask_system():
    """스마트 재질문 시스템 테스트"""
    print("🤖 스마트 재질문 시스템 테스트 시작")
    print("=" * 60)
    
    # 메모리 매니저 생성
    memory_manager = ChatMemoryManager()
    
    # 테스트 시나리오들
    test_scenarios = [
        "홍대에서 카페 추천해줘",
        "데이트 장소 추천해줘",
        "할거리 추천해줘",
        "서울에서 분위기 있는 곳 추천해줘"
    ]
    
    for i, user_input in enumerate(test_scenarios, 1):
        print(f"\n🧪 시나리오 {i}: '{user_input}'")
        print("-" * 40)
        
        # 새 세션 생성
        session_id = f"test_session_{i}"
        memory_manager.get_or_create_session(session_id)
        
        # 스마트 분석 수행
        next_action = memory_manager.get_smart_next_action(session_id, user_input)
        print(f"📊 완성도 점수: {next_action['completion_score']:.2f}")
        print(f"🏷️ 질문 유형: {next_action['question_type']}")
        print(f"🎯 다음 행동: {next_action['action']}")
        
        # 행동에 따른 응답 생성
        if next_action['action'] == 'ask_highest_priority_missing':
            question_result = memory_manager.generate_smart_question(session_id, user_input)
            print(f"❓ 질문: {question_result['question']}")
            print(f"📝 누락 필드: {question_result['missing_field']}")
            print(f"⚠️ 필수 여부: {question_result['is_essential']}")
        elif next_action['action'] == 'offer_recommendation_with_options':
            options = memory_manager.generate_recommendation_options(session_id)
            print(f"💡 메시지: {options['message']}")
        elif next_action['action'] == 'offer_recommendation_with_optional_details':
            options = memory_manager.generate_recommendation_options(session_id)
            print(f"📋 메시지: {options['message']}")
            print(f"⏭️ 건너뛸 수 있음: {options['can_skip']}")
        else:
            print("✅ 추천 진행 준비 완료")
        
        print()

async def smart_chat_system():
    """스마트 재질문이 통합된 채팅 시스템"""
    print("🤖 DayToCourse 스마트 채팅봇 시작!")
    print("=" * 50)
    print("💬 메시지를 입력하세요 (종료: 'quit', 'exit')")
    print("🔄 세션 초기화: 'clear' 또는 'reset'")
    print("📊 세션 정보: 'info' 또는 'status'")
    print("-" * 50)
    
    # 메모리 매니저 생성
    memory_manager = ChatMemoryManager()
    session_id = memory_manager.get_or_create_session()
    print(f"세션 ID: {session_id}")
    
    # 첫 인사
    greeting = "안녕하세요! 완벽한 데이트 코스를 찾아드릴게요 😊 어떤 데이트를 원하시나요?"
    memory_manager.add_message(session_id, "assistant", greeting)
    print(f"\n🤖 AI: {greeting}")
    
    while True:
        try:
            # 사용자 입력
            user_input = input(f"\n👤 당신: ").strip()
            
            # 종료 명령어
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n👋 채팅을 종료합니다. 즐거운 데이트 되세요!")
                break
            
            # 빈 입력
            if not user_input:
                continue
            
            # 특수 명령어 처리
            if user_input.lower() in ['clear', 'reset']:
                memory_manager.clear_session(session_id)
                session_id = memory_manager.get_or_create_session()
                print("🗑️ 세션이 초기화되었습니다.")
                greeting = "안녕하세요! 완벽한 데이트 코스를 찾아드릴게요 😊 어떤 데이트를 원하시나요?"
                memory_manager.add_message(session_id, "assistant", greeting)
                print(f"\n🤖 AI: {greeting}")
                continue
            
            if user_input.lower() in ['info', 'status']:
                context = memory_manager.get_session_context(session_id)
                current_info = memory_manager.get_current_info(session_id)
                print(f"\n📊 세션 정보:")
                print(f"  - 완성도 점수: {context['completion_score']:.2f}")
                print(f"  - 질문 유형: {current_info['state'].get('question_type', 'general')}")
                print(f"  - 강제 질문 수: {current_info['state'].get('forced_questions_count', 0)}")
                print(f"  - 총 질문 수: {current_info['state'].get('total_questions_count', 0)}")
                continue
            
            # 메시지 추가 및 분석
            memory_manager.add_message(session_id, "user", user_input)
            
            # 건너뛰기 요청 확인 (우선 체크)
            skip_keywords = ["이대로", "추천해줘", "바로 추천", "지금 추천", "괜찮아요"]
            is_skip_request = any(keyword in user_input for keyword in skip_keywords)
            
            # 추천 요청 시 JSON 저장 처리
            if is_skip_request:
                # 추천 요청과 함께 JSON 저장
                current_info = memory_manager.get_current_info(session_id)
                context = memory_manager.get_session_context(session_id)
                state = context["state"]
                
                # 요청 타입 추정
                request_type = state.get("location_type", "area_recommendation")
                
                # None 값 필터링
                def clean_dict(d):
                    if isinstance(d, dict):
                        return {k: clean_dict(v) for k, v in d.items() if v is not None and v != []}
                    elif isinstance(d, list):
                        return [clean_dict(x) for x in d if x is not None]
                    else:
                        return d
                
                current_info_clean = clean_dict(current_info)
                place_json = build_place_agent_json(request_type, current_info_clean)
                
                # JSON 파일 저장
                import json
                filename = "place_agent_request_from_chat.json"
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(place_json, f, ensure_ascii=False, indent=2)
                
                print(f"\n💾 [Place Agent JSON이 저장되었습니다: {filename}]")
                print("📊 저장된 데이터:")
                print(json.dumps(place_json, ensure_ascii=False, indent=2)[:500] + '\n...')
            
            # 추가 정보 입력 패턴 감지 (더 정확한 키워드)
            additional_info_keywords = [
                "예산", "만원", "원", "돈", "비용", "가격", "상관없", 
                "오전", "오후", "저녁", "밤", "새벽", "점심", "아침", "시간",
                "지하철", "버스", "자차", "차", "도보", "걸어", "택시", "따릉이", "교통", "이동",
                "프라이빗", "조용한", "로맨틱", "야경", "실내", "야외", "특별", "요청"
            ]
            is_additional_info = any(keyword in user_input for keyword in additional_info_keywords)
            
            print(f"🔍 [입력 분석] 건너뛰기: {is_skip_request}, 추가정보: {is_additional_info}")
            
            if is_skip_request:
                # 추천 진행
                ai_response = "✨ 알겠습니다! 지금까지 수집한 정보로 최고의 데이트 코스를 추천드리겠습니다!"
                print(f"\n⏭️ [DEBUG] 사용자 요청으로 추천 진행")
                
            elif is_additional_info:
                # 추가 정보 처리
                print(f"\n📝 [DEBUG] 추가 정보 입력 감지됨")
                try:
                    followup = memory_manager.handle_additional_info_input(session_id, user_input)
                    if 'error' in followup:
                        print(f"❌ 추가 정보 처리 오류: {followup['error']}")
                        ai_response = "죄송해요, 정보 처리 중 오류가 발생했습니다. 다시 말씀해주세요."
                    else:
                        ai_response = followup['message']
                        completion_ratio = followup.get('completion_ratio', 0)
                        print(f"📈 추가 정보 완성도: {completion_ratio:.2f}")
                except Exception as e:
                    print(f"❌ 추가 정보 처리 예외: {e}")
                    ai_response = "정보를 처리하는 중 문제가 발생했습니다. 다시 시도해주세요."
                
            else:
                # 기본 스마트 행동 결정
                next_action = memory_manager.get_smart_next_action(session_id, user_input)
                
                # 행동에 따른 응답 생성
                if next_action['action'] == 'ask_highest_priority_missing':
                    question_result = memory_manager.generate_smart_question(session_id, user_input)
                    ai_response = question_result['question']
                    print(f"\n🔍 [DEBUG] 누락 필드: {question_result['missing_field']} (필수: {question_result['is_essential']})")
                    
                elif next_action['action'] == 'offer_recommendation_with_options':
                    options = memory_manager.generate_recommendation_options(session_id)
                    ai_response = options['message']
                    print(f"\n💡 [DEBUG] 선택권 제공 모드")
                    
                elif next_action['action'] == 'offer_recommendation_with_optional_details':
                    options = memory_manager.generate_recommendation_options(session_id)
                    ai_response = options['message']
                    print(f"\n📋 [DEBUG] 선택적 정보 수집 모드")
                    
                elif next_action['action'] in ['provide_recommendation_with_optional_details', 'provide_basic_recommendation']:
                    ai_response = "✨ 완벽해요! 지금 가지고 있는 정보로 최고의 데이트 코스를 추천드리겠습니다!"
                    print(f"\n🎯 [DEBUG] 추천 진행 - 완성도: {next_action['completion_score']:.2f}")
                    print("\n👉 이대로 추천을 원하시면 Enter를 입력하세요.")
                    # 엔터 입력 대기
                    enter_input = input("\n⏎ Enter: ").strip()
                    if enter_input == "":
                        # JSON 저장 로직 (place agent용)
                        current_info = memory_manager.get_current_info(session_id)
                        context = memory_manager.get_session_context(session_id)
                        state = context["state"]
                        request_type = state.get("location_type", "area_recommendation")
                        def clean_dict(d):
                            if isinstance(d, dict):
                                return {k: clean_dict(v) for k, v in d.items() if v is not None and v != []}
                            elif isinstance(d, list):
                                return [clean_dict(x) for x in d if x is not None]
                            else:
                                return d
                        current_info_clean = clean_dict(current_info)
                        place_json = build_place_agent_json(request_type, current_info_clean)
                        import json
                        filename = "place_agent_request_from_chat.json"
                        with open(filename, "w", encoding="utf-8") as f:
                            json.dump(place_json, f, ensure_ascii=False, indent=2)
                        print(f"\n�� [Place Agent JSON이 저장되었습니다: {filename}]")
                        print("📊 저장된 데이터:")
                        print(json.dumps(place_json, ensure_ascii=False, indent=2)[:500] + '\n...')
                else:
                    ai_response = "죄송해요, 잠시 처리 중 문제가 발생했습니다. 다시 말씀해주세요."
            
            # AI 응답 메시지 추가 및 출력
            memory_manager.add_message(session_id, "assistant", ai_response)
            print(f"\n🤖 AI: {ai_response}")
            
            # 완성도 정보 표시
            print(f"📊 완성도: {next_action['completion_score']:.2f} | 질문타입: {next_action['question_type']}")
            
        except KeyboardInterrupt:
            print("\n\n👋 채팅을 종료합니다.")
            break
        except Exception as e:
            print(f"\n❌ 오류 발생: {e}")
            continue

async def interactive_dynamic_chat():
    """실제 사용자와 대화할 수 있는 인터랙티브 채팅"""
    print("🤖 DayToCourse 동적 채팅봇 시작!")
    print("=" * 50)
    print("💬 메시지를 입력하세요 (종료: 'quit', 'exit')")
    print("🔄 세션 초기화: 'clear' 또는 'reset'")
    print("📊 세션 정보: 'info' 또는 'status'")
    print("-" * 50)
    
    # 메모리 매니저 생성
    memory_manager = ChatMemoryManager()
    session_id = memory_manager.get_or_create_session()
    print(f"세션 ID: {session_id}")
    
    # 첫 인사
    greeting = "안녕하세요! 완벽한 데이트 코스를 찾아드릴게요 😊 어떤 데이트를 원하시나요?"
    memory_manager.add_message(session_id, "assistant", greeting)
    print(f"\n🤖 AI: {greeting}")
    
    while True:
        try:
            # 사용자 입력
            user_input = input(f"\n👤 당신: ").strip()
            
            # 종료 명령어
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n👋 채팅을 종료합니다. 즐거운 데이트 되세요!")
                break
            
            # 빈 입력
            if not user_input:
                continue
            
            # 특수 명령어 처리
            if user_input.lower() in ['clear', 'reset']:
                memory_manager.clear_session(session_id)
                session_id = memory_manager.get_or_create_session()
                print("🗑️ 세션이 초기화되었습니다.")
                continue
            
            if user_input.lower() in ['info', 'status']:
                context = memory_manager.get_session_context(session_id)
                print(f"\n📊 세션 정보:")
                print(f"   - 세션 ID: {session_id}")
                print(f"   - 정보 완성도: {context['completion_score']:.2f}")
                print(f"   - 대화 길이: {context['conversation_length']}")
                print(f"   - 부족한 정보: {memory_manager.get_missing_critical_info(session_id)}")
                print(f"   - 추천 가능: {memory_manager.is_ready_for_recommendation(session_id)}")
                continue
            
            # 사용자 메시지 처리
            memory_manager.add_message(session_id, "user", user_input)
            
            # AI 응답 생성
            if memory_manager.is_ready_for_recommendation(session_id):
                # 추천 생성
                context = memory_manager.get_session_context(session_id)
                user_profile = context["user_profile"]
                location = context["state"]["location"]
                
                ai_response = f"완벽해요! 🎉\n\n"
                ai_response += f"📍 위치: {location}\n"
                ai_response += f"👤 나이: {user_profile.age}세\n"
                ai_response += f"💕 관계: {user_profile.relationship_stage}\n"
                
                if user_profile.atmosphere_preference:
                    ai_response += f"🎨 분위기: {user_profile.atmosphere_preference}\n"
                
                ai_response += f"\n{location}에서 {user_profile.age}세 {user_profile.relationship_stage} 단계 커플을 위한 "
                
                if user_profile.atmosphere_preference:
                    ai_response += f"{user_profile.atmosphere_preference}한 "
                
                ai_response += "데이트 코스를 찾아드릴게요! ✨\n\n"
                ai_response += "[실제 서비스에서는 여기서 서브 에이전트를 호출하여 구체적인 장소들을 추천합니다]"
                
            else:
                # 재질문 생성
                missing = memory_manager.get_missing_critical_info(session_id)
                if not missing:
                    # 필수 정보는 모두 있고, 추가 정보 입력 단계에서 사용자가 입력을 했을 때
                    ai_response = "입력해주신 조건을 반영해서 추천을 준비할게요!"
                elif "location" in missing:
                    ai_response = "어느 지역에서 데이트를 원하시나요? (예: 홍대, 강남, 이태원 등)"
                elif "age" in missing:
                    ai_response = "나이가 어떻게 되시나요? 연령대에 맞는 곳으로 추천드릴게요!"
                elif "relationship_stage" in missing:
                    ai_response = "혹시 연인분이신가요, 아니면 썸 단계이신가요? 분위기가 조금 달라질 수 있어서요 😊"
                elif "concept" in missing:
                    ai_response = "어떤 분위기를 원하시나요? (로맨틱/캐주얼/활기찬)"
                else:
                    ai_response = "더 정확한 추천을 위해 추가 정보가 필요해요. 예산은 어느 정도로 생각하시나요?"
            
            # AI 응답 출력 및 저장
            memory_manager.add_message(session_id, "assistant", ai_response)
            print(f"\n🤖 AI: {ai_response}")
            
            # 완성도 표시
            context = memory_manager.get_session_context(session_id)
            print(f"\n📊 정보 완성도: {context['completion_score']:.2f}")
            
        except KeyboardInterrupt:
            print("\n\n👋 채팅을 종료합니다.")
            break
        except Exception as e:
            print(f"\n❌ 오류 발생: {e}")
            print("다시 시도해주세요.")
    
    print("감사합니다! ��")

# 구 테스트 시스템 끝

# === Place Agent 요청 타입별 필수/선택 필드 정의 ===
PLACE_AGENT_REQUIRED_FIELDS = {
    'exact_locations': ['areas'],
    'area_recommendation': ['location_request', 'user_context', 'selected_categories'],
    'proximity_based': ['location_request', 'user_context', 'selected_categories'],
}
PLACE_AGENT_OPTIONAL_FIELDS = {
    'area_recommendation': ['user_context.preferences', 'user_context.requirements', 'selected_categories'],
    'proximity_based': ['user_context.preferences', 'user_context.requirements', 'selected_categories'],
}

# === 필수 정보 수집 함수 ===
def collect_required_fields(user_input, current_info, request_type):
    """
    필수 정보가 모두 채워질 때까지 반복 질문
    current_info: dict (user_profile, location 등)
    request_type: exact_locations/area_recommendation/proximity_based
    """
    required_fields = PLACE_AGENT_REQUIRED_FIELDS.get(request_type, [])
    missing = []
    for field in required_fields:
        # 단순화: areas/location_request/user_context 등만 체크
        if field == 'areas' and not current_info.get('areas'):
            missing.append('areas')
        if field == 'location_request' and not current_info.get('location_request'):
            missing.append('location_request')
        if field == 'user_context' and not current_info.get('user_context'):
            missing.append('user_context')
        if field == 'selected_categories' and not current_info.get('selected_categories'):
            missing.append('selected_categories')
    return missing

# === 선택 정보 입력 기회 제공 함수 ===
def prompt_optional_fields():
    print("\n더 자세한 조건(예산, 시간, 선호, 특수 조건 등)을 입력하시겠어요?")
    print("예시: '3-5만원, 오후, 조용한 곳, 주차 가능'")
    print("건너뛰려면 Enter만 눌러주세요.")
    detail_input = input("입력: ").strip()
    return detail_input

# === Place Agent JSON 생성 함수 ===
def build_place_agent_json(request_type, current_info, optional_info=None):
    import uuid
    from datetime import datetime, timezone
    request_id = f"req-{uuid.uuid4()}"
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    base = {
        "request_id": request_id,
        "timestamp": timestamp,
        "request_type": request_type,
    }
    # 필수 필드 (기본값 포함)
    if request_type == 'exact_locations':
        base["areas"] = current_info.get("areas", [{"sequence": 1, "area_name": current_info.get("location", "서울")}])
    else:
        # location/concept 값이 있으면 반드시 반영 (location_analysis 우선 사용)
        location_analysis = current_info.get("location_analysis", {})
        extracted_places = location_analysis.get("extracted_places", [])
        
        # 추출된 장소가 있으면 사용, 없으면 기본 location 필드 사용
        if extracted_places:
            location_val = extracted_places
        else:
            location_val = [current_info.get("location")] if current_info.get("location") else []
        
        print(f"[JSON 생성 디버깅] current_info 전체: {current_info}")
        print(f"[JSON 생성 디버깅] location_analysis: {location_analysis}")
        print(f"[JSON 생성 디버깅] 최종 location_val: {location_val}")
        
        # 위치 요청 필드 개선 - 다양한 위치 표현 지원
        location_request = {
            "proximity_type": "general",
            "reference_areas": location_val,
            "place_count": 3,
            "proximity_preference": "any"
        }
        
        # location_analysis에서 더 정교한 위치 정보 추출
        if location_analysis:
            spatial_context = location_analysis.get("spatial_context", "")
            user_intent = location_analysis.get("user_intent", "")
            
            # 공간 맥락에 따른 proximity_type 결정
            if "사이" in spatial_context or "중간" in spatial_context:
                location_request["proximity_type"] = "between"
                location_request["proximity_preference"] = "middle"
            elif "근처" in spatial_context or "근기" in spatial_context:
                location_request["proximity_type"] = "near"
                location_request["proximity_preference"] = "close"
            elif "거쳐서" in spatial_context or "따라" in spatial_context:
                location_request["proximity_type"] = "route"
                location_request["proximity_preference"] = "along_route"
            elif len(location_val) > 1:
                location_request["proximity_type"] = "proximity_based"
                location_request["proximity_preference"] = "accessible"
            
            # 사용자 의도에 따른 place_count 조정
            if "코스" in user_intent or "여러 곳" in user_intent:
                location_request["place_count"] = 5
            elif "한 곳" in user_intent or "한군데" in user_intent:
                location_request["place_count"] = 1
        
        base["location_request"] = location_request
        # 사용자 미추출 정보 개선
        user_profile = current_info.get("user_profile")
        preferences = []
        
        # preferences 배열 채우기 - 다양한 소스에서 가져오기
        if user_profile and hasattr(user_profile, 'preferences') and user_profile.preferences:
            preferences.extend(user_profile.preferences)
        
        # 컴셉 정보도 preferences에 추가
        concept = current_info.get("concept")
        if concept:
            preferences.append(f"{concept} 분위기")
        
        # 기본 user_context 생성
        user_context = {
            "demographics": {
                "age": user_profile.age if user_profile else None,
                "mbti": user_profile.mbti if user_profile else None,
                "relationship_stage": user_profile.relationship_stage if user_profile else None
            },
            "preferences": preferences,
            "requirements": {
                "budget_level": user_profile.budget_level if user_profile else None,
                "time_preference": user_profile.time_preference if user_profile else None,
                "transportation": user_profile.transportation if user_profile else None,
                "max_travel_time": user_profile.max_travel_time if user_profile else None,
                "weather_condition": None,  # 기본값
                "atmosphere_preference": user_profile.atmosphere_preference if user_profile else None
            }
        }
        
        base["user_context"] = user_context
        base["selected_categories"] = current_info.get("selected_categories", ["카페", "음식점", "문화시설"])
    # 선택 필드(있으면 추가)
    if optional_info:
        # 간단히 user_context.requirements, preferences 등 추가
        if 'user_context' in base and optional_info:
            base['user_context'].setdefault('preferences', [])
            base['user_context'].setdefault('requirements', {})
            # 예시: '3-5만원, 오후, 조용한 곳, 주차 가능' → 간단 파싱
            if ',' in optional_info:
                for item in optional_info.split(','):
                    item = item.strip()
                    if '만원' in item or '예산' in item:
                        base['user_context']['requirements']['budget'] = item
                    elif '오후' in item or '아침' in item or '저녁' in item or '밤' in item:
                        base['user_context']['requirements']['time_preference'] = item
                    elif '주차' in item:
                        base['user_context']['requirements']['special_needs'] = item
                    else:
                        base['user_context']['preferences'].append(item)
            else:
                base['user_context']['preferences'].append(optional_info)
    return base

def extract_info_by_keywords(user_message: str) -> dict:
    """키워드 매칭으로 정보 추출 (LLM 실패 시 fallback)"""
    extracted_info = {
        'basic_profile': {},
        'requirements': {},
        'preferences': []
    }
    
    # 관계 정보 추출
    relationship_keywords = {
        '연인': ['연인', '여자친구', '남자친구', '와이프', '남편', '커플'],
        '썸': ['썸', '소개팅', '미팅', '처음 만남'],
        '친구': ['친구', '동료', '지인', '가족']
    }
    
    for relationship, keywords in relationship_keywords.items():
        if any(keyword in user_message for keyword in keywords):
            extracted_info['basic_profile']['relationship_stage'] = relationship
            break
    
    # 컨셉/분위기 추출
    concept_keywords = {
        '로맨틱': ['로맨틱', '로맨틱한', '분위기', '분위기 있는', '조용한', '차분한', '감성적'],
        '캐주얼': ['캐주얼', '편안한', '자연스러운', '일상적'],
        '액티브': ['액티브', '활동적', '체험', '재미있는', '신나는', '활기찬']
    }
    
    for concept, keywords in concept_keywords.items():
        if any(keyword in user_message for keyword in keywords):
            extracted_info['preferences'].append(concept)
            break
    
    # 나이 추출 (간단한 패턴)
    import re
    age_match = re.search(r'(\d{1,2})세', user_message)
    if age_match:
        extracted_info['basic_profile']['age'] = int(age_match.group(1))
    
    # MBTI 추출
    mbti_pattern = r'\b([EI][NS][TF][JP])\b'
    mbti_match = re.search(mbti_pattern, user_message)
    if mbti_match:
        extracted_info['basic_profile']['mbti'] = mbti_match.group(1)
    
    # 예산 정보 추출
    budget_patterns = [
        (r'(\d{1,2})만원', 'budget_level'),
        (r'저렴', 'budget_level'),
        (r'비싸', 'budget_level')
    ]
    
    for pattern, field in budget_patterns:
        if re.search(pattern, user_message):
            extracted_info['requirements'][field] = True
            break
    
    # 시간대 추출
    time_keywords = {
        '아침': ['아침', '오전'],
        '점심': ['점심', '오후'],
        '저녁': ['저녁', '밤', '야간']
    }
    
    for time, keywords in time_keywords.items():
        if any(keyword in user_message for keyword in keywords):
            extracted_info['requirements']['time_preference'] = time
            break
    
    return extracted_info

if __name__ == "__main__":
    # 스마트 채팅 시스템 실행
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "test":
            # 테스트 모드
            asyncio.run(test_smart_reask_system())
        else:
            print("사용 가능한 옵션:")
            print("  python main_agent.py      - 스마트 채팅 시스템 (기본)")
            print("  python main_agent.py test - 시나리오 테스트 모드")
    else:
        # 기본 동작: 스마트 채팅 시스템
        async def smart_chat_with_json_save():
            print("🤖 DayToCourse 스마트 채팅봇 시작!")
            print("=" * 50)
            print("💬 메시지를 입력하세요 (종료: 'quit', 'exit')")
            print("🔄 세션 초기화: 'clear' 또는 'reset'")
            print("📊 세션 정보: 'info' 또는 'status'")
            print("💾 디버그용 JSON 저장: 'json', 'save', 'debug'")
            print("🎯 추천 요청 시 자동 JSON 저장: '추천해줘', '바로 추천', '지금 추천'")
            print("-" * 50)
            memory_manager = ChatMemoryManager()
            session_id = memory_manager.get_or_create_session()
            print(f"세션 ID: {session_id}")
            greeting = "안녕하세요! 완벽한 데이트 코스를 찾아드릴게요 😊 어떤 데이트를 원하시나요?"
            memory_manager.add_message(session_id, "assistant", greeting)
            print(f"\n🤖 AI: {greeting}")
            while True:
                try:
                    user_input = input(f"\n👤 당신: ").strip()
                    if user_input.lower() in ['quit', 'exit', 'q']:
                        print("\n👋 채팅을 종료합니다. 즐거운 데이트 되세요!")
                        break
                    if not user_input:
                        continue
                    if user_input.lower() in ['clear', 'reset']:
                        memory_manager.clear_session(session_id)
                        session_id = memory_manager.get_or_create_session()
                        print("🗑️ 세션이 초기화되었습니다.")
                        greeting = "안녕하세요! 완벽한 데이트 코스를 찾아드릴게요 😊 어떤 데이트를 원하시나요?"
                        memory_manager.add_message(session_id, "assistant", greeting)
                        print(f"\n🤖 AI: {greeting}")
                        continue
                    if user_input.lower() in ['info', 'status']:
                        context = memory_manager.get_session_context(session_id)
                        current_info = memory_manager.get_current_info(session_id)
                        print(f"\n📊 세션 정보:")
                        print(f"  - 완성도 점수: {context['completion_score']:.2f}")
                        print(f"  - 질문 유형: {current_info['state'].get('question_type', 'general')}")
                        print(f"  - 강제 질문 수: {current_info['state'].get('forced_questions_count', 0)}")
                        print(f"  - 총 질문 수: {current_info['state'].get('total_questions_count', 0)}")
                        continue
                    # === 디버그용 JSON 저장 명령어 (기존 유지) ===
                    if user_input.lower() in ['json', 'save', 'debug']:
                        # memory_manager의 get_current_info 사용하여 location_analysis 포함
                        current_info = memory_manager.get_current_info(session_id)
                        context = memory_manager.get_session_context(session_id)
                        state = context["state"]
                        # 요청 타입 추정(간단화)
                        request_type = state.get("location_type", "area_recommendation")
                        # None 값 필터링
                        def clean_dict(d):
                            if isinstance(d, dict):
                                return {k: clean_dict(v) for k, v in d.items() if v is not None and v != []}
                            elif isinstance(d, list):
                                return [clean_dict(x) for x in d if x is not None]
                            else:
                                return d
                        current_info = clean_dict(current_info)
                        place_json = build_place_agent_json(request_type, current_info)
                        import json
                        filename = "place_agent_request_debug.json"
                        with open(filename, "w", encoding="utf-8") as f:
                            json.dump(place_json, f, ensure_ascii=False, indent=2)
                        print(f"\n[디버그용 JSON이 저장되었습니다: {filename}]")
                        print(json.dumps(place_json, ensure_ascii=False, indent=2)[:500] + '\n...')
                        continue
                    # === 일반 대화 흐름 ===
                    memory_manager.add_message(session_id, "user", user_input)
                    next_action = memory_manager.get_smart_next_action(session_id, user_input)
                    if next_action['action'] == 'ask_highest_priority_missing':
                        question_result = memory_manager.generate_smart_question(session_id, user_input)
                        ai_response = question_result['question']
                        print(f"\n🔍 [DEBUG] 누락 필드: {question_result['missing_field']} (필수: {question_result['is_essential']})")
                    elif next_action['action'] == 'offer_recommendation_with_options':
                        options = memory_manager.generate_recommendation_options(session_id)
                        ai_response = options['message']
                        print(f"\n💡 [DEBUG] 선택권 제공 모드")
                    elif next_action['action'] == 'offer_recommendation_with_optional_details':
                        options = memory_manager.generate_recommendation_options(session_id)
                        ai_response = options['message']
                        print(f"\n📋 [DEBUG] 선택적 정보 수집 모드")
                    elif next_action['action'] in ['provide_recommendation_with_optional_details', 'provide_basic_recommendation']:
                        ai_response = "✨ 완벽해요! 지금 가지고 있는 정보로 최고의 데이트 코스를 추천드리겠습니다!"
                        print(f"\n🎯 [DEBUG] 추천 진행 - 완성도: {next_action['completion_score']:.2f}")
                    else:
                        ai_response = "죄송해요, 잠시 처리 중 문제가 발생했습니다. 다시 말씀해주세요."
                    memory_manager.add_message(session_id, "assistant", ai_response)
                    print(f"\n🤖 AI: {ai_response}")
                    print(f"📊 완성도: {next_action['completion_score']:.2f} | 질문타입: {next_action['question_type']}")
                except KeyboardInterrupt:
                    print("\n\n👋 채팅을 종료합니다.")
                    break
                except Exception as e:
                    print(f"\n❌ 오류 발생: {e}")
                    continue
            print("감사합니다! 🙏")
        import asyncio
        asyncio.run(smart_chat_with_json_save())
