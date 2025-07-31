# /backend/app/schemas/token.py

from pydantic import BaseModel

class Token(BaseModel):
    """
    用于登录接口返回的 Token 模型
    """
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """
    用于解析 JWT Token 内部数据的模型 (payload)
    'sub' (subject) 是 JWT 标准中推荐用来存放用户唯一标识的字段。
    """
    sub: str