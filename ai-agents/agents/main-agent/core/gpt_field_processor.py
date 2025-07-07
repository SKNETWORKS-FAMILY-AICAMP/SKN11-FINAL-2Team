from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
import json
from typing import Dict, Any, Optional, Union
import re

class GPTFieldProcessor:
    def __init__(self, openai_api_key: str):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, openai_api_key=openai_api_key)
        
        # 필드별 처리 규칙 정의
        self.field_specs = {
            "age": {
                "output_type": "int",
                "valid_range": (1, 100),
                "examples": ["25", "30", "스물다섯", "20대 중반", "서른"],
                "description": "나이를 숫자로 변환"
            },
            "gender": {
                "output_type": "string",
                "valid_values": ["남", "여"],
                "examples": ["남자", "여자", "남성", "여성", "male", "female"],
                "description": "성별을 남/여로 정규화"
            },
            "mbti": {
                "output_type": "string",
                "pattern": r"^[EINS][NSFT][FT][JP]$",
                "examples": ["enfp", "ENFP", "엔프피", "외향적"],
                "description": "MBTI를 4글자 대문자로 정규화"
            },
            "duration": {
                "output_type": "string",
                "flexible_validation": True,
                "pattern": r"^\d+시간$|^반나절$|^하루종일$",
                "examples": ["4", "네시간", "4시간", "5시간", "7시간", "시간을 5시간으로 늘려주세요", "시간을 6시간으로", "5시간으로 해주세요", "반나절정도", "하루", "종일"],
                "description": "데이트 시간을 표준 형식으로 변환, 모든 시간 범위 자동 처리"
            },
            "place_count": {
                "output_type": "int",
                "valid_range": (1, 5),
                "examples": ["3개", "세개", "3곳", "3", "세 곳", "3개로 해주세요", "3개로 바꿔주세요", "개수를 3개로", "장소 3개"],
                "description": "장소 개수를 숫자로 변환"
            },
            "address": {
                "output_type": "string",
                "preserve_stations": True,
                "examples": ["홍대입구역", "용산역", "홍익대 근처", "강남 쪽"],
                "description": "지역명을 정확히 보존하되 모호한 표현만 정규화"
            },
            "relationship_stage": {
                "output_type": "string",
                "valid_values": ["연인", "썸", "친구", "소개팅"],
                "examples": ["남친", "여친", "애인", "커플", "친구사이", "썸타는사이"],
                "description": "관계를 표준 카테고리로 분류"
            },
            "atmosphere": {
                "output_type": "string",
                "examples": ["아늑한", "활기찬", "로맨틱", "조용한", "북적북적한"],
                "description": "분위기를 명확한 형용사로 정규화"
            },
            "budget": {
                "output_type": "string",
                "examples": ["5만원", "십만원", "10만원", "적당히", "많이"],
                "description": "예산을 구체적인 금액으로 변환"
            },
            "time_slot": {
                "output_type": "string",
                "valid_values": ["오전", "오후", "저녁", "밤"],
                "examples": ["아침", "점심", "낮", "밤", "새벽"],
                "description": "시간대를 표준 구간으로 분류"
            },
            "car_owned": {
                "output_type": "bool",
                "examples": ["예", "네", "있어요", "소유", "아니오", "없어요", "없음"],
                "description": "차량 소유 여부를 true/false로 변환"
            },
            "transportation": {
                "output_type": "string",
                "valid_values": ["지하철", "버스", "자가용", "택시", "도보", "자전거"],
                "examples": ["지하철", "전철", "버스", "차", "자동차", "걸어서", "택시"],
                "description": "교통수단을 표준 명칭으로 정규화"
            },
            "general_preferences": {
                "output_type": "list",
                "examples": ["조용한 곳, 야외, 디저트", "카페, 산책, 영화", "맛집 투어"],
                "description": "선호사항을 리스트로 변환"
            },
            "description": {
                "output_type": "string",
                "examples": ["영화 좋아하는 20대", "조용한 성격", "활발한 편"],
                "description": "자기소개를 자연스럽게 정리"
            }
        }

    async def process_field(self, field_name: str, user_input: str) -> Dict[str, Any]:
        """
        필드별 사용자 입력을 GPT로 처리하여 정규화된 값 반환
        
        Returns:
            {
                "success": bool,
                "value": Any,  # 정규화된 값
                "original": str,  # 원본 입력
                "confidence": float,  # 신뢰도
                "error_message": str  # 실패 시 오류 메시지
            }
        """
        if field_name not in self.field_specs:
            return {
                "success": False,
                "value": None,
                "original": user_input,
                "confidence": 0.0,
                "error_message": f"지원하지 않는 필드입니다: {field_name}"
            }

        spec = self.field_specs[field_name]
        
        prompt = self._build_processing_prompt(field_name, user_input, spec)
        
        try:
            print(f"[GPT_PROCESSOR] 필드 처리 시작 - {field_name}: '{user_input}'")
            
            # GPT 호출 (재시도 로직 포함)
            max_retries = 2
            for attempt in range(max_retries + 1):
                try:
                    result = await self.llm.ainvoke([HumanMessage(content=prompt)])
                    print(f"[GPT_PROCESSOR] GPT 응답 (시도 {attempt + 1}): {result.content[:200]}...")
                    
                    # JSON 추출 및 정제
                    json_content = self._extract_json_from_response(result.content)
                    
                    # JSON 파싱
                    response_data = json.loads(json_content)
                    
                    # 필수 필드 검증
                    if "value" not in response_data or "confidence" not in response_data:
                        raise ValueError(f"GPT 응답에 필수 필드 누락: {response_data}")
                    
                    # 신뢰도 검증
                    confidence = float(response_data["confidence"])
                    if not (0.0 <= confidence <= 1.0):
                        print(f"[WARNING] 신뢰도 범위 오류, 0.5로 조정: {confidence}")
                        confidence = 0.5
                    
                    # 타입 변환 및 검증
                    processed_value = self._validate_and_convert(response_data.get("value"), spec)
                    
                    print(f"[GPT_PROCESSOR] 처리 성공 - {field_name}: '{user_input}' → '{processed_value}' (신뢰도: {confidence})")
                    
                    return {
                        "success": True,
                        "value": processed_value,
                        "original": user_input,
                        "confidence": confidence,
                        "error_message": None
                    }
                    
                except json.JSONDecodeError as e:
                    print(f"[ERROR] JSON 파싱 실패 (시도 {attempt + 1}): {e}")
                    if attempt == max_retries:
                        raise
                    continue
                except Exception as e:
                    print(f"[ERROR] GPT 처리 실패 (시도 {attempt + 1}): {e}")
                    if attempt == max_retries:
                        raise
                    continue
            
        except Exception as e:
            print(f"[ERROR] GPT 필드 처리 최종 실패 - {field_name}: '{user_input}' - {str(e)}")
            return {
                "success": False,
                "value": None,
                "original": user_input,
                "confidence": 0.0,
                "error_message": f"필드 처리 실패: {str(e)}"
            }

    def _build_processing_prompt(self, field_name: str, user_input: str, spec: Dict) -> str:
        """필드별 GPT 프롬프트 생성"""
        
        prompt = f"""
사용자가 {field_name} 정보로 "{user_input}"라고 입력했습니다.

필드 설명: {spec['description']}
출력 타입: {spec['output_type']}

"""
        
        # 필드별 특별 규칙 추가
        if field_name == "address":
            prompt += """
중요한 규칙:
1. 역명(예: 홍대입구역, 용산역, 강남역)은 절대 변경하지 마세요
2. "홍대입구역" → "홍대입구역" (그대로)
3. "용산역" → "용산역" (그대로) 
4. "홍익대 근처", "홍대 쪽" → "홍대" (동네명으로 변환)
5. "강남 어디든" → "강남" (동네명으로 변환)
"""
        
        if "valid_values" in spec:
            prompt += f"가능한 값: {spec['valid_values']}\n"
        
        if "valid_range" in spec:
            prompt += f"유효 범위: {spec['valid_range'][0]} ~ {spec['valid_range'][1]}\n"
        
        if "pattern" in spec:
            prompt += f"형식: {spec['pattern']}\n"
        
        prompt += f"""
예시 입력들: {spec['examples']}

반드시 다음 JSON 형식으로만 응답해주세요. 코드 블록이나 다른 텍스트 없이 순수 JSON만:

{{
    "value": "정규화된 값",
    "confidence": 0.9,
    "reasoning": "변환 이유"
}}

중요사항:
- 변환할 수 없는 입력이면 confidence를 0.3 이하로 설정
- ```json 같은 코드 블록 사용 금지
- value는 반드시 지정된 output_type에 맞는 값으로 설정
"""
        
        return prompt

    def _validate_and_convert(self, value: Any, spec: Dict) -> Any:
        """타입 변환 및 검증"""
        
        if value is None:
            return None
            
        output_type = spec.get("output_type", "string")
        
        try:
            if output_type == "int":
                converted = int(value) if isinstance(value, str) and value.isdigit() else int(value)
                
                # 범위 체크
                if "valid_range" in spec:
                    min_val, max_val = spec["valid_range"]
                    if not (min_val <= converted <= max_val):
                        raise ValueError(f"값이 유효 범위를 벗어남: {converted}")
                
                return converted
                
            elif output_type == "string":
                converted = str(value).strip()
                
                # 유연한 검증 모드 확인
                if spec.get("flexible_validation", False):
                    # 패턴만 체크하고 valid_values는 무시
                    if "pattern" in spec:
                        if not re.match(spec["pattern"], converted):
                            raise ValueError(f"패턴에 맞지 않음: {converted}")
                else:
                    # 기존 엄격한 검증
                    if "valid_values" in spec:
                        if converted not in spec["valid_values"]:
                            raise ValueError(f"유효하지 않은 값: {converted}")
                    
                    if "pattern" in spec:
                        if not re.match(spec["pattern"], converted):
                            raise ValueError(f"패턴에 맞지 않음: {converted}")
                
                return converted
                
            elif output_type == "bool":
                if isinstance(value, bool):
                    return value
                elif isinstance(value, str):
                    value_lower = value.lower().strip()
                    if value_lower in ["true", "yes", "예", "네", "있어요", "소유", "맞아요", "y"]:
                        return True
                    elif value_lower in ["false", "no", "아니오", "없어요", "없음", "아니", "n"]:
                        return False
                    else:
                        raise ValueError(f"불리언 값으로 변환할 수 없음: {value}")
                else:
                    return bool(value)
                    
            elif output_type == "list":
                if isinstance(value, list):
                    return value
                elif isinstance(value, str):
                    # 쉼표로 구분된 문자열을 리스트로 변환
                    return [item.strip() for item in value.split(",") if item.strip()]
                else:
                    return [str(value)]
                
            else:
                return value
                
        except (ValueError, TypeError) as e:
            raise ValueError(f"타입 변환 실패: {str(e)}")

    def _extract_json_from_response(self, response_content: str) -> str:
        """GPT 응답에서 JSON 부분만 추출"""
        import re
        
        # 코드 블록 제거 (```json ... ``` 또는 ``` ... ```)
        if "```json" in response_content:
            # ```json과 ```사이의 내용 추출
            match = re.search(r'```json\s*(.*?)\s*```', response_content, re.DOTALL)
            if match:
                return match.group(1).strip()
        elif "```" in response_content:
            # ```과 ```사이의 내용 추출
            match = re.search(r'```\s*(.*?)\s*```', response_content, re.DOTALL)
            if match:
                return match.group(1).strip()
        
        # JSON 객체 직접 추출 시도
        # { ... } 패턴 찾기
        brace_count = 0
        start_idx = -1
        
        for i, char in enumerate(response_content):
            if char == '{':
                if start_idx == -1:
                    start_idx = i
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0 and start_idx != -1:
                    # 완전한 JSON 객체 발견
                    return response_content[start_idx:i+1]
        
        # 그냥 전체 응답 반환 (마지막 시도)
        return response_content.strip()

    async def process_modification_request(self, field_name: str, user_request: str, current_value: Any) -> Dict[str, Any]:
        """
        필드 수정 요청을 자연어로 처리
        예: "첫번째를 카페로 바꿔줘", "2번을 다른걸로"
        """
        
        prompt = f"""
사용자가 {field_name} 필드의 현재 값 "{current_value}"에 대해 
"{user_request}"라고 수정 요청했습니다.

사용자가 무엇을 원하는지 파악하고 수정사항을 JSON으로 응답해주세요:

{{
    "action": "modify|replace|add|remove",
    "target": "수정 대상",
    "new_value": "새로운 값",
    "understood_request": "요청 이해 내용",
    "confidence": 0.9
}}

이해할 수 없는 요청이면 confidence를 0.3 이하로 설정하세요.
"""
        
        try:
            result = await self.llm.ainvoke([HumanMessage(content=prompt)])
            json_content = self._extract_json_from_response(result.content)
            return json.loads(json_content)
        except Exception as e:
            print(f"[ERROR] 수정 요청 처리 실패: {e}")
            return {
                "action": "error",
                "confidence": 0.0,
                "understood_request": "요청을 이해할 수 없습니다"
            }