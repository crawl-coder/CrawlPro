# /backend/app/api/deps.py

from typing import Generator, Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import engine
from app import models
from app.crud import user as crud_user
from app.schemas.token import TokenPayload  # 确保路径正确

# --- 1. OAuth2 密码流方案 ---
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)


# --- 2. 数据库会话依赖 ---
def get_db() -> Generator[Session, None, None]:
    """为每个请求提供独立的数据库会话"""
    with Session(engine) as db:
        yield db


# --- 3. 获取当前活跃用户（核心依赖）---
def get_current_active_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> models.User:
    """
    解码 JWT 并返回当前已认证且活跃的用户。
    若 token 无效、过期、用户不存在或被禁用，则抛出相应异常。
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        username: str = payload.get("sub")
        if not username:
            raise credentials_exception
        # 可选：验证 payload 结构
        TokenPayload(sub=username)
    except (JWTError, ValidationError):
        raise credentials_exception

    user = crud_user.get_by_username(db, username=username)
    if not user:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )

    return user


# --- 4. 获取当前活跃超级用户 ---
def get_current_active_superuser(
    current_user: models.User = Depends(get_current_active_user)
) -> models.User:
    """
    确保当前用户是活跃的超级管理员。
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    return current_user


# --- 5. 类型别名（推荐在路由中使用）---

# 普通登录用户（已激活）
CurrentUser = Annotated[models.User, Depends(get_current_active_user)]

# 超级管理员用户
CurrentSuperuser = Annotated[models.User, Depends(get_current_active_superuser)]