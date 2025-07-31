from pydantic import BaseModel
from typing import Optional
from datetime import datetime


# 基础模型，包含所有模型共有的字段
class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None


# 创建时使用的模型
class ProjectCreate(ProjectBase):
    pass


# 更新时使用的模型
class ProjectUpdate(ProjectBase):
    pass


# 从数据库读取时返回给客户端的模型
class Project(ProjectBase):
    id: int
    package_path: str
    created_at: datetime

    class Config:
        from_attributes = True  # 在Pydantic V2中，应为 from_attributes = True


class ProjectOut(ProjectBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True  # Pydantic V2