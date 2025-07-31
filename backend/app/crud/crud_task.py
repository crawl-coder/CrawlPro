# /backend/app/crud/crud_task.py

from typing import Any, Dict, List, Optional, cast

from sqlalchemy.orm import Session
from sqlalchemy import Select, select, delete, or_, and_
from sqlalchemy.sql import func

from app.crud.base import CRUDBase
from app.models.task import Task
from app.schemas.task import TaskCreate, TaskUpdate


class CRUDTask(CRUDBase[Task, TaskCreate, TaskUpdate]):
    """
    针对 Task 模型的专用 CRUD 操作
    支持按项目过滤、启用/禁用、定时表达式管理等
    """

    def get_by_name(self, db: Session, *, name: str) -> Optional[Task]:
        """根据任务名称获取单个任务（名称在项目中应唯一，但全局不强制）"""
        stmt: Select[tuple[Task]] = select(self.model).where(self.model.name == name)
        result = db.execute(stmt)
        return result.scalar_one_or_none()

    def get_multi_by_project(
        self, db: Session, *, project_id: int, skip: int = 0, limit: int = 100
    ) -> List[Task]:
        """获取某个项目下的所有任务（分页）"""
        stmt: Select[tuple[Task]] = (
            select(self.model)
            .where(self.model.project_id == project_id)
            .offset(skip)
            .limit(limit)
            .order_by(self.model.created_at.desc())
        )
        result = db.execute(stmt)
        return cast(List[Task], result.scalars().all())

    def get_enabled_tasks(self, db: Session) -> List[Task]:
        """获取所有启用中的定时任务（用于调度器）"""
        stmt: Select[tuple[Task]] = (
            select(self.model)
            .where(self.model.is_enabled == True)  # noqa: E712
            .where(self.model.cron_expression.isnot(None))
        )
        result = db.execute(stmt)
        return cast(List[Task], result.scalars().all())

    def get_pending_tasks(self, db: Session) -> List[Task]:
        """获取所有待执行的定时任务（is_enabled=True 且 cron_expression 非空）"""
        return self.get_enabled_tasks(db)  # 可扩展为更复杂的条件

    def create(self, db: Session, *, obj_in: TaskCreate) -> Task:
        """创建新任务，校验 project_id 是否存在"""
        # 可选：验证 project_id 是否真实存在
        from app.crud.crud_project import project
        proj = project.get_by_name(db, id=obj_in.project_id)
        if not proj:
            raise ValueError(f"Project with ID {obj_in.project_id} does not exist.")

        obj_in_data = obj_in.model_dump(exclude_unset=True)
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
        db_obj: Task,
        obj_in: TaskUpdate | Dict[str, Any]
    ) -> Task:
        """更新任务，支持部分字段更新"""
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        # 如果更新了 project_id，验证项目是否存在
        if "project_id" in update_data:
            from app.crud import project
            proj = project.get(db, id=update_data["project_id"])
            if not proj:
                raise ValueError(f"Project with ID {update_data['project_id']} does not exist.")

        return super().update(db, db_obj=db_obj, obj_in=update_data)

    def toggle_enable(self, db: Session, *, id: int, enable: bool) -> Optional[Task]:
        """启用或禁用任务"""
        task = self.get(db, id=id)
        if not task:
            return None
        task.is_enabled = enable
        db.add(task)
        db.commit()
        db.refresh(task)
        return task

    def remove_by_project(self, db: Session, *, project_id: int) -> int:
        """删除某个项目下的所有任务（用于项目级联删除）"""
        stmt = delete(self.model).where(self.model.project_id == project_id)
        result = db.execute(stmt)
        db.commit()
        return result.rowcount  # 返回删除数量

    def search(self, db: Session, *, query: str, skip: int = 0, limit: int = 100) -> List[Task]:
        """模糊搜索任务名称或爬虫名称"""
        stmt: Select[tuple[Task]] = (
            select(self.model)
            .where(
                or_(
                    self.model.name.ilike(f"%{query}%"),
                    self.model.spider_name.ilike(f"%{query}%")
                )
            )
            .offset(skip)
            .limit(limit)
        )
        result = db.execute(stmt)
        return cast(List[Task], result.scalars().all())


# 创建实例供其他模块使用
task = CRUDTask(Task)