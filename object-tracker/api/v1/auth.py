import uuid
from datetime import datetime

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

from authlib.integrations.starlette_client import OAuth
import os

router = APIRouter()

oauth = OAuth()
oauth.register(
    name="google",
    client_id=os.getenv("GOOGLE_CLIENT_ID", "dummy"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET", "dummy"),
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

    await log_audit_event(db, user.id, "REGISTER")
    return user


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)
):
    email_normalized = form_data.username.strip().lower()
    result = await db.execute(select(User).where(User.email == email_normalized))
    user = result.scalars().first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        if user:
            await log_audit_event(db, user.id, "LOGIN_FAILED")
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    user.last_login = datetime.utcnow()
    await db.commit()

    access_token = create_access_token(data={"user_id": user.id})
    await log_audit_event(db, user.id, "LOGIN_SUCCESS")

    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/google/login")
async def google_login(request: Request):
    # Determine the callback URL based on the incoming request
    redirect_uri = str(request.url_for("auth_google_callback"))
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback")
async def auth_google_callback(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

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

    user.last_login = datetime.utcnow()
    await db.commit()
    await db.refresh(user)

    access_token = create_access_token(data={"user_id": user.id})
    await log_audit_event(db, user.id, "LOGIN_SUCCESS_GOOGLE")

    # Redirect back to the Streamlit app with the token
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:8501")
    return RedirectResponse(url=f"{frontend_url}/?token={access_token}")
