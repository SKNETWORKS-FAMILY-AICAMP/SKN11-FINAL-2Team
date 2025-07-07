from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_
from models.couple import Couple
from models.user import User
from schemas.couple import CoupleCreate

# 연인 관계 생성
async def create_couple(db: AsyncSession, couple_in: CoupleCreate):
    couple = Couple(**couple_in.model_dump())
    db.add(couple)
    await db.commit()
    await db.refresh(couple)
    return couple

# 사용자의 연인 관계 조회
async def get_couple_by_user_id(db: AsyncSession, user_id: str):
    result = await db.execute(
        select(Couple).where(
            or_(
                Couple.user1_id == user_id,
                Couple.user2_id == user_id
            )
        )
    )
    return result.scalar_one_or_none()

# 연인 관계 해제
async def delete_couple(db: AsyncSession, couple_id: int, user_id: str):
    # 해당 연인 관계가 사용자와 관련이 있는지 확인
    result = await db.execute(
        select(Couple).where(
            Couple.couple_id == couple_id,
            or_(
                Couple.user1_id == user_id,
                Couple.user2_id == user_id
            )
        )
    )
    couple = result.scalar_one_or_none()
    if not couple:
        raise ValueError("해당 연인 관계를 찾을 수 없거나 권한이 없습니다.")
    
    await db.delete(couple)
    await db.commit()
    return True

# 연인 관계 존재 여부 확인
async def check_couple_exists(db: AsyncSession, user1_id: str, user2_id: str):
    result = await db.execute(
        select(Couple).where(
            or_(
                (Couple.user1_id == user1_id) & (Couple.user2_id == user2_id),
                (Couple.user1_id == user2_id) & (Couple.user2_id == user1_id)
            )
        )
    )
    return result.scalar_one_or_none() is not None