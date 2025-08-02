from fastapi import APIRouter, Depends, HTTPException,Body, Header, Form, status
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from datetime import datetime, timedelta, timezone
from app.database import get_db, redis_client
from passlib.context import CryptContext
from app.models import User, UserRole, Log, LogAction
from app.schemas import UserCreate, UserResponse, LogType
from app.utils.auth import hash_password, verify_password, get_current_user
from app.models import NotificationType, Notification, NotificationStatus
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

    notification = Notification(
        user_id=new_user.id,
        title="Welcome to EmotionAI!",
        message=(
            "Your account has been successfully registered.\n\n"
            "To get the most out of EmotionAI, we encourage you to start using the application regularly "
            "and take a few monitoring sessions. The insights, emotional reports, and progress charts will "
            "only start appearing once you've interacted with the system over time.\n\n"
            "Make sure to use EmotionAI during your daily activities — not just while sitting idle — "
            "so it can accurately understand and reflect your emotional patterns in real-world scenarios.\n\n"
            "Begin your journey toward emotional awareness and self-improvement today!"
        ),
        notification_type=NotificationType.INFORMATIVE, 
        sent_at=datetime.utcnow(),
        status=NotificationStatus.SENT
    )
    db.add(notification)

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
async def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == form_data.username).first()

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if user.two_factor_enabled:
        return {
            "two_factor_required": True,
            "email": user.email,
            "message": "Two-factor authentication required"
        }
    
    print("hello")
    return complete_login(user, db)

@router.post("/complete-login")
async def complete_login_after_2fa(
    email: str = Form(...),
    password: str = Form(...),
    otp: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == email).first()
    
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if user.two_factor_enabled:
        if not otp:
            raise HTTPException(status_code=400, detail="OTP required")
        
        if not user.two_factor_secret or user.two_factor_secret != otp:
            raise HTTPException(status_code=400, detail="Invalid OTP")
        
        # if (datetime.utcnow() - user.otp_created_at) > timedelta(minutes=5):
        #     raise HTTPException(status_code=400, detail="OTP expired")
        
        user.two_factor_secret = None
    
    return complete_login(user, db)

def complete_login(user: User, db: Session):
    print("Hello")
    token_data = {
        "user_id": user.id,
        "role": user.role,
        "email": user.email 
    }
    token = create_access_token(token_data)
    print(token)
    
    user.last_login = datetime.now(timezone.utc)
    user.jwt_token = token
    user.is_verified = True
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
        timestamp=datetime.now(timezone.utc),
        action=LogAction.LOGIN
    )
    db.add(log_entry)
    db.commit()

    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": int(timedelta(days=1).total_seconds()),  
        "role": user.role,
        "is_verified": user.is_verified,
        "user_id": user.id,
        "two_factor_enabled": user.two_factor_enabled,
        "email": user.email  
    }

@router.post("/logout")
def logout(
    authorization: str = Header(None, alias="Authorization"), 
    db: Session = Depends(get_db), 
):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")

    token = authorization.replace("Bearer ", "")
    
    try:
        current_user = verify_token(token)
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

    expires_in = current_user["exp"] - int(datetime.utcnow().timestamp())
    if expires_in > 0:
        redis_client.setex(f"blacklist:{token}", expires_in, "blacklisted")

    user = db.query(User).filter(User.id == current_user["user_id"]).first()
    if user:
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
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    log_entry = Log(
        user_id=current_user.id,
        message=f"User {current_user.email} viewed their profile",
        timestamp=datetime.now(timezone.utc),
        log_type=LogType.INFO,
        action=LogAction.VIEW_PROFILE
    )
    db.add(log_entry)
    db.commit()

    return current_user