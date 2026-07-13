from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
from datetime import datetime

from db.database import get_db
from db.models import User
from db.schemas import UserCreate, UserResponse, Token
from core.security import verify_password, get_password_hash, create_access_token
from api.deps import get_current_user
from services.audit_service import log_audit_event

router = APIRouter()

@router.post("/register", response_model=UserResponse)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user_in.email))
    user = result.scalars().first()
    if user:
        raise HTTPException(status_code=400, detail="Email already registered")
        
    user = User(
        id=str(uuid.uuid4()),
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        name=user_in.name
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    await log_audit_event(db, user.id, "REGISTER")
    return user

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == form_data.username))
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
