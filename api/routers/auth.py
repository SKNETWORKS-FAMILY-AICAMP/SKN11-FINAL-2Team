from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
import httpx
import config
from db.session import get_db
from models.user import User
from models.user_oauth import UserOAuth
from crud.crud_user import get_user_by_kakao_id, create_user_with_oauth

router = APIRouter()

class SocialLoginRequest(BaseModel):
    provider: str
    code: str

class SocialLoginResponse(BaseModel):
    accessToken: str
    user: dict
    is_new_user: bool

@router.post("/auth/social-login")
async def social_login(request: SocialLoginRequest, db: AsyncSession = Depends(get_db)):
    if request.provider != "kakao":
        raise HTTPException(status_code=400, detail="지원하지 않는 소셜 로그인 제공자입니다.")
    
    try:
        # 카카오 토큰 요청
        token_url = "https://kauth.kakao.com/oauth/token"
        token_data = {
            "grant_type": "authorization_code",
            "client_id": config.KAKAO_REST_API_KEY,
            "redirect_uri": config.KAKAO_REDIRECT_URI,
            "code": request.code
        }
        
        async with httpx.AsyncClient() as client:
            token_response = await client.post(token_url, data=token_data)
            
        if token_response.status_code != 200:
            raise HTTPException(status_code=400, detail="카카오 토큰 요청 실패")
            
        token_info = token_response.json()
        access_token = token_info["access_token"]
        
        # 카카오 사용자 정보 요청
        user_url = "https://kapi.kakao.com/v2/user/me"
        headers = {"Authorization": f"Bearer {access_token}"}
        
        async with httpx.AsyncClient() as client:
            user_response = await client.get(user_url, headers=headers)
            
        if user_response.status_code != 200:
            raise HTTPException(status_code=400, detail="카카오 사용자 정보 요청 실패")
            
        user_info = user_response.json()
        kakao_id = str(user_info["id"])
        nickname = user_info.get("properties", {}).get("nickname", "")
        email = user_info.get("kakao_account", {}).get("email", "")
        
        # 기존 사용자 확인
        existing_user = await get_user_by_kakao_id(db, kakao_id)
        
        if existing_user:
            # 기존 사용자 로그인
            user_data = {
                "user_id": existing_user.user_id,
                "nickname": existing_user.nickname,
                "email": existing_user.email or ""
            }
            return SocialLoginResponse(
                accessToken=f"token_{existing_user.user_id}",
                user=user_data,
                is_new_user=False
            )
        else:
            # 새로운 사용자 생성
            new_user = await create_user_with_oauth(db, kakao_id, nickname, email, access_token)
            user_data = {
                "user_id": new_user.user_id,
                "nickname": new_user.nickname,
                "email": new_user.email or ""
            }
            return SocialLoginResponse(
                accessToken=f"token_{new_user.user_id}",
                user=user_data,
                is_new_user=True
            )
            
    except Exception as e:
        import traceback
        print(f"에러 발생: {str(e)}")
        print(f"에러 트레이스: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"소셜 로그인 처리 중 오류 발생: {str(e)}")

@router.get("/oauth/callback/kakao")
async def kakao_callback(code: str):
    # 받은 code로 토큰 요청 등 추가 로직 작성
    return {"message": "카카오 로그인 콜백 성공", "code": code}
