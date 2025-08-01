# /app/schemas/git_credential.py
from pydantic import BaseModel
from typing import Optional

class GitCredentialBase(BaseModel):
    provider: str
    username: str
    # 注意：我们不会在 Schema 中包含 token，以避免意外泄露

class GitCredentialCreate(GitCredentialBase):
    token: str  # 创建时需要提供 token

class GitCredentialUpdate(GitCredentialBase):
    token: Optional[str] = None  # 更新时可选

class GitCredentialOut(GitCredentialBase):
    id: int
    # 注意：我们不会在输出中包含 token 字段！

    class Config:
        from_attributes = True