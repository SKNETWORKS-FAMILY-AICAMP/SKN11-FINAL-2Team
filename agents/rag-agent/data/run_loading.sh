#!/bin/bash

# 벡터 DB 로딩 스크립트 실행기
# data/places 디렉토리의 데이터를 벡터 DB에 로드

echo "🚀 벡터 DB 로딩 시작..."
echo "================================"

# 현재 디렉토리 확인
echo "📁 현재 위치: $(pwd)"

# places 디렉토리 확인
if [ ! -d "places" ]; then
    echo "❌ places 디렉토리가 없습니다!"
    echo ""
    echo "다음 위치에 JSON 파일들을 복사해주세요:"
    echo "   $(pwd)/places/"
    echo ""
    echo "복사해야 할 파일들:"
    echo "   - 음식점.json"
    echo "   - 카페.json" 
    echo "   - 술집.json"
    echo "   - 문화시설.json"
    echo "   - 휴식시설.json"
    echo "   - 야외활동.json"
    echo "   - 엔터테인먼트.json"
    echo "   - 쇼핑.json"
    echo "   - 주차장.json"
    echo "   - 기타.json"
    exit 1
fi

# 환경 확인
if [ ! -f "../.env" ]; then
    echo "❌ .env 파일이 없습니다!"
    echo "   OPENAI_API_KEY를 설정해주세요."
    exit 1
fi

# JSON 파일 존재 확인
echo "📄 JSON 파일 확인..."
json_count=$(find places -name "*.json" | wc -l)
if [ $json_count -eq 0 ]; then
    echo "❌ places 디렉토리에 JSON 파일이 없습니다!"
    exit 1
fi
echo "   발견된 JSON 파일: $json_count 개"

# Python 스크립트 실행
echo "🐍 Python 스크립트 실행..."
python3 load_final_data.py

echo "================================"
echo "✅ 벡터 DB 로딩 완료!"
echo ""
echo "이제 다음 명령으로 시스템을 시작할 수 있습니다:"
echo "cd .. && python src/main.py"
