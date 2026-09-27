# -*- coding: utf-8 -*-
"""
【選填功能】智慧考程與每日行程規劃引擎路由模組 (app/routers/planner.py)
說明：
1. 學生自主選擇啟用/關閉（非強制性）：若關閉，切換為自由自主刷題模式。
2. 啟用時，接收考試名稱、段考日期、起始日、緩衝休息天數與各科範圍清單。
3. 自動調用排程演算法生成每日推薦任務，考前自動保留緩衝期並提供超前預習動態激勵。
"""

import json
import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, ExamPlan
from app.schemas import (
    ExamPlanConfig,
    ExamPlanDetailResponse,
    ExamScopeItem,
    DailyScheduleItem,
    DailyTask
)
from app.security import get_current_user
from app.scheduler_algo import generate_smart_daily_schedule

router = APIRouter(prefix="/api/planner", tags=["智慧考程與每日行程規劃引擎"])

# ==============================================================================
# 1. 取得當前學生之考程與行程規劃
# ==============================================================================
@router.get("", response_model=ExamPlanDetailResponse, summary="取得個人智慧考程與每日推薦行程")
def get_user_exam_plan(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    讀取目前使用者的考程規劃：
    - 若無設定，回傳預設未啟用狀態之模板。
    - 若已啟用，動態運算距離考試剩餘天數、考前緩衝日、各日行程清單與是否進度超前。
    """
    plan = db.query(ExamPlan).filter(ExamPlan.user_id == current_user.id).first()

    today = datetime.date.today().strftime("%Y-%m-%d")
    default_exam_date = (datetime.date.today() + datetime.timedelta(days=21)).strftime("%Y-%m-%d")

    if not plan:
        # 若尚未建立考程，回傳預設初始空架構
        return ExamPlanDetailResponse(
            id=None,
            is_enabled=False,
            exam_name="第一次段考",
            exam_date=default_exam_date,
            start_date=today,
            buffer_days=2,
            days_remaining=21,
            total_days=21,
            current_progress=0,
            is_ahead_of_schedule=False,
            subjects_scope=[],
            daily_schedule=[]
        )

    # 解析存於資料庫的範圍 JSON
    try:
        raw_scope = json.loads(plan.subjects_scope) if plan.subjects_scope else []
    except Exception:
        raw_scope = []

    # 執行排程運算
    schedule_data, total_days, days_remaining, is_ahead = generate_smart_daily_schedule(
        start_date_str=plan.start_date,
        exam_date_str=plan.exam_date,
        buffer_days=plan.buffer_days,
        subjects_scope=raw_scope,
        current_progress=plan.current_progress
    )

    # 轉換成 Pydantic 模型格式
    formatted_scope = [
        ExamScopeItem(subject=s.get("subject", ""), chapters=s.get("chapters", []))
        for s in raw_scope
    ]

    formatted_schedule: list[DailyScheduleItem] = []
    for d in schedule_data:
        tasks = [
            DailyTask(
                subject=t["subject"],
                chapter=t["chapter"],
                suggested_questions=t["suggested_questions"],
                is_preview=t.get("is_preview", False)
            )
            for t in d["tasks"]
        ]
        formatted_schedule.append(DailyScheduleItem(
            day_number=d["day_number"],
            date=d["date"],
            is_buffer_day=d["is_buffer_day"],
            status=d["status"],
            tasks=tasks,
            buffer_note=d.get("buffer_note")
        ))

    return ExamPlanDetailResponse(
        id=plan.id,
        is_enabled=plan.is_enabled,
        exam_name=plan.exam_name,
        exam_date=plan.exam_date,
        start_date=plan.start_date,
        buffer_days=plan.buffer_days,
        days_remaining=days_remaining,
        total_days=total_days,
        current_progress=plan.current_progress,
        is_ahead_of_schedule=is_ahead,
        subjects_scope=formatted_scope,
        daily_schedule=formatted_schedule
    )

# ==============================================================================
# 2. 建立或更新考程設定 (非強制性)
# ==============================================================================
@router.post("", response_model=ExamPlanDetailResponse, summary="儲存或更新智慧考程與範圍設定")
def save_exam_plan(
    config: ExamPlanConfig,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    設定學生個人的考程：
    - is_enabled: 是否啟用（若設為 False 則轉為自主自由刷題模式）
    - exam_name: 段考名稱
    - exam_date: 目標段考日
    - start_date: 起始排程日
    - buffer_days: 考前衝刺與休息天數
    - subjects_scope: 各科考試範圍
    """
    plan = db.query(ExamPlan).filter(ExamPlan.user_id == current_user.id).first()

    scope_json = json.dumps([s.model_dump() for s in config.subjects_scope], ensure_ascii=False)

    if not plan:
        plan = ExamPlan(
            user_id=current_user.id,
            is_enabled=config.is_enabled,
            exam_name=config.exam_name,
            exam_date=config.exam_date,
            start_date=config.start_date,
            buffer_days=config.buffer_days,
            subjects_scope=scope_json,
            current_progress=0,
            is_ahead_of_schedule=False
        )
        db.add(plan)
    else:
        plan.is_enabled = config.is_enabled
        plan.exam_name = config.exam_name
        plan.exam_date = config.exam_date
        plan.start_date = config.start_date
        plan.buffer_days = config.buffer_days
        plan.subjects_scope = scope_json

    db.commit()
    db.refresh(plan)

    # 重新取得排程回傳
    return get_user_exam_plan(current_user=current_user, db=db)

# ==============================================================================
# 3. 快速切換考程啟用開關 (Toggle is_enabled)
# ==============================================================================
@router.patch("/toggle", summary="切換智慧考程啟用開關")
def toggle_exam_plan(
    enabled: bool,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    一鍵切換「智慧考程規劃」或「自由自主刷題」模式。
    """
    plan = db.query(ExamPlan).filter(ExamPlan.user_id == current_user.id).first()
    if not plan:
        today = datetime.date.today().strftime("%Y-%m-%d")
        exam_date = (datetime.date.today() + datetime.timedelta(days=21)).strftime("%Y-%m-%d")
        plan = ExamPlan(
            user_id=current_user.id,
            is_enabled=enabled,
            exam_name="第一次段考",
            exam_date=exam_date,
            start_date=today,
            buffer_days=2,
            subjects_scope="[]",
            current_progress=0
        )
        db.add(plan)
    else:
        plan.is_enabled = enabled

    db.commit()
    return {"message": "考程狀態更新成功", "is_enabled": enabled}

# ==============================================================================
# 4. 更新學習進度百分比 (可由作答完成自動推進)
# ==============================================================================
@router.patch("/progress", summary="手動或自動更新考程完成百分比")
def update_plan_progress(
    progress_percent: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    更新考程進度百分比 (0 至 100)
    """
    plan = db.query(ExamPlan).filter(ExamPlan.user_id == current_user.id).first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="尚未建立考程規劃")
    
    plan.current_progress = min(100, max(0, progress_percent))
    db.commit()
    return {"message": "考程進度更新成功", "current_progress": plan.current_progress}
