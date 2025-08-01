from fastapi import APIRouter, HTTPException, Depends
from random import randint
from app.schemas import OTPverify, OTPsend
from app.services.email_serivce import send_email_otp
from sqlalchemy.orm import Session
from app.models import User
from app.database import get_db
from app.models import User

async def update_user_otp(email: str, otp: str, db: Session):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise ValueError("User not found")
    
    user.two_factor_secret = otp
    db.commit()
    db.refresh(user)

async def mark_two_factor_enabled(email: str, otp: str, enable: bool, db: Session):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise ValueError("User not found")

    if user.two_factor_secret != otp:
        raise ValueError("Invalid OTP")

    user.two_factor_enabled = enable
    user.two_factor_secret = None if not enable else user.two_factor_secret
    db.commit()

router = APIRouter()

@router.post('/api/send_otp')
async def send_otp(data: OTPsend, db: Session = Depends(get_db)):
    otp = str(randint(100000, 999999))
    await update_user_otp(data.email, otp, db)
    await send_email_otp(data.email, f"Your OTP is: {otp}")
    return {"message": "OTP sent"}

@router.post('/api/verify_otp')
async def verify_otp(data: OTPverify, db: Session = Depends(get_db)):
    try:
        await mark_two_factor_enabled(data.email, data.otp, data.enable, db)
        message = "Two-Factor Authentication Enabled" if data.enable else "Two-Factor Authentication Disabled"
        return {"success": True, "message": message}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))