# /backend/app/api/v1/endpoints/users.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app import deps
from app import models, schemas
from app.crud import user as crud_user

router = APIRouter()


@router.post("/", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def register_user(
    *,
    db: Session = Depends(deps.get_db),
    user_in: schemas.UserCreate,
):
    """
    【开放】用户注册接口
    任何人都可以调用此接口创建账户
    """
    existing = crud_user.get_by_username(db, username=user_in.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )

    if user_in.email:
        existing_email = crud_user.get_by_email(db, email=user_in.email)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

    user = crud_user.create(db, obj_in=user_in)
    return user


@router.get("/me", response_model=schemas.UserOut)
def read_user_me(
    current_user: models.User = Depends(deps.get_current_active_user)
):
    """
    获取当前登录用户的个人信息
    """
    return current_user


# --- 以下为管理员专用接口 ---
# 需要 superuser 权限

@router.get("/", response_model=List[schemas.UserOut])
def read_users(
    *,
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps.get_current_active_superuser)
):
    """
    【管理员】获取所有用户列表
    """
    return crud_user.get_multi(db, skip=skip, limit=limit)


@router.get("/{user_id}", response_model=schemas.UserOut)
def read_user_by_id(
    *,
    user_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_superuser)
):
    """
    【管理员】根据 ID 获取用户信息
    """
    user = crud_user.get(db, id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def _ensure_not_self(*, current_user: models.User, target_id: int):
    """
    内部工具函数：确保目标用户不是操作者自己
    用于防止管理员锁死自己的账户
    """
    if current_user.id == target_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot perform this action on your own account"
        )


@router.put("/{user_id}/activate")
def activate_user(
    *,
    user_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_superuser)
):
    """
    【管理员】启用用户
    ✅ 允许对自己操作（无风险）
    """
    user = crud_user.get(db, id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.is_active:
        return {"success": True, "user_id": user_id, "is_active": True}

    crud_user.activate(db, id=user_id)
    return {"success": True, "user_id": user_id, "is_active": True}


@router.put("/{user_id}/deactivate")
def deactivate_user(
    *,
    user_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_superuser)
):
    """
    【管理员】禁用用户
    ❌ 禁止对自己操作（防止锁死）
    """
    _ensure_not_self(current_user=current_user, target_id=user_id)

    user = crud_user.get(db, id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.is_active:
        return {"success": True, "user_id": user_id, "is_active": False}

    crud_user.deactivate(db, id=user_id)
    return {"success": True, "user_id": user_id, "is_active": False}


@router.put("/{user_id}/make-superuser")
def grant_superuser(
    *,
    user_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_superuser)
):
    """
    【管理员】赋予超级权限
    ✅ 允许对自己操作（无风险）
    """
    user = crud_user.get(db, id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.is_superuser:
        return {"success": True, "user_id": user_id, "is_superuser": True}

    crud_user.make_superuser(db, id=user_id)
    return {"success": True, "user_id": user_id, "is_superuser": True}


@router.put("/{user_id}/revoke-superuser")
def revoke_superuser(
    *,
    user_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_superuser)
):
    """
    【管理员】撤销超级权限
    ❌ 禁止对自己操作（防止锁死）
    """
    _ensure_not_self(current_user=current_user, target_id=user_id)

    user = crud_user.get(db, id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.is_superuser:
        return {"success": True, "user_id": user_id, "is_superuser": False}

    crud_user.revoke_superuser(db, id=user_id)
    return {"success": True, "user_id": user_id, "is_superuser": False}