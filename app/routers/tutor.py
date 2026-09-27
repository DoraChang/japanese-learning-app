# -*- coding: utf-8 -*-
"""
AI 智慧小家教（拍照引導模式）路由模組 (app/routers/tutor.py)
說明：
1. 支援學生拍照或上傳題目圖片 (支援 Base64 或 Multipart 檔案上傳)。
2. 呼叫蘇格拉底啟發式教學引擎：
   - 核心原則：【絕對不直接給出最終答案】！
   - 提供觀念拆解三部曲、引導反問句與思考提示。
3. 具備 Prompt 注入攻擊防禦盾，杜絕學生以誘導性字眼強索答案。
"""

import os
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from app.schemas import AITutorPhotoAskRequest, AITutorGuidanceResponse
from app.security import get_current_user
from app.models import User
from app.ai_tutor import analyze_photo_and_guide

router = APIRouter(prefix="/api/tutor", tags=["AI 拍照蘇格拉底小家教"])

# 上傳檔案暫存目錄
UPLOAD_DIR = os.path.join(os.getcwd(), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ==============================================================================
# 1. 拍照上傳題目檔案並獲取蘇格拉底引導
# ==============================================================================
@router.post("/photo-guide", response_model=AITutorGuidanceResponse, summary="拍照上傳題目圖片進行蘇格拉底式思考引導 (不直接給答案)")
async def upload_photo_and_guide(
    file: Optional[UploadFile] = File(None),
    question_text: Optional[str] = Form(None),
    subject: Optional[str] = Form("綜合學科"),
    student_thought: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user)
):
    """
    接收學生拍攝之題目相片與思考盲點：
    - 安全儲存圖片檔案以利後續分析。
    - 啟動蘇格拉底引導分析，輸出步驟拆解與啟發式反問。
    """
    image_url = None
    if file and file.filename:
        # 安全驗證副檔名
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="不支援的圖片格式，請上傳 JPG, PNG 或 WEBP 格式相片"
            )
        
        # 生成安全隨機檔名
        safe_filename = f"{uuid.uuid4().hex}{ext}"
        target_path = os.path.join(UPLOAD_DIR, safe_filename)
        
        contents = await file.read()
        with open(target_path, "wb") as f:
            f.write(contents)
        
        image_url = f"/uploads/{safe_filename}"

    # 執行蘇格拉底引導推論
    result = analyze_photo_and_guide(
        image_url=image_url,
        question_text=question_text,
        subject=subject,
        student_thought=student_thought
    )

    return AITutorGuidanceResponse(
        core_concept=result["core_concept"],
        thought_steps=result["thought_steps"],
        socratic_question=result["socratic_question"],
        guidance_message=result["guidance_message"],
        anti_spoiler_shield=result["anti_spoiler_shield"]
    )

# ==============================================================================
# 2. JSON 格式拍照 Base64 諮詢
# ==============================================================================
@router.post("/ask-json", response_model=AITutorGuidanceResponse, summary="以 JSON 格式提交 Base64 題目圖片與盲點")
def ask_tutor_json(
    data: AITutorPhotoAskRequest,
    current_user: User = Depends(get_current_user)
):
    """
    JSON 格式快速介接端點，支援前端 Camera 串流直接傳入 Base64 圖片。
    """
    result = analyze_photo_and_guide(
        image_base64=data.image_base64,
        image_url=data.image_url,
        question_text=data.question_text,
        subject=data.subject,
        student_thought=data.student_thought
    )

    return AITutorGuidanceResponse(
        core_concept=result["core_concept"],
        thought_steps=result["thought_steps"],
        socratic_question=result["socratic_question"],
        guidance_message=result["guidance_message"],
        anti_spoiler_shield=result["anti_spoiler_shield"]
    )
