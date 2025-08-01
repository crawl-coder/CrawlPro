# /app/api/v1/endpoints/projects.py
import shutil
import os
import zipfile
from loguru import logger
from typing import List, Any, Optional
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from app import deps
from app import models, schemas
from app.core.config import settings
from app.crud import project as crud_project
from app.crud import git_credential as crud_git_cred
from app.utils.git_utils import clone_project_from_git

router = APIRouter()


@router.post("/", response_model=schemas.ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(
        *,
        db: Session = Depends(deps.get_db),
        name: str = Form(...),
        description: str = Form(""),
        file: Optional[Any] = File(None),
        files: Optional[Any] = File(None),
        git_repo_url: Optional[str] = Form(None),
        git_branch: Optional[str] = Form("main"),
        current_user: models.User = Depends(deps.get_current_active_user)
) -> Any:
    """
    创建一个新的爬虫项目。
    会自动处理值为 "string" 或无效的参数。
    只要 file, files, git_repo_url 中有一个提供了有效源，即视为成功。
    """
    # --- 1. 预处理所有源参数，将无效值转为 None ---
    if git_repo_url and isinstance(git_repo_url, str):
        if git_repo_url.strip().lower() in ["", "string", "none", "null"]:
            git_repo_url = None

    processed_file: Optional[UploadFile] = None
    if file is not None and isinstance(file, UploadFile) and file.filename:
        processed_file = file
    else:
        logger.warning(f"Invalid 'file' parameter received: {file} (type: {type(file)}), treating as None.")

    processed_files: Optional[List[UploadFile]] = None
    if files is not None:
        valid_files = []
        if isinstance(files, UploadFile) and files.filename:
            valid_files.append(files)
        elif isinstance(files, list):
            for f in files:
                if isinstance(f, UploadFile) and f.filename:
                    valid_files.append(f)
                else:
                    logger.warning(f"Invalid item in 'files' list: {f} (type: {type(f)})")
        else:
            logger.warning(f"Invalid 'files' parameter type: {type(files)}, treating as None.")
        processed_files = valid_files if valid_files else None

    # --- 2. 确定有效的项目源 ---
    sources = [
        ('git_repo_url', git_repo_url),
        ('file', processed_file),
        ('files', processed_files and len(processed_files) > 0)
    ]
    provided_sources = [name for name, provided in sources if provided]
    if len(provided_sources) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid project source provided. Please provide a valid file, multiple files, or a git_repo_url."
        )

    # --- 3. 检查项目是否已存在 ---
    if crud_project.get_by_name(db, name=name):
        raise HTTPException(status_code=400, detail="Project with this name already exists")

    # --- 4. 创建项目目录 ---
    project_dir = os.path.join(settings.PROJECTS_DIR, name)
    abs_project_dir = os.path.abspath(project_dir)
    if os.path.exists(project_dir):
        logger.error(f"Target directory already exists: {abs_project_dir}")
        raise HTTPException(status_code=400, detail="Project directory already exists on disk")

    logger.info(f"Creating project directory at ABSOLUTE path: {abs_project_dir}")
    logger.info(f"Server Info: Projects are stored under ROOT directory: {os.path.abspath(settings.PROJECTS_DIR)}")

    try:
        # 创建目录
        os.makedirs(project_dir, exist_ok=False)

        # --- 5. 处理项目源 ---
        # 优先级：git_repo_url > file > files
        if git_repo_url:
            provider = "github"
            git_cred = crud_git_cred.get_by_user_and_provider(db, user_id=current_user.id, provider=provider)
            username = git_cred.username if git_cred else None
            password = git_cred.token if git_cred else None
            clone_project_from_git(
                repo_url=git_repo_url,
                target_path=project_dir,
                branch=git_branch or "main",
                username=username,
                password=password
            )
        elif processed_file:
            filename = processed_file.filename.lower()
            if filename.endswith('.zip'):
                _handle_archive_upload(processed_file, project_dir)
            elif filename.endswith('.py'):
                _handle_single_script_upload(processed_file, project_dir)
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Only .zip or .py files are allowed for single file upload."
                )
        elif processed_files:
            _handle_multiple_files_upload(processed_files, project_dir)

        # --- 6. 创建数据库记录 ---
        # ✅ 关键：在创建数据库记录之前，确保 package_path 已知
        project_in = schemas.ProjectCreate(
            name=name,
            description=description,
            owner_id=current_user.id,  # ✅ 注入 owner_id
            package_path=abs_project_dir  # ✅ 注入 package_path
        )

        # ✅ 调用 CRUD create 方法
        created_project = crud_project.create(db=db, obj_in=project_in)

        logger.info(f"Successfully created project '{name}' in database.")
        return created_project

    except HTTPException:
        # 如果是 HTTPException，先删除可能创建的目录
        shutil.rmtree(project_dir, ignore_errors=True)
        raise
    except Exception as e:
        # 对于其他异常，也尝试清理目录
        shutil.rmtree(project_dir, ignore_errors=True)
        logger.error(f"Failed to create project '{name}': {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create project: {str(e)}")
    finally:
        # 安全关闭文件
        if processed_file and hasattr(processed_file, 'file'):
            processed_file.file.close()
        if processed_files:
            for f in processed_files:
                if hasattr(f, 'file'):
                    f.file.close()


# --- 辅助函数 ---
def _handle_archive_upload(upload_file: UploadFile, target_dir: str):
    temp_path = os.path.join(target_dir, upload_file.filename)
    try:
        with open(temp_path, "wb") as f:
            shutil.copyfileobj(upload_file.file, f)
        with zipfile.ZipFile(temp_path, 'r') as zip_ref:
            zip_ref.extractall(target_dir)
        os.remove(temp_path)
    except (zipfile.BadZipFile, OSError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid or corrupted archive: {str(e)}")


def _handle_single_script_upload(upload_file: UploadFile, target_dir: str):
    try:
        script_path = os.path.join(target_dir, "run.py")
        with open(script_path, "wb") as f:
            shutil.copyfileobj(upload_file.file, f)
        init_path = os.path.join(target_dir, "__init__.py")
        with open(init_path, "w") as f:
            f.write("# Project package init\n")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save script: {str(e)}")


def _handle_multiple_files_upload(files: List[UploadFile], target_dir: str):
    try:
        for upload_file in files:
            if not upload_file.filename:
                continue
            file_path = os.path.join(target_dir, upload_file.filename)
            file_dir = os.path.dirname(file_path)
            os.makedirs(file_dir, exist_ok=True)
            with open(file_path, "wb") as f:
                shutil.copyfileobj(upload_file.file, f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process file upload: {str(e)}")


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
    # ✅ 修正：使用正确的方法构建查询
    projects = crud_project.get_multi_by_owner(
        db,
        owner_id=current_user.id,
        skip=skip,
        limit=limit
    )
    return projects


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