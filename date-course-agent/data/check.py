# 현재 벡터 DB 상태를 빠르게 확인하는 스크립트
import sys
import os

# 프로젝트 루트 경로 추가  
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    from src.database.qdrant_client import get_qdrant_client
    
    print("🔍 현재 벡터 DB 상태 확인 중...")
    
    client = get_qdrant_client()
    info = client.get_collection_info()
    
    print(f"📊 현재 저장된 벡터 수: {info['points_count']}개")
    
    if info['points_count'] > 0:
        print("✅ 기존 데이터가 있습니다!")
        print("💡 이어서 로딩할 수 있어요.")
    else:
        print("📭 저장된 데이터가 없습니다.")
        print("💡 처음부터 시작해야 합니다.")
        
except Exception as e:
    print(f"❌ 확인 실패: {e}")
    print("💡 Qdrant 서버가 실행 중인지 확인해주세요.")