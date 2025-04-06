from fastapi import APIRouter, Depends, HTTPException,Body, Header
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
import redis
from datetime import datetime
from app.database import get_db, redis_client
from passlib.context import CryptContext
from app.models import User, UserRole, Log, LogAction
from app.schemas import UserCreate, UserResponse, LogType
from app.utils.auth import hash_password, verify_password
from app.utils.jwt import create_access_token, verify_token

router = APIRouter(prefix="/auth", tags=["Authentication"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# done
@router.post("/register", response_model=UserResponse)
def register_user(
    user: UserCreate, 
    db: Session = Depends(get_db)
):
    first_user = db.query(User).first()

    existing_user = db.query(User).filter(User.email == user.email or User.username == user.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    if user.real_time_monitoring_access == False or user.real_time_monitoring_access == None:
        raise HTTPException(status_code=400, detail="Real-time monitoring access is required")
    
    hashed_password = hash_password(user.password)
    new_user = User(
        email=user.email,
        username=user.username,
        password_hash=hashed_password,
        real_time_monitoring_access=user.real_time_monitoring_access,
    )

    if first_user is None:
        new_user.role = UserRole.ADMIN

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    log_entry = Log(
        user_id=new_user.id,
        log_type=LogType.INFO,  
        message=f"User {new_user.email} registered successfully", 
        action = LogAction.REGISTER
    )
    db.add(log_entry)
    db.commit()

    return new_user

# done
@router.post("/login")
def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(get_db)
):

    user = db.query(User).filter(User.email == form_data.username).first()

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token({"user_id": user.id, "role": user.role})

    user.is_verified = True
    user.last_login = datetime.utcnow()
    user.jwt_token = token
    user.is_active = True

    if user.role == UserRole.ADMIN:
        user.can_manage_users = True
        user.can_export_reports = True
        user.emotion_data_access = True
        db.commit()

    log_entry = Log(
        user_id=user.id,
        log_type=LogType.INFO,
        message=f"User {user.email} logged in",
        timestamp=datetime.utcnow(),
        action= LogAction.LOGIN
    )
    db.add(log_entry)
    db.commit() 

    return {"access_token": token, 
            "token_type": "bearer",
            "role": user.role,
            "is_verified": user.is_verified,
            "user_id": user.id,
            }

@router.post("/logout")
def logout(
    password: str = Body(..., embed=True),  
    authorization: str = Header(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(verify_token)
):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")

    token = authorization.replace("Bearer ", "")

    user = db.query(User).filter(User.id == current_user["user_id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not pwd_context.verify(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect password")

    expires_in = current_user["exp"] - int(datetime.utcnow().timestamp())
    if expires_in > 0:
        redis_client.setex(f"blacklist:{token}", expires_in, "blacklisted")

    user.jwt_token = None
    db.commit()
    db.refresh(user)

    log_entry = Log(
        user_id=user.id,
        message=f"User {user.email} logged out",
        timestamp=datetime.utcnow(),
        action=LogAction.LOGOUT,
        log_type=LogType.INFO
    )
    db.add(log_entry)
    db.commit()

    return {"message": "Logout successful"}

@router.get("/me", response_model=UserResponse)
def get_current_user_profile(
    current_user: User = Depends(verify_token), 
    db: Session = Depends(get_db)
    ):

    user = db.query(User).filter(User.id == current_user["user_id"]).first()

    if not user:
        raise HTTPException(status_code = 404 , details = "User not found")
    
    log_entry = Log(
        user_id=user.id,
        message=f"User {user.email} updated their profile",
        timestamp=datetime.utcnow(),
        log_type=LogType.INFO,
        action= LogAction.VIEW_PROFILE
    )
    db.add(log_entry)
    db.commit()

    return user
