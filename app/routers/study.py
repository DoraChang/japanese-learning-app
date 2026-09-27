# -*- coding: utf-8 -*-
"""
多維度學習選單與題庫刷題路由模組 (app/routers/study.py)
說明：
1. 提供國高中多維度教材版本選單資料 (學制、年級、出版社、科目與限定標籤)。
2. 支援按條件查詢題庫題目 (支援 #期中重點、#易混淆題、#挑戰題 等限定標籤)。
3. 實作題目作答判定：
   - 答對：核發基礎 15 EXP 與 Combo 連擊加成，更新使用者等級並觸發可能之升級。
   - 答錯：自動將題目收錄進「智慧錯題本 (MistakeNotebook)」歸檔，重設 Combo。
"""

import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Question, MistakeNotebook, StudyLog
from app.schemas import (
    QuestionResponse,
    QuestionSubmitAnswerRequest,
    QuestionAnswerResult
)
from app.security import get_current_user
from app.gamification import (
    EXP_BASE_CORRECT,
    EXP_COMBO_BONUS,
    apply_exp_gain,
    get_level_info
)
from app.config import (
    SCHOOL_LEVELS,
    GRADES_BY_LEVEL,
    PUBLISHERS_BY_LEVEL,
    SUBJECTS_BY_LEVEL,
    QUESTION_TAGS
)

router = APIRouter(prefix="/api/study", tags=["學習選單與題庫刷題"])

# ==============================================================================
# 1. 取得多維度動態教材選單設定
# ==============================================================================
@router.get("/curriculum-options", summary="取得多維度學制、年級、出版社與科目對應選項")
def get_curriculum_options():
    """
    提供前端動態聯動選單資料：
    - 學制 (國中 / 高中)
    - 各學制適用之年級
    - 各學制適用之主流出版社 (如 康軒、南一、翰林、龍騰、三民、泰宇)
    - 核心科目與限定標籤清單
    """
    return {
        "school_levels": SCHOOL_LEVELS,
        "grades_by_level": GRADES_BY_LEVEL,
        "publishers_by_level": PUBLISHERS_BY_LEVEL,
        "subjects_by_level": SUBJECTS_BY_LEVEL,
        "available_tags": QUESTION_TAGS
    }

# ==============================================================================
# 2. 依多維度條件與標籤篩選題目清單
# ==============================================================================
@router.get("/questions", response_model=List[QuestionResponse], summary="取得題庫題目清單 (支援限定標籤篩選)")
def get_questions(
    school_level: Optional[str] = Query(None, description="學制: junior 或 senior"),
    grade: Optional[str] = Query(None, description="年級代碼 (如 j7, s10)"),
    publisher: Optional[str] = Query(None, description="出版社 (康軒, 翰林, 龍騰...)"),
    subject: Optional[str] = Query(None, description="科目 (國文, 英文, 數學...)"),
    tag: Optional[str] = Query(None, description="限定標籤 (如 #期中重點, #挑戰題)"),
    limit: int = Query(20, ge=1, le=100, description="回傳題數上限"),
    db: Session = Depends(get_db)
):
    """
    根據學生所選學制、年級、出版社、科目或限定標籤檢索題目。
    """
    query = db.query(Question)

    if school_level:
        query = query.filter(Question.school_level == school_level)
    if grade:
        query = query.filter(Question.grade == grade)
    if publisher:
        query = query.filter(Question.publisher == publisher)
    if subject:
        query = query.filter(Question.subject == subject)
    if tag:
        query = query.filter(Question.tags.like(f"%{tag}%"))

    questions = query.limit(limit).all()

    results: List[QuestionResponse] = []
    for q in questions:
        # 解析選項 JSON 字串
        try:
            parsed_options = json.loads(q.options)
        except Exception:
            parsed_options = ["A", "B", "C", "D"]

        # 解析標籤清單
        tags_list = [t.strip() for t in q.tags.split(",") if t.strip()] if q.tags else []

        results.append(QuestionResponse(
            id=q.id,
            school_level=q.school_level,
            grade=q.grade,
            publisher=q.publisher,
            subject=q.subject,
            chapter=q.chapter,
            content=q.content,
            options=parsed_options,
            tags=tags_list,
            difficulty=q.difficulty
        ))

    return results

# ==============================================================================
# 3. 提交答案結算與自動入錯題本
# ==============================================================================
@router.post("/submit", response_model=QuestionAnswerResult, summary="提交單題答案並結算 EXP 與錯題收錄")
def submit_question_answer(
    data: QuestionSubmitAnswerRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    刷題核心作答判定：
    - 比對正確答案。
    - 答對：Combo +1，結算基本 EXP 與 Combo 加成，更新使用者等級並檢查是否 Level Up。
    - 答錯：Combo 歸零，並自動收錄至「智慧錯題本」供後續複習。
    - 寫入 StudyLog 供數據分析與家長專區檢視。
    """
    question = db.query(Question).filter(Question.id == data.question_id).first()
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="該題目不存在")

    is_correct = (data.selected_option.strip().upper() == question.correct_answer.strip().upper())

    exp_earned = 0
    is_level_up = False
    message = ""

    if is_correct:
        # 答對邏輯
        current_user.combo += 1
        combo_bonus = min(current_user.combo * EXP_COMBO_BONUS, 20)
        exp_earned = EXP_BASE_CORRECT + combo_bonus

        new_total_exp, new_level, new_title, is_level_up = apply_exp_gain(current_user.exp, exp_earned)
        current_user.exp = new_total_exp
        current_user.level = new_level

        message = f"🎉 答對了！獲得 {exp_earned} EXP (含 Combo x{current_user.combo} 加成)！"
        if is_level_up:
            message += f" 🌟 恭喜晉升至【{new_title}】！"
    else:
        # 答錯邏輯：Combo 重置，自動收錄進入錯題本
        current_user.combo = 0
        exp_earned = 0
        message = "💡 很可惜答錯了，該題目已自動收錄至您的【智慧錯題本】，複習答對即可畢業！"

        # 檢查錯題本是否已存在
        mistake = db.query(MistakeNotebook).filter(
            MistakeNotebook.user_id == current_user.id,
            MistakeNotebook.question_id == question.id
        ).first()

        if mistake:
            mistake.wrong_count += 1
            mistake.consecutive_correct = 0
            mistake.is_graduated = False
            mistake.mastery_rate = max(0, mistake.mastery_rate - 20)
        else:
            new_mistake = MistakeNotebook(
                user_id=current_user.id,
                question_id=question.id,
                wrong_count=1,
                consecutive_correct=0,
                mastery_rate=0,
                is_graduated=False
            )
            db.add(new_mistake)

    # 寫入答題日誌
    log_entry = StudyLog(
        user_id=current_user.id,
        question_id=question.id,
        selected_option=data.selected_option.strip().upper(),
        is_correct=is_correct,
        exp_earned=exp_earned
    )
    db.add(log_entry)
    db.commit()
    db.refresh(current_user)

    lvl_info = get_level_info(current_user.exp)

    return QuestionAnswerResult(
        is_correct=is_correct,
        correct_answer=question.correct_answer,
        explanation=question.explanation,
        exp_earned=exp_earned,
        current_combo=current_user.combo,
        new_total_exp=current_user.exp,
        new_level=lvl_info["level"],
        new_level_title=lvl_info["title"],
        is_level_up=is_level_up,
        message=message
    )
