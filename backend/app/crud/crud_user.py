# /backend/app/crud/crud_user.py

from typing import Any, Dict, List, Optional, cast

from sqlalchemy.orm import Session
from sqlalchemy import Select, select, update, delete, or_
from sqlalchemy.sql import func

from app.crud.base import CRUDBase
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    """
    针对 User 模型的专用 CRUD 操作
    包含用户名/邮箱唯一性校验、超级用户支持、启用状态管理等
    """

    def get_by_username(self, db: Session, *, username: str) -> Optional[User]:
        """根据用户名获取用户（唯一）"""
        stmt: Select[tuple[User]] = select(self.model).where(self.model.username == username)
        result = db.execute(stmt)
        return result.scalar_one_or_none()

    def get_by_email(self, db: Session, *, email: str) -> Optional[User]:
        """根据邮箱获取用户（唯一）"""
        if not email:
            return None
        stmt: Select[tuple[User]] = select(self.model).where(self.model.email == email)
        result = db.execute(stmt)
        return result.scalar_one_or_none()

    def get_multi_by_status(
        self, db: Session, *, is_active: bool = True, skip: int = 0, limit: int = 100
    ) -> List[User]:
        """获取指定状态（启用/禁用）的用户列表"""
        stmt: Select[tuple[User]] = (
            select(self.model)
            .where(self.model.is_active == is_active)
            .offset(skip)
            .limit(limit)
            .order_by(self.model.created_at.desc())
        )
        result = db.execute(stmt)
        return cast(List[User], result.scalars().all())

    def get_multi_search(
        self, db: Session, *, query: str, skip: int = 0, limit: int = 100
    ) -> List[User]:
        """模糊搜索用户名或邮箱"""
        stmt: Select[tuple[User]] = (
            select(self.model)
            .where(
                or_(
                    self.model.username.ilike(f"%{query}%"),
                    self.model.email.ilike(f"%{query}%")
                )
            )
            .offset(skip)
            .limit(limit)
        )
        result = db.execute(stmt)
        return cast(List[User], result.scalars().all())

    def create(self, db: Session, *, obj_in: UserCreate) -> User:
        """
        创建新用户，自动哈希密码
        假设传入的 obj_in.password 已由 Schema 校验
        """
        # 检查用户名或邮箱是否已存在
        existing_username = self.get_by_username(db, username=obj_in.username)
        if existing_username:
            raise ValueError(f"Username '{obj_in.username}' is already taken.")

        if obj_in.email:
            existing_email = self.get_by_email(db, email=obj_in.email)
            if existing_email:
                raise ValueError(f"Email '{obj_in.email}' is already registered.")

        obj_in_data = obj_in.model_dump(exclude_unset=True)

        # 提取密码并移除，稍后哈希
        password = obj_in_data.pop("password")
        hashed_password = self._hash_password(password)

        # 创建用户对象
        db_obj = self.model(
            **obj_in_data,
            hashed_password=hashed_password
        )
        db.add(db_obj)
        db.flush()
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(
        self,
        db: Session,
        *,
        db_obj: User,
        obj_in: UserUpdate | Dict[str, Any]
    ) -> User:
        """
        更新用户信息，支持密码更新（自动哈希）
        """
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        # 检查邮箱是否被占用
        if "email" in update_data and update_data["email"]:
            existing = self.get_by_email(db, email=update_data["email"])
            if existing and existing.id != db_obj.id:
                raise ValueError(f"Email '{update_data['email']}' is already registered.")

        # 如果更新了密码，先哈希
        if "password" in update_data:
            password = update_data.pop("password")
            hashed_password = self._hash_password(password)
            update_data["hashed_password"] = hashed_password

        return super().update(db, db_obj=db_obj, obj_in=update_data)

    def authenticate(self, db: Session, *, username: str, password: str) -> Optional[User]:
        """
        用户登录认证
        :param db: 数据库会话
        :param username: 用户名
        :param password: 明文密码
        :return: 用户对象 或 None
        """
        user = self.get_by_username(db, username=username)
        if not user:
            return None
        if not self._verify_password(password, user.hashed_password):
            return None
        return user

    def activate(self, db: Session, *, id: int) -> Optional[User]:
        """启用用户"""
        return self._set_active_status(db, id=id, is_active=True)

    def deactivate(self, db: Session, *, id: int) -> Optional[User]:
        """禁用用户（软删除）"""
        return self._set_active_status(db, id=id, is_active=False)

    def _set_active_status(self, db: Session, *, id: int, is_active: bool) -> Optional[User]:
        """内部方法：设置用户启用状态"""
        user = self.get(db, id=id)
        if not user:
            return None
        user.is_active = is_active
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def _hash_password(self, password: str) -> str:
        """
        密码哈希（使用 passlib）
        你需要安装：pip install passlib[bcrypt]
        """
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        return pwd_context.hash(password)

    def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        return pwd_context.verify(plain_password, hashed_password)

    def make_superuser(self, db: Session, *, id: int) -> Optional[User]:
        """赋予用户超级权限"""
        user = self.get(db, id=id)
        if not user:
            return None
        user.is_superuser = True
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def revoke_superuser(self, db: Session, *, id: int) -> Optional[User]:
        """撤销超级权限"""
        user = self.get(db, id=id)
        if not user:
            return None
        user.is_superuser = False
        db.add(user)
        db.commit()
        db.refresh(user)
        return user


# 创建实例供其他模块使用
user = CRUDUser(User)