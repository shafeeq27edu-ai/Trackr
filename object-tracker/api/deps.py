import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import ALGORITHM, SECRET_KEY
from db.database import get_db
from db.models import User
from db.schemas import TokenData

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login", auto_error=False)


async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    auth_header: str | None = request.headers.get("Authorization")
    if auth_header is None or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token: str = auth_header.split(" ")[1]
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        if not isinstance(user_id, str):
            raise credentials_exception
        token_data = TokenData(user_id=user_id)
    except jwt.PyJWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == token_data.user_id))
    user = result.scalars().first()
    if user is None:
        raise credentials_exception
    return user
