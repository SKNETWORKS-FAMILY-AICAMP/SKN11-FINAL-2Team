from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_
from models.couple import Couple
from models.user import User
from schemas.couple import CoupleCreate
from crud.crud_couple_request import cancel_accepted_request  # 연인 신청 상태 취소용

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

    # 사용자 정보 조회
    my_result = await db.execute(select(User).where(User.user_id == user_id))
    me = my_result.scalar_one_or_none()

    # ❗ 잘못된 부분 수정
    partner_id = couple.user1_id if couple.user2_id == user_id else couple.user2_id
    partner_result = await db.execute(select(User).where(User.user_id == partner_id))
    partner = partner_result.scalar_one_or_none()

    if not me or not partner:
        raise ValueError("사용자 정보를 찾을 수 없습니다.")

    # 연인 신청 상태도 'cancelled'로 변경
    await cancel_accepted_request(db, user_id, partner.nickname)

    # 연인 관계 삭제
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
