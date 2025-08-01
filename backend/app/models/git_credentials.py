# /app/models/git_credential.py
from sqlalchemy import Column, Integer, String, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.db.base_class import Base
from app.core.config import settings
from cryptography.fernet import Fernet

class GitCredential(Base):
    __tablename__ = "git_credentials"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("cp_users.id"), nullable=False)
    provider = Column(String(50), nullable=False)  # e.g., "github", "gitlab"
    username = Column(String(100), nullable=False)
    # 加密存储的 Token
    _encrypted_token = Column("encrypted_token", Text, nullable=False)

    # 建立与 User 的关系
    user = relationship("User", back_populates="git_credentials")

    @property
    def token(self):
        """解密并返回 Token"""
        if self._encrypted_token:
            f = Fernet(settings.ENCRYPTION_KEY.encode())
            return f.decrypt(self._encrypted_token.encode()).decode()
        return None

    @token.setter
    def token(self, raw_token: str):
        """加密 Token 并存储"""
        f = Fernet(settings.ENCRYPTION_KEY.encode())
        self._encrypted_token = f.encrypt(raw_token.encode()).decode()