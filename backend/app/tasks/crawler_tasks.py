# /backend/app/tasks/crawler_tasks.py
import json
import os
import subprocess
import datetime
import time
from typing import Dict, Any
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


def _build_command(entrypoint: str, args: dict = None, worker_os: str = "LINUX") -> list:
    """
    根据入口文件类型和操作系统构建执行命令
    :param entrypoint: 入口文件名（如 run.py, start.sh）
    :param args: 命令行参数
    :param worker_os: 操作系统类型（"WINDOWS", "LINUX", "MACOS"）
    :return: 命令列表
    """
    filename = entrypoint.lower()
    args_list = []

    if args:
        for k, v in args.items():
            args_list.append(f"--{k}")
            args_list.append(str(v))

    # 根据操作系统和文件类型构建命令
    if filename.endswith(".py"):
        if worker_os == "WINDOWS":
            return ["python", entrypoint] + args_list
        else:
            return ["python3", entrypoint] + args_list

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

    elif filename.endswith(".exe"):
        if worker_os == "WINDOWS":
            return [entrypoint] + args_list
        else:
            raise ValueError("Executable .exe files are only supported on Windows")

    else:
        raise ValueError(f"Unsupported script type: {entrypoint}")


def _read_log_tail(log_file: str, lines: int = 1000) -> str:
    """读取日志末尾 N 行"""
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            return "".join(f.readlines()[-lines:])
    except Exception as e:
        return f"[Log read failed: {str(e)}]"


def _update_task_run_status(
    db: Session,
    db_task_run,
    status: TaskRunStatus,
    log_output: str,
    end_time: datetime.datetime = None
):
    """统一更新任务执行状态"""
    if not db_task_run:
        return

    end_time = end_time or datetime.datetime.utcnow()
    update_data = schemas.TaskRunUpdate(
        status=status,
        end_time=end_time,
        log_output=log_output
    )
    crud.task_run.update(db, db_obj=db_task_run, obj_in=update_data)


@celery.task(base=GenericTask, bind=True, name="tasks.run_generic_script")
def run_generic_script(
    self,
    original_task_id: int,
    project_name: str,
    entrypoint: str = "run.py",
    args: Dict[str, Any] = None,
    env: Dict[str, str] = None
):
    """
    在 Celery Worker 中运行任意脚本（Python, Shell, Node.js 等）
    支持中断、日志记录、状态更新
    """
    db_task_run = None
    log_file = None

    try:
        # === 1. 创建任务执行记录 ===
        with SessionLocal() as db:
            task_run_in = schemas.TaskRunCreate(
                task_id=original_task_id,
                celery_task_id=self.request.id,
                worker_node=self.request.hostname
            )
            db_task_run = crud.task_run.create(db, obj_in=task_run_in)
            db.commit()
            db.refresh(db_task_run)

        # === 2. 检查项目路径 ===
        project_dir = os.path.join(settings.PROJECTS_DIR, project_name)
        if not os.path.isdir(project_dir):
            raise FileNotFoundError(f"Project directory not found: {project_dir}")

        entrypoint_path = os.path.join(project_dir, entrypoint)
        if not os.path.isfile(entrypoint_path):
            raise FileNotFoundError(f"Entrypoint script not found: {entrypoint_path}")

        # === 3. 获取 Worker 操作系统 ===
        worker_os = getattr(self.request, 'hostname', 'unknown').upper()
        # 更准确的方式：在 worker_signals 中设置，或通过 platform
        # 但此处为兼容性，建议在 env 中注入 OS
        detected_os = os.getenv("OS_TYPE", "LINUX")  # 可由 worker_signals 设置

        # === 4. 构建命令 ===
        try:
            command = _build_command(entrypoint, args, worker_os=detected_os)
        except ValueError as e:
            raise RuntimeError(f"Command build failed: {str(e)}")

        # === 5. 准备环境变量 ===
        exec_env = os.environ.copy()
        exec_env.update({
            "CRAWLPRO_TASK_ID": str(original_task_id),
            "CRAWLPRO_PROJECT_NAME": project_name,
            "CRAWLPRO_ENTRYPOINT": entrypoint,
            "CRAWLPRO_WORKER_HOSTNAME": self.request.hostname or "unknown",
            "CRAWLPRO_WORKER_OS": detected_os,
            "PYTHONUNBUFFERED": "1",
        })
        if args:
            exec_env["CRAWLPRO_ARGS"] = json.dumps(args)
        if env:
            exec_env.update(env)

        # === 6. 日志文件路径 ===
        log_filename = f"{project_name}_{os.path.splitext(entrypoint)[0]}_{self.request.id}.log"
        log_file = os.path.join(settings.LOGS_DIR, "runs", log_filename)
        os.makedirs(os.path.dirname(log_file), exist_ok=True)

        # === 7. 更新状态为 RUNNING ===
        self.update_state(state="RUNNING", meta={
            "status": "Script started",
            "log_file": log_file,
            "command": " ".join(command)
        })

        # === 8. 执行脚本 ===
        with open(log_file, "w", encoding="utf-8") as log_f:
            process = subprocess.Popen(
                command,
                cwd=project_dir,
                env=exec_env,
                stdout=log_f,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )

            while process.poll() is None:
                if self.request.called:  # 被 revoke（中断）
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                    break
                time.sleep(0.5)

            return_code = process.poll()

        # === 9. 更新最终状态 ===
        with SessionLocal() as db:
            log_content = _read_log_tail(log_file)

            if return_code == 0:
                _update_task_run_status(db, db_task_run, TaskRunStatus.SUCCESS, log_content)
                return {"status": "success", "return_code": 0}
            elif self.request.called:
                _update_task_run_status(
                    db, db_task_run, TaskRunStatus.FAILURE,
                    f"{log_content}\n[INFO] Task was manually stopped."
                )
                return {"status": "stopped"}
            else:
                error_msg = f"Script exited with code {return_code}"
                _update_task_run_status(
                    db, db_task_run, TaskRunStatus.FAILURE,
                    f"{log_content}\n[ERROR] {error_msg}"
                )
                return {"status": "failure", "return_code": return_code}

    except Exception as e:
        error_msg = f"Task execution failed: {type(e).__name__}: {str(e)}"
        print(f"[CELERY TASK ERROR] {error_msg}")

        try:
            with SessionLocal() as db:
                if db_task_run:
                    _update_task_run_status(db, db_task_run, TaskRunStatus.FAILURE, error_msg)
        except Exception as db_err:
            print(f"[CELERY TASK ERROR] Failed to update DB status: {db_err}")

        raise