# -*- coding: utf-8 -*-
"""
精選題庫種子資料與資料庫初始化模組 (app/seed_data.py)
說明：
1. 提供臺灣國中與高中核心科目精選題庫，涵蓋康軒、南一、翰林、龍騰、三民等出版社。
2. 每題包含詳細章節、題目內容、四選一選項、標準答案、詳細解析與限定標籤 (#期中重點, #易混淆題, #挑戰題, #歷屆會考, #素養導向)。
3. 當資料庫題庫表為空時，自動執行種子注入。
"""

import json
from sqlalchemy.orm import Session
from app.models import Question, Base
from app.database import engine

SAMPLE_QUESTIONS = [
    # --- 國中 數學 (翰林 / 康軒) ---
    {
        "school_level": "junior",
        "grade": "j7",
        "publisher": "翰林",
        "subject": "數學",
        "chapter": "第一章 乘法公式與多項式",
        "content": "若 a + b = 7 且 a × b = 10，則 a² + b² 的值為何？",
        "options": json.dumps(["29", "39", "49", "59"], ensure_ascii=False),
        "correct_answer": "A",
        "explanation": "由乘法公式 (a + b)² = a² + 2ab + b²，可得 7² = a² + 2(10) + b²，即 49 = a² + b² + 20，故 a² + b² = 49 - 20 = 29。",
        "tags": "#期中重點,#易混淆題",
        "difficulty": 2
    },
    {
        "school_level": "junior",
        "grade": "j7",
        "publisher": "康軒",
        "subject": "數學",
        "chapter": "第二章 一元一次方程式",
        "content": "小華口袋裡有 5 元與 10 元硬幣共 20 枚，合計 160 元。請問 10 元硬幣有幾枚？",
        "options": json.dumps(["8 枚", "10 枚", "12 枚", "14 枚"], ensure_ascii=False),
        "correct_answer": "C",
        "explanation": "設 10 元硬幣有 x 枚，則 5 元硬幣有 (20 - x) 枚。列式：10x + 5(20 - x) = 160 => 10x + 100 - 5x = 160 => 5x = 60 => x = 12。",
        "tags": "#期中重點,#素養導向",
        "difficulty": 2
    },
    {
        "school_level": "junior",
        "grade": "j8",
        "publisher": "南一",
        "subject": "理化",
        "chapter": "第一單元 物質的組成與反應",
        "content": "在常溫常壓下，將 20 公克的食鹽加入 80 公克的水中，完全溶解無沉澱，此時食鹽水的重量百分率濃度為何？",
        "options": json.dumps(["15%", "20%", "25%", "30%"], ensure_ascii=False),
        "correct_answer": "B",
        "explanation": "重量百分率濃度 = (溶質重 / 溶液重) × 100% = [20 / (20 + 80)] × 100% = (20 / 100) × 100% = 20%。",
        "tags": "#易混淆題,#期中重點",
        "difficulty": 2
    },
    {
        "school_level": "junior",
        "grade": "j9",
        "publisher": "康軒",
        "subject": "理化",
        "chapter": "力與運動",
        "content": "一質量為 2 公斤的物體受到 10 牛頓的水平定力作用，在光滑水平面上運動，則該物體的加速度大小為多少 m/s²？",
        "options": json.dumps(["2 m/s²", "5 m/s²", "10 m/s²", "20 m/s²"], ensure_ascii=False),
        "correct_answer": "B",
        "explanation": "根據牛頓第二運動定律 F = m × a，10 N = 2 kg × a，解得 a = 5 m/s²。",
        "tags": "#歷屆會考,#挑戰題",
        "difficulty": 3
    },
    # --- 國中 英文 ---
    {
        "school_level": "junior",
        "grade": "j8",
        "publisher": "翰林",
        "subject": "英文",
        "chapter": "Unit 3 Past Continuous Tense",
        "content": "When the earthquake happened yesterday afternoon, Linda _______ a shower in the bathroom.",
        "options": json.dumps(["takes", "is taking", "was taking", "has taken"], ensure_ascii=False),
        "correct_answer": "C",
        "explanation": "過去特定時刻正在發生的動作應使用過去進行式 (was/were + V-ing)。主詞 Linda 為第三人稱單數，故選 was taking。",
        "tags": "#期中重點,#易混淆題",
        "difficulty": 2
    },
    # --- 國中 國文 ---
    {
        "school_level": "junior",
        "grade": "j7",
        "publisher": "南一",
        "subject": "國文",
        "chapter": "論語選",
        "content": "《論語》：「學而時習之，不亦說乎？」句中的「說」字通假為何字？其意義為何？",
        "options": json.dumps(["通「悅」，喜悅", "通「說」，解釋", "通「閱」，閱讀", "通「躍」，躍升"], ensure_ascii=False),
        "correct_answer": "A",
        "explanation": "「不亦說乎」之「說」為通假字，音同義通「悅」，意指心中感到愉悅喜樂。",
        "tags": "#期中重點,#觀念破盲",
        "difficulty": 1
    },
    # --- 高中 數學A (龍騰 / 三民) ---
    {
        "school_level": "senior",
        "grade": "s10",
        "publisher": "龍騰",
        "subject": "數學A",
        "chapter": "多項式函數",
        "content": "設 f(x) = x³ - 3x² + 4x - 2，求 f(x) 除以 (x - 1) 的餘式為何？",
        "options": json.dumps(["0", "1", "2", "-1"], ensure_ascii=False),
        "correct_answer": "A",
        "explanation": "由餘式定理，f(x) 除以 (x - 1) 之餘式為 f(1)。代入計算：f(1) = 1³ - 3(1)² + 4(1) - 2 = 1 - 3 + 4 - 2 = 0。",
        "tags": "#期中重點,#歷屆學測",
        "difficulty": 2
    },
    {
        "school_level": "senior",
        "grade": "s11",
        "publisher": "龍騰",
        "subject": "數學A",
        "chapter": "三角函數",
        "content": "若 θ 為第二象限角且 sin θ = 3/5，則 cos θ 的值為何？",
        "options": json.dumps(["4/5", "-4/5", "3/4", "-3/4"], ensure_ascii=False),
        "correct_answer": "B",
        "explanation": "由畢氏三角恆等式 sin²θ + cos²θ = 1，可得 cos²θ = 1 - (3/5)² = 16/25。因 θ 在第二象限，cos θ < 0，故 cos θ = -4/5。",
        "tags": "#易混淆題,#期中重點",
        "difficulty": 2
    },
    # --- 高中 物理 (泰宇 / 龍騰) ---
    {
        "school_level": "senior",
        "grade": "s11",
        "publisher": "泰宇",
        "subject": "物理",
        "chapter": "動量與能量守恆",
        "content": "在沒有外力作用的封閉系統中，兩物體發生完全非彈性碰撞後合為一體運動，下列何者必守恆？",
        "options": json.dumps(["僅動量守恆", "僅動能守恆", "動量與動能皆守恆", "兩者皆不守恆"], ensure_ascii=False),
        "correct_answer": "A",
        "explanation": "在完全非彈性碰撞中，因無外力故「總動量守恆」；但碰撞過程中有最大動能轉化為內能/熱能，故「動能不守恆」。",
        "tags": "#觀念破盲,#挑戰題",
        "difficulty": 3
    },
    # --- 高中 化學 ---
    {
        "school_level": "senior",
        "grade": "s10",
        "publisher": "三民",
        "subject": "化學",
        "chapter": "化學計量與反應",
        "content": "完全燃燒 1 莫耳的甲烷 (CH₄)，需要消耗多少莫耳的氧氣 (O₂)？",
        "options": json.dumps(["1 莫耳", "1.5 莫耳", "2 莫耳", "3 莫耳"], ensure_ascii=False),
        "correct_answer": "C",
        "explanation": "平衡化學反應方程式為：CH₄ + 2O₂ → CO₂ + 2H₂O。1 莫耳 CH₄ 與 2 莫耳 O₂ 剛好完全反應。",
        "tags": "#期中重點,#基礎紮根",
        "difficulty": 1
    }
]

def init_seed_data(db: Session):
    """
    檢查題庫是否已存在數據，若為空則寫入精選國高中種子試題
    """
    count = db.query(Question).count()
    if count == 0:
        for q_data in SAMPLE_QUESTIONS:
            question = Question(
                school_level=q_data["school_level"],
                grade=q_data["grade"],
                publisher=q_data["publisher"],
                subject=q_data["subject"],
                chapter=q_data["chapter"],
                content=q_data["content"],
                options=q_data["options"],
                correct_answer=q_data["correct_answer"],
                explanation=q_data["explanation"],
                tags=q_data["tags"],
                difficulty=q_data["difficulty"]
            )
            db.add(question)
        db.commit()
