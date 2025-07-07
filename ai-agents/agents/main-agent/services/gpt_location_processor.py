"""GPT 기반 장소 배치 처리 서비스"""

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
import json
from typing import Dict, Any

class GPTLocationProcessor:
    def __init__(self, openai_api_key: str):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, openai_api_key=openai_api_key)
    
    async def process_location_clustering(self, user_input: str, place_count: int) -> Dict[str, Any]:
        """GPT가 장소 배치 요청을 JSON으로 직접 처리"""
        
        prompt = f"""
        당신은 데이트 코스 장소 배치 전문가입니다.
        사용자의 요청을 분석하여 정해진 JSON 스키마에 맞게 장소 배치 정보를 작성해주세요.

        === 사용자 요청 ===
        "{user_input}"
        
        === 전체 장소 개수 ===
        {place_count}개
        
        === 출력 JSON 스키마 ===
        {{
            "groups": [
                {{
                    "places": [1, 2],
                    "location": "이촌동"
                }},
                {{
                    "places": [3],
                    "location": "이태원"
                }}
            ],
            "strategy": "user_defined",
            "valid": true,
            "message": "✅ 1,2번째 장소: 이촌동, 3번째 장소: 이태원"
        }}
        
        === 처리 규칙 ===
        1. places: 해당 지역에 배치될 장소 번호들 (1부터 {place_count}까지)
        2. location: 구체적인 지역명 (예: "홍대", "강남", "이태원" 등)
        3. strategy: "user_defined" 고정
        4. valid: 성공적으로 파싱되었으면 true
        5. message: 사용자에게 보여줄 확인 메시지
        
        === 특수 케이스 처리 ===
        - "모두 같은 지역": groups에 모든 장소를 하나의 그룹으로
        - "모두 다른 지역": 각 장소를 별도 그룹으로 (지역명은 "다른 지역"으로)
        - 구체적 지역 지정: 사용자가 명시한 대로 그룹 분할
        
        중요: 코드 블록(```) 없이 순수 JSON만 반환하세요.
        """
        
        try:
            result = await self.llm.ainvoke([HumanMessage(content=prompt)])
            print(f"[GPT_LOCATION] GPT 원본 응답: {result.content}")
            
            # JSON 추출 및 정제
            json_content = self._extract_json_from_response(result.content)
            data = json.loads(json_content)
            
            # 데이터 검증
            if not data.get("groups") or not isinstance(data["groups"], list):
                raise ValueError("Invalid groups format")
            
            # 모든 장소 번호가 포함되었는지 확인
            all_places = set()
            for group in data["groups"]:
                all_places.update(group.get("places", []))
            
            expected_places = set(range(1, place_count + 1))
            if all_places != expected_places:
                print(f"[WARNING] 장소 번호 불일치: 예상={expected_places}, 실제={all_places}")
            
            print(f"[GPT_LOCATION] 장소 배치 처리 성공: {len(data['groups'])}개 그룹")
            return data
            
        except Exception as e:
            print(f"[ERROR] GPT 장소 배치 처리 실패: {e}")
            print(f"[ERROR] GPT 응답: {result.content if 'result' in locals() else 'API 호출 실패'}")
            
            # 실패 시 기본 응답
            return {
                "groups": [],
                "strategy": "user_defined",
                "valid": False,
                "message": f"❌ 요청을 이해하지 못했습니다. 다시 말씀해주세요.\n\n💡 예시: '1,2번은 홍대로 하고 3번은 강남으로 해주세요'"
            }
    
    def _extract_json_from_response(self, response_content: str) -> str:
        """GPT 응답에서 JSON 부분만 추출"""
        response_content = response_content.strip()
        
        # 코드 블록 제거
        if response_content.startswith("```"):
            lines = response_content.split('\n')
            response_content = '\n'.join(lines[1:-1])
        
        # JSON 시작/끝 찾기
        start_idx = response_content.find('{')
        if start_idx == -1:
            raise ValueError("JSON 시작 부분을 찾을 수 없습니다")
        
        # 중괄호 균형 맞추기
        brace_count = 0
        for i, char in enumerate(response_content[start_idx:], start_idx):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    return response_content[start_idx:i+1]
        
        return response_content.strip()