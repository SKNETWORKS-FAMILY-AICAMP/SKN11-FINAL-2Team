# 입력 데이터 검증기
# - JSON 스키마 검증
# - 필수 필드 확인
# - 데이터 타입 검증

from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from loguru import logger

class DataValidator:
    """입력 데이터 검증 클래스"""
    
    @staticmethod
    def validate_request_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        메인 에이전트로부터 받은 요청 데이터 검증
        
        Args:
            data: 검증할 요청 데이터
            
        Returns:
            검증된 데이터
            
        Raises:
            ValidationError: 데이터가 유효하지 않은 경우
        """
        logger.info("🔍 요청 데이터 검증 시작")
        
        try:
            # 최상위 필수 필드 검증
            required_fields = [
                'request_id', 'timestamp', 'search_targets', 
                'user_context', 'course_planning'
            ]
            
            DataValidator._validate_required_fields(data, required_fields, "root")
            
            # search_targets 검증
            DataValidator._validate_search_targets(data['search_targets'])
            
            # user_context 검증
            DataValidator._validate_user_context(data['user_context'])
            
            # course_planning 검증
            DataValidator._validate_course_planning(data['course_planning'])
            
            logger.info("✅ 요청 데이터 검증 완료")
            return data
            
        except Exception as e:
            logger.error(f"❌ 요청 데이터 검증 실패: {e}")
            raise ValueError(f"데이터 검증 실패: {str(e)}")
    
    @staticmethod
    def _validate_required_fields(data: Dict[str, Any], required_fields: List[str], context: str):
        """필수 필드 존재 여부 검증"""
        for field in required_fields:
            if field not in data:
                raise ValueError(f"{context}에 필수 필드 '{field}'가 없습니다.")
    
    @staticmethod
    def _validate_search_targets(search_targets: List[Dict[str, Any]]):
        """search_targets 배열 검증"""
        if not isinstance(search_targets, list):
            raise ValueError("search_targets는 배열이어야 합니다.")
        
        if len(search_targets) == 0:
            raise ValueError("search_targets는 최소 1개 이상의 항목을 포함해야 합니다.")
        
        if len(search_targets) > 10:  # 최대 10개로 제한
            raise ValueError("search_targets는 최대 10개까지만 허용됩니다.")
        
        # 각 search_target 검증
        for i, target in enumerate(search_targets):
            DataValidator._validate_search_target(target, i)
    
    @staticmethod
    def _validate_search_target(target: Dict[str, Any], index: int):
        """개별 search_target 검증"""
        required_fields = ['sequence', 'category', 'location', 'semantic_query']
        DataValidator._validate_required_fields(target, required_fields, f"search_targets[{index}]")
        
        # sequence 검증
        if not isinstance(target['sequence'], int) or target['sequence'] < 1:
            raise ValueError(f"search_targets[{index}].sequence는 1 이상의 정수여야 합니다.")
        
        # category 검증
        allowed_categories = ['음식점', '술집', '문화시설', '휴식시설', '야외활동', '카페', '쇼핑', '엔터테인먼트']
        if target['category'] not in allowed_categories:
            raise ValueError(
                f"search_targets[{index}].category는 다음 중 하나여야 합니다: {allowed_categories}"
            )
        
        # location 검증
        DataValidator._validate_location(target['location'], f"search_targets[{index}].location")
        
        # semantic_query 검증
        if not isinstance(target['semantic_query'], str) or len(target['semantic_query'].strip()) == 0:
            raise ValueError(f"search_targets[{index}].semantic_query는 비어있지 않은 문자열이어야 합니다.")
        
        if len(target['semantic_query']) > 500:  # 최대 길이 제한
            raise ValueError(f"search_targets[{index}].semantic_query는 500자 이하여야 합니다.")
    
    @staticmethod
    def _validate_location(location: Dict[str, Any], context: str):
        """위치 정보 검증"""
        required_fields = ['area_name', 'coordinates']
        DataValidator._validate_required_fields(location, required_fields, context)
        
        # coordinates 검증
        coords = location['coordinates']
        coord_fields = ['latitude', 'longitude']
        DataValidator._validate_required_fields(coords, coord_fields, f"{context}.coordinates")
        
        # 위도/경도 값 검증
        lat = coords['latitude']
        lon = coords['longitude']
        
        if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
            raise ValueError(f"{context}.coordinates의 위도/경도는 숫자여야 합니다.")
        
        if not DataValidator.validate_coordinates(lat, lon):
            raise ValueError(f"{context}.coordinates의 위도/경도 값이 유효하지 않습니다.")
    
    @staticmethod
    def _validate_user_context(user_context: Dict[str, Any]):
        """user_context 검증"""
        required_fields = ['demographics', 'preferences', 'requirements']
        DataValidator._validate_required_fields(user_context, required_fields, "user_context")
        
        # demographics 검증
        demographics = user_context['demographics']
        demo_fields = ['age', 'relationship_stage']
        DataValidator._validate_required_fields(demographics, demo_fields, "user_context.demographics")
        
        # age 검증
        age = demographics['age']
        if not isinstance(age, int) or age < 15 or age > 100:
            raise ValueError("user_context.demographics.age는 15-100 사이의 정수여야 합니다.")
        
        # preferences 검증
        preferences = user_context['preferences']
        if not isinstance(preferences, list):
            raise ValueError("user_context.preferences는 배열이어야 합니다.")
        
        # requirements 검증
        requirements = user_context['requirements']
        req_fields = ['time_preference', 'party_size', 'transportation']
        DataValidator._validate_required_fields(requirements, req_fields, "user_context.requirements")
        
        # party_size 검증
        party_size = requirements['party_size']
        if not isinstance(party_size, int) or party_size < 1 or party_size > 20:
            raise ValueError("user_context.requirements.party_size는 1-20 사이의 정수여야 합니다.")
    
    @staticmethod
    def _validate_course_planning(course_planning: Dict[str, Any]):
        """course_planning 검증"""
        required_fields = ['optimization_goals', 'route_constraints']
        DataValidator._validate_required_fields(course_planning, required_fields, "course_planning")
        
        # optimization_goals 검증
        goals = course_planning['optimization_goals']
        if not isinstance(goals, list):
            raise ValueError("course_planning.optimization_goals는 배열이어야 합니다.")
        
        # route_constraints 검증
        constraints = course_planning['route_constraints']
        constraint_fields = ['max_travel_time_between', 'total_course_duration']
        DataValidator._validate_required_fields(constraints, constraint_fields, "course_planning.route_constraints")
        
        # 시간 제약 검증
        max_travel = constraints['max_travel_time_between']
        total_duration = constraints['total_course_duration']
        
        if not isinstance(max_travel, (int, float)) or max_travel <= 0:
            raise ValueError("course_planning.route_constraints.max_travel_time_between은 양수여야 합니다.")
        
        if not isinstance(total_duration, (int, float)) or total_duration <= 0:
            raise ValueError("course_planning.route_constraints.total_course_duration은 양수여야 합니다.")
        
        # sequence_optimization 검증 및 boolean 변환
        if 'sequence_optimization' in course_planning:
            seq_opt = course_planning['sequence_optimization']
            seq_opt_fields = ['allow_reordering', 'prioritize_given_sequence']
            DataValidator._validate_required_fields(seq_opt, seq_opt_fields, "course_planning.sequence_optimization")
            
            # boolean 변환 처리
            for field in seq_opt_fields:
                value = seq_opt[field]
                if isinstance(value, str):
                    seq_opt[field] = value.lower() in ('true', '1', 'yes', 'on')
                elif not isinstance(value, bool):
                    seq_opt[field] = bool(value)
    
    @staticmethod
    def validate_coordinates(lat: float, lon: float) -> bool:
        """위도/경도 유효성 검증"""
        return -90 <= lat <= 90 and -180 <= lon <= 180
    
    @staticmethod
    def validate_place_data(place: Dict[str, Any]) -> bool:
        """장소 데이터 유효성 검증"""
        try:
            required_fields = ['place_id', 'place_name', 'latitude', 'longitude', 'description', 'category']
            DataValidator._validate_required_fields(place, required_fields, "place_data")
            
            # 위도/경도 검증
            if not DataValidator.validate_coordinates(place['latitude'], place['longitude']):
                return False
            
            # 카테고리 검증
            allowed_categories = ['음식점', '술집', '문화시설', '휴식시설', '야외활동', '카페', '쇼핑', '엔터테인먼트']
            if place['category'] not in allowed_categories:
                return False
            
            return True
            
        except Exception:
            return False
    
    @staticmethod
    def sanitize_text(text: str) -> str:
        """텍스트 정제 (특수문자 제거, 길이 제한 등)"""
        if not isinstance(text, str):
            return ""
        
        # 양쪽 공백 제거
        text = text.strip()
        
        # 연속된 공백을 하나로 변경
        import re
        text = re.sub(r'\s+', ' ', text)
        
        # 최대 길이 제한 (1000자)
        if len(text) > 1000:
            text = text[:1000]
        
        return text
    
    @staticmethod
    def validate_weather_condition(weather: str) -> bool:
        """날씨 조건 검증"""
        allowed_weather = ['맑음', '비', 'sunny', 'rainy']
        return weather in allowed_weather
    
    @staticmethod
    def validate_search_attempt(attempt: str) -> bool:
        """검색 시도 단계 검증"""
        allowed_attempts = ['1차', '2차', '3차', 'first', 'second', 'third']
        return attempt in allowed_attempts

# 편의 함수들
def validate_request(data: Dict[str, Any]) -> Dict[str, Any]:
    """요청 데이터 검증 편의 함수"""
    return DataValidator.validate_request_data(data)

def is_valid_coordinates(lat: float, lon: float) -> bool:
    """위도/경도 유효성 검증 편의 함수"""
    return DataValidator.validate_coordinates(lat, lon)

def is_valid_place(place: Dict[str, Any]) -> bool:
    """장소 데이터 유효성 검증 편의 함수"""
    return DataValidator.validate_place_data(place)

if __name__ == "__main__":
    # 테스트 실행
    test_data = {
        "request_id": "test-001",
        "timestamp": "2025-06-30T15:30:00Z",
        "search_targets": [
            {
                "sequence": 1,
                "category": "음식점",
                "location": {
                    "area_name": "홍대",
                    "coordinates": {"latitude": 37.5519, "longitude": 126.9245}
                },
                "semantic_query": "홍대에서 커플이 가기 좋은 로맨틱한 파인다이닝 레스토랑"
            }
        ],
        "user_context": {
            "demographics": {"age": 28, "relationship_stage": "연인"},
            "preferences": ["로맨틱한 분위기", "저녁 데이트"],
            "requirements": {
                "time_preference": "저녁",
                "party_size": 2,
                "transportation": "대중교통"
            }
        },
        "course_planning": {
            "optimization_goals": ["로맨틱한 저녁 데이트 경험 극대화"],
            "route_constraints": {
                "max_travel_time_between": 30,
                "total_course_duration": 300
            }
        }
    }
    
    try:
        validated = DataValidator.validate_request_data(test_data)
        print("✅ 데이터 검증 테스트 성공")
    except ValueError as e:
        print(f"❌ 데이터 검증 테스트 실패: {e}")
