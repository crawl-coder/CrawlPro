# /backend/app/crud/base.py

from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union, cast

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy import Delete, Select, delete, select
from sqlalchemy.orm import Session

from app.db.base_class import Base

# --- 泛型类型定义 ---
ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: Type[ModelType]):
        self.model = model

    def get(self, db: Session, id: Any) -> Optional[ModelType]:
        """通过 ID 获取单个对象"""
        stmt: Select[tuple[ModelType]] = select(self.model).where(self.model.id == id)  # type: ignore
        result = db.execute(stmt)
        return result.scalar_one_or_none()

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> List[ModelType]:
        """获取多个对象（支持分页）"""
        stmt: Select[tuple[ModelType]] = select(self.model).offset(skip).limit(limit)
        result = db.execute(stmt)
        # 显式转换为 List，避免类型错误
        return list(result.scalars().all())

    def create(self, db: Session, *, obj_in: CreateSchemaType) -> ModelType:
        """根据 Pydantic Schema 创建新对象"""
        obj_in_data = jsonable_encoder(obj_in)
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
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]]
    ) -> ModelType:
        """更新一个已存在的数据库对象"""
        obj_data = jsonable_encoder(db_obj)

        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])

        db.add(db_obj)
        db.flush()
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, id: int) -> Optional[ModelType]:
        """通过 ID 删除一个对象"""
        stmt: Select[tuple[ModelType]] = select(self.model).where(self.model.id == id)  # type: ignore
        result = db.execute(stmt)
        obj = result.scalar_one_or_none()
        if obj is not None:
            db.delete(obj)
            db.commit()
        return obj