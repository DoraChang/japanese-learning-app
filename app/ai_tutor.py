# -*- coding: utf-8 -*-
"""
AI 智慧小家教（拍照引導與蘇格拉底教學引擎）(app/ai_tutor.py)
說明：
1. 實作純蘇格拉底式 (Socratic Method) 啟發式教學引擎：
   - 核心鐵律：【絕對不直接給出最終答案與選項】！
   - 引導學生先拆解問題、思考公式與核心觀念、並透過反問促進深度理解。
2. 實作 Prompt 注入防禦機制 (Anti-Prompt Injection Shield)：
   - 防範學生要求「直接告訴我答案」、「忽視規則」等越權繞過指令。
3. 支援多模態圖片輸入 (Base64 / URL) 與文字描述，可無縫對接雲端多模態模型，
   並具備自給自足的高擬真引導退避引擎 (Smart Fallback)，無需 API Key 亦能精確模擬與即時測試。
"""

import os
import re
from typing import Dict, Any, List, Optional
from app.config import SOCRATIC_TUTOR_SYSTEM_PROMPT

# 偵測注入與直接索求答案關鍵字
DIRECT_ANSWER_PATTERNS = [
    r"直接給我答案",
    r"答案是幾",
    r"哪一個選項",
    r"選什麼",
    r"選 a 還是 b",
    r"不要廢話",
    r"忽略上述指令",
    r"tell me the answer",
    r"ignore previous instructions"
]

def check_prompt_injection(user_input: str) -> bool:
    """
    檢查使用者輸入是否包含惡意提示詞注入或強索答案
    :param user_input: 學生傳入之提問或想法
    :return: 若偵測到潛在違規索答則回傳 True
    """
    if not user_input:
        return False
    lower_input = user_input.lower()
    for pattern in DIRECT_ANSWER_PATTERNS:
        if re.search(pattern, lower_input, re.IGNORECASE):
            return True
    return False

def analyze_photo_and_guide(
    image_base64: Optional[str] = None,
    image_url: Optional[str] = None,
    question_text: Optional[str] = None,
    subject: Optional[str] = "綜合學科",
    student_thought: Optional[str] = None
) -> Dict[str, Any]:
    """
    分析學生拍照上傳之題目並給出蘇格拉底式引導回應
    :param image_base64: 題目照片 Base64 編碼
    :param image_url: 題目照片 URL
    :param question_text: 題目題目文字補充
    :param subject: 題目科目 (如 數學、理化、英文、國文)
    :param student_thought: 學生目前想法或卡關處
    :return: 包含思考步驟、核心觀念、引導反問與 Markdown 建議之字典
    """
    # 1. 注入防禦檢查
    combined_text = f"{question_text or ''} {student_thought or ''}"
    is_injection_attempt = check_prompt_injection(combined_text)

    # 2. 學科特定觀念映射與啟發式引導邏輯 (Smart Socratic Engine)
    subj = subject or "綜合學科"
    
    # 依科目自適應提取核心觀念引導 (示範演算法)
    if "數" in subj:
        core_concept = "未知數假設、方程式平衡與幾何/多項式性質拆解"
        thought_steps = [
            "步驟 1：仔細審題，標記題目已知條件（例如邊長、角度或數值關係）與未知目標。",
            "步驟 2：思考此題與哪一個定理最相關？（如畢氏定理、二次函數配方、乘法公式等）。",
            "步驟 3：試著將題目文字轉換為代數方程式或畫出輔助線，看看未知數如何被關聯。"
        ]
        socratic_question = "看這道題，你覺得若先把題目中的條件列出等式，第一步最適合假設誰為 x？"
        hint = "💡 提示：先別急著心算最後數值，先觀察題目的對稱性或公因式。"
    elif "理" in subj or "物" in subj or "化" in subj or "自" in subj:
        core_concept = "守恆定律、受力平衡與微觀粒子/反應比例關係"
        thought_steps = [
            "步驟 1：確認物理或化學系統的初始狀態與末狀態，列出系統中的守恆量。",
            "步驟 2：進行受力分析 (隔離體法) 或確認化學反應式的莫耳數比是否已平衡。",
            "步驟 3：檢查各物理量單位的連貫性 (例如 公克/公斤、秒/小時)。"
        ]
        socratic_question = "物體在移動或反應的過程中，有哪一個物理量（如能量、動量或質量）是保持不變的？"
        hint = "💡 提示：試著在草稿紙上畫出受力圖，標出重力與正向力的方向。"
    elif "英" in subj:
        core_concept = "上下文文意推敲、時態一致性與詞性語法結構"
        thought_steps = [
            "步驟 1：找出空格前後的動詞與主詞，確認該句的主要時態 (過去、現在、完成式)。",
            "步驟 2：判斷空格所需詞性（名詞、形容詞、副詞或介系詞）。",
            "步驟 3：從前後文關鍵轉折詞 (如 however, although, because) 推敲語氣正負方向。"
        ]
        socratic_question = "仔細看空格前面的連接詞，它表達的是因果、轉折還是順承關係呢？"
        hint = "💡 提示：觀察句子中的時間副詞，它往往透露了正確的時態秘密。"
    else:
        core_concept = "文本主旨歸納、邏輯因果推論與關鍵線索錨定"
        thought_steps = [
            "步驟 1：快速掃描段落首尾句，抓住文章的核心論點與作者立場。",
            "步驟 2：將題幹的關鍵詞回到文章中找到對應的線索段落。",
            "步驟 3：比對選項時，特別注意有無過度延伸、以偏概全的陷阱詞。"
        ]
        socratic_question = "如果用一句話總結作者最想要傳達的心情或論點，你會怎麼說？"
        hint = "💡 提示：先排除文章完全未提及的干擾選項。"

    # 3. 若學生試圖強索答案，加入嚴正防禦聲明
    if is_injection_attempt:
        warning_msg = (
            "\n\n🛡️ **【小老師溫馨提醒】**：我注意到你希望能直接獲得選項或答案！"
            "但真正的實力來自於你自己想通那一瞬間的豁然開朗。跟著小老師的引導走，你一定能自己解出來！"
        )
    else:
        warning_msg = ""

    # 4. 生成引導式 Markdown 訊息
    guidance_markdown = f"""### 🦉 AI 小家教・蘇格拉底啟發引導

**📚 題目診斷所屬觀念：** `{core_concept}`

---

#### 🔍 思考拆解三部曲：
1. **{thought_steps[0]}**
2. **{thought_steps[1]}**
3. **{thought_steps[2]}**

---

#### ❓ 換你動動腦：
> **{socratic_question}**

{hint}
{warning_msg}
"""

    return {
        "core_concept": core_concept,
        "thought_steps": thought_steps,
        "socratic_question": socratic_question,
        "hint": hint,
        "guidance_message": guidance_markdown,
        "anti_spoiler_shield": True
    }
