# -*- coding: utf-8 -*-
"""
智慧錯題本與熟練度畢業機制路由模組 (app/routers/mistakes.py)
說明：
1. 學生刷題答錯時自動收錄至錯題本。
2. 支援依未熟練 (待複習) 與已熟練 (已畢業) 檢視錯題清單。
3. 實作錯題複習機制：
   - 複習答對：連續答對次數 +1，熟練度提升；連續答對 2 次或熟練度達 100% 即可「熟練畢業 (Graduated)」，獲得 30 EXP 畢業激勵！
   - 複習答錯：連續答對歸零，熟練度扣減，持續留在待複習隊列。
"""

import json
import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Question, MistakeNotebook
from app.schemas import (
    MistakeItemResponse,
    MistakeReviewSubmitRequest,
    MistakeReviewResult
)
from app.security import get_current_user
from app.gamification import EXP_MISTAKE_GRADUATE, apply_exp_gain

router = APIRouter(prefix="/api/mistakes", tags=["智慧錯題本與熟練度機制"])

# ==============================================================================
# 1. 取得學生個人錯題本清單
# ==============================================================================
@router.get("", response_model=List[MistakeItemResponse], summary="取得個人錯題本題目清單 (待複習或已畢業)")
def get_mistakes(
    graduated: Optional[bool] = Query(False, description="是否已熟練畢業 (False: 待複習 / True: 已熟練畢業)"),
    subject: Optional[str] = Query(None, description="依學科篩選"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    查詢目前登入學生的錯題記錄：
    - 預設列出尚未畢業 (待複習) 的題目。
    - 結合題目原文、選項、標籤與學生個人備忘筆記。
    """
    query = db.query(MistakeNotebook).join(Question).filter(
        MistakeNotebook.user_id == current_user.id
    )

    if graduated is not None:
        query = query.filter(MistakeNotebook.is_graduated == graduated)

    if subject:
        query = query.filter(Question.subject == subject)

    # 依照最後複習時間排序
    mistakes = query.order_by(MistakeNotebook.last_reviewed_at.desc()).all()

    results: List[MistakeItemResponse] = []
    for m in mistakes:
        q = m.question
        try:
            options_list = json.loads(q.options)
        except Exception:
            options_list = ["A", "B", "C", "D"]

        tags_list = [t.strip() for t in q.tags.split(",") if t.strip()] if q.tags else []

        results.append(MistakeItemResponse(
            id=m.id,
            question_id=q.id,
            school_level=q.school_level,
            grade=q.grade,
            publisher=q.publisher,
            subject=q.subject,
            chapter=q.chapter,
            content=q.content,
            options=options_list,
            tags=tags_list,
            wrong_count=m.wrong_count,
            consecutive_correct=m.consecutive_correct,
            mastery_rate=m.mastery_rate,
            is_graduated=m.is_graduated,
            student_notes=m.student_notes,
            last_reviewed_at=m.last_reviewed_at.strftime("%Y-%m-%d %H:%M") if m.last_reviewed_at else None
        ))

    return results

# ==============================================================================
# 2. 錯題複習作答與熟練度畢業結算
# ==============================================================================
@router.post("/review", response_model=MistakeReviewResult, summary="複習錯題作答並判定是否熟練畢業")
def review_mistake(
    data: MistakeReviewSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    錯題複習專用驗證邏輯：
    - 驗證該錯題記錄確實屬於當前登入者 (防水平越權)。
    - 連續答對 2 次或熟練度達 100% 即達到畢業標準。
    - 畢業時發放 30 經驗值。
    """
    mistake = db.query(MistakeNotebook).filter(
        MistakeNotebook.id == data.mistake_id,
        MistakeNotebook.user_id == current_user.id
    ).first()

    if not mistake:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="找不到該筆錯題紀錄")

    question = mistake.question
    is_correct = (data.selected_option.strip().upper() == question.correct_answer.strip().upper())

    if data.student_notes is not None:
        mistake.student_notes = data.student_notes

    mistake.last_reviewed_at = datetime.datetime.now(datetime.timezone.utc)
    exp_earned = 0

    if is_correct:
        mistake.consecutive_correct += 1
        mistake.mastery_rate = min(100, mistake.mastery_rate + 50)

        # 達到畢業條件：連續答對 2 次以上或熟練度達 100%
        if mistake.consecutive_correct >= 2 or mistake.mastery_rate >= 100:
            if not mistake.is_graduated:
                mistake.is_graduated = True
                exp_earned = EXP_MISTAKE_GRADUATE
                new_exp, new_lvl, new_title, _ = apply_exp_gain(current_user.exp, exp_earned)
                current_user.exp = new_exp
                current_user.level = new_lvl
                message = f"🎓 太棒了！該題已【熟練畢業】，獲得畢業獎勵 +{exp_earned} EXP！"
            else:
                message = "🎉 複習答對！該題維持在熟練畢業名單中！"
        else:
            message = f"✅ 複習答對！連續答對 {mistake.consecutive_correct} 次，再答對 1 次即可熟練畢業！"
    else:
        mistake.consecutive_correct = 0
        mistake.wrong_count += 1
        mistake.mastery_rate = max(0, mistake.mastery_rate - 30)
        mistake.is_graduated = False
        message = "💡 本次複習答錯，建議參考下方詳解觀念，或點擊 AI 小家教引導思考！"

    db.commit()
    db.refresh(mistake)

    return MistakeReviewResult(
        is_correct=is_correct,
        correct_answer=question.correct_answer,
        explanation=question.explanation,
        consecutive_correct=mistake.consecutive_correct,
        mastery_rate=mistake.mastery_rate,
        is_graduated=mistake.is_graduated,
        exp_earned=exp_earned,
        message=message
    )

# ==============================================================================
# 3. 儲存錯題個人筆記與盲點備忘
# ==============================================================================
@router.patch("/{mistake_id}/notes", summary="更新學生錯題筆記心得")
def update_mistake_note(
    mistake_id: int,
    notes: str = Query(..., description="自訂筆記內容"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    學生自訂每道錯題之解題盲點與重點備忘。
    """
    mistake = db.query(MistakeNotebook).filter(
        MistakeNotebook.id == mistake_id,
        MistakeNotebook.user_id == current_user.id
    ).first()

    if not mistake:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="找不到該筆錯題紀錄")

    mistake.student_notes = notes
    db.commit()
    return {"message": "筆記已成功更新", "mistake_id": mistake_id}
