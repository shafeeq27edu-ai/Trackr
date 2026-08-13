import os
import uuid
from datetime import datetime

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user
from core.security import create_access_token, get_password_hash, verify_password
from db.database import get_db
from db.models import User
from db.schemas import Token, UserCreate, UserResponse
from services.audit_service import log_audit_event

router = APIRouter()

AUTH_CODES = {}

oauth = OAuth()
from core.logging import logger

client_id = os.getenv("GOOGLE_CLIENT_ID", "dummy")
client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "dummy")

if client_id == "dummy" or client_secret == "dummy":
    logger.warning("GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET is missing or set to 'dummy'. Google OAuth login will fail.")

oauth.register(
    name="google",
    client_id=client_id,
    client_secret=client_secret,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


@router.post("/register", response_model=UserResponse)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    email_normalized = user_in.email.strip().lower()
    result = await db.execute(select(User).where(User.email == email_normalized))
    user = result.scalars().first()
    if user:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        id=str(uuid.uuid4()),
        email=user_in.email.strip().lower(),
        hashed_password=get_password_hash(user_in.password),
        name=user_in.name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    await log_audit_event(db, str(user.id), "REGISTER")
    return user


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)
):
    email_normalized = form_data.username.strip().lower()
    result = await db.execute(select(User).where(User.email == email_normalized))
    user = result.scalars().first()
    if not user or not verify_password(form_data.password, str(user.hashed_password)):
        if user:
            await log_audit_event(db, str(user.id), "LOGIN_FAILED")
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    user.last_login = datetime.utcnow()  # type: ignore[assignment]
    await db.commit()

    access_token = create_access_token(data={"user_id": str(user.id)})
    await log_audit_event(db, str(user.id), "LOGIN_SUCCESS")

    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/google/login")
async def google_login(request: Request):
    public_url = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/")
    redirect_uri = f"{public_url}/api/v1/auth/google/callback"
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback")
async def auth_google_callback(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as e:
        logger.error("OAuth error")
        raise HTTPException(status_code=400, detail="OAuth authorization failed")

    user_info = token.get("userinfo")
    if not user_info:
        raise HTTPException(status_code=400, detail="Could not fetch user info from Google")

    email = user_info.get("email").strip().lower()
    name = user_info.get("name", "Google User")

    # Link or Create Account
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()

    if not user:
        # Create a new user with random password (since they use OAuth)
        user = User(
            id=str(uuid.uuid4()),
            email=email,
            hashed_password=get_password_hash(str(uuid.uuid4())),
            name=name,
        )
        db.add(user)

    user.last_login = datetime.utcnow()  # type: ignore[assignment]
    await db.commit()
    await db.refresh(user)

    access_token = create_access_token(data={"user_id": str(user.id)})
    await log_audit_event(db, str(user.id), "LOGIN_SUCCESS_GOOGLE")

    auth_code = str(uuid.uuid4())
    AUTH_CODES[auth_code] = access_token

    # Redirect back to the Streamlit app with the auth_code
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:8501")
    return RedirectResponse(url=f"{frontend_url}/?auth_code={auth_code}")

@router.post("/exchange")
async def exchange_code(code: str):
    if code in AUTH_CODES:
        token = AUTH_CODES.pop(code)
        return {"access_token": token, "token_type": "bearer"}
    raise HTTPException(status_code=400, detail="Invalid or expired code")
