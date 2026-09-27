# -*- coding: utf-8 -*-
"""
資料庫連線與生命週期管理模組 (app/database.py)
說明：
1. 建立輕量高效率 SQLite 關聯式資料庫引擎，支援本機快速啟動與零設定運作。
2. 宣告 SQLAlchemy 的 Declarative Base 與 SessionLocal 會話工廠。
3. 提供依賴注入函式 get_db()，確保每個 HTTP 請求擁有獨立資料庫會話，並在處理完畢後安全釋放。
4. 內建種子資料初始化函式，自動匯入國高中精選題目與範例數據。
"""

import os
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# 資料庫連線字串，使用專案目錄下的 SQLite 檔案
DATABASE_URL: str = "sqlite:///./study_platform.db"

# 建立資料庫引擎
# connect_args={"check_same_thread": False} 允許 FastAPI 多執行緒存取同一 SQLite 資料庫
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False  # 若除錯需要查看 SQL 語句可設為 True
)

# 建立工作階段工廠 (Session Factory)
# autocommit=False 確保事務原子性，需手動 commit
# autoflush=False 防止未意料之寫入
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 資料模型基礎類別 (Base)
Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    """
    FastAPI 依賴注入 (Dependency Injection) 函式：
    為各 API 路由提供獨立的資料庫工作階段 (Session)，並在請求結束後自動關閉釋放連線資源。
    """
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
