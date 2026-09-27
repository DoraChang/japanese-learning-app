# -*- coding: utf-8 -*-
"""
家長專區與防越權監控路由模組 (app/routers/parent.py)
說明：
1. 嚴格實作 RBAC 角色限制：僅限定家長身分 (role == "parent") 存取。
2. 實作「添加小孩帳號」機制：支援輸入小孩 Google 帳號 (Email) 或 8 碼專屬「家長綁定代碼 (binding_code)」。
3. 嚴格防禦 BOLA / IDOR 水平與垂直越權攻擊：
   所有查詢子女學習概況與指派作業的 API，必須在 DB 層通過 verify_parent_child_relationship 檢驗！
4. 提供作業指派、進度追蹤與子女段考倒數即時儀表板。
"""

import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    User,
    ParentChild,
    ExamPlan,
    MistakeNotebook,
    HomeworkAssignment,
    StudyLog
)
from app.schemas import (
    AddChildRequest,
    ChildSummaryResponse,
    HomeworkAssignmentCreate,
    HomeworkResponse
)
from app.security import (
    get_current_user,
    require_roles,
    verify_parent_child_relationship
)
from app.gamification import get_level_info
from app.config import ROLE_PARENT

router = APIRouter(prefix="/api/parent", tags=["家長專區與防越權監控"])

# ==============================================================================
# 1. 家長綁定未成年子女帳號 (輸入 Email 或 專屬代碼)
# ==============================================================================
@router.post("/bind-child", summary="家長添加並綁定子女帳號 (防偽造與年齡核驗)")
def bind_child_account(
    data: AddChildRequest,
    current_parent: User = Depends(require_roles([ROLE_PARENT])),
    db: Session = Depends(get_db)
):
    """
    家長添加小孩機制：
    - 支援以小孩 Email 或綁定代碼 (binding_code) 查找。
    - 查核小孩帳號存在性與未成年身分。
    - 建立 ParentChild 安全關聯。
    """
    if not data.child_email and not data.binding_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="請提供小孩的 Google 帳號 Email 或 8 碼綁定代碼"
        )
    
    query = db.query(User)
    if data.child_email:
        child = query.filter(User.email == str(data.child_email).strip().lower()).first()
    else:
        child = query.filter(User.binding_code == data.binding_code.strip().upper()).first()

    if not child:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="查無此學生帳號，請確認 Email 或綁定代碼是否正確輸入"
        )

    # 禁止將自己綁定為小孩
    if child.id == current_parent.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="操作無效：無法將自身帳號綁定為子女"
        )

    # 檢查是否已重複綁定
    existing_link = db.query(ParentChild).filter(
        ParentChild.parent_id == current_parent.id,
        ParentChild.child_id == child.id
    ).first()

    if existing_link:
        return {
            "message": f"您先前已成功綁定學生【{child.name}】！",
            "child_id": child.id,
            "child_name": child.name
        }

    # 建立正式關聯
    new_relation = ParentChild(
        parent_id=current_parent.id,
        child_id=child.id,
        is_verified=True
    )
    db.add(new_relation)
    db.commit()

    return {
        "message": f"🎉 成功添加並綁定子女【{child.name}】，您現在可隨時查看其學習進度與指派任務！",
        "child_id": child.id,
        "child_name": child.name
    }

# ==============================================================================
# 2. 列出當前家長已綁定之所有子女概況清單
# ==============================================================================
@router.get("/children", response_model=List[ChildSummaryResponse], summary="取得家長所屬子女學習進度清單 (強制關聯過濾)")
def get_bound_children(
    current_parent: User = Depends(require_roles([ROLE_PARENT])),
    db: Session = Depends(get_db)
):
    """
    僅回傳屬於 current_parent 的小孩資料，徹底防止水平窺探其他家庭的學生數據。
    """
    relations = db.query(ParentChild).filter(ParentChild.parent_id == current_parent.id).all()
    
    today_start = datetime.datetime.now(datetime.timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    summaries: List[ChildSummaryResponse] = []

    for rel in relations:
        child = rel.child
        if not child:
            continue

        # 計算今日答題題數
        today_count = db.query(StudyLog).filter(
            StudyLog.user_id == child.id,
            StudyLog.created_at >= today_start
        ).count()

        # 錯題本統計
        total_mistakes = db.query(MistakeNotebook).filter(MistakeNotebook.user_id == child.id).count()
        graduated_mistakes = db.query(MistakeNotebook).filter(
            MistakeNotebook.user_id == child.id,
            MistakeNotebook.is_graduated == True
        ).count()

        # 段考考程概況
        plan = db.query(ExamPlan).filter(
            ExamPlan.user_id == child.id,
            ExamPlan.is_enabled == True
        ).first()

        active_exam_name = plan.exam_name if plan else None
        exam_progress = plan.current_progress if plan else None
        exam_days_remaining = None
        if plan:
            try:
                target_dt = datetime.datetime.strptime(plan.exam_date, "%Y-%m-%d").date()
                exam_days_remaining = max(0, (target_dt - datetime.date.today()).days)
            except Exception:
                exam_days_remaining = 0

        # 待完成作業數
        pending_hw_count = db.query(HomeworkAssignment).filter(
            HomeworkAssignment.child_id == child.id,
            HomeworkAssignment.status == "pending"
        ).count()

        lvl_info = get_level_info(child.exp)

        summaries.append(ChildSummaryResponse(
            child_id=child.id,
            name=child.name,
            email=child.email,
            avatar=child.avatar,
            age=child.age,
            is_minor=child.is_minor,
            binding_code=child.binding_code,
            exp=child.exp,
            level=lvl_info["level"],
            level_title=lvl_info["title"],
            today_practiced_count=today_count,
            total_mistakes=total_mistakes,
            graduated_mistakes=graduated_mistakes,
            active_exam_plan=active_exam_name,
            exam_days_remaining=exam_days_remaining,
            exam_progress=exam_progress,
            pending_homeworks_count=pending_hw_count
        ))

    return summaries

# ==============================================================================
# 3. 家長指派作業給指定子女 (嚴格防水平越權檢驗)
# ==============================================================================
@router.post("/homework", response_model=HomeworkResponse, summary="家長指派自主練習作業 (嚴格 BOLA 關聯校驗)")
def assign_homework(
    data: HomeworkAssignmentCreate,
    current_parent: User = Depends(require_roles([ROLE_PARENT])),
    db: Session = Depends(get_db)
):
    """
    指派作業關鍵資安防護：
    - verify_parent_child_relationship 會先確認 data.child_id 是否確實是該家長的子女。
    - 若非其子女，立即拋出 403 Forbidden 阻斷！
    """
    child = verify_parent_child_relationship(current_parent, data.child_id, db)

    homework = HomeworkAssignment(
        parent_id=current_parent.id,
        child_id=child.id,
        title=data.title,
        description=data.description,
        subject=data.subject,
        target_count=data.target_count,
        completed_count=0,
        due_date=data.due_date,
        status="pending"
    )
    db.add(homework)
    db.commit()
    db.refresh(homework)

    return HomeworkResponse(
        id=homework.id,
        child_id=child.id,
        child_name=child.name,
        title=homework.title,
        description=homework.description,
        subject=homework.subject,
        target_count=homework.target_count,
        completed_count=homework.completed_count,
        due_date=homework.due_date,
        status=homework.status,
        created_at=homework.created_at.strftime("%Y-%m-%d %H:%M")
    )

# ==============================================================================
# 4. 取得家長指派之所有作業清單
# ==============================================================================
@router.get("/homeworks", response_model=List[HomeworkResponse], summary="取得家長指派的所有作業狀態")
def get_parent_homeworks(
    child_id: Optional[int] = Query(None, description="可選：特定子女 ID"),
    current_parent: User = Depends(require_roles([ROLE_PARENT])),
    db: Session = Depends(get_db)
):
    """
    查詢家長指派的作業清單。若指定 child_id，則先通過防越權關聯核實。
    """
    query = db.query(HomeworkAssignment).filter(HomeworkAssignment.parent_id == current_parent.id)

    if child_id:
        # 防越權校驗
        verify_parent_child_relationship(current_parent, child_id, db)
        query = query.filter(HomeworkAssignment.child_id == child_id)

    homeworks = query.order_by(HomeworkAssignment.created_at.desc()).all()

    results: List[HomeworkResponse] = []
    for hw in homeworks:
        child_name = hw.child.name if hw.child else "學生"
        results.append(HomeworkResponse(
            id=hw.id,
            child_id=hw.child_id,
            child_name=child_name,
            title=hw.title,
            description=hw.description,
            subject=hw.subject,
            target_count=hw.target_count,
            completed_count=hw.completed_count,
            due_date=hw.due_date,
            status=hw.status,
            created_at=hw.created_at.strftime("%Y-%m-%d %H:%M")
        ))

    return results
