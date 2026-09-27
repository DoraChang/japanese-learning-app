# -*- coding: utf-8 -*-
"""
智慧考程與每日行程規劃排程演算法 (app/scheduler_algo.py)
說明：
1. 實作非強制性彈性考程引擎的核心排程演算法。
2. 計算考前剩餘天數，扣除考前緩衝休息與衝刺天數 (buffer_days) 後，將各科章節均勻分派至各學習日。
3. 考前緩衝天數自動設定為「錯題全盤複習、總結複習與考前作息調節」，不安排全新章節。
4. 支援「超前預習演算法」：當學生當前進度超前時，動態推薦下階段單元預習與挑戰題。
"""

import datetime
import math
from typing import List, Dict, Any, Tuple
from app.schemas import ExamScopeItem, DailyScheduleItem, DailyTask

def generate_smart_daily_schedule(
    start_date_str: str,
    exam_date_str: str,
    buffer_days: int,
    subjects_scope: List[Dict[str, Any]],
    current_progress: int = 0
) -> Tuple[List[Dict[str, Any]], int, int, bool]:
    """
    智慧考程排程核心演算法
    :param start_date_str: 規劃起始日 (YYYY-MM-DD)
    :param exam_date_str: 段考目標日 (YYYY-MM-DD)
    :param buffer_days: 考前保留緩衝與複習衝刺天數
    :param subjects_scope: 各科考試單元與章節清單
    :param current_progress: 目前已完成之進度百分比 (0~100)
    :return: (daily_schedule_list, total_days, days_remaining, is_ahead)
    """
    try:
        start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()
        exam_date = datetime.datetime.strptime(exam_date_str, "%Y-%m-%d").date()
    except ValueError:
        # 日期格式異常保護
        start_date = datetime.date.today()
        exam_date = start_date + datetime.timedelta(days=14)

    today = datetime.date.today()
    total_days = max(1, (exam_date - start_date).days)
    days_remaining = max(0, (exam_date - today).days)

    # 緩衝天數合理性防護：最多不超過總天數的 50%
    actual_buffer_days = min(buffer_days, max(1, total_days // 2))
    effective_study_days = max(1, total_days - actual_buffer_days)

    # 1. 攤平所有需要研讀的章節單元
    all_chapter_tasks: List[Dict[str, str]] = []
    for item in subjects_scope:
        subject = item.get("subject", "主要學科")
        chapters = item.get("chapters", [])
        for ch in chapters:
            all_chapter_tasks.append({
                "subject": subject,
                "chapter": ch
            })

    total_task_count = len(all_chapter_tasks)
    
    # 2. 計算每日應完成章節數 (平均分攤)
    if total_task_count == 0:
        tasks_per_day = 1
    else:
        tasks_per_day = math.ceil(total_task_count / effective_study_days)

    # 3. 逐日產生行程清單
    schedule: List[Dict[str, Any]] = []
    task_index = 0

    for day_i in range(total_days):
        current_day_date = start_date + datetime.timedelta(days=day_i)
        date_str = current_day_date.strftime("%Y-%m-%d")
        is_buffer = day_i >= effective_study_days

        # 狀態標記
        if current_day_date < today:
            status = "completed"
        elif current_day_date == today:
            status = "today"
        elif is_buffer:
            status = "buffer"
        else:
            status = "upcoming"

        day_tasks: List[Dict[str, Any]] = []
        buffer_note = None

        if is_buffer:
            # 考前緩衝日：不排新進度，強化錯題本與心理調適
            buffer_remaining_day = total_days - day_i
            buffer_note = f"【考前衝刺與錯題總體檢】第 {buffer_remaining_day} 階段：無新章節負擔，專注於智慧錯題本二次通關與考前作息調節。"
            day_tasks.append({
                "subject": "總複習",
                "chapter": "智慧錯題本集中突破 & 歷屆會考/學測精選",
                "suggested_questions": 15,
                "is_preview": False
            })
        else:
            # 一般研習日：分配章節
            assigned_for_today = 0
            while task_index < total_task_count and assigned_for_today < tasks_per_day:
                task_item = all_chapter_tasks[task_index]
                day_tasks.append({
                    "subject": task_item["subject"],
                    "chapter": task_item["chapter"],
                    "suggested_questions": 10,
                    "is_preview": False
                })
                task_index += 1
                assigned_for_today += 1

            # 若章節已全部分派完畢，但還有剩餘研習日，則轉為模考與深化練習
            if not day_tasks:
                day_tasks.append({
                    "subject": "綜合深化",
                    "chapter": "進階素養題練習與觀念總成",
                    "suggested_questions": 10,
                    "is_preview": True
                })

        schedule.append({
            "day_number": day_i + 1,
            "date": date_str,
            "is_buffer_day": is_buffer,
            "status": status,
            "tasks": day_tasks,
            "buffer_note": buffer_note
        })

    # 4. 判定是否「進度超前」：
    # 期望進度百分比 = (今日已過天數 / 有效學習天數) * 100
    days_elapsed = max(0, (today - start_date).days)
    expected_progress = min(100, int((days_elapsed / effective_study_days) * 100))
    is_ahead = current_progress > (expected_progress + 15)  # 超過期望 15% 視為進度超前

    # 若進度超前，系統在今日任務中追加「彈性超前預習鼓勵」
    if is_ahead:
        for day in schedule:
            if day["status"] == "today":
                day["tasks"].append({
                    "subject": "榮譽超前",
                    "chapter": "🌟 表現優異！進度已超前，推薦自由預習下一冊章節或挑戰 #挑戰題 標籤！",
                    "suggested_questions": 5,
                    "is_preview": True
                })

    return schedule, total_days, days_remaining, is_ahead
