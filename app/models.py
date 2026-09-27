# -*- coding: utf-8 -*-
"""
資料庫關聯模型定義模組 (app/models.py)
說明：
1. 建立符合 RBAC 資安規範與關聯性檢查的 SQLAlchemy ORM 資料表模型。
2. 包含使用者 (User)、家長子女關聯 (ParentChild)、智慧考程 (ExamPlan)、題庫 (Question)、
   錯題本 (MistakeNotebook)、家長指派作業 (HomeworkAssignment)、學習紀錄 (StudyLog) 與意見反饋 (Feedback)。
3. 嚴格防止水平與垂直越權攻擊，確保每個外鍵關聯皆具備索引以提供極速查詢效能。
"""

import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    Text,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Index
)
from sqlalchemy.orm import relationship
from app.database import Base

def utc_now():
    """取得當前 UTC 時間 (支援 Python 3.12+ 現代標準)"""
    return datetime.datetime.now(datetime.timezone.utc)

# ==============================================================================
# 1. 使用者主資料表 (User)
# ==============================================================================
class User(Base):
    """
    使用者核心實體模型
    - 支援 Google OAuth 2.0 帳號綁定。
    - 包含身分角色 (學生、家長、教師)、年齡與未成年判定。
    - 提供未成年學生專屬綁定代碼 (binding_code) 供家長進行授權綁定。
    - 追蹤遊戲化等級 (Level 1~10)、累計經驗值 (EXP) 與連續答對計數 (Combo)。
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="使用者唯一識別碼")
    email = Column(String(128), unique=True, nullable=False, index=True, comment="電子郵件信箱 (Google 帳號)")
    name = Column(String(64), nullable=False, default="學習夥伴", comment="使用者顯示姓名")
    avatar = Column(String(256), nullable=True, comment="頭像圖片網址")
    role = Column(String(20), nullable=False, default="student", comment="身分角色 (student / parent / teacher)")
    age = Column(Integer, nullable=True, comment="使用者年齡")
    is_minor = Column(Boolean, default=True, comment="是否為未成年人 (< 18 歲)")
    binding_code = Column(String(16), unique=True, nullable=True, index=True, comment="未成年專屬家長綁定代碼")
    is_onboarded = Column(Boolean, default=False, comment="是否已完成首次身分與年齡確認精靈")
    
    # 遊戲化系統欄位
    exp = Column(Integer, default=0, comment="目前累積總經驗值")
    level = Column(Integer, default=1, comment="目前遊戲化等級 (1 至 10 級)")
    combo = Column(Integer, default=0, comment="當前連續答對題數 (Combo)")

    # 學習選單偏好
    school_level = Column(String(16), default="junior", comment="學制：junior (國中) / senior (高中)")
    grade = Column(String(16), default="j7", comment="目前就讀年級代碼 (如 j7, j8, j9, s10, s11, s12)")
    theme_preference = Column(String(16), default="system", comment="UI 主題：system (預設) / dark / light")

    # 時間戳記
    created_at = Column(DateTime, default=utc_now, comment="帳號建立時間")
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, comment="最後資料更新時間")

    # 關聯設定
    exam_plans = relationship("ExamPlan", back_populates="student", cascade="all, delete-orphan")
    mistakes = relationship("MistakeNotebook", back_populates="student", cascade="all, delete-orphan")
    study_logs = relationship("StudyLog", back_populates="student", cascade="all, delete-orphan")


# ==============================================================================
# 2. 家長與小孩綁定關聯資料表 (ParentChild)
# ==============================================================================
class ParentChild(Base):
    """
    家長與子女關聯資料表
    - 嚴格落實 RBAC 關聯性驗證，家長只能存取存在於此表之子女資料。
    - 防止 BOLA / IDOR 越權攻擊之核心基石。
    """
    __tablename__ = "parent_children"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="關聯唯一識別碼")
    parent_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True, comment="家長使用者識別碼")
    child_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True, comment="子女使用者識別碼")
    is_verified = Column(Boolean, default=True, comment="是否完成授權驗證")
    created_at = Column(DateTime, default=utc_now, comment="綁定建立時間")

    # 建立複合唯一索引，防止重複綁定同一小孩
    __table_args__ = (
        UniqueConstraint("parent_id", "child_id", name="uq_parent_child"),
    )

    parent = relationship("User", foreign_keys=[parent_id])
    child = relationship("User", foreign_keys=[child_id])


# ==============================================================================
# 3. 題庫資料表 (Question)
# ==============================================================================
class Question(Base):
    """
    精準國高中題庫模型
    - 支援依學制、年級、出版社、科目與章節進行篩選。
    - 支援限定標籤系統 (#期中重點, #易混淆題, #挑戰題, #歷屆會考, #素養導向)。
    """
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="題目唯一識別碼")
    school_level = Column(String(16), nullable=False, index=True, comment="學制：junior / senior")
    grade = Column(String(16), nullable=False, index=True, comment="年級代碼 (j7, j8, j9, s10, s11, s12)")
    publisher = Column(String(32), nullable=False, index=True, comment="出版社 (康軒, 南一, 翰林, 龍騰, 三民, 泰宇)")
    subject = Column(String(32), nullable=False, index=True, comment="科目 (國文, 英文, 數學, 自然, 物理, 化學...)")
    chapter = Column(String(64), nullable=False, comment="課次或章節名稱")
    content = Column(Text, nullable=False, comment="題目內文描述")
    options = Column(Text, nullable=False, comment="選項 JSON 字串，格式為 [A, B, C, D]")
    correct_answer = Column(String(8), nullable=False, comment="標準答案 (A / B / C / D)")
    explanation = Column(Text, nullable=True, comment="題目完整詳解與觀念解說")
    tags = Column(String(256), nullable=True, index=True, comment="題目限定標籤 (以逗號分隔，如 #期中重點,#易混淆題)")
    difficulty = Column(Integer, default=2, comment="難易度等級 (1: 基礎, 2: 中等, 3: 進階, 4: 挑戰)")
    created_at = Column(DateTime, default=utc_now, comment="題目建立時間")


# ==============================================================================
# 4. 【選填功能】智慧考程與每日行程規劃資料表 (ExamPlan)
# ==============================================================================
class ExamPlan(Base):
    """
    學生個人智慧考程排程模型
    - 非強制性：學生可自由選擇是否啟用 (is_enabled)。
    - 若啟用，系統排程演算法會依據考試剩餘天數自動計算每日行程，並預留緩衝休息天數。
    - 支援進度超前自動標記，激勵超前預習。
    """
    __tablename__ = "exam_plans"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="考程規劃唯一識別碼")
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True, comment="學生使用者識別碼")
    is_enabled = Column(Boolean, default=False, comment="是否啟用考程規劃 (False 則為自由刷題模式)")
    exam_name = Column(String(64), nullable=False, default="第一次段考", comment="考程名稱 (如：第一次段考、第二次段考、期末考)")
    exam_date = Column(String(16), nullable=False, comment="段考目標日期 (YYYY-MM-DD)")
    start_date = Column(String(16), nullable=False, comment="排程開始日期 (YYYY-MM-DD)")
    buffer_days = Column(Integer, default=2, comment="考前保留之衝刺與緩衝休息天數")
    subjects_scope = Column(Text, nullable=False, comment="各科考試範圍 JSON 字串")
    daily_schedule = Column(Text, nullable=True, comment="演算法排定之每日推薦進度 JSON 字串")
    current_progress = Column(Integer, default=0, comment="目前排程完成進度百分比 (0 至 100)")
    is_ahead_of_schedule = Column(Boolean, default=False, comment="是否進度超前 (若超前則推薦延伸預習)")
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, comment="最後更新時間")

    student = relationship("User", back_populates="exam_plans")


# ==============================================================================
# 5. 智慧錯題本與熟練度資料表 (MistakeNotebook)
# ==============================================================================
class MistakeNotebook(Base):
    """
    錯題本實體模型
    - 學生答錯題目時自動收錄。
    - 記錄累計答錯次數與連續答對次數 (consecutive_correct)。
    - 連續答對 2 次以上或熟練度達 100% 標記為「已熟練畢業 (is_graduated)」。
    """
    __tablename__ = "mistake_notebooks"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="錯題紀錄識別碼")
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True, comment="學生識別碼")
    question_id = Column(Integer, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True, comment="題庫識別碼")
    wrong_count = Column(Integer, default=1, comment="歷史答錯次數累計")
    consecutive_correct = Column(Integer, default=0, comment="複習連續答對次數")
    mastery_rate = Column(Integer, default=0, comment="目前熟練度百分比 (0 至 100)")
    is_graduated = Column(Boolean, default=False, comment="是否已熟練畢業 (移出待複習隊列)")
    student_notes = Column(Text, nullable=True, comment="學生自訂思考筆記與解題備忘")
    last_reviewed_at = Column(DateTime, default=utc_now, comment="最近複習作答時間")
    created_at = Column(DateTime, default=utc_now, comment="初次答錯加入時間")

    # 確保每個學生對同一題目只存在一筆錯題本主記錄
    __table_args__ = (
        UniqueConstraint("user_id", "question_id", name="uq_user_mistake_question"),
    )

    student = relationship("User", back_populates="mistakes")
    question = relationship("Question")


# ==============================================================================
# 6. 家長指派作業資料表 (HomeworkAssignment)
# ==============================================================================
class HomeworkAssignment(Base):
    """
    家長指派作業實體模型
    - 家長可針對已綁定子女指派練習作業。
    - 追蹤目標題數與完成狀態。
    """
    __tablename__ = "homework_assignments"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="作業指派唯一識別碼")
    parent_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True, comment="家長識別碼")
    child_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True, comment="子女識別碼")
    title = Column(String(128), nullable=False, comment="作業名稱 (如：數學第一章重點複習)")
    description = Column(Text, nullable=True, comment="作業說明或家長叮嚀")
    subject = Column(String(32), nullable=False, comment="指派作業科目")
    target_count = Column(Integer, default=5, comment="目標完成題數")
    completed_count = Column(Integer, default=0, comment="目前已完成題數")
    due_date = Column(String(16), nullable=False, comment="截止日期 (YYYY-MM-DD)")
    status = Column(String(16), default="pending", comment="作業狀態 (pending: 進行中 / completed: 已完成)")
    created_at = Column(DateTime, default=utc_now, comment="指派建立時間")

    parent = relationship("User", foreign_keys=[parent_id])
    child = relationship("User", foreign_keys=[child_id])


# ==============================================================================
# 7. 學習日誌與答題遙測資料表 (StudyLog)
# ==============================================================================
class StudyLog(Base):
    """
    答題日誌資料表
    - 記錄每筆刷題作答明細，用於統計圖表、EXP 計算與家長監控面板。
    """
    __tablename__ = "study_logs"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="日誌識別碼")
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True, comment="作答學生識別碼")
    question_id = Column(Integer, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True, comment="題目識別碼")
    selected_option = Column(String(8), nullable=False, comment="學生所選選項 (A/B/C/D)")
    is_correct = Column(Boolean, nullable=False, comment="是否答對")
    exp_earned = Column(Integer, default=0, comment="本次答題獲得之經驗值")
    created_at = Column(DateTime, default=utc_now, comment="作答時間戳記")

    student = relationship("User", back_populates="study_logs")
    question = relationship("Question")


# ==============================================================================
# 8. 即時意見反饋資料表 (Feedback)
# ==============================================================================
class Feedback(Base):
    """
    使用者意見反饋模型
    - 收集學生、家長與教師的改進建議與 Bug 回報。
    """
    __tablename__ = "feedbacks"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="反饋識別碼")
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True, comment="反饋者識別碼")
    category = Column(String(32), default="suggestion", comment="分類 (suggestion: 建議 / bug: 程式錯誤 / question: 題目疑義)")
    content = Column(Text, nullable=False, comment="反饋內容詳情")
    contact_email = Column(String(128), nullable=True, comment="聯絡信箱 (可選)")
    status = Column(String(16), default="received", comment="處理狀態 (received / reviewing / resolved)")
    created_at = Column(DateTime, default=utc_now, comment="提交時間")

    user = relationship("User")
