import os
import sys
import subprocess

def install_requirements(project_dir: str):
    req_file = os.path.join(project_dir, "requirements.txt")
    if os.path.exists(req_file):
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", req_file], check=True)


def detect_entrypoint(project_dir: str) -> str:
    candidates = [
        "run.py", "start.py", "main.py",
        "run.sh", "start.sh",
        "index.js", "app.js"
    ]
    for f in candidates:
        if os.path.exists(os.path.join(project_dir, f)):
            return f
    return "run.py"  # 默认