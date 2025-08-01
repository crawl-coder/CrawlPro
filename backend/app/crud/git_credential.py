# /app/crud/git_credential.py
from typing import List, Optional
from sqlalchemy.orm import Session
from app.crud.base import CRUDBase
from app.models.git_credentials import GitCredential
from app.schemas.git_credential import GitCredentialCreate, GitCredentialUpdate

class CRUDGitCredential(CRUDBase[GitCredential, GitCredentialCreate, GitCredentialUpdate]):
    def get_by_user_and_provider(
        self, db: Session, *, user_id: int, provider: str
    ) -> Optional[GitCredential]:
        return db.query(self.model).filter(
            self.model.user_id == user_id,
            self.model.provider == provider
        ).first()

    def get_multi_by_user(
        self, db: Session, *, user_id: int, skip: int = 0, limit: int = 100
    ) -> List[GitCredential]:
        return (
            db.query(self.model)
            .filter(self.model.user_id == user_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

git_credential = CRUDGitCredential(GitCredential)