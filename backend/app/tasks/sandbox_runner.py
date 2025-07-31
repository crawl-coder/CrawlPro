# /app/tasks/sandbox_runner.py
import docker

def run_in_docker(project_name: str, entrypoint: str, args: dict):
    client = docker.from_env()
    container = client.containers.run(
        image="python:3.10-slim",  # 或自定义镜像
        command=["python", entrypoint, "--args", json.dumps(args)],
        volumes={f"/data/projects/{project_name}": {"bind": "/app", "mode": "ro"}},
        working_dir="/app",
        mem_limit="512m",
        network_mode="none",  # 禁用网络（可选）
        remove=True,
        stdout=True,
        stderr=True
    )
    return container.logs().decode()