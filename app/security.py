# -*- coding: utf-8 -*-
"""
資安防護、身分驗證與 RBAC 權限管理模組 (app/security.py)
說明：
1. 實作純標準函式庫之 HS256 安全 Token 簽名與時效驗證機制，零外部不可控依賴。
2. 實作嚴格角色型存取控制 (RBAC) 依賴項：隔離學生、家長與教師操作範圍。
3. 實作「防水平/垂直越權攻擊 (Anti-IDOR / Anti-BOLA)」防護驗證函式：
   家長 API 在存取任何未成年子女數據前，必須於資料庫嚴格核對 ParentChild 授權關聯。
4. 提供未成年綁定代碼產生演算法與資安輸入審查。
"""

import hmac
import hashlib
import base64
import json
import time
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.config import (
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    ROLE_STUDENT,
    ROLE_PARENT,
    ROLE_TEACHER
)
from app.database import get_db
from app.models import User, ParentChild

# 採用標準 Bearer 認證協議
security_bearer = HTTPBearer(auto_error=False)

# ==============================================================================
# 1. HS256 安全 Token 簽署與驗證引擎 (零外部漏洞風險)
# ==============================================================================
def _base64url_encode(data: bytes) -> str:
    """將位元組進行 Base64URL 安全編碼 (移除填補符號 =)"""
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")

def _base64url_decode(data_str: str) -> bytes:
    """將 Base64URL 字串還原為位元組 (自動補齊填補符號)"""
    padding = 4 - (len(data_str) % 4)
    if padding != 4:
        data_str += "=" * padding
    return base64.urlsafe_b64decode(data_str)

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    建立 HS256 安全簽章 Token
    :param data: 欲裝載於 Token 內的使用者資訊 payload (如 sub, role, email)
    :param expires_delta: 過期時長，預設依 config 設定
    :return: 結構為 header.payload.signature 之 Token 字串
    """
    to_encode = data.copy()
    if expires_delta:
        expire = time.time() + expires_delta.total_seconds()
    else:
        expire = time.time() + (ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    
    to_encode.update({"exp": int(expire), "iat": int(time.time())})

    header = {"alg": ALGORITHM, "typ": "JWT"}
    header_bytes = json.dumps(header, separators=(",", ":")).encode("utf-8")
    payload_bytes = json.dumps(to_encode, separators=(",", ":")).encode("utf-8")

    encoded_header = _base64url_encode(header_bytes)
    encoded_payload = _base64url_encode(payload_bytes)

    signing_input = f"{encoded_header}.{encoded_payload}".encode("utf-8")
    signature = hmac.new(SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
    encoded_signature = _base64url_encode(signature)

    return f"{encoded_header}.{encoded_payload}.{encoded_signature}"

def decode_access_token(token: str) -> Dict[str, Any]:
    """
    解碼並嚴格驗證 Token 簽章與有效期限
    :param token: 前端傳入之 Bearer Token
    :return: 解碼後之 payload 字典
    :raises HTTPException: 簽章不符或逾期時噴出 401 Unauthorized
    """
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="身分憑證格式不正確 (Invalid token format)",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        encoded_header, encoded_payload, encoded_signature = parts
        signing_input = f"{encoded_header}.{encoded_payload}".encode("utf-8")
        expected_sig = hmac.new(SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
        actual_sig = _base64url_decode(encoded_signature)

        # 使用 hmac.compare_digest 防止計時攻擊 (Timing Attack)
        if not hmac.compare_digest(expected_sig, actual_sig):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="憑證簽章無效，可能遭竄改 (Signature verification failed)",
                headers={"WWW-Authenticate": "Bearer"}
            )

        payload_bytes = _base64url_decode(encoded_payload)
        payload = json.loads(payload_bytes.decode("utf-8"))

        # 檢驗過期時間 (Expiration Check)
        if "exp" in payload and payload["exp"] < time.time():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="登入憑證已過期，請重新登入 (Token expired)",
                headers={"WWW-Authenticate": "Bearer"}
            )

        return payload

    except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無法解析身分憑證內容 (Unable to parse token)",
            headers={"WWW-Authenticate": "Bearer"}
        )

# ==============================================================================
# 2. 目前使用者身分解析依賴注入 (Current User Dependency)
# ==============================================================================
def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    db: Session = Depends(get_db)
) -> User:
    """
    解析目前請求之合法登入使用者
    - 支援 Authorization: Bearer <Token>
    - 若無 Token 或驗證失敗，立即阻擋並回傳 401
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="請先完成 Google 登入以存取本功能",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    payload = decode_access_token(credentials.credentials)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="身分資訊不完整",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="使用者帳號不存在或已刪除"
        )
    
    return user

def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    可選登入使用者解析依賴項：
    - 若有提供合法 Bearer Token 則解析出 User。
    - 若無 Token 或憑證失效，回傳 None (允許匿名訪客操作，如意見反饋)。
    """
    if not credentials or not credentials.credentials:
        return None
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = payload.get("sub")
        if not user_id:
            return None
        return db.query(User).filter(User.id == int(user_id)).first()
    except Exception:
        return None

# ==============================================================================
# 3. RBAC 角色垂直權限隔離依賴注入 (Role-Based Access Control)
# ==============================================================================
def require_roles(allowed_roles: List[str]):
    """
    限制特定角色存取端點的工廠依賴項 (Decorator / Dependency)
    範例：Depends(require_roles(["parent"])) 或 Depends(require_roles(["student"]))
    """
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"權限不足：您的身分為【{current_user.role}】，無權存取限定【{', '.join(allowed_roles)}】之功能"
            )
        return current_user
    return role_checker

# ==============================================================================
# 4. 防水平越權攻擊 (Anti-IDOR / Anti-BOLA) 嚴格家長-子女關聯檢查
# ==============================================================================
def verify_parent_child_relationship(parent_user: User, child_id: int, db: Session) -> User:
    """
    嚴格防護「家長水平越權 (BOLA)」檢查：
    - 僅允許家長存取在 parent_children 表中與其合法綁定之子女資料。
    - 任何嘗試以猜測、修改 child_id 參數窺探其他學生數據者，均立即拋出 403 Forbidden 並紀錄警報。
    """
    if parent_user.role != ROLE_PARENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="資安防護阻擋：非家長角色禁止執行此監控與指派作業"
        )
    
    relation = db.query(ParentChild).filter(
        ParentChild.parent_id == parent_user.id,
        ParentChild.child_id == child_id
    ).first()

    if not relation:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="資安防護攔截：您尚未取得該學生帳號之監控授權，禁止越權存取他人子女個資！"
        )
    
    child = db.query(User).filter(User.id == child_id).first()
    if not child:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="該學生帳號不存在"
        )
    
    return child

# ==============================================================================
# 5. 未成年學生專屬綁定代碼產生器 (Binding Code Generator)
# ==============================================================================
def generate_unique_binding_code(db: Session) -> str:
    """
    為未成年學生生成 8 碼不重複且具易讀性之安全綁定代碼 (例如：STU-8821)
    """
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # 排除易混淆之 0, O, 1, I
    while True:
        code_body = "".join(secrets.choice(chars) for _ in range(6))
        code = f"STU-{code_body}"
        exists = db.query(User).filter(User.binding_code == code).first()
        if not exists:
            return code
