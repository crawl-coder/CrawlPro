# /backend/app/crud/crud_project.py

from typing import Any, Dict, List, Optional, Type, cast

from sqlalchemy.orm import Session
from sqlalchemy import Select, select, delete
from sqlalchemy.sql import func

from app.crud.base import CRUDBase
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate


class CRUDProject(CRUDBase[Project, ProjectCreate, ProjectUpdate]):
    """
    针对 Project 模型的专用 CRUD 操作
    继承自通用 CRUDBase，可扩展自定义方法
    """

    def get_by_name(self, db: Session, *, name: str) -> Optional[Project]:
        """根据项目名称获取单个项目（名称唯一）"""
        stmt: Select[tuple[Project]] = select(self.model).where(self.model.name == name)
        result = db.execute(stmt)
        return result.scalar_one_or_none()

    def get_multi_paginated(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> List[Project]:
        """分页查询项目列表，按创建时间倒序"""
        stmt: Select[tuple[Project]] = (
            select(self.model)
            .offset(skip)
            .limit(limit)
            .order_by(self.model.created_at.desc())
        )
        result = db.execute(stmt)
        return cast(List[Project], result.scalars().all())

    def get_multi_by_owner(
        self, db: Session, *, owner_id: int, skip: int = 0, limit: int = 100
    ) -> List[Project]:
        """
        根据所有者 ID 查询其拥有的项目列表（分页）
        """
        stmt: Select[tuple[Project]] = (
            select(self.model)
            .where(self.model.owner_id == owner_id)
            .offset(skip)
            .limit(limit)
            .order_by(self.model.created_at.desc())
        )
        result = db.execute(stmt)
        return cast(List[Project], result.scalars().all())

    def create(self, db: Session, *, obj_in: ProjectCreate) -> Project:
        """创建新项目，确保名称唯一，并注入 owner_id 和 package_path"""
        existing = self.get_by_name(db, name=obj_in.name)
        if existing:
            raise ValueError(f"Project with name '{obj_in.name}' already exists.")

        obj_in_data = obj_in.model_dump(exclude_unset=True)

        if 'owner_id' not in obj_in_data:
            raise ValueError("owner_id is required")
        if 'package_path' not in obj_in_data:
            raise ValueError("package_path is required")

        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        db.flush()
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(
        self,
        db: Session,
        *,
        db_obj: Project,
        obj_in: ProjectUpdate | Dict[str, Any]
    ) -> Project:
        """更新项目，防止重命名导致重复"""
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        if "name" in update_data:
            existing = self.get_by_name(db, name=update_data["name"])
            if existing and existing.id != db_obj.id:
                raise ValueError(f"Project name '{update_data['name']}' is already taken.")

        return super().update(db, db_obj=db_obj, obj_in=obj_in)

    def remove(self, db: Session, *, id: int) -> Optional[Project]:
        """删除项目"""
        stmt: Select[tuple[Project]] = select(self.model).where(self.model.id == id)
        result = db.execute(stmt)
        obj = result.scalar_one_or_none()
        if obj is not None:
            db.delete(obj)
            db.commit()
        return obj

    def get_statistics(self, db: Session) -> Dict[str, Any]:
        """获取项目统计信息"""
        total = db.execute(select(func.count(self.model.id))).scalar() or 0
        latest = db.execute(
            select(self.model).order_by(self.model.created_at.desc()).limit(1)
        ).scalar_one_or_none()

        return {
            "total_projects": total,
            "latest_project": latest.name if latest else None,
            "latest_created_at": latest.created_at if latest else None,
        }


# 创建实例供其他模块使用
project = CRUDProject(Project)