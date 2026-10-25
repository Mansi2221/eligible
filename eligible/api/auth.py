"""JWT bearer auth + role-based access control.

Every request carries a Bearer JWT; a FastAPI dependency verifies the signature
and extracts the role claim. `require_role` enforces RBAC so, e.g., a trial
sign-off endpoint reserved for a physician cannot be called with an analyst token.

`issue_token` stands in for the OIDC issuer for local/demo use, in production
the tokens come from an external IdP and only verification runs here.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from eligible.config import get_settings

ROLES = ("data_analyst", "coordinator", "physician")
# Role hierarchy: a higher role satisfies a requirement for a lower one.
_RANK = {"data_analyst": 1, "coordinator": 2, "physician": 3}

_bearer = HTTPBearer(auto_error=True)


class User(BaseModel):
    sub: str
    role: str


def issue_token(sub: str, role: str, expires_minutes: int = 60) -> str:
    if role not in ROLES:
        raise ValueError(f"unknown role {role!r}")
    s = get_settings()
    now = datetime.now(timezone.utc)
    claims = {"sub": sub, "role": role, "iat": now, "exp": now + timedelta(minutes=expires_minutes)}
    return jwt.encode(claims, s.jwt_secret, algorithm=s.jwt_algorithm)


def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(_bearer),
) -> User:
    s = get_settings()
    try:
        payload = jwt.decode(creds.credentials, s.jwt_secret, algorithms=[s.jwt_algorithm])
    except JWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid or expired token")
    role = payload.get("role")
    if role not in ROLES:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "token missing a valid role")
    return User(sub=payload.get("sub", ""), role=role)


def require_role(minimum: str):
    """Dependency factory: require at least `minimum` role rank."""
    needed = _RANK[minimum]

    def _dep(user: User = Depends(get_current_user)) -> User:
        if _RANK[user.role] < needed:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"role '{user.role}' cannot access an endpoint requiring '{minimum}'",
            )
        return user

    return _dep
