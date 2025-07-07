from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
import json
from typing import Dict, Any, List, Optional
from models.smart_models import IntentAnalysis

class IntentAnalyzer:
    def __init__(self, openai_api_key: str):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, openai_api_key=openai_api_key)

    async def analyze_user_intent(self, user_input: str, current_stage: str,
                                  conversation_history: List[Dict],
                                  expected_field: Optional[str] = None) -> IntentAnalysis:
        """사용자 의도 분석"""

        prompt = f"""
        현재 단계: {current_stage}
        기대하는 정보: {expected_field}
        사용자 입력: "{user_input}"
        최근 대화: {conversation_history[-3:]}

        사용자의 의도를 분석해주세요:
        1. normal_flow: 정상적인 정보 제공
        2. exception_handling: 잘못된 입력이나 이해 부족
        3. modification_request: 이전 선택사항 수정 요청

        JSON 형식으로 응답:
        {{
            "action": "normal_flow|exception_handling|modification_request",
            "field": "{expected_field}",
            "confidence": 0.8,
            "next_action": "구체적인 다음 행동",
            "context_understanding": {{
                "user_seems_confused": false,
                "wants_to_change_previous": false,
                "providing_valid_info": true
            }}
        }}
        """

        result = await self.llm.ainvoke([HumanMessage(content=prompt)])
        try:
            data = json.loads(result.content)
            return IntentAnalysis(**data)
        except:
            return IntentAnalysis(
                action="exception_handling",
                field=expected_field,
                confidence=0.3,
                next_action="재질문 필요",
                context_understanding={}
            )