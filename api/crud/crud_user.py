from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.sql import func
from models.user import User
from models.user_oauth import UserOAuth
from schemas.user import UserCreate

async def get_user_by_email(db: AsyncSession, email: str):
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()

async def get_user_by_nickname(db: AsyncSession, nickname: str):
    result = await db.execute(select(User).where(User.nickname == nickname))
    return result.scalar_one_or_none()

async def get_user_by_kakao_id(db: AsyncSession, kakao_id: str):
    result = await db.execute(select(UserOAuth).where(UserOAuth.provider_user_id == kakao_id, UserOAuth.provider_type == "kakao"))
    oauth_user = result.scalar_one_or_none()
    if oauth_user:
        user_result = await db.execute(select(User).where(User.user_id == oauth_user.user_id))
        return user_result.scalar_one_or_none()
    return None

# 새 사용자 생성 (카카오 로그인용)
async def create_user(db: AsyncSession, user_in: UserCreate):
    db_user = User(**user_in.model_dump())
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

async def create_user_with_oauth(db: AsyncSession, kakao_id: str, nickname: str, email: str, access_token: str = ""):
    # 새로운 사용자 생성
    db_user = User(
        email=email,
        nickname=nickname
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    
    # OAuth 정보 저장
    db_oauth = UserOAuth(
        user_id=db_user.user_id,
        provider_type="kakao",
        provider_user_id=kakao_id,
        access_token=access_token
    )
    db.add(db_oauth)
    await db.commit()
    
    return db_user

# 기존 사용자 조회
async def get_user(db: AsyncSession, user_id: str):
    result = await db.execute(select(User).where(User.user_id == user_id))
    return result.scalar_one_or_none()

# 기존 사용자 수정
async def update_user(db: AsyncSession, user_id: str, user_in: UserCreate):
    db_user = await get_user(db, user_id)
    if not db_user:
        return None
    for key, value in user_in.model_dump(exclude_unset=True).items():
        setattr(db_user, key, value)
    await db.commit()
    await db.refresh(db_user)
    return db_user

# 닉네임 업데이트
async def update_user_nickname(db: AsyncSession, user_id: str, nickname: str):
    db_user = await get_user(db, user_id)
    if not db_user:
        return None
    db_user.nickname = nickname
    await db.commit()
    await db.refresh(db_user)
    return db_user

# 프로필 업데이트 (profile_detail 포함) - 완전한 구현
async def update_user_profile(db: AsyncSession, user_id: str, update_data: dict):
    from sqlalchemy.orm import Session
    from sqlalchemy import update as sqlalchemy_update
    
    # 기존 사용자 조회
    db_user = await get_user(db, user_id)
    if not db_user:
        return None
    
    # 업데이트할 값들 준비
    update_values = {}
    
    if "nickname" in update_data:
        update_values["nickname"] = update_data["nickname"]
    
    if "profile_detail" in update_data:
        # 기존 profile_detail과 새 데이터 병합
        current_profile = db_user.profile_detail or {}
        new_profile = {**current_profile, **update_data["profile_detail"]}
        update_values["profile_detail"] = new_profile
    
    if update_values:
        # SQLAlchemy update 구문 사용 (JSON 필드도 올바르게 처리됨)
        stmt = sqlalchemy_update(User).where(User.user_id == user_id).values(**update_values)
        result = await db.execute(stmt)
        
        # 업데이트된 행이 있는지 확인
        if result.rowcount == 0:
            return None
            
        await db.commit()
    
    # 업데이트된 사용자 정보 반환
    return await get_user(db, user_id)

# 기존 사용자 삭제
async def delete_user(db: AsyncSession, user_id: str):
    db_user = await get_user(db, user_id)
    if not db_user:
        return None
    await db.delete(db_user)
    await db.commit()
    return db_user

async def update_profile_detail(db: AsyncSession, user_id: str, profile_data: dict):
    """채팅에서 수집된 프로필 정보로 사용자 프로필 업데이트"""
    from sqlalchemy import update as sqlalchemy_update
    
    # 기존 사용자 조회
    db_user = await get_user(db, user_id)
    if not db_user:
        return None
    
    # 기존 profile_detail과 새 데이터 병합
    current_profile = db_user.profile_detail or {}
    
    # 빈값 필터링
    filtered_profile_data = {}
    for key, value in profile_data.items():
        if value is not None and value != "" and value != []:
            filtered_profile_data[key] = value
    
    new_profile = {**current_profile, **filtered_profile_data}
    
    # User 테이블의 기본 필드도 업데이트 (기존 호환성 유지)
    update_values = {
        "profile_detail": new_profile,
        "updated_at": func.now()
    }
    
    # 기본 필드에도 저장 (마이페이지 호환성)
    if "age" in filtered_profile_data:
        update_values["age"] = filtered_profile_data["age"]
    if "gender" in filtered_profile_data:
        update_values["gender"] = filtered_profile_data["gender"]
    if "mbti" in filtered_profile_data:
        update_values["mbti"] = filtered_profile_data["mbti"]
    if "general_preferences" in filtered_profile_data:
        update_values["general_preferences"] = filtered_profile_data["general_preferences"]
    
    # SQLAlchemy update 구문 사용
    stmt = sqlalchemy_update(User).where(User.user_id == user_id).values(**update_values)
    result = await db.execute(stmt)
    await db.commit()
    
    if result.rowcount > 0:
        # 업데이트된 사용자 정보 반환
        return await get_user(db, user_id)
    return None
