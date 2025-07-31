# /backend/app/api/v1/endpoints/task_runs.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app import deps
from app import models, schemas
from app.crud import task_run as crud_task_run

router = APIRouter(
    prefix="/task_runs",
    tags=["task_runs"],
    responses={404: {"description": "Not found"}}
)


@router.get("/", response_model=List[schemas.TaskRunOut])
def read_task_runs(
    *,
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps.get_current_active_user)
):
    """
    获取任务执行记录列表（分页）

    - **权限**：登录用户可访问
    - **用途**：监控面板、任务历史
    """
    runs = crud_task_run.get_multi(db, skip=skip, limit=limit)
    return runs


@router.get("/{run_id}", response_model=schemas.TaskRunOut)
def read_task_run(
    *,
    run_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user)
):
    """
    根据 ID 获取单个任务执行记录

    - **权限**：登录用户可访问
    """
    run = crud_task_run.get(db, id=run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Task run not found")
    return run


@router.get("/task/{task_id}", response_model=List[schemas.TaskRunOut])
def read_task_runs_by_task(
    *,
    task_id: int,
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: 100,
    current_user: models.User = Depends(deps.get_current_active_user)
):
    """
    获取某个任务的所有执行记录（按时间倒序）

    - **权限**：登录用户可访问
    - **用途**：任务详情页 → 历史执行记录
    """
    stmt = crud_task_run.select().where(crud_task_run.model.task_id == task_id) \
                        .offset(skip).limit(limit).order_by(crud_task_run.model.start_time.desc())
    result = db.execute(stmt)
    runs = list(result.scalars().all())
    if not runs:
        raise HTTPException(status_code=404, detail="No runs found for this task")
    return runs


@router.get("/celery/{celery_task_id}", response_model=schemas.TaskRunOut)
def read_task_run_by_celery_id(
    *,
    celery_task_id: str,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user)
):
    """
    根据 Celery 任务 ID 查询执行记录

    - **权限**：登录用户可访问
    - **用途**：实时日志页通过 celery_task_id 获取 run 信息
    """
    run = crud_task_run.get_by_celery_id(db, celery_task_id=celery_task_id)
    if not run:
        raise HTTPException(status_code=404, detail="Task run not found")
    return run


@router.delete("/{run_id}", response_model=schemas.TaskRunOut)
def delete_task_run(
    *,
    run_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_superuser)
):
    """
    【管理员专用】删除某条任务执行记录

    - **权限**：仅 superuser 可访问
    - **用途**：清理数据、调试
    """
    run = crud_task_run.get(db, id=run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Task run not found")

    db.delete(run)
    db.commit()
    return run