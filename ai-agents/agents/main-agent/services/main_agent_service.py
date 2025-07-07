from langchain.memory import ConversationBufferMemory
from langchain_openai import ChatOpenAI
import os
import uuid
import json
from typing import Optional, Dict, Any, Tuple

from core.profile_extractor import (
    extract_profile_from_llm, 
    rule_based_gender_relationship, 
    llm_correct_field, 
    REQUIRED_KEYS
)
from core.location_processor import extract_location_request_from_llm
from core.agent_builders import (
    build_place_agent_json, 
    build_rag_agent_json
)
from models.request_models import MainAgentRequest, UserProfile, LocationRequest
from models.response_models import MainAgentResponse

# 시간-장소 개수 지능형 제약 시스템
TIME_PLACE_CONSTRAINTS = {
    "1시간": {"max_places": 1, "recommended_places": 1, "categories": ["카페"]},
    "2시간": {"max_places": 2, "recommended_places": 2, "categories": ["카페", "음식점"]},
    "3시간": {"max_places": 3, "recommended_places": 2, "categories": ["카페", "음식점", "문화시설"]},
    "4시간": {"max_places": 3, "recommended_places": 3, "categories": ["카페", "음식점", "문화시설", "쇼핑"]},
    "5시간": {"max_places": 4, "recommended_places": 4, "categories": ["카페", "음식점", "문화시설", "쇼핑", "야외활동"]},
    "6시간": {"max_places": 5, "recommended_places": 4, "categories": ["카페", "음식점", "문화시설", "쇼핑", "야외활동"]},
    "반나절": {"max_places": 4, "recommended_places": 3, "categories": ["카페", "음식점", "문화시설", "쇼핑", "야외활동"]},
    "하루종일": {"max_places": 5, "recommended_places": 4, "categories": ["카페", "음식점", "문화시설", "쇼핑", "야외활동", "엔터테인먼트"]}
}

# 필수 정보와 질문 매핑 (확장)
REQUIRED_FIELDS_AND_QUESTIONS = [
    ("age", "나이를 알려주세요. (예: 25살, 30대 등)"),
    ("gender", "성별을 알려주세요. (예: 남, 여)"),
    ("mbti", "MBTI 유형을 알려주세요. (예: ENFP, INFP 등)"),
    ("relationship_stage", "상대와의 관계를 알려주세요. (예: 연인, 썸, 친구 등)"),
    ("atmosphere", "어떤 분위기를 원하시나요? (예: 아늑한, 활기찬 등)"),
    ("budget", "예산은 얼마 정도 생각하시나요? (예: 5만원, 10만원 등)"),
    ("time_slot", "몇 시/시간대에 데이트를 원하시나요? (예: 오전, 오후, 저녁, 밤 등)"),
    ("duration", "몇 시간 정도 데이트를 하실 예정인가요? (예: 1시간, 2시간, 3시간, 반나절, 하루종일 등)"),
    ("place_count", "몇 개의 장소를 방문하고 싶으세요? (예: 2개, 3개 등)")
]
REQUIRED_FIELDS = [f for f, _ in REQUIRED_FIELDS_AND_QUESTIONS]

OPTIONAL_FIELDS = [
    ("car_owned", "🚗 차량을 소유하고 계신가요?\n소유하고 계시면 '예', 그렇지 않으면 '아니오'라고 입력해 주세요."),
    ("transportation", "🚇 데이트 시 주로 어떤 교통수단을 이용하실 예정인가요?\n예시: 지하철, 버스, 자가용, 택시, 도보 등"),
    ("description", "📝 간단한 자기소개(성격, 취미, 관심사 등)를 자유롭게 입력해 주세요!\n예시: '영화를 좋아하는 20대 직장인입니다.'"),
    ("general_preferences", "✨ 데이트에서 선호하는 요소를 쉼표로 구분해서 입력해 주세요!\n예시: 조용한 곳, 야외, 디저트, 분위기 좋은 카페")
]
FIELD_QUESTION_DICT = {
    "age": "🎂 나이를 숫자로 입력해 주세요!\n예시: 25, 30 등",
    "gender": "🚻 성별을 입력해 주세요!\n예시: 남, 여",
    "mbti": "🧬 MBTI 유형을 입력해 주세요!\n예시: ENFP, INFP 등",
    "address": "📍 데이트를 원하는 지역이나 동네를 입력해 주세요!\n예시: 홍대, 강남, 이태원 등",
    "relationship_stage": "💑 상대방과의 관계를 입력해 주세요!\n예시: 연인, 썸, 친구 등",
    "atmosphere": "🌈 원하는 데이트 분위기를 입력해 주세요!\n예시: 아늑한, 활기찬, 조용한, 로맨틱 등",
    "budget": "💸 한 번의 데이트에 사용할 예산을 입력해 주세요!\n예시: 5만원, 10만원 이하 등",
    "time_slot": "⏰ 데이트를 원하는 시간대를 입력해 주세요!\n예시: 오전, 오후, 저녁, 밤 등",
    "duration": "⏱️ 데이트 시간은 얼마나 할 예정인가요?\n예시: 1시간, 2시간, 3시간, 반나절, 하루종일 등",
    "place_count": "🔢 몇 개의 장소를 방문하고 싶으세요?\n예시: 2개, 3개 등"
}

# 세션별 정보 누적용 임시 메모리 (실제 서비스에서는 DB/Redis 권장)
SESSION_INFO: Dict[str, Dict[str, Any]] = {}

class MainAgentService:
    def __init__(self, openai_api_key: Optional[str] = None):
        self.openai_api_key = openai_api_key or os.environ.get("OPENAI_API_KEY")
        self.llm = None
        print(f"[DEBUG] MainAgentService 초기화: API KEY {'설정됨' if self.openai_api_key else '미설정'}")
        if self.openai_api_key:
            try:
                self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, openai_api_key=self.openai_api_key)
                print(f"[DEBUG] LLM 초기화 성공")
            except Exception as e:
                print(f"[ERROR] LLM 초기화 실패: {str(e)}")
        self.memory_sessions: Dict[str, ConversationBufferMemory] = {}
        self.llm_correction_cache: Dict[str, Dict[str, str]] = {}  # session_id -> {(field, value): corrected
    
    def get_llm_corrected(self, session_id: str, key: str, value: str) -> str:
        cache = self.llm_correction_cache.setdefault(session_id, {})
        cache_key = f"{key}:{value}"
        if cache_key in cache:
            return cache[cache_key]
        corrected = llm_correct_field(self.llm, key, value)
        cache[cache_key] = corrected
        return corrected
    
    def get_smart_recommendations_for_duration(self, duration: str) -> dict:
        """데이트 시간에 따른 스마트 추천 - 동적 계산"""
        # 시간 정규화
        normalized_duration = self._normalize_duration(duration)
        
        # 하드코딩된 값이 있으면 사용
        if normalized_duration in TIME_PLACE_CONSTRAINTS:
            return TIME_PLACE_CONSTRAINTS[normalized_duration]
        
        # 동적 계산: "X시간" 패턴 처리
        import re
        hour_match = re.match(r'^(\d+)시간$', normalized_duration)
        if hour_match:
            hours = int(hour_match.group(1))
            return self._calculate_dynamic_constraints(hours)
        
        # 기본값
        return {"max_places": 3, "recommended_places": 3, "categories": ["카페", "음식점", "문화시설"]}
    
    def _calculate_dynamic_constraints(self, hours: int) -> dict:
        """시간에 따른 동적 제약 계산"""
        if hours <= 1:
            return {"max_places": 1, "recommended_places": 1, "categories": ["카페"]}
        elif hours <= 2:
            return {"max_places": 2, "recommended_places": 2, "categories": ["카페", "음식점"]}
        elif hours <= 3:
            return {"max_places": 3, "recommended_places": 2, "categories": ["카페", "음식점", "문화시설"]}
        elif hours <= 4:
            return {"max_places": 3, "recommended_places": 3, "categories": ["카페", "음식점", "문화시설", "쇼핑"]}
        elif hours <= 6:
            return {"max_places": 4, "recommended_places": 4, "categories": ["카페", "음식점", "문화시설", "쇼핑", "야외활동"]}
        elif hours <= 8:
            return {"max_places": 5, "recommended_places": 4, "categories": ["카페", "음식점", "문화시설", "쇼핑", "야외활동"]}
        else:  # 9시간 이상
            return {"max_places": 6, "recommended_places": 5, "categories": ["카페", "음식점", "문화시설", "쇼핑", "야외활동", "엔터테인먼트"]}
    
    def _normalize_duration(self, duration: str) -> str:
        """GPT 기반 시간 표현 정규화"""
        duration = duration.strip()
        
        # GPT로 시간 파싱 시도
        if self.llm:
            try:
                gpt_result = self._parse_duration_with_gpt(duration)
                if gpt_result:
                    return gpt_result
            except Exception as e:
                print(f"[WARNING] GPT 시간 파싱 실패, 기존 로직 사용: {e}")
        
        # 기존 키워드 기반 로직 (폴백)
        if any(word in duration for word in ["1시간", "한시간"]):
            return "1시간"
        elif any(word in duration for word in ["2시간", "두시간"]):
            return "2시간"
        elif any(word in duration for word in ["3시간", "세시간"]):
            return "3시간"
        elif any(word in duration for word in ["4시간", "네시간", "사시간"]):
            return "4시간"
        elif any(word in duration for word in ["반나절", "5시간", "6시간"]):
            return "반나절"
        elif any(word in duration for word in ["하루", "하루종일", "종일", "7시간", "8시간", "9시간", "10시간"]):
            return "하루종일"
        else:
            return "3시간"  # 기본값
    
    def _parse_duration_with_gpt(self, duration_input: str) -> str:
        """GPT를 사용한 시간 범위 파싱"""
        prompt = f"""
다음 시간 표현을 분석해서 정확한 시간을 JSON 형태로 반환해주세요.

입력: "{duration_input}"

다음 JSON 형식으로만 답변해주세요:
{{
    "total_hours": 숫자,
    "normalized_duration": "X시간" 또는 "반나절" 또는 "하루종일"
}}

규칙:
- "5시부터 10시까지" → 5시간
- "오후 3시부터 오후 8시까지" → 5시간  
- "저녁 6시부터 밤 11시까지" → 5시간
- 1-4시간 → "X시간"
- 5-6시간 → "반나절" 
- 7시간 이상 → "하루종일"
"""
        
        try:
            response = self.llm.invoke(prompt)
            result_text = response.content.strip()
            
            # JSON 파싱
            import json
            import re
            
            # JSON 부분만 추출
            json_match = re.search(r'\{[^}]+\}', result_text)
            if json_match:
                result_json = json.loads(json_match.group())
                return result_json.get("normalized_duration", "3시간")
            
        except Exception as e:
            print(f"[ERROR] GPT 시간 파싱 실패: {e}")
            
        return None
    
    def _generate_constraint_violation_message(self, duration: str, requested: int, max_allowed: int, constraints: dict) -> str:
        """제약 위반 시 GPT 기반 재확인 메시지 생성"""
        if not self.llm:
            # LLM이 없을 경우 기본 메시지
            return f"⚠️ {duration} 데이트에 {requested}개 장소는 조금 빡빡할 수 있어요! 최대 {max_allowed}개를 추천드려요. {max_allowed}개로 하시겠어요? 아니면 시간을 늘리시겠어요?"
        
        available_categories = constraints.get("categories", [])
        
        prompt = f"""
사용자가 {duration} 데이트에 {requested}개 장소를 원하지만, 실제로는 최대 {max_allowed}개까지만 가능합니다.

다음을 포함해서 정중하고 친근한 톤으로 재확인 메시지를 작성해주세요:
1. 왜 {requested}개가 어려운지 간단히 설명
2. {max_allowed}개를 추천하는 이유
3. 사용자의 선택권 제시 (개수 조정 또는 시간 늘리기)
4. 지원 가능한 카테고리 언급: {', '.join(available_categories[:4])}

예시 톤: "아, {duration} 데이트에 {requested}개 장소는 조금 빡빡할 수 있어요! 각 장소에서 충분히 즐기시려면..."

단순한 텍스트로만 답변해주세요.
"""
        
        try:
            response = self.llm.invoke(prompt)
            return response.content.strip()
        except Exception as e:
            print(f"[ERROR] GPT 재확인 메시지 생성 실패: {e}")
            # 폴백: 기본 메시지
            return f"⚠️ {duration} 데이트에 {requested}개 장소는 조금 빡빡할 수 있어요! 최대 {max_allowed}개를 추천드려요. {max_allowed}개로 하시겠어요? 아니면 시간을 늘리시겠어요?"
    
    def _normalize_duration_input(self, user_input: str) -> str:
        """사용자 입력을 시간 표현으로 정규화"""
        user_input = user_input.strip()
        
        # 숫자만 입력한 경우
        if user_input.isdigit():
            num = int(user_input)
            if num == 1:
                return "1시간"
            elif num == 2:
                return "2시간"
            elif num == 3:
                return "3시간"
            elif num == 4:
                return "4시간"
            elif num >= 5:
                return "반나절"
            else:
                return "3시간"  # 기본값
        
        # 기존 정규화 함수 사용
        return self._normalize_duration(user_input)
    
    def _normalize_place_count_input(self, user_input: str) -> str:
        """사용자 place_count 입력을 정규화"""
        user_input = user_input.strip()
        
        # 숫자만 입력한 경우
        if user_input.isdigit():
            return f"{user_input}"
        
        # "3개", "3곳" 등의 경우
        import re
        numbers = re.findall(r'\d+', user_input)
        if numbers:
            return f"{numbers[0]}"
        
        # 기본값
        return "3"
    
    def _generate_smart_place_count_question(self, duration: str) -> str:
        """시간에 따른 스마트한 장소 개수 질문 생성"""
        constraints = self.get_smart_recommendations_for_duration(duration)
        max_places = constraints["max_places"]
        recommended_places = constraints["recommended_places"]
        
        # 시간별 개수별 배분 계산
        import re
        duration_num = re.findall(r'\d+', duration)
        if duration_num:
            total_minutes = int(duration_num[0]) * 60
        elif "반나절" in duration:
            total_minutes = 300  # 5시간
        elif "하루" in duration:
            total_minutes = 480  # 8시간
        else:
            total_minutes = 180  # 3시간 기본값
        
        question = f"🕐 {duration} 데이트 예정이시군요!\n몇 개의 장소를 방문하고 싶으세요?\n\n"
        
        # 각 개수별 시간 배분 표시
        for i in range(1, max_places + 1):
            time_per_place = total_minutes // i
            hours = time_per_place // 60
            minutes = time_per_place % 60
            
            if hours > 0 and minutes > 0:
                time_str = f"{hours}시간 {minutes}분"
            elif hours > 0:
                time_str = f"{hours}시간"
            else:
                time_str = f"{minutes}분"
            
            if i == recommended_places:
                question += f"• {i}개 - 추천! (각 장소당 약 {time_str}) ⭐\n"
            else:
                question += f"• {i}개 - (각 장소당 약 {time_str})\n"
        
        question += f"\n💡 최대 {max_places}개까지 가능해요!"
        return question
    
    def validate_time_place_constraints(self, duration: str, place_count: str) -> tuple:
        """시간-장소 개수 제약 검증 (강화) - GPT 재확인 메시지 포함"""
        constraints = self.get_smart_recommendations_for_duration(duration)
        
        try:
            # place_count에서 숫자 추출
            import re
            numbers = re.findall(r'\d+', place_count)
            if numbers:
                requested_count = int(numbers[0])
            else:
                requested_count = constraints["recommended_places"]
        except:
            requested_count = constraints["recommended_places"]
        
        max_places = constraints["max_places"]
        recommended_places = constraints["recommended_places"]
        available_categories = constraints["categories"]
        
        if requested_count > max_places:
            # GPT로 정중한 재확인 메시지 생성
            gpt_message = self._generate_constraint_violation_message(
                duration, requested_count, max_places, constraints
            )
            return "needs_reconfirmation", gpt_message
        elif requested_count < 1:
            return False, f"⚠️ 최소 1개 장소는 선택해야 해요! {recommended_places}개를 추천드려요."
        else:
            success_msg = f"✅ {duration} 데이트에 {requested_count}개 장소가 딱 맞아요!\n"
            success_msg += f"💡 선택 가능한 카테고리: {', '.join(available_categories)}"
            return True, success_msg
    
    async def generate_category_recommendations(self, profile_data: Dict, place_count: int, conversation_context: str = "") -> list:
        """완전 동적 카테고리 추천 - 하드코딩 제거"""
        from services.intelligent_category_generator import IntelligentCategoryGenerator
        
        # 지능형 카테고리 생성기 사용
        generator = IntelligentCategoryGenerator(self.openai_api_key)
        
        try:
            recommendations = await generator.generate_contextual_categories(
                profile_data=profile_data,
                place_count=place_count,
                conversation_context=conversation_context
            )
            
            print(f"[MAIN_AGENT] 동적 카테고리 추천 성공: {len(recommendations)}개")
            return recommendations
            
        except ValueError as ve:
            # 시간-장소 제약 위반 예외 처리
            if str(ve).startswith("CONSTRAINT_VIOLATION:"):
                print(f"[CONSTRAINT] IntelligentCategoryGenerator 제약 위반: {ve}")
                # 예외를 다시 발생시켜서 상위 레벨에서 처리
                raise ve
            else:
                print(f"[ERROR] IntelligentCategoryGenerator 값 오류: {ve}")
                # 다음 단계로 진행
                pass
            
        except Exception as e:
            print(f"[ERROR] 동적 카테고리 생성 실패, SmartCategoryRecommender 사용: {e}")
            
            # SmartCategoryRecommender로 fallback
            from services.smart_category_recommender import SmartCategoryRecommender
            smart_recommender = SmartCategoryRecommender(self.openai_api_key)
            
            try:
                fallback_recommendations = await smart_recommender.generate_personalized_categories(
                    profile_data=profile_data,
                    place_count=place_count,
                    conversation_context=conversation_context
                )
                print(f"[MAIN_AGENT] SmartCategoryRecommender 사용 성공: {len(fallback_recommendations)}개")
                return fallback_recommendations
                
            except ValueError as ve:
                # 시간-장소 제약 위반 예외 처리
                if str(ve).startswith("CONSTRAINT_VIOLATION:"):
                    constraint_message = str(ve).replace("CONSTRAINT_VIOLATION:", "")
                    print(f"[CONSTRAINT] 제약 위반 감지: {constraint_message}")
                    # 예외를 다시 발생시켜서 상위 레벨에서 처리
                    raise ValueError(f"CONSTRAINT_VIOLATION:{constraint_message}")
                else:
                    print(f"[ERROR] SmartCategoryRecommender 값 오류: {ve}")
                    return await self._emergency_category_fallback(profile_data, place_count)
                    
            except Exception as e2:
                print(f"[ERROR] SmartCategoryRecommender도 실패: {e2}")
                # 최종 emergency fallback (기존 방식)
                return await self._emergency_category_fallback(profile_data, place_count)
    
    def format_category_recommendation_message(self, recommendations: list, duration: str = "", place_count: int = 3) -> str:
        """카테고리 추천 메시지 포맷팅 - CategoryRecommendation 객체 전용"""
        message = ""
        
        # 시간 제약 정보 추가
        if duration:
            constraints = self.get_smart_recommendations_for_duration(duration)
            message += f"⏰ {duration} 데이트 기준으로 추천드려요!\n"
            message += f"💡 이 시간대에는 최대 {constraints['max_places']}개 장소까지 가능해요.\n\n"
        
        message += "🎯 장소별 카테고리를 이렇게 추천드려요:\n\n"
        
        for rec in recommendations:
            # CategoryRecommendation 객체만 처리
            seq = rec.sequence
            category = rec.category
            alternatives = " 또는 ".join(rec.alternatives)
            has_alternatives = bool(rec.alternatives)
            
            message += f"{seq}️⃣ {seq}번째 장소: {category}"
            if has_alternatives:
                message += f" (또는 {alternatives})"
            message += "\n"
        
        message += "\n이렇게 하시겠어요? 아니면 바꾸고 싶은 곳이 있나요?"
        message += "\n💬 예시: '2번째를 쇼핑으로 바꿔줘', '1번을 카페로 해주세요'"
        return message
    
    def format_smart_category_message(self, smart_recommendations: list, duration: str = "", place_count: int = 3) -> str:
        """스마트 카테고리 추천 메시지 포맷팅"""
        message = ""
        
        # 시간 제약 정보 추가
        if duration:
            constraints = self.get_smart_recommendations_for_duration(duration)
            message += f"⏰ {duration} 데이트 기준으로 추천드려요!\n"
            message += f"💡 이 시간대에는 최대 {constraints['max_places']}개 장소까지 가능해요.\n\n"
        
        message += "🎯 당신의 프로필을 분석해서 개인화된 카테고리를 추천드려요:\n\n"
        
        for rec in smart_recommendations:
            # CategoryRecommendation 객체만 처리
            seq = rec.sequence
            category = rec.category
            reason = rec.reason
            alternatives = " 또는 ".join(rec.alternatives)
            
            message += f"{seq}️⃣ {seq}번째 장소: {category}\n"
            message += f"   💭 이유: {reason}\n"
            if rec.alternatives:
                message += f"   🔄 대안: {alternatives}\n"
            message += "\n"
        
        message += "이렇게 하시겠어요? 아니면 바꾸고 싶은 곳이 있나요?"
        message += "\n💬 예시: '2번째를 쇼핑으로 바꿔줘', '1번을 카페로 해주세요'"
        return message
    
    def parse_category_modification(self, user_input: str, current_recommendations: list) -> tuple:
        """사용자의 카테고리 수정 요청 파싱"""
        import re
        
        # "1번째를 쇼핑으로", "2번 카페로 바꿔줘" 등의 패턴 매칭
        patterns = [
            r'(\d+)번째?를?\s*([가-힣]+)으?로?',
            r'(\d+)번?을?\s*([가-힣]+)으?로?\s*바꿔?',
            r'(\d+)번째?\s*([가-힣]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, user_input)
            if match:
                sequence = int(match.group(1))
                new_category = match.group(2).strip()
                
                # 유효한 카테고리인지 확인
                valid_categories = ["카페", "음식점", "문화시설", "쇼핑", "엔터테인먼트", "야외활동", "휴식시설", "술집"]
                if new_category in valid_categories:
                    # 추천 리스트 업데이트 - CategoryRecommendation 객체만 처리
                    for rec in current_recommendations:
                        if rec.sequence == sequence:
                            rec.category = new_category
                            break
                    return True, f"✅ {sequence}번째 장소를 {new_category}으로 변경했어요!"
        
        return False, "죄송해요, 어떤 장소를 어떻게 바꾸고 싶으신지 명확하게 말씀해주세요. 예: '2번째를 쇼핑으로 바꿔줘'"
    
    async def parse_location_clustering_request(self, user_input: str, place_count: int) -> dict:
        """GPT 기반 장소 배치 지정 파싱 - 정규식 완전 제거"""
        print(f"[GPT_LOCATION] 장소 배치 요청 처리 시작: {user_input}")
        
        # GPT 기반 처리로 완전 대체
        if not hasattr(self, 'location_processor'):
            self.location_processor = GPTLocationProcessor(self.openai_api_key)
        
        return await self.location_processor.process_location_clustering(user_input, place_count)
    
    
    def format_location_clustering_confirmation(self, clustering_info: dict, categories: list, profile=None) -> str:
        """장소 배치 확인 메시지 포맷팅 - 카테고리 상세 정보 + 시간 분배 + 이동시간 통합"""
        message = "🗺️ 정리하면 이렇게 됩니다:\n\n"
        
        # 시간 분배 정보 가져오기
        time_allocations = {}
        if hasattr(self, 'llm') and self.llm:
            try:
                # 사용자 프로필에서 실제 duration 가져오기
                actual_duration = profile.duration if profile and profile.duration else None
                time_data = self._get_time_allocation_data(categories, clustering_info, actual_duration)
                time_allocations = time_data
            except Exception as e:
                print(f"[WARNING] 시간 분배 생성 실패: {e}")
        
        # 이동시간 정보 가져오기
        travel_times = {}
        if hasattr(self, 'llm') and self.llm:
            try:
                travel_data = self._get_travel_time_data(categories, clustering_info)
                travel_times = travel_data
            except Exception as e:
                print(f"[WARNING] 이동시간 계산 실패: {e}")
        
        previous_location = None
        for group in clustering_info["groups"]:
            places = group["places"]
            location = group["location"]
            
            for place_num in places:
                # 해당 순서의 카테고리 정보 찾기
                category = "카페"  # 기본값
                reason = ""
                alternatives = []
                
                for cat in categories:
                    # CategoryRecommendation 객체만 처리
                    if cat.sequence == place_num:
                        category = cat.category
                        reason = getattr(cat, 'reason', '')
                        alternatives = getattr(cat, 'alternatives', [])
                        break
                
                # 이동시간 표시 (첫 번째 장소가 아니고 다른 지역으로 이동하는 경우)
                if previous_location and previous_location != location:
                    travel_time = travel_times.get(f"{previous_location}-{location}", "약 20분")
                    message += f"🚶 {previous_location} → {location} {travel_time}\n\n"
                
                # 시간 분배 정보
                allocated_time = time_allocations.get(place_num, "1시간 30분")
                
                # 상세 정보 포함한 메시지 생성
                message += f"{place_num}️⃣ {place_num}번째 장소: {category} ({location}) - {allocated_time}\n"
                if reason:
                    message += f"💭 이유: {reason}\n"
                if alternatives:
                    alternatives_text = " 또는 ".join(alternatives)
                    message += f"🔄 대안: {alternatives_text}\n"
                message += "\n"
                
                previous_location = location
        
        message += "이렇게 맞나요? 맞으시면 '맞아요'라고 말씀해주세요!"
        return message
    
    def _get_time_allocation_data(self, categories: list, clustering_info: dict, actual_duration: str = None) -> dict:
        """시간 분배 데이터 생성 - 실제 사용자 입력 시간 사용"""
        # 카테고리 정보 수집
        places_info = []
        for group in clustering_info["groups"]:
            for place_num in group["places"]:
                for cat in categories:
                    if cat.sequence == place_num:
                        places_info.append({
                            "sequence": place_num,
                            "category": cat.category,
                            "location": group["location"]
                        })
                        break
        
        # 실제 사용자 입력 시간 사용 (하드코딩 제거)
        total_duration = actual_duration if actual_duration else "4시간"  # 기본값
        
        # 총 시간을 분으로 변환
        total_minutes = self._parse_duration_to_minutes(total_duration)
        place_count = len(places_info)
        
        # 이동시간 동적 계산 (동네별 차등화)
        estimated_travel_time = self._calculate_dynamic_travel_time(clustering_info, place_count)
        available_time = total_minutes - estimated_travel_time
        
        # 각 장소당 권장 시간 계산 (5분 단위로 조정)
        raw_time_per_place = available_time // place_count if place_count > 0 else 90
        time_per_place = self._round_to_five_minutes(raw_time_per_place)
        
        prompt = f"""
다음 데이트 장소들에 대해 각 장소별 시간 분배만 JSON 형타로 생성해주세요.

장소 정보: {places_info}
총 시간: {total_duration}
장소 개수: {place_count}개
각 장소당 권장 시간: {time_per_place}분
예상 이동시간: {estimated_travel_time}분

다음 JSON 형식으로만 답변해주세요:
{{
    "allocations": {{
        "1": "1시간 30분",
        "2": "2시간",
        "3": "1시간",
        "4": "1시간 30분"
    }}
}}

중요한 규칙:
- 모든 장소의 시간 합계 + 이동시간 = 정확히 {total_duration}
- 각 장소는 최소 30분, 최대 180분
- 전체 합계가 {total_minutes}분을 초과하면 절대 안됨
- 각 장소당 대략 {time_per_place}분 내외로 할당
- 모든 시간은 반드시 5분 단위로 할당 (예: 45분, 60분, 75분, 90분 등)
"""
        
        try:
            response = self.llm.invoke(prompt)
            result_text = response.content.strip()
            
            import json
            import re
            
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                result_json = json.loads(json_match.group())
                allocations = result_json.get("allocations", {})
                # 키를 int로 변환
                return {int(k): v for k, v in allocations.items()}
            
        except Exception as e:
            print(f"[ERROR] 시간 분배 데이터 생성 실패: {e}")
            
        return {}
    
    def _get_travel_time_data(self, categories: list, clustering_info: dict) -> dict:
        """이동시간 데이터 생성"""
        # 이동 경로 정보 수집
        routes = []
        previous_location = None
        
        for group in clustering_info["groups"]:
            for place_num in group["places"]:
                current_location = group["location"]
                if previous_location and previous_location != current_location:
                    routes.append({
                        "from": previous_location,
                        "to": current_location
                    })
                previous_location = current_location
        
        if not routes:
            return {}
        
        prompt = f"""
다음 서울 지역 간 이동시간을 JSON 형태로 계산해주세요.

이동 경로: {routes}

다음 JSON 형식으로만 답변해주세요:
{{
    "travel_times": {{
        "이촌동-이태원": "25분 (지하철 6호선)",
        "이태원-홍대": "30분 (지하철 6호선→2호선)"
    }}
}}

규칙:
- 같은 구 내: 도보 5-10분
- 인접한 구: 지하철/버스 15-25분  
- 먼 거리: 지하철/버스 25-40분
- 강남-강북 간: 30-45분
- 실제 서울 지하철노선 고려
"""
        
        try:
            response = self.llm.invoke(prompt)
            result_text = response.content.strip()
            
            import json
            import re
            
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                result_json = json.loads(json_match.group())
                return result_json.get("travel_times", {})
            
        except Exception as e:
            print(f"[ERROR] 이동시간 데이터 생성 실패: {e}")
            
        # 폴백: 기본 이동시간
        result = {}
        for route in routes:
            key = f"{route['from']}-{route['to']}"
            result[key] = "약 20분"
        return result
    
    def _generate_time_allocation_with_gpt(self, categories: list, clustering_info: dict, actual_duration: str = None) -> str:
        """GPT를 사용한 시간 분배 생성 - 실제 사용자 입력 시간 기반"""
        # 카테고리 정보 수집
        places_info = []
        for group in clustering_info["groups"]:
            for place_num in group["places"]:
                for cat in categories:
                    if cat.sequence == place_num:
                        places_info.append({
                            "sequence": place_num,
                            "category": cat.category,
                            "location": group["location"]
                        })
                        break
        
        # 실제 사용자 입력 시간 사용 (하드코딩 제거)
        total_duration = actual_duration if actual_duration else "6시간"
        
        # 총 시간을 분으로 변환
        total_minutes = self._parse_duration_to_minutes(total_duration)
        place_count = len(categories)
        
        # 이동시간 고려 (장소 간 평균 15분씩)
        estimated_travel_time = max(0, (place_count - 1) * 15)
        available_time = total_minutes - estimated_travel_time
        
        # 각 장소당 권장 시간 계산
        time_per_place = available_time // place_count if place_count > 0 else 90
        
        prompt = f"""
다음 데이트 장소들에 대해 각 장소별 시간 분배만 JSON 형태로 생성해주세요.

장소 정보: {places_info}
총 시간: {total_duration}
장소 개수: {place_count}개
각 장소당 권장 시간: {time_per_place}분
예상 이동시간: {estimated_travel_time}분

다음 JSON 형식으로만 답변해주세요:
{{
    "places": [
        {{
            "sequence": 1,
            "category": "카테고리명",
            "allocated_time": "1시간 30분"
        }}
    ]
}}

중요한 규칙:
- 모든 장소의 시간 합계 + 이동시간 = 정확히 {total_duration}
- 각 장소는 최소 30분, 최대 180분
- 전체 합계가 {total_minutes}분을 초과하면 절대 안됨
"""
        
        try:
            response = self.llm.invoke(prompt)
            result_text = response.content.strip()
            
            # JSON 파싱
            import json
            import re
            
            # JSON 부분만 추출
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                result_json = json.loads(json_match.group())
                places_data = result_json.get("places", [])
                
                # 간단한 형태로 포맷팅
                result = ""
                for place in places_data:
                    seq = place.get("sequence")
                    category = place.get("category")
                    time = place.get("allocated_time")
                    result += f"{seq}번째 {category}: {time}\n"
                
                return result.strip()
            
        except Exception as e:
            print(f"[ERROR] GPT 시간 분배 생성 실패: {e}")
            
        return None
    
    def _parse_duration_to_minutes(self, duration: str) -> int:
        """시간 표현을 분으로 변환"""
        try:
            import re
            
            # "6시간" 같은 기본값 처리
            if not duration or duration == "6시간":
                return 360  # 6시간 기본값
            
            # "X시간" 패턴 처리
            hour_match = re.search(r'(\d+)시간', duration)
            if hour_match:
                return int(hour_match.group(1)) * 60
            
            # "반나절" 처리
            if "반나절" in duration:
                return 300  # 5시간
            
            # "하루종일" 처리
            if any(word in duration for word in ["하루", "종일"]):
                return 480  # 8시간
            
            # 숫자만 입력한 경우
            if duration.isdigit():
                return int(duration) * 60
            
            # 기본값
            return 180  # 3시간
            
        except Exception as e:
            print(f"[ERROR] 시간 파싱 실패: {e}")
            return 180  # 3시간 기본값
    
    def _calculate_dynamic_travel_time(self, clustering_info: dict, place_count: int) -> int:
        """동네별 동적 이동시간 계산"""
        if not clustering_info or place_count <= 1:
            return 0
        
        try:
            groups = clustering_info.get("groups", [])
            if not groups:
                return max(0, (place_count - 1) * 15)  # 기본값
            
            total_travel_time = 0
            previous_location = None
            
            for group in groups:
                current_location = group.get("location", "")
                
                if previous_location and previous_location != current_location:
                    # 다른 동네로 이동
                    travel_time = self._estimate_area_travel_time(previous_location, current_location)
                    total_travel_time += travel_time
                elif previous_location == current_location:
                    # 같은 동네 내 이동
                    total_travel_time += 5  # 5분
                
                previous_location = current_location
            
            return total_travel_time
            
        except Exception as e:
            print(f"[ERROR] 동적 이동시간 계산 실패: {e}")
            return max(0, (place_count - 1) * 15)  # 기본값
    
    def _estimate_area_travel_time(self, from_area: str, to_area: str) -> int:
        """지역 간 이동시간 추정"""
        try:
            # GPT로 실제 서울 지역 간 이동시간 계산
            if self.llm:
                prompt = f"""
서울 {from_area}에서 {to_area}까지의 대중교통 이동시간을 분 단위로 추정해주세요.

고려사항:
- 지하철/버스 이용
- 평일 오후 기준
- 도보 시간 포함
- 환승 시간 포함

숫자만 답변해주세요. (예: 25)
"""
                
                result = self.llm.invoke(prompt)
                time_str = result.content.strip()
                
                # 숫자 추출
                import re
                numbers = re.findall(r'\d+', time_str)
                if numbers:
                    return int(numbers[0])
            
            # 폴백: 기본 추정치
            if from_area == to_area:
                return 5  # 같은 동네
            else:
                return 25  # 다른 동네
                
        except Exception as e:
            print(f"[ERROR] 지역 간 이동시간 추정 실패: {e}")
            return 25  # 기본값
    
    def _round_to_five_minutes(self, minutes: int) -> int:
        """시간을 5분 단위로 반올림/반내림"""
        return round(minutes / 5) * 5
    
    def _generate_travel_time_with_gpt(self, categories: list, clustering_info: dict) -> str:
        """GPT/카카오 API 기반 이동시간 계산 JSON 생성"""
        # 이동 경로 정보 수집
        routes = []
        previous_location = None
        
        for group in clustering_info["groups"]:
            for place_num in group["places"]:
                current_location = group["location"]
                if previous_location and previous_location != current_location:
                    # 다른 지역으로 이동
                    for cat in categories:
                        if cat.sequence == place_num:
                            routes.append({
                                "from_location": previous_location,
                                "to_location": current_location,
                                "sequence": place_num,
                                "category": cat.category
                            })
                            break
                previous_location = current_location
        
        if not routes:
            return "모든 장소가 같은 지역이라 이동시간이 거의 없어요! (도보 5-10분)"
        
        prompt = f"""
다음 이동 경로들에 대해 실제 서울 지역 간 이동시간을 JSON 형태로 정확히 계산해주세요.

이동 경로: {routes}

다음 JSON 형식으로만 답변해주세요:
{{
    "routes": [
        {{
            "from": "지역1",
            "to": "지역2", 
            "estimated_time": "25분",
            "method": "지하철 6호선",
            "distance": "약 3km"
        }}
    ],
    "formatted_travel": "이촌동 → 이태원 25분 (지하철 6호선)\\n이태원 → 홍대 30분 (지하철 6호선→2호선)"
}}

중요한 규칙:
- 실제 서울 지하철 노선도와 환승 시간 고려
- 평일 오후 기준 대중교통 이용 시간
- 도보 시간 포함 (역에서 목적지까지)
- 일반적인 추정치: 같은 구(10-15분), 인접구(20-30분), 먼거리(30-50분)
- 강남-강북 간에는 추가 시간 고려
"""
        
        try:
            response = self.llm.invoke(prompt)
            result_text = response.content.strip()
            
            # JSON 파싱
            import json
            import re
            
            # JSON 부분만 추출
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                result_json = json.loads(json_match.group())
                return result_json.get("formatted_travel", "")
            
        except Exception as e:
            print(f"[ERROR] GPT 이동시간 계산 실패: {e}")
            
        # 폴백: 기본 이동시간 계산
        if routes:
            fallback_travel = []
            for route in routes:
                if route["from_location"] != route["to_location"]:
                    fallback_travel.append(f"{route['from_location']} → {route['to_location']} 약 20분")
            return "\n".join(fallback_travel) if fallback_travel else "이동시간 계산 불가"
        
        return None
    
    async def handle_user_modifications(self, user_input: str, session_info: dict) -> tuple:
        """사용자 수정 요청 통합 처리"""
        user_input = user_input.strip()
        
        # 장소 개수 변경 요청인지 확인 ("카테고리 2개만 하고 싶어", "3개로 해줘")
        if any(word in user_input for word in ["개만", "개로", "갯수", "개수"]):
            import re
            numbers = re.findall(r'\d+', user_input)
            if numbers:
                new_count = int(numbers[0])
                # 새로운 개수로 카테고리 재생성
                return "place_count_changed", f"✅ {new_count}개 장소로 변경하겠습니다!", new_count
        
        # 시간 변경 요청인지 확인 ("시간을 5시간으로 늘려주세요", "5시간으로 해주세요")
        if any(word in user_input for word in ["시간", "시간을", "시간으로", "늘려", "늘리"]):
            import re
            # "시간" 앞에 있는 숫자를 찾아서 duration 업데이트
            time_patterns = re.findall(r'(\d+)\s*시간', user_input)
            if time_patterns:
                new_duration = f"{time_patterns[0]}시간"
                return "duration_changed", f"✅ {new_duration}으로 변경하겠습니다!", new_duration
        
        # 카테고리 수정 요청인지 확인
        if any(word in user_input for word in ["바꿔", "수정", "변경", "번째를", "번을"]):
            if "category_recommendations" in session_info:
                success, message = self.parse_category_modification(user_input, session_info["category_recommendations"])
                if success:
                    return "category_modified", message
                else:
                    return "modification_failed", message
        
        # 장소 배치 수정 요청인지 확인  
        if any(word in user_input for word in ["지역", "장소", "곳", "번은", "로 하고", "에서"]):
            place_count = session_info.get("place_count", 3)
            if isinstance(place_count, str):
                import re
                numbers = re.findall(r'\d+', place_count)
                place_count = int(numbers[0]) if numbers else 3
            
            clustering_info = await self.location_processor.process_location_clustering(user_input, place_count)
            if clustering_info["valid"]:
                session_info["location_clustering"] = clustering_info
                return "location_clustering_set", clustering_info["message"]
            else:
                return "location_clustering_failed", clustering_info["message"]
        
        return "no_modification", "이해하지 못했어요. 구체적으로 무엇을 바꾸고 싶으신지 말씀해주세요."
    
    def get_or_create_memory(self, session_id: str) -> ConversationBufferMemory:
        """세션별 메모리 관리"""
        if session_id not in self.memory_sessions:
            self.memory_sessions[session_id] = ConversationBufferMemory()
        return self.memory_sessions[session_id]
    
    def extract_and_validate_profile(self, user_message: str, session_id: str) -> UserProfile:
        """사용자 메시지에서 프로필 추출 및 검증"""
        if not self.llm:
            # OpenAI API 키가 없는 경우 기본값 반환
            return UserProfile()
        
        # LLM으로 프로필 추출
        extracted = extract_profile_from_llm(self.llm, user_message)
        
        # 필수 키들로 프로필 구성
        profile_data = {}
        for k in REQUIRED_KEYS:
            profile_data[k] = extracted.get(k, "")
        
        # 검증 및 교정 (필요시)
        for k in REQUIRED_KEYS:
            if k == "address":
                continue
            if profile_data[k]:
                corrected = self.get_llm_corrected(session_id, k, profile_data[k])
                if corrected:
                    profile_data[k] = corrected
        
        return UserProfile(**profile_data)
    
    def extract_location_request(self, user_message: str, address_hint: Optional[str] = None) -> LocationRequest:
        """위치 요청 정보 추출"""
        if not self.llm:
            # 기본값 반환
            return LocationRequest(reference_areas=[address_hint] if address_hint else [])
        
        location_data = extract_location_request_from_llm(self.llm, user_message, address_hint)
        return self.safe_create_location_request(location_data, address_hint)
    
    async def _emergency_category_fallback(self, profile_data: Dict, place_count: int) -> list:
        """최종 emergency fallback - 기본 카테고리 생성"""
        from models.smart_models import CategoryRecommendation
        
        # 시간대 기반 최소한의 동적 선택
        time_slot = profile_data.get("time_slot", "저녁")
        
        if time_slot == "오전":
            base_categories = ["카페", "문화시설", "야외활동", "쇼핑"]
        elif time_slot == "오후":
            base_categories = ["카페", "음식점", "쇼핑", "문화시설"]
        elif time_slot == "저녁":
            base_categories = ["카페", "음식점", "문화시설", "술집"]
        else:  # 밤
            base_categories = ["술집", "카페", "엔터테인먼트", "휴식시설"]
        
        recommendations = []
        for i in range(place_count):
            category = base_categories[i % len(base_categories)]
            reason = f"{time_slot} 시간대에 적합한 {category} 추천"
            
            recommendations.append(CategoryRecommendation(
                sequence=i + 1,
                category=category,
                reason=reason,
                alternatives=["카페", "음식점"]
            ))
        
        print(f"[EMERGENCY_FALLBACK] 시간대({time_slot}) 기반 기본 추천 생성: {len(recommendations)}개")
        return recommendations
    
    async def _process_all_profile_fields_with_gpt(self, profile: 'UserProfile', user_input: str, session_info: dict, session_id: str) -> bool:
        """
        GPT가 사용자 입력을 분석해서 모든 프로필 필드를 자동으로 업데이트
        상용 급 완전 자동화 처리
        """
        print(f"[GPT_AUTO_UPDATE] 사용자 입력 분석 시작: '{user_input}'")
        
        # 모든 필드를 GPT가 체크할 대상 필드들
        target_fields = [
            "duration", "place_count", "address", "time_slot", "atmosphere", 
            "budget", "transportation", "car_owned", "relationship_stage",
            "general_preferences", "description"
        ]
        
        updated_fields = []
        
        # 각 필드를 GPT가 처리
        for field_name in target_fields:
            try:
                # 현재 값 가져오기
                current_value = getattr(profile, field_name, None)
                
                # GPT로 필드 처리
                result = await self.field_processor.process_field(field_name, user_input)
                
                if result["success"] and result["confidence"] >= 0.7:
                    new_value = result["value"]
                    
                    # 값이 실제로 변경된 경우만 업데이트
                    if current_value != new_value and new_value is not None:
                        setattr(profile, field_name, new_value)
                        updated_fields.append({
                            "field": field_name,
                            "old": current_value,
                            "new": new_value,
                            "confidence": result["confidence"]
                        })
                        print(f"[GPT_AUTO_UPDATE] {field_name}: '{current_value}' → '{new_value}' (신뢰도: {result['confidence']})")
                    
            except Exception as e:
                print(f"[ERROR] GPT 필드 처리 실패 - {field_name}: {e}")
                continue
        
        # 프로필 업데이트 저장
        if updated_fields:
            session_info['profile'] = profile
            SESSION_INFO[session_id] = session_info
            print(f"[GPT_AUTO_UPDATE] 완료 - {len(updated_fields)}개 필드 업데이트: {[f['field'] for f in updated_fields]}")
            return True
        else:
            print(f"[GPT_AUTO_UPDATE] 업데이트될 필드 없음")
            return False
    
    def safe_create_location_request(self, location_data: dict, address_hint: Optional[str] = None) -> LocationRequest:
        """안전한 LocationRequest 객체 생성"""
        return LocationRequest(
            proximity_type=location_data.get("proximity_type") or "near",
            reference_areas=location_data.get("reference_areas") or ([address_hint] if address_hint else []),
            place_count=location_data.get("place_count") or 3,
            proximity_preference=location_data.get("proximity_preference"),
            transportation=location_data.get("transportation") or "지하철"
        )
    
    def build_agent_requests(self, profile: UserProfile, location_request: LocationRequest, max_travel_time: int = 30, session_info: dict = None, session_id: str = None) -> tuple:
        """Place Agent와 RAG Agent 요청 JSON 생성 - 중복 호출 방지"""
        # session_info 데이터 보장
        if session_info is None and session_id:
            session_info = SESSION_INFO.get(session_id, {})
            print(f"[DEBUG] build_agent_requests - session_id {session_id}에서 session_info 획득")
        
        if session_info is None:
            session_info = {}
            print(f"⚠️ [CRITICAL] build_agent_requests - session_info가 여전히 None, 빈 딕셔너리 사용")
        
        # 🔥 CRITICAL: location_clustering 정보 검증 및 보장
        location_clustering = session_info.get('location_clustering')
        if not location_clustering:
            print(f"🚨 [CRITICAL ERROR] location_clustering이 session_info에 없음!")
            print(f"🚨 [CRITICAL ERROR] 사용자 지정 지역 정보가 Place Agent에 전달되지 않을 것임!")
            print(f"🚨 [CRITICAL ERROR] session_info keys: {list(session_info.keys())}")
        else:
            print(f"✅ [SUCCESS] location_clustering 정보 확인됨")
            print(f"✅ [SUCCESS] Strategy: {location_clustering.get('strategy', 'unknown')}")
            print(f"✅ [SUCCESS] Valid: {location_clustering.get('valid', False)}")
            print(f"✅ [SUCCESS] Groups: {len(location_clustering.get('groups', []))}개")
        
        # 디버깅: session_info 내용 확인
        print(f"[DEBUG] build_agent_requests - session_info keys: {list(session_info.keys())}")
        print(f"[DEBUG] build_agent_requests - location_clustering 존재: {bool(session_info.get('location_clustering'))}")
        if session_info.get('location_clustering'):
            print(f"[DEBUG] build_agent_requests - location_clustering 내용: {session_info['location_clustering']}")
        
        # 🔥 중복 호출 방지: Place Agent JSON 생성하지 않음
        # execute_recommendation_flow에서만 실제 Place Agent 호출하도록 수정
        print(f"[DEBUG] build_agent_requests - Place Agent 중복 호출 방지를 위해 JSON 생성 건너뜀")
        place_json = None
        
        # RAG Agent 요청도 마찬가지로 execute_recommendation_flow에서 처리
        rag_json = None
        
        return place_json, rag_json
    
    def _call_place_agent(self, profile, location_request, max_travel_time, session_info):
        """실제 Place Agent 호출"""
        import requests
        import os
        from core.agent_builders import build_place_agent_json
        
        try:
            PLACE_AGENT_URL = os.getenv("PLACE_AGENT_URL", "http://localhost:8002")
            
            # Place Agent 요청 생성
            place_request = build_place_agent_json(
                profile.model_dump(), 
                location_request.dict(), 
                max_travel_time,
                session_info
            )
            
            print(f"[DEBUG] _call_place_agent - Place Agent 호출: {PLACE_AGENT_URL}/place-agent")
            
            # 실제 Place Agent 호출
            place_response = requests.post(
                f"{PLACE_AGENT_URL}/place-agent",
                json=place_request,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if place_response.status_code != 200:
                print(f"[ERROR] _call_place_agent - Place Agent 호출 실패: HTTP {place_response.status_code}")
                return None
                
            place_result = place_response.json()
            print(f"[DEBUG] _call_place_agent - Place Agent 응답 성공")
            
            if not place_result.get("success"):
                print(f"[ERROR] _call_place_agent - Place Agent 처리 실패")
                return None
                
            return place_result
            
        except Exception as e:
            print(f"[ERROR] _call_place_agent - 호출 중 오류: {str(e)}")
            return None
    
    async def process_request(self, request: MainAgentRequest) -> MainAgentResponse:
        try:
            print(f"[DEBUG] MainAgentService.process_request 시작: {request.user_message[:50]}...")
            session_id = request.session_id or str(uuid.uuid4())
            memory = self.get_or_create_memory(session_id)
            memory.save_context(
                {"input": "사용자 요청"}, 
                {"output": request.user_message}
            )
            session_info = SESSION_INFO.get(session_id, {})
            if 'profile' not in session_info:
                session_info['profile'] = UserProfile()
            profile = session_info['profile']
            
            # 백엔드에서 받은 기존 유저 프로필 정보 적용
            if hasattr(request, 'user_profile') and request.user_profile:
                self._apply_existing_profile_data(profile, request.user_profile)
            
            # 새로운 스마트 컴포넌트 초기화
            from services.smart_exception_handler import SmartExceptionHandler
            from services.smart_category_recommender import SmartCategoryRecommender
            from core.intent_analyzer import IntentAnalyzer
            from core.gpt_field_processor import GPTFieldProcessor
            from services.gpt_location_processor import GPTLocationProcessor
            
            if not hasattr(self, 'exception_handler'):
                self.exception_handler = SmartExceptionHandler(self.openai_api_key)
            if not hasattr(self, 'category_recommender'):
                self.category_recommender = SmartCategoryRecommender(self.openai_api_key)
            if not hasattr(self, 'intent_analyzer'):
                self.intent_analyzer = IntentAnalyzer(self.openai_api_key)
            if not hasattr(self, 'field_processor'):
                self.field_processor = GPTFieldProcessor(self.openai_api_key)
            if not hasattr(self, 'location_processor'):
                self.location_processor = GPTLocationProcessor(self.openai_api_key)
            needs_optional_info_ask = session_info.get("_needs_optional_info_ask", False)
            optional_info_pending = session_info.get("_optional_info_pending", False)
            optional_idx = session_info.get("_optional_idx", 0)
            recommend_ready = session_info.get("_recommend_ready", False)
            is_first_message = session_info.get("_is_first_message", True)

            # 1. 첫 메시지(세션 시작)에는 LLM으로 전체 필수 정보 추출
            if is_first_message:
                print(f"[DEBUG] 첫 메시지 처리 시작, LLM 상태: {'설정됨' if self.llm else '미설정'}")
                if not self.llm:
                    print(f"[ERROR] LLM이 초기화되지 않음")
                    raise Exception("OpenAI API 키가 설정되지 않았거나 LLM 초기화에 실패했습니다.")
                
                print(f"[DEBUG] extract_profile_from_llm 호출 시작")
                extracted = extract_profile_from_llm(self.llm, request.user_message)
                print(f"[DEBUG] extract_profile_from_llm 완료: {extracted}")
                extracted = rule_based_gender_relationship(request.user_message, extracted)
                print(f"[DEBUG] rule_based_gender_relationship 완료: {extracted}")
                for k in REQUIRED_KEYS:
                    if extracted.get(k):
                        setattr(profile, k, extracted[k])
                
                # address 기본값 강제 설정 (사용자 입력 불필요)
                if not profile.address:
                    profile.address = "서울"
                
                # 위치 정보 추출 및 address 보완
                location_data = extract_location_request_from_llm(self.llm, request.user_message, address_hint=profile.address)
                if location_data.get("reference_areas"):
                    profile.address = location_data["reference_areas"][0]
                location_request = self.safe_create_location_request(location_data, profile.address)
                session_info["_is_first_message"] = False
                SESSION_INFO[session_id] = session_info
            else:
                # 2. 이후에는 키워드 기반(입력값 그대로 저장)
                # 필수 정보 중 누락된 필드만 하나씩 질문
                missing_fields = [k for k in REQUIRED_KEYS if not getattr(profile, k)]
                if missing_fields:
                    # 사용자가 입력한 값을 바로 저장
                    last_asked = session_info.get("_last_asked_field", None)
                    preference_confirmation_field = session_info.get("_preference_confirmation_field", None)
                    
                    if last_asked:
                        user_input = request.user_message.strip()
                        
                        # 선호도 재확인 응답 처리
                        if preference_confirmation_field and last_asked == preference_confirmation_field:
                            if user_input.lower() in ['같게', '그대로', '예', '네', 'yes', 'y']:
                                # 기존 값 유지 (이미 설정되어 있음)
                                pass
                            else:
                                # 새로운 값으로 업데이트
                                setattr(profile, last_asked, user_input)
                            session_info["_preference_confirmation_field"] = None
                        else:
                            # GPT 기반 필드 처리를 최우선으로 시도
                            try:
                                processing_result = await self.field_processor.process_field(last_asked, user_input)
                                
                                if processing_result["success"] and processing_result["confidence"] >= 0.6:
                                    # GPT 처리 성공
                                    setattr(profile, last_asked, processing_result["value"])
                                    print(f"[SUCCESS] GPT 필드 처리: {last_asked} = {user_input} → {processing_result['value']}")
                                    
                                    # 재시도 카운트 초기화
                                    if f"_retry_{last_asked}" in session_info:
                                        del session_info[f"_retry_{last_asked}"]
                                        
                                else:
                                    # GPT 신뢰도 낮음 - 의도 분석 후 예외 처리
                                    print(f"[LOW_CONFIDENCE] GPT 신뢰도 낮음: {processing_result.get('confidence', 0)}")
                                    
                                    conversation_history = [{"input": request.user_message}]
                                    intent_analysis = await self.intent_analyzer.analyze_user_intent(
                                        user_input, f"collecting_{last_asked}", conversation_history, last_asked
                                    )
                                    
                                    if intent_analysis.action == "exception_handling":
                                        # 스마트 예외 처리
                                        retry_count = session_info.get(f"_retry_{last_asked}", 0) + 1
                                        session_info[f"_retry_{last_asked}"] = retry_count
                                        
                                        smart_error_message = await self.exception_handler.handle_invalid_input(
                                            last_asked, user_input, retry_count, conversation_history
                                        )
                                        
                                        return MainAgentResponse(
                                            success=True,
                                            session_id=session_id,
                                            profile=profile,
                                            location_request=LocationRequest(reference_areas=[]),
                                            message=smart_error_message,
                                            needs_recommendation=False,
                                            suggestions=[]
                                        )
                                    else:
                                        # 정상 처리로 간주 - 기존 로직 사용
                                        if last_asked == "duration":
                                            normalized_duration = self._normalize_duration_input(user_input)
                                            setattr(profile, last_asked, normalized_duration)
                                        elif last_asked == "place_count":
                                            normalized_place_count = self._normalize_place_count_input(user_input)
                                            setattr(profile, last_asked, normalized_place_count)
                                        else:
                                            setattr(profile, last_asked, user_input)
                                        print(f"[FALLBACK] 기존 로직 사용: {last_asked} = {user_input}")
                                        
                                        # 재시도 카운트 초기화
                                        if f"_retry_{last_asked}" in session_info:
                                            del session_info[f"_retry_{last_asked}"]
                                        
                            except Exception as e:
                                print(f"[ERROR] GPT 필드 처리 완전 실패: {e}")
                                # 최종 폴백 - 기존 로직만 사용
                                if last_asked == "duration":
                                    normalized_duration = self._normalize_duration_input(user_input)
                                    setattr(profile, last_asked, normalized_duration)
                                elif last_asked == "place_count":
                                    normalized_place_count = self._normalize_place_count_input(user_input)
                                    setattr(profile, last_asked, normalized_place_count)
                                else:
                                    setattr(profile, last_asked, user_input)
                                print(f"[FINAL_FALLBACK] 기존 로직 사용: {last_asked} = {user_input}")
                        
                        session_info["_last_asked_field"] = None
                        SESSION_INFO[session_id] = session_info
                        # 다시 누락 필드 체크
                        missing_fields = [k for k in REQUIRED_KEYS if not getattr(profile, k)]
                    if missing_fields:
                        next_field = missing_fields[0]
                        
                        # 선호도 관련 필드는 재확인 질문
                        if self._should_ask_preference_confirmation(profile, next_field):
                            current_value = getattr(profile, next_field)
                            question = self._generate_preference_confirmation_question(next_field, str(current_value))
                            session_info["_preference_confirmation_field"] = next_field
                        else:
                            question = FIELD_QUESTION_DICT[next_field]
                        
                        session_info["_last_asked_field"] = next_field
                        SESSION_INFO[session_id] = session_info
                        return MainAgentResponse(
                            success=True,
                            session_id=session_id,
                            profile=profile,
                            location_request=LocationRequest(reference_areas=[]),
                            message=question,
                            needs_recommendation=False,
                            suggestions=missing_fields
                        )
                # 위치 정보는 null로 처리, 장소배치에서 구체적으로 설정
                location_data = extract_location_request_from_llm(self.llm, request.user_message, address_hint=profile.address)
                if not profile.address and location_data.get("reference_areas"):
                    profile.address = location_data["reference_areas"][0]
                
                # 위치 정보가 없어도 계속 진행 (장소배치에서 처리)
                location_request = self.safe_create_location_request(location_data, profile.address or "서울")

            # 3. 필수 정보가 모두 입력된 후, 스마트 추천 및 검증
            missing_fields = [k for k in REQUIRED_KEYS if not getattr(profile, k)]
            if missing_fields:
                # 누락 필드가 있으면 그 필드만 재질문(키워드 기반)
                next_field = missing_fields[0]
                
                # duration과 place_count가 모두 있으면 제약 조건 확인
                if next_field == "place_count" and profile.duration:
                    question = self._generate_smart_place_count_question(profile.duration)
                else:
                    question = FIELD_QUESTION_DICT[next_field]
                
                session_info["_last_asked_field"] = next_field
                SESSION_INFO[session_id] = session_info
                return MainAgentResponse(
                    success=True,
                    session_id=session_id,
                    profile=profile,
                    location_request=LocationRequest(reference_areas=[]),
                    message=question,
                    needs_recommendation=False,
                    suggestions=missing_fields
                )
            
            # 3.5. 시간-장소 개수 제약 검증
            if profile.duration and profile.place_count:
                valid, validation_message = self.validate_time_place_constraints(profile.duration, profile.place_count)
                if not valid:
                    # 제약 조건 위반 시 place_count 재설정
                    constraints = self.get_smart_recommendations_for_duration(profile.duration)
                    profile.place_count = str(constraints["recommended_places"])
                    session_info["profile"] = profile
                    SESSION_INFO[session_id] = session_info
                    return MainAgentResponse(
                        success=True,
                        session_id=session_id,
                        profile=profile,
                        location_request=LocationRequest(reference_areas=[]),
                        message=f"{validation_message}\n{constraints['recommended_places']}개로 조정했어요. 계속 진행하시겠어요? (예/아니오)",
                        needs_recommendation=False,
                        suggestions=[]
                    )

            # 4-1. 카테고리 선택 단계 (필수)
            if not session_info.get("_category_selected", False):
                if not session_info.get("_category_asked", False):
                    # 카테고리 추천 생성
                    import re
                    place_count = 3  # 기본값
                    if profile.place_count:
                        numbers = re.findall(r'\d+', str(profile.place_count))
                        if numbers:
                            place_count = int(numbers[0])
                    
                    # 동적 카테고리 추천 (IntelligentCategoryGenerator 사용)
                    try:
                        smart_recommendations = await self.generate_category_recommendations(
                            profile_data=profile.model_dump(),
                            place_count=place_count,
                            conversation_context=str(memory.buffer)
                        )
                    except ValueError as ve:
                        # 제약 위반 예외 처리 - 사용자에게 메시지 전달
                        if str(ve).startswith("CONSTRAINT_VIOLATION:"):
                            constraint_message = str(ve).replace("CONSTRAINT_VIOLATION:", "")
                            print(f"[ERROR] 동적 카테고리 추천 실패: {ve}")
                            return MainAgentResponse(
                                success=True,
                                session_id=session_id,
                                profile=profile,
                                location_request=location_request,
                                message=constraint_message,
                                needs_recommendation=False,
                                suggestions=["3개로 해주세요", "시간을 5시간으로 늘려주세요", "다시 추천해주세요"]
                            )
                        else:
                            print(f"[ERROR] 동적 카테고리 추천 실패: {ve}")
                            smart_recommendations = await self._emergency_category_fallback(profile.model_dump(), place_count)
                    except Exception as e:
                        print(f"[ERROR] 동적 카테고리 추천 실패: {e}")
                        smart_recommendations = await self._emergency_category_fallback(profile.model_dump(), place_count)
                    
                    session_info["category_recommendations"] = smart_recommendations
                    session_info["_category_asked"] = True
                    SESSION_INFO[session_id] = session_info
                    
                    message = self.format_smart_category_message(smart_recommendations, profile.duration, place_count)
                    return MainAgentResponse(
                        success=True,
                        session_id=session_id,
                        profile=profile,
                        location_request=location_request,
                        message=message,
                        needs_recommendation=False,
                        suggestions=["맞아요", "2번째를 쇼핑으로 바꿔줘", "1번을 카페로 해주세요"]
                    )
                else:
                    # 카테고리 수정 처리
                    user_input = request.user_message.strip()
                    if user_input.lower() in ['좋아요', '맞아요', '그렇게 해주세요', '예', '네', '좋습니다', '괜찮아요']:
                        session_info["_category_selected"] = True
                        SESSION_INFO[session_id] = session_info
                    else:
                        # 먼저 GPT가 전체 프로필 필드 업데이트 처리
                        updated = await self._process_all_profile_fields_with_gpt(profile, user_input, session_info, session_id)
                        
                        # 필드가 업데이트됐다면 제약 검증 다시 확인하고 카테고리 재생성
                        if updated:
                            import re
                            place_count = 3  # 기본값
                            if profile.place_count:
                                numbers = re.findall(r'\d+', str(profile.place_count))
                                if numbers:
                                    place_count = int(numbers[0])
                            
                            try:
                                # 업데이트된 프로필로 카테고리 재생성 시도
                                new_recommendations = await self.generate_category_recommendations(
                                    profile_data=profile.model_dump(),
                                    place_count=place_count,
                                    conversation_context=str(memory.buffer)
                                )
                                
                                # 성공하면 새로운 추천 제공
                                session_info["category_recommendations"] = new_recommendations
                                session_info["_category_asked"] = True
                                SESSION_INFO[session_id] = session_info
                                
                                message = self.format_smart_category_message(new_recommendations, profile.duration, place_count)
                                return MainAgentResponse(
                                    success=True,
                                    session_id=session_id,
                                    profile=profile,
                                    location_request=location_request,
                                    message=f"✅ 프로필 업데이트 완료!\n\n{message}",
                                    needs_recommendation=False,
                                    suggestions=["맞아요", "2번째를 쇼핑으로 바꿔줘", "1번을 카페로 해주세요"]
                                )
                                
                            except ValueError as ve:
                                # 여전히 제약 위반이면 사용자에게 알림
                                if str(ve).startswith("CONSTRAINT_VIOLATION:"):
                                    constraint_message = str(ve).replace("CONSTRAINT_VIOLATION:", "")
                                    return MainAgentResponse(
                                        success=True,
                                        session_id=session_id,
                                        profile=profile,
                                        location_request=location_request,
                                        message=constraint_message,
                                        needs_recommendation=False,
                                        suggestions=["3개로 해주세요", "시간을 더 늘려주세요", "다시 추천해주세요"]
                                    )
                            except Exception as e:
                                print(f"[ERROR] 프로필 업데이트 후 카테고리 재생성 실패: {e}")
                                # 에러 시 기본 카테고리 수정 로직으로 진행
                                pass
                        
                        # GPT 기반 카테고리 수정 처리
                        try:
                            current_recommendations = session_info.get("category_recommendations", [])
                            
                            # GPT 필드 프로세서로 수정 요청 처리
                            modification_result = await self.field_processor.process_modification_request(
                                "category", user_input, current_recommendations
                            )
                            
                            if modification_result.get("confidence", 0) >= 0.7:
                                # GPT 수정 처리 성공
                                print(f"[SUCCESS] GPT 카테고리 수정: {modification_result.get('understood_request')}")
                                
                                # 카테고리 수정 적용 - 이미 CategoryRecommendation 객체이므로 바로 사용
                                
                                smart_modification_result = await self.category_recommender.handle_category_modification(
                                    user_input, current_recommendations
                                )
                                
                                if smart_modification_result.get("action") != "error":
                                    # 스마트 수정 성공
                                    updated_recommendations = smart_modification_result.get("updated_recommendations", [])
                                    session_info["category_recommendations"] = updated_recommendations
                                    SESSION_INFO[session_id] = session_info
                                    
                                    # 수정된 추천을 보여주기
                                    smart_recs = []
                                    for rec in updated_recommendations:
                                        from models.smart_models import CategoryRecommendation
                                        smart_recs.append(CategoryRecommendation(**rec))
                                    
                                    import re
                                    place_count = 3
                                    if profile.place_count:
                                        if isinstance(profile.place_count, int):
                                            place_count = profile.place_count
                                        else:
                                            numbers = re.findall(r'\d+', str(profile.place_count))
                                            if numbers:
                                                place_count = int(numbers[0])
                                    
                                    updated_message = self.format_smart_category_message(smart_recs, profile.duration, place_count)
                                    return MainAgentResponse(
                                        success=True,
                                        session_id=session_id,
                                        profile=profile,
                                        location_request=location_request,
                                        message=f"✅ {modification_result.get('understood_request', '수정 완료')}\n\n{updated_message}",
                                        needs_recommendation=False,
                                        suggestions=["맞아요", "다른 걸로 또 바꿔주세요"]
                                    )
                                else:
                                    # 스마트 수정 실패 - 기본 로직으로 폴백
                                    print(f"[FALLBACK] 스마트 카테고리 수정 실패, 기본 로직 사용")
                                    fallback_result = await self.handle_user_modifications(user_input, session_info)
                                    modification_type = fallback_result[0]
                                    message = fallback_result[1]
                                    
                                    # 기본 로직 성공 시 처리
                                    if modification_type == "category_modified":
                                        # 수정된 카테고리로 다시 메시지 생성
                                        updated_recommendations = session_info.get("category_recommendations", [])
                                        import re
                                        place_count = 3  # 기본값
                                        if profile.place_count:
                                            numbers = re.findall(r'\d+', str(profile.place_count))
                                            if numbers:
                                                place_count = int(numbers[0])
                                        updated_message = self.format_category_recommendation_message(updated_recommendations, profile.duration, place_count)
                                        return MainAgentResponse(
                                            success=True,
                                            session_id=session_id,
                                            profile=profile,
                                            location_request=location_request,
                                            message=f"{message}\n\n{updated_message}",
                                            needs_recommendation=False,
                                            suggestions=["맞아요", "또 다른 변경사항이 있으시면 말씀해주세요"]
                                        )
                                    elif modification_type == "duration_changed":
                                        # 시간 변경 - 이미 위에서 처리됨
                                        new_duration = fallback_result[2] if len(fallback_result) > 2 else "4시간"
                                        profile.duration = new_duration
                                        return MainAgentResponse(
                                            success=True,
                                            session_id=session_id,
                                            profile=profile,
                                            location_request=location_request,
                                            message=f"{message}\n\n다시 카테고4리를 추천드립니다.",
                                            needs_recommendation=False,
                                            suggestions=["맞아요", "다른 시간으로 바꿔주세요"]
                                        )
                            else:
                                # GPT 이해 실패 - 기본 로직으로 폴백
                                print(f"[FALLBACK] GPT 카테고리 수정 이해 실패, 기본 로직 사용")
                                fallback_result = await self.handle_user_modifications(user_input, session_info)
                                modification_type = fallback_result[0]
                                message = fallback_result[1]
                                
                                # 기본 로직 성공 시 처리
                                if modification_type == "category_modified":
                                    # 수정된 카테고리로 다시 메시지 생성
                                    updated_recommendations = session_info.get("category_recommendations", [])
                                    import re
                                    place_count = 3  # 기본값
                                    if profile.place_count:
                                        numbers = re.findall(r'\d+', str(profile.place_count))
                                        if numbers:
                                            place_count = int(numbers[0])
                                    updated_message = self.format_category_recommendation_message(updated_recommendations, profile.duration, place_count)
                                    return MainAgentResponse(
                                        success=True,
                                        session_id=session_id,
                                        profile=profile,
                                        location_request=location_request,
                                        message=f"{message}\n\n{updated_message}",
                                        needs_recommendation=False,
                                        suggestions=["맞아요", "또 다른 변경사항이 있으시면 말씀해주세요"]
                                    )
                                elif modification_type == "duration_changed":
                                    # 시간 변경 - 이미 위에서 처리됨
                                    new_duration = fallback_result[2] if len(fallback_result) > 2 else "4시간"
                                    profile.duration = new_duration
                                    return MainAgentResponse(
                                        success=True,
                                        session_id=session_id,
                                        profile=profile,
                                        location_request=location_request,
                                        message=f"{message}\n\n다시 카테고4리를 추천드립니다.",
                                        needs_recommendation=False,
                                        suggestions=["맞아요", "다른 시간으로 바꿔주세요"]
                                    )
                                
                        except Exception as e:
                            print(f"[ERROR] GPT 카테고리 수정 실패, 기본 로직 사용: {e}")
                            # 기본 수정 로직으로 폴백
                            fallback_result = await self.handle_user_modifications(user_input, session_info)
                            modification_type = fallback_result[0]
                            message = fallback_result[1]
                            
                            # 기본 로직 성공 시 처리
                            if modification_type == "category_modified":
                                # 수정된 카테고리로 다시 메시지 생성
                                updated_recommendations = session_info.get("category_recommendations", [])
                                import re
                                place_count = 3  # 기본값
                                if profile.place_count:
                                    numbers = re.findall(r'\d+', str(profile.place_count))
                                    if numbers:
                                        place_count = int(numbers[0])
                                updated_message = self.format_category_recommendation_message(updated_recommendations, profile.duration, place_count)
                                return MainAgentResponse(
                                    success=True,
                                    session_id=session_id,
                                    profile=profile,
                                    location_request=location_request,
                                    message=f"{message}\n\n{updated_message}",
                                    needs_recommendation=False,
                                    suggestions=["맞아요", "또 다른 변경사항이 있으시면 말씀해주세요"]
                                )
                        
                        # 남은 fallback 로직 처리
                        if 'modification_type' in locals() and 'message' in locals():
                            if modification_type == "place_count_changed":
                                # 장소 개수 변경 - 새로운 카테고리 추천 생성
                                new_count = fallback_result[2] if len(fallback_result) > 2 else 3
                                profile.place_count = f"{new_count}개"
                                
                                # 새로운 카테고리 추천 생성 (동적)
                                profile_dict = profile.dict()
                                try:
                                    new_category_recommendations = await self.generate_category_recommendations(
                                        profile_data=profile_dict,
                                        place_count=new_count,
                                        conversation_context=request.user_message
                                    )
                                    session_info["category_recommendations"] = new_category_recommendations
                                    SESSION_INFO[session_id] = session_info
                                except ValueError as ve:
                                    # 제약 위반 예외 처리 - 사용자에게 메시지 전달
                                    if str(ve).startswith("CONSTRAINT_VIOLATION:"):
                                        constraint_message = str(ve).replace("CONSTRAINT_VIOLATION:", "")
                                        return MainAgentResponse(
                                            success=True,
                                            session_id=session_id,
                                            profile=profile,
                                            location_request=location_request,
                                            message=constraint_message,
                                            needs_recommendation=False,
                                            suggestions=["3개로 해주세요", "시간을 5시간으로 늘려주세요", "다시 추천해주세요"]
                                        )
                                    else:
                                        # 다른 ValueError - emergency fallback 사용
                                        new_category_recommendations = await self._emergency_category_fallback(profile_dict, new_count)
                                        session_info["category_recommendations"] = new_category_recommendations
                                        SESSION_INFO[session_id] = session_info
                                except Exception as e:
                                    # 다른 예외 - emergency fallback 사용
                                    new_category_recommendations = await self._emergency_category_fallback(profile_dict, new_count)
                                    session_info["category_recommendations"] = new_category_recommendations
                                    SESSION_INFO[session_id] = session_info
                                
                                new_message = self.format_category_recommendation_message(new_category_recommendations, profile.duration, new_count)
                                return MainAgentResponse(
                                    success=True,
                                    session_id=session_id,
                                    profile=profile,
                                    location_request=location_request,
                                    message=f"{message}\n\n{new_message}",
                                    needs_recommendation=False,
                                    suggestions=["맞아요", "다른 개수로 바꿔주세요"]
                                )
                            elif modification_type == "duration_changed":
                                # 시간 변경 - 새로운 시간으로 카테고리 재생성
                                new_duration = fallback_result[2] if len(fallback_result) > 2 else "4시간"
                                profile.duration = new_duration
                                
                                # 장소 개수 파싱
                                import re
                                place_count = 3  # 기본값
                                if profile.place_count:
                                    numbers = re.findall(r'\d+', str(profile.place_count))
                                    if numbers:
                                        place_count = int(numbers[0])
                                
                                # 새로운 카테고리 추천 생성 (동적)
                                profile_dict = profile.dict()
                                try:
                                    new_category_recommendations = await self.generate_category_recommendations(
                                        profile_data=profile_dict,
                                        place_count=place_count,
                                        conversation_context=request.user_message
                                    )
                                    session_info["category_recommendations"] = new_category_recommendations
                                    SESSION_INFO[session_id] = session_info
                                    
                                    new_message = self.format_category_recommendation_message(new_category_recommendations, profile.duration, place_count)
                                    return MainAgentResponse(
                                        success=True,
                                        session_id=session_id,
                                        profile=profile,
                                        location_request=location_request,
                                        message=f"{message}\n\n{new_message}",
                                        needs_recommendation=False,
                                        suggestions=["맞아요", "다른 시간으로 바꿔주세요"]
                                    )
                                except ValueError as ve:
                                    # 제약 위반 예외 처리 - 사용자에게 메시지 전달
                                    if str(ve).startswith("CONSTRAINT_VIOLATION:"):
                                        constraint_message = str(ve).replace("CONSTRAINT_VIOLATION:", "")
                                        return MainAgentResponse(
                                            success=True,
                                            session_id=session_id,
                                            profile=profile,
                                            location_request=location_request,
                                            message=constraint_message,
                                            needs_recommendation=False,
                                            suggestions=["3개로 해주세요", "시간을 6시간으로 늘려주세요", "다시 추천해주세요"]
                                        )
                                    else:
                                        # 다른 ValueError - emergency fallback 사용
                                        new_category_recommendations = await self._emergency_category_fallback(profile_dict, place_count)
                                        session_info["category_recommendations"] = new_category_recommendations
                                        SESSION_INFO[session_id] = session_info
                                        
                                        new_message = self.format_category_recommendation_message(new_category_recommendations, profile.duration, place_count)
                                        return MainAgentResponse(
                                            success=True,
                                            session_id=session_id,
                                            profile=profile,
                                            location_request=location_request,
                                            message=f"{message}\n\n{new_message}",
                                            needs_recommendation=False,
                                            suggestions=["맞아요", "다른 시간으로 바꿔주세요"]
                                        )
                                except Exception as e:
                                    # 다른 예외 - emergency fallback 사용
                                    new_category_recommendations = await self._emergency_category_fallback(profile_dict, place_count)
                                    session_info["category_recommendations"] = new_category_recommendations
                                    SESSION_INFO[session_id] = session_info
                                    
                                    new_message = self.format_category_recommendation_message(new_category_recommendations, profile.duration, place_count)
                                    return MainAgentResponse(
                                        success=True,
                                        session_id=session_id,
                                        profile=profile,
                                        location_request=location_request,
                                        message=f"{message}\n\n{new_message}",
                                        needs_recommendation=False,
                                        suggestions=["맞아요", "다른 시간으로 바꿔주세요"]
                                    )
                            elif modification_type == "category_modified":
                                # 이미 위에서 처리됨
                                pass
                            else:
                                return MainAgentResponse(
                                    success=True,
                                    session_id=session_id,
                                    profile=profile,
                                    location_request=location_request,
                                    message=message if 'message' in locals() else "이해하지 못했어요. 다시 말씀해주세요.",
                                    needs_recommendation=False,
                                    suggestions=["맞아요", "2번째를 쇼핑으로 바꿔줘", "2개만 하고 싶어"]
                                )
                        else:
                            # 모든 처리가 실패한 경우
                            return MainAgentResponse(
                                success=True,
                                session_id=session_id,
                                profile=profile,
                                location_request=location_request,
                                message="이해하지 못했어요. 다시 말씀해주세요.",
                                needs_recommendation=False,
                                suggestions=["맞아요", "2번째를 쇼핑으로 바꿔줘", "2개만 하고 싶어"]
                            )

            # 4-2. 지역 배치 선택 단계 (필수)
            if not session_info.get("_location_clustering_selected", False):
                if not session_info.get("_location_clustering_asked", False):
                    # 지역 배치 질문
                    import re
                    place_count = 3  # 기본값
                    if profile.place_count:
                        numbers = re.findall(r'\d+', str(profile.place_count))
                        if numbers:
                            place_count = int(numbers[0])
                    
                    session_info["_location_clustering_asked"] = True
                    SESSION_INFO[session_id] = session_info
                    
                    message = f"🗺️ 이제 장소 배치를 정해볼까요?\n\n{place_count}개의 장소를 어떻게 배치하시겠어요?\n\n" \
                             f"예시:\n" \
                             f"• '1,2번은 이촌동으로 하고 3번은 이태원으로 해주세요'\n" \
                             f"• '모두 같은 지역으로 해주세요'\n" \
                             f"• '모두 다른 지역으로 해주세요'"
                    
                    return MainAgentResponse(
                        success=True,
                        session_id=session_id,
                        profile=profile,
                        location_request=location_request,
                        message=message,
                        needs_recommendation=False,
                        suggestions=["모두 같은 지역으로", "모두 다른 지역으로", "1,2번은 홍대로"]
                    )
                else:
                    # GPT 기반 지역 배치 처리
                    user_input = request.user_message.strip()
                    import re
                    place_count = 3  # 기본값
                    if profile.place_count:
                        if isinstance(profile.place_count, int):
                            place_count = profile.place_count
                        else:
                            numbers = re.findall(r'\d+', str(profile.place_count))
                            if numbers:
                                place_count = int(numbers[0])
                    
                    try:
                        # GPT가 직접 장소 배치 JSON 생성
                        from services.gpt_location_processor import GPTLocationProcessor
                        if not hasattr(self, 'location_processor'):
                            self.location_processor = GPTLocationProcessor(self.openai_api_key)
                        
                        clustering_info = await self.location_processor.process_location_clustering(user_input, place_count)
                        
                        if clustering_info["valid"]:
                            session_info["location_clustering"] = clustering_info
                            session_info["_location_clustering_selected"] = True
                            SESSION_INFO[session_id] = session_info
                            
                            # 최종 확인 메시지
                            category_recommendations = session_info.get("category_recommendations", [])
                            # 데이터 타입 검증 및 변환
                            from utils.data_validator import CategoryDataValidator
                            validated_recommendations = CategoryDataValidator.ensure_category_recommendations(category_recommendations)
                            confirmation_message = self.format_location_clustering_confirmation(clustering_info, validated_recommendations, profile)
                            
                            return MainAgentResponse(
                                success=True,
                                session_id=session_id,
                                profile=profile,
                                location_request=location_request,
                                message=confirmation_message,
                                needs_recommendation=False,
                                suggestions=["맞아요", "추천 시작해주세요"]
                            )
                        else:
                            # GPT 이해 실패 - 기본 로직
                            print(f"[FALLBACK] GPT 지역 배치 이해 실패, 기본 로직 사용")
                            clustering_info = await self.parse_location_clustering_request(user_input, place_count)
                            
                            if clustering_info["valid"]:
                                session_info["location_clustering"] = clustering_info
                                session_info["_location_clustering_selected"] = True
                                SESSION_INFO[session_id] = session_info
                                
                                category_recommendations = session_info.get("category_recommendations", [])
                                # 데이터 타입 검증 및 변환
                                from utils.data_validator import CategoryDataValidator
                                validated_recommendations = CategoryDataValidator.ensure_category_recommendations(category_recommendations)
                                confirmation_message = self.format_location_clustering_confirmation(clustering_info, validated_recommendations, profile)
                                
                                return MainAgentResponse(
                                    success=True,
                                    session_id=session_id,
                                    profile=profile,
                                    location_request=location_request,
                                    message=confirmation_message,
                                    needs_recommendation=False,
                                    suggestions=["맞아요", "추천 시작해주세요"]
                                )
                            else:
                                return MainAgentResponse(
                                    success=True,
                                    session_id=session_id,
                                    profile=profile,
                                    location_request=location_request,
                                    message=clustering_info["message"],
                                    needs_recommendation=False,
                                    suggestions=["모두 같은 지역으로", "1,2번은 홍대로"]
                                )
                    except Exception as e:
                        print(f"[ERROR] GPT 지역 배치 처리 실패: {e}")
                        # 완전 폴백 - 기존 로직
                        clustering_info = await self.parse_location_clustering_request(user_input, place_count)
                        
                        if clustering_info["valid"]:
                            session_info["location_clustering"] = clustering_info
                            session_info["_location_clustering_selected"] = True
                            SESSION_INFO[session_id] = session_info
                            
                            category_recommendations = session_info.get("category_recommendations", [])
                            # 데이터 타입 검증 및 변환
                            from utils.data_validator import CategoryDataValidator
                            validated_recommendations = CategoryDataValidator.ensure_category_recommendations(category_recommendations)
                            confirmation_message = self.format_location_clustering_confirmation(clustering_info, validated_recommendations, profile)
                            
                            return MainAgentResponse(
                                success=True,
                                session_id=session_id,
                                profile=profile,
                                location_request=location_request,
                                message=confirmation_message,
                                needs_recommendation=False,
                                suggestions=["맞아요", "추천 시작해주세요"]
                            )
                        else:
                            return MainAgentResponse(
                                success=True,
                                session_id=session_id,
                                profile=profile,
                                location_request=location_request,
                                message=clustering_info["message"],
                                needs_recommendation=False,
                                suggestions=["모두 같은 지역으로", "1,2번은 홍대로"]
                            )

            # 4-3. 최종 확인 후 추가 정보로 진행
            if not session_info.get("_final_confirmation", False):
                user_input = request.user_message.strip()
                if user_input.lower() in ['추천 시작해주세요', '시작', '바로 추천']:
                    # 추가 정보 스킵하고 바로 추천
                    session_info["_final_confirmation"] = True
                    session_info["_needs_optional_info_ask"] = True
                    session_info["_skip_optional"] = True
                    SESSION_INFO[session_id] = session_info
                elif user_input.lower() in ['맞아요', '좋아요', '예', '네']:
                    # 추가 정보 질문으로 진행
                    session_info["_final_confirmation"] = True
                    SESSION_INFO[session_id] = session_info
                else:
                    return MainAgentResponse(
                        success=True,
                        session_id=session_id,
                        profile=profile,
                        location_request=location_request,
                        message="최종 확인이 필요해요.\n• '맞아요' - 추가 정보 입력 후 추천\n• '추천 시작해주세요' - 바로 추천 시작",
                        needs_recommendation=False,
                        suggestions=["맞아요", "추천 시작해주세요"]
                    )

            # 5. 부가 정보 입력 의사 질문
            if not needs_optional_info_ask and OPTIONAL_FIELDS and not session_info.get("_skip_optional", False):
                session_info["_needs_optional_info_ask"] = True
                SESSION_INFO[session_id] = session_info
                return MainAgentResponse(
                    success=True,
                    session_id=session_id,
                    profile=profile,
                    location_request=location_request,
                    message="추가 정보(차량 보유, 교통수단, 개인 취향 등)를 입력하시겠습니까? (예/아니오)",
                    needs_recommendation=False,
                    suggestions=[]
                )

            # 5. 부가 정보 입력 분기 및 실제 입력(키워드 기반)
            if needs_optional_info_ask and not optional_info_pending:
                user_reply = request.user_message.strip().lower()
                if user_reply in ["예", "yes", "y"]:
                    session_info["_optional_info_pending"] = True
                    session_info["_optional_idx"] = 0
                    SESSION_INFO[session_id] = session_info
                    key, question = OPTIONAL_FIELDS[0]
                    return MainAgentResponse(
                        success=True,
                        session_id=session_id,
                        profile=profile,
                        location_request=location_request,
                        message=question,
                        needs_recommendation=False,
                        suggestions=[]
                    )
                elif user_reply in ["아니오", "no", "n"]:
                    session_info["_optional_info_pending"] = False
                    session_info["_optional_idx"] = 0
                    session_info["_needs_save_confirmation"] = True
                    SESSION_INFO[session_id] = session_info
                else:
                    SESSION_INFO[session_id] = session_info
                    return MainAgentResponse(
                        success=True,
                        session_id=session_id,
                        profile=profile,
                        location_request=location_request,
                        message="'예' 또는 '아니오'로 답변해 주세요. 추가 정보(차량 보유, 교통수단, 개인 취향 등)를 입력하시겠습니까? (예/아니오)",
                        needs_recommendation=False,
                        suggestions=[]
                    )

            if optional_info_pending:
                idx = session_info.get("_optional_idx", 0)
                if idx < len(OPTIONAL_FIELDS):
                    key, question = OPTIONAL_FIELDS[idx]
                    answer = request.user_message.strip()
                    if not answer:
                        session_info["_optional_idx"] = idx + 1
                        SESSION_INFO[session_id] = session_info
                        if idx + 1 < len(OPTIONAL_FIELDS):
                            next_key, next_question = OPTIONAL_FIELDS[idx + 1]
                            return MainAgentResponse(
                                success=True,
                                session_id=session_id,
                                profile=profile,
                                location_request=location_request,
                                message=next_question,
                                needs_recommendation=False,
                                suggestions=[]
                            )
                        else:
                            session_info["_optional_info_pending"] = False
                            session_info["_optional_idx"] = 0
                            SESSION_INFO[session_id] = session_info
                    else:
                        # GPT 기반 부가 정보 처리
                        try:
                            processing_result = await self.field_processor.process_field(key, answer)
                            
                            if processing_result["success"] and processing_result["confidence"] >= 0.6:
                                # GPT 처리 성공
                                setattr(profile, key, processing_result["value"])
                                print(f"[SUCCESS] GPT 부가 정보 처리: {key} = {answer} → {processing_result['value']}")
                            else:
                                # GPT 처리 실패 - 기존 로직으로 폴백
                                if key == "general_preferences":
                                    setattr(profile, key, [x.strip() for x in answer.split(",") if x.strip()])
                                elif key == "car_owned":
                                    setattr(profile, key, answer in ["예", "yes", "Yes", "Y", "y", "true", "True"])
                                elif key == "place_count":
                                    if isinstance(answer, int):
                                        setattr(profile, key, answer)
                                    elif isinstance(answer, str) and answer.isdigit():
                                        setattr(profile, key, int(answer))
                                    else:
                                        setattr(profile, key, 3)
                                elif key == "transportation":
                                    setattr(profile, key, answer.strip())
                                else:
                                    setattr(profile, key, answer)
                                print(f"[FALLBACK] 기존 로직 사용: {key} = {answer}")
                        except Exception as e:
                            print(f"[ERROR] GPT 부가 정보 처리 실패: {e}")
                            # 완전 폴백 - 기존 로직
                            if key == "general_preferences":
                                setattr(profile, key, [x.strip() for x in answer.split(",") if x.strip()])
                            elif key == "car_owned":
                                setattr(profile, key, answer in ["예", "yes", "Yes", "Y", "y", "true", "True"])
                            elif key == "place_count":
                                if isinstance(answer, int):
                                    setattr(profile, key, answer)
                                elif isinstance(answer, str) and answer.isdigit():
                                    setattr(profile, key, int(answer))
                                else:
                                    setattr(profile, key, 3)
                            elif key == "transportation":
                                setattr(profile, key, answer.strip())
                            else:
                                setattr(profile, key, answer)
                        session_info["_optional_idx"] = idx + 1
                        SESSION_INFO[session_id] = session_info
                        if idx + 1 < len(OPTIONAL_FIELDS):
                            next_key, next_question = OPTIONAL_FIELDS[idx + 1]
                            return MainAgentResponse(
                                success=True,
                                session_id=session_id,
                                profile=profile,
                                location_request=location_request,
                                message=next_question,
                                needs_recommendation=False,
                                suggestions=[]
                            )
                        else:
                            session_info["_optional_info_pending"] = False
                            session_info["_optional_idx"] = 0
                            session_info["_needs_save_confirmation"] = True
                            SESSION_INFO[session_id] = session_info
                else:
                    session_info["_optional_info_pending"] = False
                    session_info["_optional_idx"] = 0
                    session_info["_needs_save_confirmation"] = True
                    SESSION_INFO[session_id] = session_info
            
            # 5.5. 프로필 저장 여부 확인
            needs_save_confirmation = session_info.get("_needs_save_confirmation", False)
            if needs_save_confirmation:
                user_reply = request.user_message.strip().lower()
                if user_reply in ["예", "yes", "y", "저장", "네", "좋아요"]:
                    session_info["_save_profile"] = True
                    session_info["_needs_save_confirmation"] = False
                    SESSION_INFO[session_id] = session_info
                elif user_reply in ["아니오", "no", "n", "안함", "저장안함", "괜찮아요"]:
                    session_info["_save_profile"] = False
                    session_info["_needs_save_confirmation"] = False
                    SESSION_INFO[session_id] = session_info
                else:
                    # 처음 물어보거나 잘못된 답변인 경우
                    if not session_info.get("_asked_save_confirmation", False):
                        session_info["_asked_save_confirmation"] = True
                        SESSION_INFO[session_id] = session_info
                        return MainAgentResponse(
                            success=True,
                            session_id=session_id,
                            profile=profile,
                            location_request=location_request,
                            message="💾 이번에 입력해주신 정보를 프로필에 저장하시겠어요?\n\n✅ 저장하시면 다음에 더 빠르게 추천받을 수 있어요!\n\n'예' 또는 '아니오'로 답변해 주세요.",
                            needs_recommendation=False,
                            suggestions=["예", "아니오"]
                        )
                    else:
                        # 잘못된 답변
                        return MainAgentResponse(
                            success=True,
                            session_id=session_id,
                            profile=profile,
                            location_request=location_request,
                            message="'예' 또는 '아니오'로 답변해 주세요.\n\n💾 이번에 입력해주신 정보를 프로필에 저장하시겠어요?",
                            needs_recommendation=False,
                            suggestions=["예", "아니오"]
                        )


            # 6. 추천 바로 실행
            place_agent_request, rag_agent_request = self.build_agent_requests(
                profile, location_request, request.max_travel_time, session_info, session_id
            )
            
            # 저장 여부 정보 가져오기
            save_profile = session_info.get("_save_profile", False)
            
            return MainAgentResponse(
                success=True,
                session_id=session_id,
                profile=profile,
                location_request=location_request,
                place_agent_request=place_agent_request,
                rag_agent_request=rag_agent_request,
                message="추천이 완료되었습니다!",
                needs_recommendation=True,
                suggestions=[],
                save_profile=save_profile
            )
        except Exception as e:
            print(f"[ERROR] MainAgentService.process_request 전체 오류: {e}")
            import traceback
            traceback.print_exc()
            
            return MainAgentResponse(
                success=False,
                session_id=request.session_id or str(uuid.uuid4()),
                profile=UserProfile(),
                location_request=LocationRequest(reference_areas=[]),
                error=str(e),
                message=f"시스템 처리 중 일시적인 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
                needs_recommendation=False,
                suggestions=["다시 시도하기", "새로 시작하기", "이전 단계로"]
            )
    
    def get_session_memory(self, session_id: str) -> Optional[str]:
        """세션 메모리 내용 반환"""
        if session_id in self.memory_sessions:
            return self.memory_sessions[session_id].buffer
        return None
    
    def clear_session(self, session_id: str) -> bool:
        """세션 메모리 삭제"""
        if session_id in self.memory_sessions:
            del self.memory_sessions[session_id]
            return True
        return False
    
    def _apply_existing_profile_data(self, profile: UserProfile, existing_data):
        """백엔드에서 받은 기존 유저 프로필 데이터를 현재 프로필에 적용"""
        try:
            if existing_data is None:
                print(f"[DEBUG] existing_data가 None입니다.")
                return
                
            print(f"[DEBUG] existing_data 원본: {existing_data}")
            print(f"[DEBUG] existing_data 타입: {type(existing_data)}")
                
            # Dict, Pydantic 모델 등 다양한 타입 처리
            if isinstance(existing_data, dict):
                existing_dict = existing_data
            elif hasattr(existing_data, 'dict'):
                existing_dict = existing_data.dict()
            elif hasattr(existing_data, '__dict__'):
                existing_dict = existing_data.__dict__
            else:
                print(f"[DEBUG] existing_data 타입을 처리할 수 없습니다: {type(existing_data)}")
                return
            
            print(f"[DEBUG] 처리된 existing_dict: {existing_dict}")
            
            for key, value in existing_dict.items():
                print(f"[DEBUG] 필드 확인: {key} = {value}, hasattr={hasattr(profile, key)}")
                if value is not None and value != "" and value != []:
                    if hasattr(profile, key):
                        setattr(profile, key, value)
                        print(f"[DEBUG] 기존 프로필 데이터 적용: {key} = {value}")
                    else:
                        print(f"[DEBUG] 프로필에 없는 필드: {key}")
                        
        except Exception as e:
            print(f"[ERROR] 기존 프로필 데이터 적용 중 오류: {e}")
    
    def _should_ask_preference_confirmation(self, profile: UserProfile, field_name: str) -> bool:
        """선호도 관련 필드에 대해 재확인이 필요한지 판단"""
        preference_fields = ["general_preferences", "atmosphere", "budget", "description"]
        value = getattr(profile, field_name, None)
        # 빈 문자열이나 None이면 재확인하지 않음
        return field_name in preference_fields and value is not None and value != "" and value != []
    
    def _generate_preference_confirmation_question(self, field_name: str, current_value: str) -> str:
        """선호도 재확인 질문 생성"""
        field_labels = {
            "general_preferences": "선호하는 요소",
            "atmosphere": "원하는 분위기", 
            "budget": "예산",
            "description": "자기소개"
        }
        
        label = field_labels.get(field_name, field_name)
        return f"💭 이전에 {label}를 '{current_value}'로 설정하셨는데, 이번에도 같게 하시겠어요? 아니면 다르게 하시겠어요?\n\n✅ 같게 하려면 '같게' 또는 '그대로'\n🔄 다르게 하려면 새로운 내용을 입력해 주세요!"