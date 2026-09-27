# -*- coding: utf-8 -*-
"""
遊戲化經驗值與 10 級升級曲線核心演算法 (app/gamification.py)
說明：
1. 實作 10 級經驗值成長機制：前期快速升級刺激心流與成就感，後期呈階梯式指數成長。
2. 精確計算目前等級、稱號、距離下一級所需 EXP 以及進度百分比條。
3. 支援 Combo 連擊獎勵、錯題畢業獎勵與升級慶祝事件判定。
"""

from typing import Tuple, Dict, Any
from app.config import LEVEL_CONFIG

# ==============================================================================
# 1. 經驗值常數與獎勵設定
# ==============================================================================
EXP_BASE_CORRECT: int = 15      # 單題答對基礎獎勵
EXP_COMBO_BONUS: int = 5        # 連擊每連答一題額外加成 (最高上限 20)
EXP_MISTAKE_GRADUATE: int = 30  # 錯題本題目熟練畢業特別獎勵
EXP_HOMEWORK_COMPLETE: int = 40 # 完成家長指派作業獎勵
EXP_DAILY_SCHEDULE: int = 50    # 完成當日排程目標獎勵

def get_level_info(total_exp: int) -> Dict[str, Any]:
    """
    根據使用者累積的總經驗值，計算當前等級、稱號與升級進度
    :param total_exp: 目前總經驗值
    :return: 包含 level, title, min_exp, max_exp, progress_percent, next_level_exp 的字典
    """
    current_level = 1
    current_title = LEVEL_CONFIG[0]["title"]
    min_exp = 0
    max_exp = LEVEL_CONFIG[0]["max_exp"]

    for config in LEVEL_CONFIG:
        if total_exp >= config["min_exp"]:
            current_level = config["level"]
            current_title = config["title"]
            min_exp = config["min_exp"]
            max_exp = config["max_exp"]
        else:
            break

    # 計算當前等級內的進度百分比
    if current_level >= 10:
        progress_percent = 100
        next_level_exp = 0
    else:
        level_range = max_exp - min_exp
        exp_in_level = total_exp - min_exp
        progress_percent = min(100, max(0, int((exp_in_level / level_range) * 100)))
        next_level_exp = max_exp - total_exp

    return {
        "level": current_level,
        "title": current_title,
        "current_exp": total_exp,
        "min_exp": min_exp,
        "max_exp": max_exp,
        "next_level_exp": next_level_exp,
        "progress_percent": progress_percent
    }

def apply_exp_gain(current_exp: int, gained_exp: int) -> Tuple[int, int, str, bool]:
    """
    為使用者增加經驗值，並計算是否觸發等級躍升 (Level Up)
    :param current_exp: 原有總經驗值
    :param gained_exp: 本次獲得經驗值
    :return: (new_total_exp, new_level, new_title, is_level_up)
    """
    old_info = get_level_info(current_exp)
    new_total_exp = current_exp + gained_exp
    new_info = get_level_info(new_total_exp)

    is_level_up = new_info["level"] > old_info["level"]

    return (
        new_total_exp,
        new_info["level"],
        new_info["title"],
        is_level_up
    )
