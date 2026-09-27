# -*- coding: utf-8 -*-
"""
即時意見回饋與 Bug 回報路由模組 (app/routers/feedback.py)
說明：
1. 提供學生、家長與教師隨時提交產品改善建言、題目疑義與程式錯誤回報。
2. 支援登入與訪客匿名提交，資料即時寫入關聯資料庫並提供狀態追蹤。
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Feedback, User
from app.schemas import FeedbackCreateRequest, FeedbackResponse
from app.security import get_optional_current_user

router = APIRouter(prefix="/api/feedback", tags=["即時意見反饋"])

# ==============================================================================
# 1. 提交意見回饋或 Bug 回報
# ==============================================================================
@router.post("", response_model=FeedbackResponse, summary="提交使用者建言或錯誤回報")
def submit_feedback(
    data: FeedbackCreateRequest,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """
    接收並儲存意見反饋：
    - category: suggestion (建言) / bug (錯誤) / question (題目疑義) / other (其他)
    - content: 詳細描述
    - contact_email: 聯絡信箱 (可選)
    """
    user_id = current_user.id if current_user else None
    email = data.contact_email or (current_user.email if current_user else None)

    feedback = Feedback(
        user_id=user_id,
        category=data.category,
        content=data.content.strip(),
        contact_email=email,
        status="received"
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)

    return FeedbackResponse(
        id=feedback.id,
        message="🙏 非常感謝您的寶貴反饋！我們會持續精進平台體驗與題庫品質。",
        status=feedback.status
    )
