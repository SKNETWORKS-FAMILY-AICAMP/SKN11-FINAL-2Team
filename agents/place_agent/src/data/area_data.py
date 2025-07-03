# 서울 지역 데이터
# - 지역별 좌표, 특성, 추천 매핑 데이터

from typing import Dict, List

# 서울 지역 중심 좌표 및 특성 데이터
AREA_CENTERS = {
    "홍대": {
        "lat": 37.5563, "lng": 126.9233,
        "signature_traits": ["젊은문화중심지", "자유로운예술가", "라이브음악"],
        "vibe": "자유롭고 창의적인",
        "keywords": ["클럽", "라이브 음악", "길거리 공연", "독특한 카페"]
    },
    "강남": {
        "lat": 37.4982, "lng": 127.0274,
        "signature_traits": ["세련된비즈니스가", "고급엔터테인먼트", "모던라이프스타일"],
        "vibe": "세련되고 모던한",
        "keywords": ["고급 레스토랑", "루프탑바", "쇼핑몰", "스타일리시한 카페"]
    },
    "강남역": {
        "lat": 37.4982, "lng": 127.0274,
        "signature_traits": ["교통허브중심", "지하상가", "만남의장소"],
        "vibe": "바쁘고 활기찬",
        "keywords": ["지하상가", "교통중심", "쇼핑", "만남의 장소"]
    },
    "이태원": {
        "lat": 37.5344, "lng": 126.9947,
        "signature_traits": ["이국적분위기", "글로벌다이닝", "루프탑뷰"],
        "vibe": "글로벌하고 이색적인",
        "keywords": ["다국적 음식", "이국적 분위기", "펜션카페", "루프탑 테라스"]
    },
    "성수": {
        "lat": 37.5447, "lng": 127.0557,
        "signature_traits": ["힙스터감성공간", "인더스트리얼카페", "아트갤러리"],
        "vibe": "힙하고 트렌디한",
        "keywords": ["인더스트리얼 카페", "갤러리", "공장 개조", "감성적인 공간"]
    },
    "연남": {
        "lat": 37.5589, "lng": 126.9239,
        "signature_traits": ["아늑한골목길", "감성브런치", "조용한데이트"],
        "vibe": "아늑하고 감성적인",
        "keywords": ["골목 카페", "아기자기한 상점", "감성 브런치", "조용한 분위기"]
    },
    "신촌": {
        "lat": 37.5596, "lng": 126.9422,
        "signature_traits": ["대학가활력", "젊은에너지", "친근한분위기"],
        "vibe": "활기차고 친근한",
        "keywords": ["저렴한 맛집", "학생 카페", "노래방", "활기찬 거리"]
    },
    "명동": {
        "lat": 37.5636, "lng": 126.9826,
        "signature_traits": ["전통현대조화", "관광명소", "쇼핑중심지"],
        "vibe": "전통적이면서 현대적인",
        "keywords": ["전통 찻집", "한옥 카페", "쇼핑", "관광 명소"]
    },
    "인사동": {
        "lat": 37.5717, "lng": 126.9857,
        "signature_traits": ["한국문화중심", "전통예술", "고즈넉한분위기"],
        "vibe": "고즈넉하고 문화적인",
        "keywords": ["전통차", "갤러리", "공예품", "한국 문화"]
    },
    "압구정": {
        "lat": 37.5270, "lng": 127.0276,
        "signature_traits": ["고급쇼핑문화", "럭셔리라이프", "프리미엄경험"],
        "vibe": "고급스럽고 우아한",
        "keywords": ["럭셔리 카페", "프리미엄 브런치", "디자이너 브랜드", "고급 베이커리"]
    },
    "건대": {
        "lat": 37.5403, "lng": 127.0695,
        "signature_traits": ["학생친화적공간", "24시간활력", "합리적선택"],
        "vibe": "역동적이고 친근한",
        "keywords": ["24시간 카페", "스터디 카페", "합리적 가격", "학생 친화적"]
    },
    "여의도": {
        "lat": 37.5219, "lng": 126.9245,
        "signature_traits": ["비즈니스금융중심", "한강뷰", "야경명소"],
        "vibe": "현대적이고 세련된",
        "keywords": ["한강공원", "고층빌딩", "금융가", "야경명소"]
    },
    "잠실": {
        "lat": 37.5134, "lng": 127.1000,
        "signature_traits": ["대형복합문화공간", "엔터테인먼트", "편의시설완비"],
        "vibe": "활기차고 편리한",
        "keywords": ["롯데월드", "쇼핑몰", "스카이타워", "복합문화공간"]
    },
    "고대": {
        "lat": 37.5895, "lng": 127.0323,
        "signature_traits": ["젊은학구적분위기", "대학가문화", "청춘에너지"],
        "vibe": "젊고 학구적인",
        "keywords": ["대학가", "학생문화", "저렴한식당", "스터디카페"]
    }
}

# MBTI별 선호 지역 매핑
MBTI_PREFERENCES = {
    "E": ["홍대", "강남", "신촌", "건대"],  # 외향형
    "I": ["연남", "성수", "인사동", "압구정"],  # 내향형
    "N": ["성수", "홍대", "이태원", "연남"],  # 직관형
    "S": ["명동", "인사동", "압구정", "강남"],  # 감각형
    "T": ["강남", "압구정", "성수"],  # 사고형
    "F": ["연남", "홍대", "인사동"],  # 감정형
    "J": ["압구정", "명동", "인사동"],  # 판단형
    "P": ["홍대", "성수", "이태원"]   # 인식형
}

# 관계단계별 추천 지역
RELATIONSHIP_PREFERENCES = {
    "썸": ["연남", "성수", "홍대", "이태원"],
    "연인": ["강남", "이태원", "압구정", "홍대"],
    "친구": ["홍대", "강남", "성수", "건대"]
}

def get_area_coordinates(area_name: str) -> Dict[str, float]:
    """지역명으로 좌표 조회"""
    if area_name in AREA_CENTERS:
        return {
            "latitude": AREA_CENTERS[area_name]["lat"],
            "longitude": AREA_CENTERS[area_name]["lng"]
        }
    return {"latitude": 37.5665, "longitude": 126.9780}  # 서울시청 기본값

def get_area_characteristics(area_name: str) -> Dict:
    """지역명으로 특성 정보 조회"""
    if area_name in AREA_CENTERS:
        return AREA_CENTERS[area_name]
    return {
        "signature_traits": ["일반지역"],
        "vibe": "특별한",
        "keywords": ["일반적인"]
    }

def get_predefined_areas() -> List[str]:
    """미리 정의된 지역 목록 반환"""
    return list(AREA_CENTERS.keys())

def get_mbti_preferred_areas(mbti: str) -> List[str]:
    """MBTI 타입별 추천 지역 반환"""
    preferred = []
    for char in mbti:
        if char in MBTI_PREFERENCES:
            preferred.extend(MBTI_PREFERENCES[char])
    return list(set(preferred))  # 중복 제거

def get_relationship_preferred_areas(relationship_stage: str) -> List[str]:
    """관계 단계별 추천 지역 반환"""
    return RELATIONSHIP_PREFERENCES.get(relationship_stage, [])