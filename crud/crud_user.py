from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.sql import func
from sqlalchemy import delete, update as sqlalchemy_update
from models.user import User
from models.user_oauth import UserOAuth
from schemas.user import UserCreate, UserDeleteRequest


# 이메일로 유저 조회
async def get_user_by_email(db: AsyncSession, email: str):
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


# 닉네임 중복 확인 (탈퇴 유저 포함)
async def get_user_by_nickname(db: AsyncSession, nickname: str):
    result = await db.execute(
        select(User).where(User.nickname == nickname)
    )
    return result.scalar_one_or_none()


# ✅ 카카오 ID로 유저 조회 (탈퇴 유저 포함 반환)
async def get_user_by_kakao_id(db: AsyncSession, kakao_id: str):
    result = await db.execute(
        select(UserOAuth).where(
            UserOAuth.provider_user_id == kakao_id,
            UserOAuth.provider_type == "kakao"
        )
    )
    oauth_user = result.scalar_one_or_none()
    if oauth_user:
        user_result = await db.execute(select(User).where(User.user_id == oauth_user.user_id))
        return user_result.scalar_one_or_none()
    return None


# 유저 생성
async def create_user(db: AsyncSession, user_in: UserCreate):
    db_user = User(**user_in.model_dump())
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


# ✅ OAuth 유저 생성 (자동 복구 활성화됨)
async def create_user_with_oauth(
    db: AsyncSession,
    kakao_id: str,
    nickname: str,
    email: str,
    access_token: str = ""
):
    result = await db.execute(
        select(UserOAuth).where(
            UserOAuth.provider_user_id == kakao_id,
            UserOAuth.provider_type == "kakao"
        )
    )
    oauth_user = result.scalar_one_or_none()

    if oauth_user:
        user_result = await db.execute(select(User).where(User.user_id == oauth_user.user_id))
        user = user_result.scalar_one_or_none()
        if user:
            if user.user_status == "inactive":
                user.user_status = "active"
                await db.commit()
                await db.refresh(user)

            return {
                "status": "success",
                "is_new_user": False,
                "user": {
                    "user_id": user.user_id,
                    "nickname": user.nickname,
                    "email": user.email or ""
                }
            }

    # 새 유저 생성
    db_user = User(
        email=email,
        nickname=nickname,
        user_status="active"
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)

    db_oauth = UserOAuth(
        user_id=db_user.user_id,
        provider_type="kakao",
        provider_user_id=kakao_id,
        access_token=access_token
    )
    db.add(db_oauth)
    await db.commit()

    return {
        "status": "success",
        "is_new_user": True,
        "user": {
            "user_id": db_user.user_id,
            "nickname": db_user.nickname,
            "email": db_user.email or ""
        }
    }


# user_id로 유저 조회
async def get_user(db: AsyncSession, user_id: str):
    result = await db.execute(select(User).where(User.user_id == user_id))
    return result.scalar_one_or_none()


# 유저 정보 전체 수정
async def update_user(db: AsyncSession, user_id: str, user_in: UserCreate):
    db_user = await get_user(db, user_id)
    if not db_user:
        return None
    for key, value in user_in.model_dump(exclude_unset=True).items():
        setattr(db_user, key, value)
    await db.commit()
    await db.refresh(db_user)
    return db_user


# 닉네임 변경
async def update_user_nickname(db: AsyncSession, user_id: str, nickname: str):
    db_user = await get_user(db, user_id)
    if not db_user:
        return None
    db_user.nickname = nickname
    await db.commit()
    await db.refresh(db_user)
    return db_user


# 프로필 수정
async def update_user_profile(db: AsyncSession, user_id: str, update_data: dict):
    db_user = await get_user(db, user_id)
    if not db_user:
        return None

    update_values = {}
    if "nickname" in update_data:
        update_values["nickname"] = update_data["nickname"]

    if "profile_detail" in update_data:
        current_profile = db_user.profile_detail or {}
        new_profile = {**current_profile, **update_data["profile_detail"]}
        update_values["profile_detail"] = new_profile

    if update_values:
        stmt = sqlalchemy_update(User).where(User.user_id == user_id).values(**update_values)
        result = await db.execute(stmt)
        if result.rowcount == 0:
            return None
        await db.commit()

    return await get_user(db, user_id)


# 회원 탈퇴 (논리 삭제)
async def delete_user_with_validation(db: AsyncSession, req: UserDeleteRequest):
    user = await get_user(db, req.user_id)
    if not user or user.nickname != req.nickname:
        return None
    user.user_status = "inactive"
    await db.commit()
    return True


# 마이페이지 상세정보 수정
async def update_profile_detail(db: AsyncSession, user_id: str, profile_data: dict):
    db_user = await get_user(db, user_id)
    if not db_user:
        return None

    current_profile = db_user.profile_detail or {}
    filtered_profile_data = {
        k: v for k, v in profile_data.items()
        if v is not None and v != "" and v != []
    }
    new_profile = {**current_profile, **filtered_profile_data}
    update_values = {
        "profile_detail": new_profile,
        "updated_at": func.now()
    }
    if "age" in filtered_profile_data:
        update_values["age"] = filtered_profile_data["age"]
    if "gender" in filtered_profile_data:
        update_values["gender"] = filtered_profile_data["gender"]
    if "mbti" in filtered_profile_data:
        update_values["mbti"] = filtered_profile_data["mbti"]
    if "general_preferences" in filtered_profile_data:
        update_values["general_preferences"] = filtered_profile_data["general_preferences"]

    stmt = sqlalchemy_update(User).where(User.user_id == user_id).values(**update_values)
    result = await db.execute(stmt)
    await db.commit()
    if result.rowcount > 0:
        return await get_user(db, user_id)
    return None
