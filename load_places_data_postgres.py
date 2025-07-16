#!/usr/bin/env python3
"""
PostgreSQL용 장소 데이터 로딩 스크립트
기존 load_places_data.py를 PostgreSQL용으로 수정
"""
import asyncio
import json
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from models.place import Place
from models.place_category import PlaceCategory
from models.place_category_relation import PlaceCategoryRelation
from config import DATABASE_URL

async def load_places_to_postgresql():
    """PostgreSQL에 장소 데이터 로딩"""
    print("🏗️ PostgreSQL에 장소 데이터 로딩 시작...")
    
    try:
        # 1. 데이터베이스 연결
        engine = create_async_engine(DATABASE_URL, echo=False)  # echo=False로 로그 줄임
        SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        
        # 2. 카테고리 데이터 로딩
        print("📂 카테고리 데이터 로딩...")
        categories_map = {}
        
        async with SessionLocal() as session:
            # 기본 카테고리들 생성
            categories = [
                "음식점", "카페", "문화시설", "쇼핑", "엔터테인먼트", 
                "야외활동", "휴식시설", "술집", "주차장", "기타"
            ]
            
            for cat_name in categories:
                category = PlaceCategory(
                    category_name=cat_name
                )
                session.add(category)
                await session.flush()  # ID 생성을 위해 flush
                categories_map[cat_name] = category.category_id
                
            await session.commit()
            print(f"✅ {len(categories)} 개 카테고리 생성 완료")
        
        # 3. 장소 데이터 로딩
        data_dir = "./data"
        total_places = 0
        
        if not os.path.exists(data_dir):
            print(f"❌ 데이터 디렉토리가 없습니다: {data_dir}")
            return
            
        for filename in os.listdir(data_dir):
            if filename.endswith('.json'):
                category_name = filename.replace('.json', '')
                
                if category_name not in categories_map:
                    print(f"⚠️ 알 수 없는 카테고리: {category_name}")
                    continue
                
                print(f"📥 {category_name} 데이터 로딩 중...")
                
                with open(os.path.join(data_dir, filename), 'r', encoding='utf-8') as f:
                    places_data = json.load(f)
                
                async with SessionLocal() as session:
                    count = 0
                    for place_data in places_data:
                        try:
                            # Place 객체 생성
                            place = Place(
                                name=place_data.get('name', ''),
                                address=place_data.get('address', ''),
                                description=place_data.get('description', ''),
                                latitude=float(place_data.get('latitude', 0)),
                                longitude=float(place_data.get('longitude', 0)),
                                phone=place_data.get('phone', ''),
                                website=place_data.get('website', ''),
                                opening_hours=place_data.get('opening_hours', ''),
                                rating=float(place_data.get('rating', 0)),
                                review_count=int(place_data.get('review_count', 0)),
                                price_range=place_data.get('price_range', ''),
                                features=place_data.get('features', []),
                                images=place_data.get('images', [])
                            )
                            session.add(place)
                            await session.flush()  # ID 생성
                            
                            # 카테고리 관계 생성
                            category_relation = PlaceCategoryRelation(
                                place_id=place.place_id,
                                category_id=categories_map[category_name]
                            )
                            session.add(category_relation)
                            
                            count += 1
                            
                            # 100개마다 중간 커밋
                            if count % 100 == 0:
                                await session.commit()
                                print(f"   💾 {count}개 저장 중...")
                                
                        except Exception as e:
                            print(f"   ⚠️ 장소 저장 실패: {e}")
                            continue
                    
                    await session.commit()
                    total_places += count
                    print(f"✅ {category_name}: {count}개 장소 저장 완료")
        
        await engine.dispose()
        print(f"🎉 총 {total_places}개 장소 데이터 로딩 완료!")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        print("💡 해결방법:")
        print("   1. PostgreSQL이 실행 중인지 확인")
        print("   2. reset_database_postgres.py 먼저 실행")
        print("   3. data/ 디렉토리에 JSON 파일들이 있는지 확인")
        raise

if __name__ == "__main__":
    print("🚀 PostgreSQL 장소 데이터 로딩 시작")
    asyncio.run(load_places_to_postgresql())
    print("✨ 모든 작업 완료! 서버를 시작할 수 있습니다.")