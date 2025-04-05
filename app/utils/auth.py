from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, status, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, UserRole
from app.utils.jwt import verify_token
from passlib.context import CryptContext
import redis
from typing import Dict
from app.schemas import UserResponse

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

redis_client = redis.StrictRedis(host="localhost", port=6379, db=0, decode_responses=True)

def hash_password(password: str) -> str:
    """Hash the password using bcrypt."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload: Dict[str,str] = verify_token(token)
        user_id :str = payload.get("user_id")

        user = db.query(User).filter(User.id == user_id).first()

        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        return user

    except HTTPException as e:
        raise e  

    except Exception:
        raise credentials_exception
    
def admin_required(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    payload = verify_token(token) 
    
    user = db.query(User).filter(User.id == payload["user_id"]).first()

    if not user or user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    return user  

