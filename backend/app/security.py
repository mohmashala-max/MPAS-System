from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from .models import UserRole
from .settings import get_settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")
password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, encoded: str) -> bool:
    try:
        return password_hasher.verify(encoded, password)
    except (InvalidHashError, VerificationError, VerifyMismatchError):
        return False


def require_access_token(token: str = Depends(oauth2_scheme)) -> str:
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    try:
        settings = get_settings()
        jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from error
    return token


def access_claims(token: str = Depends(require_access_token)) -> dict[str, str]:
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def require_role(*roles: UserRole):
    def dependency(claims: dict[str, str] = Depends(access_claims)) -> dict[str, str]:
        if claims.get("role") not in {role.value for role in roles}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return claims

    return dependency


def token_expiry(minutes: int = 15) -> datetime:
    return datetime.now(timezone.utc) + timedelta(minutes=minutes)


def create_access_token(
    subject: str,
    role: str,
    tenant_id: str = "tenant-development",
    facilities: list[str] | None = None,
) -> str:
    settings = get_settings()
    return jwt.encode(
        {
            "sub": subject,
            "role": role,
            "tenant_id": tenant_id,
            "facilities": facilities or ["*"],
            "exp": token_expiry(settings.access_token_minutes),
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
