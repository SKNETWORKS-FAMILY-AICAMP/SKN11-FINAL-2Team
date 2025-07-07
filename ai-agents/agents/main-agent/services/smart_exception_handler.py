from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
import json
from typing import Dict, List, Any

class SmartExceptionHandler:
    def __init__(self, openai_api_key: str):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3, openai_api_key=openai_api_key)
        self.field_descriptions = {
            "age": "나이 (숫자)",
            "gender": "성별 (남/여)",
            "mbti": "MBTI 유형 (4글자)",
            "address": "지역/동네명",
            "relationship_stage": "관계 (연인/썸/친구)",
            "atmosphere": "선호 분위기",
            "budget": "예산",
            "time_slot": "시간대 (오전/오후/저녁)",
            "duration": "데이트 시간",
            "place_count": "방문 장소 수"
        }

    async def handle_invalid_input(self, field: str, user_input: str,
                                  retry_count: int, conversation_history: List[Dict]) -> str:
        """스마트 예외 처리"""

        field_desc = self.field_descriptions.get(field, field)

        if retry_count == 1:
            # 첫 번째 실패: 간단한 재질문
            prompt = f"""
            사용자가 {field_desc} 정보를 "{user_input}"라고 입력했습니다.
            
            간단하고 친절하게 올바른 형식으로 다시 입력해달라고 요청해주세요.
            예시 한 개만 들어주세요. 2줄 이내로 짧게 답변해주세요.
            """
        elif retry_count == 2:
            # 두 번째 실패: 기본값 제안
            prompt = f"""
            사용자가 {field_desc} 정보 입력을 어려워하고 있습니다.
            
            기본값을 제안하거나 이 정보를 생략하고 진행할 수 있다고 간단히 안내해주세요.
            1줄로 짧게 답변해주세요.
            """
        else:
            # 세 번째 이상: 생략하고 진행
            prompt = f"""
            사용자가 {field_desc} 정보 입력을 계속 어려워하고 있습니다.
            
            이 정보를 생략하고 다음 단계로 진행한다고 간단히 안내해주세요.
            1줄로 짧게 답변해주세요.
            """

        result = await self.llm.ainvoke([HumanMessage(content=prompt)])
        return result.content