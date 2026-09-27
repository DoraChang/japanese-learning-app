# -*- coding: utf-8 -*-
"""
身分驗證與首次登錄精靈路由模組 (app/routers/auth.py)
說明：
1. 僅支援個人 Google 帳號 OAuth 2.0 登錄與開發者模擬模式。
2. 首次登入強制觸發「身分選擇與年齡確認」精靈 (學生、家長、教師)。
3. 未滿 18 歲自動啟動未成年防護機制並生成專屬「家長綁定代碼 (binding_code)」。
4. 提供主題偏好設定 (Dark / Light / System Default) 與個人檔案 API。
"""

import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import (
    UserLoginRequest,
    UserOnboardingRequest,
    UserProfileResponse,
    UserThemeUpdateRequest
)
from app.security import (
    create_access_token,
    get_current_user,
    generate_unique_binding_code
)
from app.gamification import get_level_info
from app.config import MINOR_AGE_THRESHOLD, VALID_ROLES

router = APIRouter(prefix="/api/auth", tags=["身分驗證與個人設定"])

# ==============================================================================
# 1. Google 帳號登錄 (OAuth 2.0 / 開發者便捷模式)
# ==============================================================================
@router.post("/google-login", summary="Google OAuth 2.0 登錄驗證")
def google_login(login_data: UserLoginRequest, db: Session = Depends(get_db)):
    """
    接收 Google OAuth 回傳之憑證進行身分認證：
    - 若帳號為初次登入，自動註冊並標記 is_onboarded = False，後續強制導向身分與年齡確認精靈。
    - 簽發 HS256 安全 Bearer Token 回傳前端。
    """
    user = db.query(User).filter(User.email == login_data.email).first()

    if not user:
        # 初次使用 Google 登錄註冊
        user = User(
            email=login_data.email,
            name=login_data.name or "學習夥伴",
            avatar=login_data.avatar or "https://api.dicebear.com/7.x/bottts/svg?seed=student",
            role="student",
            is_onboarded=False,
            is_minor=True,
            exp=0,
            level=1,
            combo=0,
            school_level="junior",
            grade="j7",
            theme_preference="system"
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # 簽發 Access Token
    token = create_access_token(data={"sub": str(user.id), "role": user.role, "email": user.email})

    return {
        "access_token": token,
        "token_type": "bearer",
        "is_onboarded": user.is_onboarded,
        "user_id": user.id,
        "role": user.role,
        "name": user.name
    }

# ==============================================================================
# 2. 首次登入強制精靈：身分選擇與年齡確認
# ==============================================================================
@router.post("/onboarding", response_model=UserProfileResponse, summary="完成首次登錄身分與年齡確認精靈")
def complete_onboarding(
    data: UserOnboardingRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    強制身分精靈：
    - 設定角色 (學生 student / 家長 parent / 教師 teacher)。
    - 輸入實質年齡：未滿 18 歲自動鎖定 is_minor = True，並指派專屬綁定代碼以利家長監護。
    - 年滿 18 歲則 is_minor = False。
    """
    if data.role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"無效的角色選擇，請選擇 {', '.join(VALID_ROLES)}"
        )
    
    current_user.role = data.role
    current_user.age = data.age
    current_user.is_minor = (data.age < MINOR_AGE_THRESHOLD)

    # 若為未成年人且尚未產生綁定代碼，自動產生專屬 8 碼代碼
    if current_user.is_minor and not current_user.binding_code:
        current_user.binding_code = generate_unique_binding_code(db)

    # 若為學生，設定學制與年級
    if data.school_level:
        current_user.school_level = data.school_level
    if data.grade:
        current_user.grade = data.grade

    current_user.is_onboarded = True
    current_user.updated_at = datetime.datetime.now(datetime.timezone.utc)

    db.commit()
    db.refresh(current_user)

    # 計算遊戲化等級資訊
    lvl_info = get_level_info(current_user.exp)

    return UserProfileResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        avatar=current_user.avatar,
        role=current_user.role,
        age=current_user.age,
        is_minor=current_user.is_minor,
        binding_code=current_user.binding_code,
        is_onboarded=current_user.is_onboarded,
        exp=current_user.exp,
        level=lvl_info["level"],
        level_title=lvl_info["title"],
        next_level_exp=lvl_info["next_level_exp"],
        level_progress_percent=lvl_info["progress_percent"],
        combo=current_user.combo,
        school_level=current_user.school_level,
        grade=current_user.grade,
        theme_preference=current_user.theme_preference
    )

# ==============================================================================
# 3. 讀取個人資料與等級資訊
# ==============================================================================
@router.get("/me", response_model=UserProfileResponse, summary="取得當前登入者個人檔案與遊戲化等級")
def get_my_profile(current_user: User = Depends(get_current_user)):
    """
    提供前端即時取得個人資訊、目前等級稱號、EXP 條與綁定代碼。
    """
    lvl_info = get_level_info(current_user.exp)
    return UserProfileResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        avatar=current_user.avatar,
        role=current_user.role,
        age=current_user.age,
        is_minor=current_user.is_minor,
        binding_code=current_user.binding_code,
        is_onboarded=current_user.is_onboarded,
        exp=current_user.exp,
        level=lvl_info["level"],
        level_title=lvl_info["title"],
        next_level_exp=lvl_info["next_level_exp"],
        level_progress_percent=lvl_info["progress_percent"],
        combo=current_user.combo,
        school_level=current_user.school_level,
        grade=current_user.grade,
        theme_preference=current_user.theme_preference
    )

# ==============================================================================
# 4. 主題設定切換 (Dark / Light / System Default)
# ==============================================================================
@router.patch("/theme", summary="切換深淺色或系統自訂主題")
def update_theme(
    theme_data: UserThemeUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    更新使用者介面主題設定 (支援: system / dark / light)
    """
    current_user.theme_preference = theme_data.theme_preference
    db.commit()
    return {"message": "主題偏好已成功更新", "theme_preference": current_user.theme_preference}
