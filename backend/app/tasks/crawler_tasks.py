# /backend/app/tasks/crawler_tasks.py
import json
import os
import sys
import subprocess
import datetime
import time
from typing import Dict, Any, Optional
from celery import Task
from sqlalchemy.orm import Session

from app.core.celery_app import celery
from app.core.config import settings
from app.db.session import SessionLocal
from app import crud, schemas
from app.models.task_run import TaskRunStatus


class GenericTask(Task):
    """支持中断的通用任务"""
    pass


@celery.task(base=GenericTask, bind=True, name="tasks.run_generic_script")
def run_generic_script(
    self,
    original_task_id: int,
    project_name: str,
    entrypoint: str = "run.py",  # 入口脚本，如 run.py, start.sh, main.js
    args: Dict[str, Any] = None,
    env: Dict[str, str] = None
):
    """
    在 Celery Worker 中运行任意脚本（Python, Shell, Node.js 等）
    :param original_task_id: CrawlPro 中的任务 ID
    :param project_name: 项目名（目录名）
    :param entrypoint: 入口文件（相对于项目根目录）
    :param args: 传递给脚本的参数（JSON 序列化后通过环境变量或命令行传入）
    :param env: 额外环境变量
    """
    logger = self
    db: Session = SessionLocal()
    db_task_run = None
    project_dir = None

    try:
        # === 1. 创建任务执行记录 ===
        task_run_in = schemas.TaskRunCreate(
            task_id=original_task_id,
            celery_task_id=self.request.id,
            worker_node=self.request.hostname
        )
        db_task_run = crud.task_run.create(db, obj_in=task_run_in)

        # === 2. 定位项目路径 ===
        project_dir = os.path.join(settings.PROJECTS_DIR, project_name)
        if not os.path.isdir(project_dir):
            raise FileNotFoundError(f"Project directory not found: {project_dir}")

        entrypoint_path = os.path.join(project_dir, entrypoint)
        if not os.path.isfile(entrypoint_path):
            raise FileNotFoundError(f"Entrypoint script not found: {entrypoint}")

        # === 3. 构建命令 ===
        command = _build_command(entrypoint, args)
        cwd = project_dir

        # === 4. 准备环境变量 ===
        exec_env = os.environ.copy()
        exec_env["CRAWLPRO_TASK_ID"] = str(original_task_id)
        exec_env["CRAWLPRO_PROJECT_NAME"] = project_name
        exec_env["CRAWLPRO_ENTRYPOINT"] = entrypoint
        exec_env["CRAWLPRO_WORKER_HOSTNAME"] = self.request.hostname
        if args:
            exec_env["CRAWLPRO_ARGS"] = json.dumps(args)
        if env:
            exec_env.update(env)  # 用户自定义环境变量

        # === 5. 日志文件 ===
        log_file = f"logs/runs/{project_name}_{os.path.splitext(entrypoint)[0]}_{self.request.id}.log"
        os.makedirs(os.path.dirname(log_file), exist_ok=True)

        # === 6. 执行脚本 ===
        self.update_state(state="RUNNING", meta={"status": "Script started"})

        with open(log_file, "w", encoding="utf-8") as log_f:
            process = subprocess.Popen(
                command,
                cwd=cwd,
                env=exec_env,
                stdout=log_f,
                stderr=subprocess.STDOUT,  # 合并 stderr 到 stdout
                text=True,
                bufsize=1,
                universal_newlines=True
            )

            # 实时检查是否被 revoke
            while process.poll() is None:
                if self.request.called:  # 被 revoke
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                    _update_task_run_stopped(db, db_task_run, log_file)
                    return {"status": "stopped"}

                time.sleep(0.5)

            # === 7. 执行完成 ===
            if process.returncode == 0:
                log_content = _read_log_tail(log_file)
                _update_task_run_success(db, db_task_run, log_content)
                return {"status": "success", "returncode": 0}
            else:
                log_content = _read_log_tail(log_file)
                _update_task_run_failed(db, db_task_run, f"Script exited with code {process.returncode}")
                return {"status": "failure", "returncode": process.returncode}

    except Exception as e:
        error_msg = f"Execution failed: {type(e).__name__}: {str(e)}"
        if db_task_run:
            _update_task_run_failed(db, db_task_run, error_msg)
        raise
    finally:
        db.close()


# === 工具函数 ===

def _build_command(entrypoint: str, args: dict = None) -> list:
    """根据入口文件类型构建执行命令"""
    filename = entrypoint.lower()
    args_list = []

    if args:
        # 将 args 转为命令行参数：--key value
        for k, v in args.items():
            args_list.append(f"--{k}")
            args_list.append(str(v))

    if filename.endswith(".py"):
        return ["python", entrypoint] + args_list
    elif filename.endswith(".sh"):
        return ["bash", entrypoint] + args_list
    elif filename.endswith(".js"):
        return ["node", entrypoint] + args_list
    elif filename.endswith(".ts"):
        return ["ts-node", entrypoint] + args_list
    elif filename.endswith(".php"):
        return ["php", entrypoint] + args_list
    elif filename.endswith(".rb"):
        return ["ruby", entrypoint] + args_list
    else:
        raise ValueError(f"Unsupported script type: {entrypoint}")


def _update_task_run_success(db: Session, db_task_run, log_output: str):
    update_data = schemas.TaskRunUpdate(
        status=TaskRunStatus.SUCCESS,
        end_time=datetime.datetime.utcnow(),
        log_output=log_output
    )
    crud.task_run.update(db, db_obj=db_task_run, obj_in=update_data)


def _update_task_run_failed(db: Session, db_task_run, error_msg: str):
    update_data = schemas.TaskRunUpdate(
        status=TaskRunStatus.FAILURE,
        end_time=datetime.datetime.utcnow(),
        log_output=error_msg
    )
    crud.task_run.update(db, db_obj=db_task_run, obj_in=update_data)


def _update_task_run_stopped(db: Session, db_task_run, log_file: str):
    log_content = _read_log_tail(log_file)
    update_data = schemas.TaskRunUpdate(
        status=TaskRunStatus.FAILURE,
        end_time=datetime.datetime.utcnow(),
        log_output=f"{log_content}\n[INFO] Task was manually stopped."
    )
    crud.task_run.update(db, db_obj=db_task_run, obj_in=update_data)


def _read_log_tail(log_file: str, lines: int = 1000) -> str:
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            return "".join(f.readlines()[-lines:])
    except Exception:
        return "[Log file not available]"