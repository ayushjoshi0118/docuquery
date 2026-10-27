from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Query, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from docuquery.database import get_db
from docuquery.models.user import User
from docuquery.schemas.auth import UserRegister, UserLogin, TokenResponse, TokenRefresh, UserOut
from docuquery.services.auth_service import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from docuquery.services.token_blacklist import revoke_token, is_token_revoked
from docuquery.core.rate_limiter import auth_rate_limiter, get_client_ip
from docuquery.api.deps import get_current_user, security
from docuquery.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(user_in: UserRegister, request: Request, db: Session = Depends(get_db)):
    """Register a new user account with rate limiting."""
    client_ip = get_client_ip(request)
    auth_rate_limiter.check(f"register:{client_ip}")

    existing = db.query(User).filter(User.email == user_in.email.lower()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists",
        )

    user = User(
        email=user_in.email.lower(),
        hashed_password=hash_password(user_in.password),
        full_name=user_in.full_name,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(login_in: UserLogin, request: Request, db: Session = Depends(get_db)):
    """Authenticate with email and password to receive JWT tokens with rate limiting."""
    client_ip = get_client_ip(request)
    auth_rate_limiter.check(f"login:{client_ip}")

    user = db.query(User).filter(User.email == login_in.email.lower()).first()
    if not user or not verify_password(login_in.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    access_token = create_access_token(user.id, user.email)
    refresh_token = create_refresh_token(user.id, user.email)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh_token_endpoint(token_in: TokenRefresh, db: Session = Depends(get_db)):
    """Refresh an expired access token using a valid refresh token with token rotation."""
    if is_token_revoked(token_in.refresh_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked",
        )

    payload = decode_token(token_in.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Invalidate used refresh token to enforce refresh token rotation
    revoke_token(token_in.refresh_token)

    access_token = create_access_token(user.id, user.email)
    new_refresh = create_refresh_token(user.id, user.email)
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(
    current_user: User = Depends(get_current_user),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    token: Optional[str] = Query(default=None),
    refresh_token: Optional[str] = Query(default=None),
):
    """
    Invalidate active access token and optional refresh token.
    """
    raw_token = credentials.credentials if credentials else token
    if raw_token:
        revoke_token(raw_token)
    if refresh_token:
        revoke_token(refresh_token)
    return {"message": "Successfully logged out and token invalidated"}


@router.get("/me", response_model=UserOut)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Get profile of currently authenticated user."""
    return current_user
