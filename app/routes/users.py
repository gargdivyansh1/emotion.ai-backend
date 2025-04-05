from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Log
from app.schemas import UserResponse, UserUpdate, ChangePassword, PublicUserData, LogType
from app.utils.auth import get_current_user, hash_password, verify_password
from datetime import datetime
from app.utils.auth import get_current_user

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/profile", response_model=UserResponse)
def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
    ):

    log_entry = Log(
        user_id=current_user.id,
        action="VIEW_PROFILE",
        message=f"User {current_user.email} viewed their profile",
        timestamp=datetime.utcnow(),
        log_type=LogType.INFO
    )
    db.add(log_entry)
    db.commit()

    return current_user

@router.put("/profile/update", response_model=UserResponse,)
def update_profile(
    user_update: UserUpdate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    update_data = user_update.dict(exclude_unset=True)  

    if "password" in update_data:
        raise HTTPException(status_code=400, detail="Password cannot be updated here.")

    if not update_data:
        raise HTTPException(status_code=400, detail="No valid fields provided for update.")

    for key, value in update_data.items():
        setattr(current_user, key, value)

    current_user.updated_at = datetime.utcnow() 

    db.commit()
    db.refresh(current_user) 

    log_entry = Log(
        user_id=current_user.id,
        action="UPDATE_PROFILE",
        message=f"User {current_user.email} updated their profile, New: {update_data}",
        timestamp=datetime.utcnow(),
        log_type=LogType.INFO
    )
    db.add(log_entry)
    db.commit() 

    return current_user  

@router.put("/change-password")
def change_password(
    change_pass: ChangePassword, 
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):

    if not verify_password(change_pass.old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect current password")
    
    if change_pass.new_password != change_pass.confirm_new_password:
        raise HTTPException(status_code=400, detail="New passwords do not match")

    
    current_user.password_hash = hash_password(change_pass.new_password)
    db.commit()
    db.refresh(current_user)

    log_entry = Log(
        user_id=current_user.id,
        action="CHANGE_PASSWORD",
        message=f"User {current_user.email} changed their password",
        timestamp=datetime.utcnow(),
        log_type=LogType.WARNING  
    )
    db.add(log_entry)
    db.commit()

    return {"message": "Password changed successfully"}

@router.get("/{username}", response_model=PublicUserData)
def get_user(
    username: str, 
    db: Session = Depends(get_db),
    current_user : User = Depends(get_current_user)
):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    log_entry = Log(
        user_id=current_user.id,
        action="VIEW_PUBLIC_PROFILE",
        message=f"User {current_user.email} viewed public profile of {user.email}",
        timestamp=datetime.utcnow(),
        log_type=LogType.INFO
    )
    db.add(log_entry)
    db.commit()

    return user

