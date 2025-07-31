# /backend/app/api/v1/endpoints/projects.py

import shutil
import os
import zipfile
from typing import List, Any
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status

from app import deps
from app import models, schemas
from app.core.config import settings
from app.crud import project as crud_project  # 使用 CRUDProject(project)

router = APIRouter()


@router.post("/", response_model=schemas.ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(
    *,
    db: Session = Depends(deps.get_db),
    name: str = Form(...),
    description: str = Form(""),
    file: UploadFile = File(...),
    current_user: models.User = Depends(deps.get_current_active_user)
) -> Any:
    """
    上传并创建一个新的爬虫项目（ZIP 包）
    - 用户必须登录
    - 项目名称唯一
    - 仅允许 .zip 文件
    - 自动解压到 PROJECTS_DIR/name/
    """
    # 1. 校验文件类型
    if not file.filename.lower().endswith(".zip"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .zip files are allowed"
        )

    # 2. 检查项目是否已存在（名称唯一）
    if crud_project.get_by_name(db, name=name):
        raise HTTPException(status_code=400, detail="Project with this name already exists")

    # 3. 创建项目目录
    project_dir = os.path.join(settings.PROJECTS_DIR, name)
    if os.path.exists(project_dir):
        raise HTTPException(status_code=400, detail="Project directory already exists on disk")

    os.makedirs(project_dir, exist_ok=False)

    temp_zip_path = os.path.join(project_dir, file.filename)

    try:
        # 4. 保存上传的 zip 文件
        with open(temp_zip_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        # 5. 解压
        with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
            zip_ref.extractall(project_dir)

        os.remove(temp_zip_path)

    except zipfile.BadZipFile:
        shutil.rmtree(project_dir)
        raise HTTPException(status_code=400, detail="Invalid zip file")
    except Exception as e:
        shutil.rmtree(project_dir)
        raise HTTPException(status_code=500, detail=f"Failed to process project package: {str(e)}")
    finally:
        file.file.close()

    # 6. 创建数据库记录（包含 owner_id 和 package_path）
    project_in = schemas.ProjectCreate(name=name, description=description)
    created_project = crud_project.create(
        db=db,
        obj_in=project_in,
        owner_id=current_user.id,
        package_path=project_dir
    )
    return created_project


@router.get("/", response_model=List[schemas.ProjectOut])
def read_projects(
    *,
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps.get_current_active_user)
):
    """
    获取当前用户自己的项目列表（分页）
    """
    stmt = crud_project.select().where(crud_project.model.owner_id == current_user.id) \
                        .offset(skip).limit(limit).order_by(crud_project.model.created_at.desc())
    result = db.execute(stmt)
    return list(result.scalars().all())


@router.get("/{project_id}", response_model=schemas.ProjectOut)
def read_project(
    *,
    project_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user)
):
    """
    获取单个项目详情，需权限校验
    """
    db_project = crud_project.get(db, id=project_id)
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")

    if db_project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions to access this project")

    return db_project


@router.put("/{project_id}", response_model=schemas.ProjectOut)
def update_project(
    *,
    project_id: int,
    project_in: schemas.ProjectUpdate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user)
):
    """
    更新项目（仅限所有者）
    """
    db_project = crud_project.get(db, id=project_id)
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")

    if db_project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # 检查新名称是否冲突（排除自己）
    if "name" in project_in.model_dump(exclude_unset=True):
        existing = crud_project.get_by_name(db, name=project_in.name)
        if existing and existing.id != project_id:
            raise HTTPException(status_code=400, detail="Project name already taken")

    db_project = crud_project.update(db=db, db_obj=db_project, obj_in=project_in)
    return db_project


@router.delete("/{project_id}", response_model=schemas.ProjectOut)
def delete_project(
    *,
    project_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user)
):
    """
    删除项目：数据库 + 磁盘文件，需权限校验
    """
    db_project = crud_project.get(db, id=project_id)
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")

    if db_project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # 1. 删除磁盘文件
    if db_project.package_path and os.path.exists(db_project.package_path):
        try:
            shutil.rmtree(db_project.package_path)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to delete project files: {str(e)}")

    # 2. 删除数据库记录（会级联删除关联任务）
    deleted_project = crud_project.remove(db=db, id=project_id)
    return deleted_project