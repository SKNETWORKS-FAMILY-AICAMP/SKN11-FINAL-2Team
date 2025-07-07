from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from db.session import get_db
from crud import crud_user
from schemas.user import UserCreate, StatusResponse, NicknameCheckRequest, UserProfileSetup, UserProfileResponse, UserProfileUpdate, UserDeleteRequest
from pydantic import BaseModel
import requests
import jwt 
import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

JWT_SECRET = os.environ.get("JWT_SECRET", "supersecret")

class SocialLoginRequest(BaseModel):
    provider: str
    code: str

class SocialLoginResponse(StatusResponse):
    accessToken: str
    is_new_user: bool
    user: dict

# 소셜 로그인은 auth.py로 이동됨

@router.post("/users/nickname/check", response_model=StatusResponse, summary="닉네임 중복 확인")
async def check_nickname_availability(req: NicknameCheckRequest, db: AsyncSession = Depends(get_db)):
    existing_user = await crud_user.get_user_by_nickname(db, req.nickname)
    
    if existing_user:
        return {
            "status": "duplicated",
            "message": "이미 사용 중인 닉네임입니다."
        }
    else:
        return {
            "status": "available", 
            "message": "사용할 수 있는 닉네임입니다."
        }

class NicknameUpdateRequest(BaseModel):
    user_id: str
    nickname: str

@router.put("/users/nickname/update", summary="닉네임 업데이트")
async def update_user_nickname(req: NicknameUpdateRequest, db: AsyncSession = Depends(get_db)):
    # 사용자 찾기
    user = await crud_user.get_user(db, req.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    
    # 닉네임 중복 확인
    existing_user = await crud_user.get_user_by_nickname(db, req.nickname)
    if existing_user and existing_user.user_id != req.user_id:
        raise HTTPException(status_code=400, detail="이미 사용 중인 닉네임입니다.")
    
    # 닉네임 업데이트
    updated_user = await crud_user.update_user_nickname(db, req.user_id, req.nickname)
    
    return {
        "status": "success",
        "user_id": updated_user.user_id,
        "nickname": updated_user.nickname
    }

@router.put("/users/profile/initial-setup", summary="회원가입 설정")
async def initial_user_setup(req: UserProfileSetup, db: AsyncSession = Depends(get_db)):
    # 기존 사용자 찾기 (카카오 로그인으로 이미 생성된 사용자)
    existing_user = await crud_user.get_user_by_nickname(db, req.nickname)
    
    if not existing_user:
        # 새 사용자 생성
        new_user = await crud_user.create_user(db, UserCreate(
            nickname=req.nickname,
            email=None
        ))
        return {
            "status": "success",
            "user_id": new_user.user_id,
            "nickname": new_user.nickname
        }
    else:
        return {
            "status": "success", 
            "user_id": existing_user.user_id,
            "nickname": existing_user.nickname
        }

@router.get("/users/profile/couple-status", summary="커플 연결 페이지 조회")
async def get_couple_status(user_id: str, db: AsyncSession = Depends(get_db)):
    user = await crud_user.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    
    return {
        "couple_info": None,
        "message": "현재 연인과 연결되어 있지 않습니다."
    }

@router.get("/users/profile/me", response_model=dict, summary="마이페이지 전체 정보 조회")
async def get_my_profile(user_id: str, db: AsyncSession = Depends(get_db)):
    user = await crud_user.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    
    # 실제 DB 데이터만 반환
    return {
        "status": "success",
        "user": {
            "user_id": user.user_id,
            "nickname": user.nickname,
            "email": user.email or "",
            "profile_detail": user.profile_detail or {
                "age_range": "",
                "gender": "",
                "mbti": "",
                "car_owner": False,
                "preferences": ""
            },
            "couple_info": user.couple_info
        }
    }

@router.put("/users/profile/update", summary="마이페이지 수정")
async def update_user_profile(req: UserProfileUpdate, db: AsyncSession = Depends(get_db)):
    # user_id를 쿼리 파라미터나 body에서 받아야 하는데, 프론트엔드 구조상 body에 포함
    # 하지만 UserProfileUpdate 스키마에 user_id가 없으므로 별도 처리 필요
    # 실제로는 JWT 토큰에서 user_id를 추출해야 하지만, 현재는 간단히 처리
    return {
        "status": "error", 
        "message": "user_id가 필요합니다."
    }

@router.put("/users/profile/update/{user_id}", summary="마이페이지 수정")
async def update_user_profile_with_id(user_id: str, req: UserProfileUpdate, db: AsyncSession = Depends(get_db)):
    try:
        # 사용자 존재 확인
        user = await crud_user.get_user(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
        
        # 업데이트 데이터 준비
        update_data = {}
        if req.nickname:
            # 닉네임 중복 확인
            existing_user = await crud_user.get_user_by_nickname(db, req.nickname)
            if existing_user and existing_user.user_id != user_id:
                raise HTTPException(status_code=400, detail="이미 사용 중인 닉네임입니다.")
            update_data["nickname"] = req.nickname
        
        if req.profile_detail:
            update_data["profile_detail"] = req.profile_detail.model_dump(exclude_unset=True)
        
        # 프로필 업데이트
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
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"프로필 업데이트 실패: {str(e)}")

@router.get("/users/profile/main", summary="메인페이지")
async def get_main_profile(user_id: str, db: AsyncSession = Depends(get_db)):
    user = await crud_user.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    
    return {
        "status": "success",
        "user": {
            "user_id": user.user_id,
            "name": user.nickname,
            "nickname": user.nickname,
            "login_info": "kakao",
            "couple_info": None
        }
    }

@router.delete("/users/profile/delete", summary="회원 탈퇴")
async def delete_user_account(req: UserDeleteRequest, db: AsyncSession = Depends(get_db)):
    user = await crud_user.get_user(db, req.user_id)
    if not user or user.nickname != req.nickname or user.email != req.email:
        return {
            "user_id": req.user_id,
            "error": {
                "code": "MISMATCH_INFO",
                "message": "입력한 정보가 사용자 정보와 일치하지 않습니다."
            }
        }
    
    await crud_user.delete_user(db, req.user_id)
    return {
        "status": "deleted",
        "user_id": req.user_id
    }