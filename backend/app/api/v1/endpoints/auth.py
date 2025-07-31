# /backend/app/api/v1/endpoints/auth.py

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app import deps
from app.core.security import create_access_token
from app.schemas.token import Token  # 确保只返回 access_token 和 token_type
from app.crud import user as crud_user

router = APIRouter(tags=["auth"], include_in_schema=True)


@router.post("/login", response_model=Token, summary="用户登录获取 JWT Token")
def login_for_access_token(
    db: Session = Depends(deps.get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    ## 用户登录接口

    使用用户名和密码获取 JWT 访问令牌。

    ### 请求参数：
    - **username**: 用户名
    - **password**: 密码

    ### 返回：
    - `access_token`: JWT 令牌
    - `token_type`: "bearer"

    ### 错误码：
    - `401`: 用户名或密码错误
    - `403`: 用户被禁用
    """
    # 1. 认证用户
    user = crud_user.authenticate(db, username=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 2. 检查用户是否被禁用（虽然 deps 中也会检查，但登录时应明确提示）
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )

    # 3. 生成 Token（payload: sub=user.username）
    access_token = create_access_token(subject=user.username)

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }