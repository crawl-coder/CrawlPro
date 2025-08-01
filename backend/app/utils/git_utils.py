# /app/utils/git_utils.py
import re

import git
import os
from loguru import logger
from typing import Optional
from urllib.parse import urlparse

def clone_project_from_git(
    repo_url: str,
    target_path: str,
    branch: str = "main",
    username: Optional[str] = None,
    password: Optional[str] = None,
    ssh_key_path: Optional[str] = None
):
    """
    从 Git 仓库克隆项目到指定路径。

    Args:
        repo_url (str): Git 仓库的 URL。
        target_path (str): 本地目标路径（应为绝对路径）。
        branch (str): 要克隆的分支名。默认为 "main"。
        username (str, optional): HTTP/HTTPS 认证用户名。
        password (str, optional): HTTP/HTTPS 认证密码。
        ssh_key_path (str, optional): SSH 私钥文件的路径（用于 SSH 认证）。
    """
    try:
        # 1. 解析 URL
        repo_url = repo_url.strip()
        ssh_pattern = r'^git@([^:]+):(.+)$'
        ssh_match = re.match(ssh_pattern, repo_url)

        if ssh_match:
            hostname = ssh_match.group(1)
            scheme = 'ssh'
            logger.debug(f"识别到SSH协议，主机: {hostname}")
        else:
            parsed_url = urlparse(repo_url)
            scheme = parsed_url.scheme.lower()
            hostname = parsed_url.hostname
            if not scheme or not hostname:
                raise ValueError(f"无效的仓库地址: {repo_url}")

        abs_target_path = os.path.abspath(target_path)
        logger.info(f"开始克隆项目到: {abs_target_path}")

        # 2. 配置认证
        git_env = {}
        clone_url = repo_url

        if scheme in ['http', 'https']:
            if username and password:
                clone_url = f"{parsed_url.scheme}://{username}:{password}@{hostname}{parsed_url.path}"
                logger.debug("使用用户名密码进行HTTPS认证")
        elif scheme == 'ssh':
            if ssh_key_path:
                if not os.path.exists(ssh_key_path):
                    raise ValueError(f"SSH密钥文件未找到: {ssh_key_path}")
                if not os.access(ssh_key_path, os.R_OK):
                    raise PermissionError(f"无权限读取SSH密钥: {ssh_key_path}")
                ssh_cmd = f'ssh -i {ssh_key_path} -o StrictHostKeyChecking=no'
                git_env['GIT_SSH_COMMAND'] = ssh_cmd
                logger.debug(f"使用SSH密钥进行认证")
        else:
            raise ValueError(f"不支持的协议: {scheme}")

        # 3. 执行克隆
        parent_dir = os.path.dirname(abs_target_path)
        if not os.path.exists(parent_dir):
            raise FileNotFoundError(f"父目录不存在: {parent_dir}")

        if os.path.exists(target_path):
            if os.listdir(target_path):
                raise FileExistsError(f"目标目录已存在且非空，无法克隆: {abs_target_path}")
            else:
                logger.warning(f"目标目录已存在但为空，将被填充: {abs_target_path}")

        repo = git.Repo.clone_from(
            url=clone_url,
            to_path=target_path,
            branch=branch,
            env=git_env,
            progress=git.RemoteProgress()
        )

        logger.success(f"项目克隆成功: {abs_target_path}")
        return repo

    except git.exc.GitCommandError as e:
        error_msg = f"Git命令执行失败: {str(e)}"
        logger.error(error_msg)
        if hasattr(e, 'stderr'):
            logger.error(f"Git错误信息: {e.stderr}")
        raise ValueError(error_msg) from e
    except (ValueError, FileExistsError, FileNotFoundError) as e:
        logger.error(str(e))
        raise
    except Exception as e:
        error_msg = f"克隆项目时发生未知错误: {str(e)}"
        logger.exception(error_msg)
        raise RuntimeError(error_msg) from e
