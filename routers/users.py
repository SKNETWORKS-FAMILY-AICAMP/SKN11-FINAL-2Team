from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from db.session import get_db
from crud import crud_user
from crud.crud_user import recreate_user_for_deactivated
from schemas.user import (
    UserCreate, StatusResponse, NicknameCheckRequest, UserProfileSetup,
    UserProfileResponse, UserProfileUpdate, UserDeleteRequest
)
from pydantic import BaseModel
import requests
import jwt
import os
from dotenv import load_dotenv

load_dotenv()
router = APIRouter()

JWT_SECRET = os.environ.get("JWT_SECRET", "supersecret")


# ✅ 카카오 access token 검증
def verify_kakao_token(provider_user_id: str, access_token: str) -> bool:
    try:
        response = requests.get(
            "https://kapi.kakao.com/v2/user/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        if response.status_code != 200:
            return False
        data = response.json()
        return str(data.get("id")) == provider_user_id
    except:
        return False


# ✅ 닉네임 중복 확인
@router.post("/users/nickname/check", response_model=StatusResponse)
async def check_nickname_availability(req: NicknameCheckRequest, db: AsyncSession = Depends(get_db)):
    existing_user = await crud_user.get_user_by_nickname(db, req.nickname)
    if existing_user:
        return {"status": "duplicated", "message": "이미 사용 중인 닉네임입니다."}
    return {"status": "available", "message": "사용 가능한 닉네임입니다."}


# ✅ 닉네임 업데이트
class NicknameUpdateRequest(BaseModel):
    user_id: str
    nickname: str


@router.put("/users/nickname/update")
async def update_user_nickname(req: NicknameUpdateRequest, db: AsyncSession = Depends(get_db)):
    user = await crud_user.get_user(db, req.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    existing_user = await crud_user.get_user_by_nickname(db, req.nickname)
    if existing_user and existing_user.user_id != req.user_id:
        raise HTTPException(status_code=400, detail="이미 사용 중인 닉네임입니다.")
    updated_user = await crud_user.update_user_nickname(db, req.user_id, req.nickname)
    return {
        "status": "success",
        "user_id": updated_user.user_id,
        "nickname": updated_user.nickname
    }


# ✅ 최초 회원가입 및 탈퇴 유저 복구
@router.put("/users/profile/initial-setup")
async def initial_user_setup(req: UserProfileSetup, db: AsyncSession = Depends(get_db)):
    if not verify_kakao_token(req.provider_user_id, req.access_token):
        raise HTTPException(status_code=401, detail="카카오 access token 검증 실패")

    # 1. 카카오 ID로 기존 유저 확인
    existing_user = await crud_user.get_user_by_kakao_id(db, req.provider_user_id)
    
    if existing_user and existing_user.user_status == "inactive":
        # 탈퇴한 유저 재가입 처리 (크레딧 지급 안함)
        result = await recreate_user_for_deactivated(
            db=db,
            kakao_id=req.provider_user_id,
            nickname=req.nickname,
            email=None,
            access_token=req.access_token
        )
    else:
        # 진짜 새 가입자 처리 (크레딧 지급함)
        result = await crud_user.create_user_with_oauth(
            db=db,
            kakao_id=req.provider_user_id,
            nickname=req.nickname,
            email=None,
            access_token=req.access_token
        )

    return result


# ✅ 마이페이지 전체 조회
@router.get("/users/profile/me")
async def get_my_profile(user_id: str, db: AsyncSession = Depends(get_db)):
    user = await crud_user.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    return {
        "status": "success",
        "user": {
            "user_id": user.user_id,
            "nickname": user.nickname,
            "email": user.email or "",
            "profile_detail": user.profile_detail or {},
            "couple_info": user.couple_info
        }
    }


# ✅ 마이페이지 수정
@router.put("/users/profile/update/{user_id}")
async def update_user_profile(user_id: str, req: UserProfileUpdate, db: AsyncSession = Depends(get_db)):
    user = await crud_user.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    update_data = {}
    if req.nickname:
        existing_user = await crud_user.get_user_by_nickname(db, req.nickname)
        if existing_user and existing_user.user_id != user_id:
            raise HTTPException(status_code=400, detail="이미 사용 중인 닉네임입니다.")
        update_data["nickname"] = req.nickname
    if req.profile_detail:
        update_data["profile_detail"] = req.profile_detail.model_dump(exclude_unset=True)

    updated_user = await crud_user.update_user_profile(db, user_id, update_data)

    return {
        "status": "success",
        "message": "프로필이 업데이트되었습니다.",
        "user": {
            "user_id": updated_user.user_id,
            "nickname": updated_user.nickname,
            "email": updated_user.email,
            "profile_detail": updated_user.profile_detail
        }
    }


# ✅ 회원 탈퇴
@router.delete("/users/profile/delete")
async def delete_user_account(req: UserDeleteRequest, db: AsyncSession = Depends(get_db)):
    success = await crud_user.delete_user_with_validation(db, req)
    if not success:
        return {
            "status": "fail",
            "error": {
                "code": "MISMATCH_INFO",
                "message": "입력한 정보가 사용자 정보와 일치하지 않습니다."
            }
        }
    return {
        "status": "deleted",
        "user_id": req.user_id
    }
