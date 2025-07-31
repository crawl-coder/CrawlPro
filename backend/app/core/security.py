# /backend/app/core/security.py

from datetime import datetime, timedelta, timezone
from typing import Any, Union, Optional

from jose import jwt, JWTError
from passlib.context import CryptContext

from app.core.config import settings


# --- 1. 密码哈希配置 ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证明文密码是否与哈希密码匹配

    :param plain_password: 用户输入的明文密码
    :param hashed_password: 数据库中存储的哈希密码
    :return: 匹配返回 True，否则 False
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    生成密码的哈希值

    :param password: 明文密码
    :return: 哈希后的字符串
    """
    return pwd_context.hash(password)


# --- 2. JWT Token 创建 ---
def create_access_token(
    *,
    subject: Union[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    创建 JWT Access Token

    :param subject: Token 主体（通常是 username 或 user_id）
    :param expires_delta: 自定义过期时间（可选）
    :return: 编码后的 JWT 字符串
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "type": "access"
    }
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


# --- 3. JWT Token 解码（可选：用于调试或中间件）---
def decode_token(token: str) -> Optional[dict]:
    """
    解码 JWT Token，不抛异常，返回 None 表示无效

    :param token: JWT 字符串
    :return: 解码后的 payload 或 None
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None


def extract_username_from_token(token: str) -> Optional[str]:
    """
    从 JWT 中提取用户名（sub 字段）

    :param token: JWT 字符串
    :return: 用户名或 None（如果无效）
    """
    payload = decode_token(token)
    if payload:
        return payload.get("sub")
    return None