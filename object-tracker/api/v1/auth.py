from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
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
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == user_in.email).first()
    if user:
        raise HTTPException(status_code=400, detail="Email already registered")
        
    user = User(
        id=str(uuid.uuid4()),
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        name=user_in.name
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    log_audit_event(db, user.id, "REGISTER")
    return user

@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        if user:
            log_audit_event(db, user.id, "LOGIN_FAILED")
        raise HTTPException(status_code=401, detail="Incorrect email or password")
        
    user.last_login = datetime.utcnow()
    db.commit()
    
    access_token = create_access_token(data={"user_id": user.id})
    log_audit_event(db, user.id, "LOGIN_SUCCESS")
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user
