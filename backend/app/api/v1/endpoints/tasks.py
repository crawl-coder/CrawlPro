# /backend/app/api/v1/endpoints/tasks.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app import deps
from app import models, schemas
from app.services.scheduler import scheduler_service
from app.crud import project as crud_project
from app.crud import task as crud_task

router = APIRouter()


def _check_task_project_permission(
    db: Session,
    task_id: int,
    user: models.User
) -> None:
    """
    内部工具函数：检查用户是否有权操作该任务（通过 project.owner_id）
    如果无权，抛出 403
    """
    db_task = crud_task.get(db, id=task_id)
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")

    db_project = crud_project.get(db, id=db_task.project_id)
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")

    if db_project.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to access this task"
        )


@router.post("/", response_model=schemas.TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(
    *,
    db: Session = Depends(deps.get_db),
    task_in: schemas.TaskCreate,
    current_user: models.User = Depends(deps.get_current_active_user)
):
    """
    创建任务：用户必须是目标项目的拥有者
    """
    # 检查项目是否存在
    project = crud_project.get(db, id=task_in.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # 权限：必须是项目所有者
    if project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to create task for this project"
        )

    try:
        db_task = crud_task.create(db=db, obj_in=task_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 调度器：如果启用且有 cron 表达式
    if db_task.is_enabled and db_task.cron_expression:
        try:
            scheduler_service.add_task(db_task)
        except Exception as e:
            print(f"[WARNING] Failed to schedule task {db_task.id}: {str(e)}")

    return db_task


@router.get("/", response_model=List[schemas.TaskOut])
def read_tasks(
    *,
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps.get_current_active_user)
):
    """
    获取当前用户有权限的任务列表（仅限自己项目下的任务）
    """
    # 获取当前用户的所有项目 ID
    stmt = crud_project.select().where(crud_project.model.owner_id == current_user.id)
    result = db.execute(stmt)
    user_projects = result.scalars().all()
    project_ids = [p.id for p in user_projects]

    if not project_ids:
        return []

    # 查询这些项目下的所有任务
    stmt = crud_task.select().where(crud_task.model.project_id.in_(project_ids)) \
                     .offset(skip).limit(limit).order_by(crud_task.model.created_at.desc())
    result = db.execute(stmt)
    return list(result.scalars().all())


@router.get("/{task_id}", response_model=schemas.TaskOut)
def read_task(
    *,
    task_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user)
):
    """
    获取单个任务：必须属于当前用户拥有的项目
    """
    _check_task_project_permission(db, task_id=task_id, user=current_user)
    return crud_task.get(db, id=task_id)


@router.put("/{task_id}", response_model=schemas.TaskOut)
def update_task(
    *,
    task_id: int,
    task_in: schemas.TaskUpdate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user)
):
    """
    更新任务：先权限校验，再操作调度器和数据库
    """
    _check_task_project_permission(db, task_id=task_id, user=current_user)
    db_task = crud_task.get(db, id=task_id)  # 已确保存在

    # 1. 从调度器移除旧任务
    if scheduler_service.has_task(task_id):
        try:
            scheduler_service.remove_task(task_id)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to remove old task from scheduler: {str(e)}"
            )

    # 2. 更新数据库
    try:
        db_task = crud_task.update(db=db, db_obj=db_task, obj_in=task_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 3. 如果启用且有 cron，重新添加
    if db_task.is_enabled and db_task.cron_expression:
        try:
            scheduler_service.add_task(db_task)
        except Exception as e:
            print(f"[WARNING] Could not reschedule task {task_id}: {str(e)}")

    return db_task


@router.delete("/{task_id}", response_model=schemas.TaskOut)
def delete_task(
    *,
    task_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user)
):
    """
    删除任务：需权限校验
    """
    _check_task_project_permission(db, task_id=task_id, user=current_user)
    db_task = crud_task.get(db, id=task_id)

    # 1. 从调度器移除
    if scheduler_service.has_task(task_id):
        try:
            scheduler_service.remove_task(task_id)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to remove task from scheduler: {str(e)}"
            )

    # 2. 删除数据库
    db_task = crud_task.remove(db=db, id=task_id)
    return db_task


@router.post("/{task_id}/toggle", response_model=schemas.TaskOut)
def toggle_task(
    *,
    task_id: int,
    enable: bool,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user)
):
    """
    启用/禁用任务：需权限校验
    """
    _check_task_project_permission(db, task_id=task_id, user=current_user)
    db_task = crud_task.get(db, id=task_id)

    was_enabled = db_task.is_enabled
    now_enabled = enable

    if was_enabled == now_enabled:
        return db_task

    try:
        # 操作调度器
        if now_enabled and db_task.cron_expression:
            scheduler_service.add_task(db_task)
        elif was_enabled:
            scheduler_service.remove_task(task_id)

        # 更新数据库
        db_task = crud_task.toggle_enable(db, id=task_id, enable=enable)
        return db_task

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Toggle failed: {str(e)}")