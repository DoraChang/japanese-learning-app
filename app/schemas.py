# -*- coding: utf-8 -*-
"""
Pydantic 資料驗證與輸出資料模型 (app/schemas.py)
說明：
1. 使用 Pydantic v2 定義全系統嚴格輸入參數校驗與輸出資料結構。
2. 包含 Google 登錄、年齡與身分驗證精靈、考程排程、錯題複習、家長監控與 AI 蘇格拉底引導模型。
3. 杜絕型別注入與非法輸入，全面強化後端 API 健全性。
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

# ==============================================================================
# 1. 身分驗證與個人設定模型 (Authentication & Profile)
# ==============================================================================
class UserLoginRequest(BaseModel):
    """Google OAuth 2.0 登錄請求模型"""
    email: str = Field(..., pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$", description="Google 帳號 Email")
    name: Optional[str] = Field("學習夥伴", description="使用者顯示名稱")
    avatar: Optional[str] = Field(None, description="使用者 Google 頭像 URL")
    google_token: Optional[str] = Field(None, description="Google OAuth ID Token (本機測試模式可帶入模擬憑證)")

class UserOnboardingRequest(BaseModel):
    """首次登錄身分選擇與年齡確認精靈模型"""
    role: str = Field(..., description="身分角色: student (學生), parent (家長), teacher (教師)")
    age: int = Field(..., ge=6, le=100, description="使用者實質年齡 (需介於 6 到 100 歲)")
    school_level: Optional[str] = Field("junior", description="學制: junior (國中), senior (高中)")
    grade: Optional[str] = Field("j7", description="年級代碼 (如 j7, j8, j9, s10, s11, s12)")

class UserProfileResponse(BaseModel):
    """使用者個人資訊與遊戲化狀態回傳模型"""
    id: int
    email: str
    name: str
    avatar: Optional[str] = None
    role: str
    age: Optional[int] = None
    is_minor: bool
    binding_code: Optional[str] = None
    is_onboarded: bool
    exp: int
    level: int
    level_title: str
    next_level_exp: int
    level_progress_percent: int
    combo: int
    school_level: str
    grade: str
    theme_preference: str

    class Config:
        from_attributes = True

class UserThemeUpdateRequest(BaseModel):
    """主題切換設定更新模型"""
    theme_preference: str = Field(..., pattern="^(system|dark|light)$", description="UI主題: system, dark, light")

class UserCurriculumUpdateRequest(BaseModel):
    """教材版本與年級更新模型"""
    school_level: str = Field(..., pattern="^(junior|senior)$", description="學制代碼")
    grade: str = Field(..., description="年級代碼")

# ==============================================================================
# 2. 題庫查詢與作答模型 (Questions & Quiz)
# ==============================================================================
class QuestionResponse(BaseModel):
    """題目回傳模型"""
    id: int
    school_level: str
    grade: str
    publisher: str
    subject: str
    chapter: str
    content: str
    options: List[str]
    tags: List[str]
    difficulty: int

class QuestionSubmitAnswerRequest(BaseModel):
    """送出題目答案請求模型"""
    question_id: int
    selected_option: str = Field(..., pattern="^[A-D]$", description="選項 A, B, C 或 D")

class QuestionAnswerResult(BaseModel):
    """作答結算與回饋模型"""
    is_correct: bool
    correct_answer: str
    explanation: Optional[str] = None
    exp_earned: int
    current_combo: int
    new_total_exp: int
    new_level: int
    new_level_title: str
    is_level_up: bool
    message: str

# ==============================================================================
# 3. 智慧考程與每日行程規劃模型 (Exam Planner Engine)
# ==============================================================================
class ExamScopeItem(BaseModel):
    """單一學科考試範圍"""
    subject: str = Field(..., description="科目名稱")
    chapters: List[str] = Field(..., description="考試章節清單")

class ExamPlanConfig(BaseModel):
    """考程設定與排程請求模型"""
    is_enabled: bool = Field(False, description="是否啟用智慧考程規劃")
    exam_name: str = Field("第一次段考", description="段考名稱")
    exam_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="考試日期 (YYYY-MM-DD)")
    start_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="開始日期 (YYYY-MM-DD)")
    buffer_days: int = Field(2, ge=0, le=14, description="考前保留緩衝與複習天數")
    subjects_scope: List[ExamScopeItem] = Field(default_factory=list, description="各科範圍清單")

class DailyTask(BaseModel):
    """每日學習任務"""
    subject: str
    chapter: str
    suggested_questions: int
    is_preview: bool = False

class DailyScheduleItem(BaseModel):
    """每日行程推薦卡片"""
    day_number: int
    date: str
    is_buffer_day: bool
    status: str  # "completed", "today", "upcoming", "buffer"
    tasks: List[DailyTask]
    buffer_note: Optional[str] = None

class ExamPlanDetailResponse(BaseModel):
    """智慧考程詳細檢視回傳模型"""
    id: Optional[int] = None
    is_enabled: bool
    exam_name: str
    exam_date: str
    start_date: str
    buffer_days: int
    days_remaining: int
    total_days: int
    current_progress: int
    is_ahead_of_schedule: bool
    subjects_scope: List[ExamScopeItem]
    daily_schedule: List[DailyScheduleItem]

# ==============================================================================
# 4. 智慧錯題本與熟練度機制模型 (Mistake Notebook)
# ==============================================================================
class MistakeItemResponse(BaseModel):
    """錯題清單項目模型"""
    id: int
    question_id: int
    school_level: str
    grade: str
    publisher: str
    subject: str
    chapter: str
    content: str
    options: List[str]
    tags: List[str]
    wrong_count: int
    consecutive_correct: int
    mastery_rate: int
    is_graduated: bool
    student_notes: Optional[str] = None
    last_reviewed_at: Optional[str] = None

class MistakeReviewSubmitRequest(BaseModel):
    """錯題複習送出模型"""
    mistake_id: int
    selected_option: str = Field(..., pattern="^[A-D]$")
    student_notes: Optional[str] = None

class MistakeReviewResult(BaseModel):
    """錯題複習判定回饋模型"""
    is_correct: bool
    correct_answer: str
    explanation: Optional[str] = None
    consecutive_correct: int
    mastery_rate: int
    is_graduated: bool
    exp_earned: int
    message: str

# ==============================================================================
# 5. 家長專區與作業指派模型 (Parent Dashboard)
# ==============================================================================
class AddChildRequest(BaseModel):
    """家長綁定小孩帳號請求模型"""
    child_email: Optional[str] = Field(None, description="小孩的 Google 帳號 Email")
    binding_code: Optional[str] = Field(None, description="小孩個人專屬未成年綁定代碼")

class HomeworkAssignmentCreate(BaseModel):
    """家長指派作業請求模型"""
    child_id: int = Field(..., description="目標子女識別碼")
    title: str = Field(..., min_length=2, max_length=128, description="作業名稱")
    description: Optional[str] = Field(None, description="備註叮嚀")
    subject: str = Field(..., description="科目")
    target_count: int = Field(5, ge=1, le=50, description="指派完成題數")
    due_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="截止日期 (YYYY-MM-DD)")

class HomeworkResponse(BaseModel):
    """作業項目回傳模型"""
    id: int
    child_id: int
    child_name: str
    title: str
    description: Optional[str] = None
    subject: str
    target_count: int
    completed_count: int
    due_date: str
    status: str
    created_at: str

class ChildSummaryResponse(BaseModel):
    """家長監控子女學習狀態摘要模型"""
    child_id: int
    name: str
    email: str
    avatar: Optional[str] = None
    age: Optional[int] = None
    is_minor: bool
    binding_code: Optional[str] = None
    exp: int
    level: int
    level_title: str
    today_practiced_count: int
    total_mistakes: int
    graduated_mistakes: int
    active_exam_plan: Optional[str] = None
    exam_days_remaining: Optional[int] = None
    exam_progress: Optional[int] = None
    pending_homeworks_count: int

# ==============================================================================
# 6. AI 拍照導師蘇格拉底引導模型 (AI Photo Tutor)
# ==============================================================================
class AITutorPhotoAskRequest(BaseModel):
    """AI 拍照小家教題目諮詢模型"""
    image_base64: Optional[str] = Field(None, description="題目照片 Base64 編碼字串")
    image_url: Optional[str] = Field(None, description="已上傳題目照片的相對或絕對 URL")
    question_text: Optional[str] = Field(None, description="題目文字補充描述")
    subject: Optional[str] = Field(None, description="題目科目")
    student_thought: Optional[str] = Field(None, description="學生目前卡關的盲點或自己的思考步驟")

class AITutorGuidanceResponse(BaseModel):
    """AI 蘇格拉底引導式回應模型 (不直接給答案)"""
    core_concept: str = Field(..., description="題目所考核心概念或定理")
    thought_steps: List[str] = Field(..., description="引導思考步驟拆解")
    socratic_question: str = Field(..., description="啟發學生自主推導的反問句")
    guidance_message: str = Field(..., description="給學生的完整引導訊息 (Markdown 格式)")
    anti_spoiler_shield: bool = Field(True, description="防爆雷直接答案保護盾狀態")

# ==============================================================================
# 7. 即時意見反饋模型 (Feedback)
# ==============================================================================
class FeedbackCreateRequest(BaseModel):
    """建立意見反饋請求模型"""
    category: str = Field("suggestion", pattern="^(suggestion|bug|question|other)$")
    content: str = Field(..., min_length=5, max_length=1000, description="意見詳情或錯誤描述")
    contact_email: Optional[str] = Field(None, description="方便聯繫的電子郵件")

class FeedbackResponse(BaseModel):
    """意見反饋回傳模型"""
    id: int
    message: str
    status: str
