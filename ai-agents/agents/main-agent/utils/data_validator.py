"""데이터 검증 및 타입 변환 유틸리티"""

from typing import List, Dict, Any, Union
from models.smart_models import CategoryRecommendation

class CategoryDataValidator:
    """카테고리 추천 데이터 검증 및 변환"""
    
    @staticmethod
    def ensure_category_recommendations(data: Union[List[Dict], List[CategoryRecommendation]]) -> List[CategoryRecommendation]:
        """카테고리 추천 데이터를 CategoryRecommendation 객체 리스트로 변환"""
        if not data:
            return []
        
        validated_recommendations = []
        
        for item in data:
            if isinstance(item, CategoryRecommendation):
                # 이미 올바른 객체
                validated_recommendations.append(item)
            elif isinstance(item, dict):
                # 딕셔너리를 객체로 변환
                try:
                    # primary 필드가 있으면 category로 변환
                    if "primary" in item and "category" not in item:
                        item["category"] = item.pop("primary")
                    
                    # 필수 필드 검증
                    if "category" not in item:
                        item["category"] = "카페"  # 기본값
                    if "sequence" not in item:
                        item["sequence"] = 1  # 기본값
                    if "reason" not in item:
                        item["reason"] = "기본 추천"  # 기본값
                    if "alternatives" not in item:
                        item["alternatives"] = []  # 기본값
                    
                    recommendation = CategoryRecommendation(**item)
                    validated_recommendations.append(recommendation)
                except Exception as e:
                    print(f"[WARNING] 잘못된 카테고리 데이터 스킵: {item}, 에러: {e}")
                    continue
            else:
                print(f"[WARNING] 알 수 없는 카테고리 데이터 타입: {type(item)}")
                continue
        
        return validated_recommendations
    
    @staticmethod
    def validate_session_info(session_info: Dict[str, Any]) -> Dict[str, Any]:
        """session_info의 category_recommendations를 검증하고 정리"""
        if "category_recommendations" in session_info:
            session_info["category_recommendations"] = CategoryDataValidator.ensure_category_recommendations(
                session_info["category_recommendations"]
            )
        
        return session_info
    
    @staticmethod
    def extract_categories_for_place_agent(recommendations: List[CategoryRecommendation]) -> List[str]:
        """Place Agent용 카테고리 리스트 추출 (None 값 방지)"""
        if not recommendations:
            return []
        
        categories = []
        for rec in recommendations:
            if hasattr(rec, 'category') and rec.category:
                categories.append(rec.category)
            else:
                categories.append("카페")  # 기본값
        
        return categories