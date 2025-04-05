from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Log, LogAction
from app.schemas import UserResponse, RoleUpdate, UserAccessUpdate, LogType
from app.utils.auth import admin_required
from datetime import datetime
from typing import List

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.get("/users", response_model = List[UserResponse])
def get_all_users(db: Session = Depends(get_db), admin: User = Depends(admin_required)):

    check_admin = db.query(User).filter(User.role == admin.role).all()
    
    if not check_admin:
        raise HTTPException(status_code=403, detail="No admin user found")
    
    users = db.query(User).filter(User.role == "USER").all()

    log_entry = Log(
        user_id=admin.id,
        action="VIEW_USERS",
        message=f"Admin {admin.email} viewed all users",
        timestamp=datetime.utcnow(),
        log_type=LogType.INFO
    )
    db.add(log_entry)
    db.commit()

    return users 

@router.put("/update_role/{user_id}")
def update_user_role(
    user_id: int, 
    role_update: RoleUpdate, 
    db: Session = Depends(get_db), admin: 
    User = Depends(admin_required)
):
    check_admin = db.query(User).filter(User.role == admin.role).all()

    if not check_admin:
        raise HTTPException(status_code=403, detail="No admin user found")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.role = role_update.role
    if role_update.role == "admin":
        user.can_manage_users = True
        user.can_export_reports = True
        user.emotion_data_access = True
    else:
        user.can_manage_users = False
        user.can_export_reports = False
        user.emotion_data_access = False

    db.commit()

    log_entry = Log(
        user_id=admin.id,
        action=LogAction.UPDATE_PROFILE,
        message=f"Admin {admin.email} changed {user.email}'s role to {user.role}",
        timestamp=datetime.utcnow(),
        log_type=LogType.INFO
    )
    db.add(log_entry)
    db.commit()

    return {"message": "User role updated successfully"}

@router.put("/manage_access/{user_id}")
def manage_user_access(
    user_id: int, 
    access_data: UserAccessUpdate, 
    db: Session = Depends(get_db), 
    admin: User = Depends(admin_required)
):

    check_admin = db.query(User).filter(User.role == admin.role).all()

    if not check_admin:
        raise HTTPException(status_code=403, detail="No admin user found")
    
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.emotion_data_access = access_data.emotion_data_access
    user.can_export_reports = access_data.can_export_reports
    
    db.commit()

    log_entry = Log(
        user_id=admin.id,
        action=LogAction.UPDATE_PROFILE,
        message=f"Admin {admin.email} updated access for {user.email} New: {access_data.dict()}",
        timestamp=datetime.utcnow(),
        log_type=LogType.INFO
    )
    db.add(log_entry)
    db.commit()

    return {"message": "User access updated successfully"}

@router.delete("/delete_user/{user_id}")
def delete_user(
    user_id: int, 
    db: Session = Depends(get_db), 
    admin: User = Depends(admin_required)
):

    check_admin = db.query(User).filter(User.role == admin.role).all()

    if not check_admin:
        raise HTTPException(status_code=403, detail="No admin user found")

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(user)

    db.commit()

    log_entry = Log(
        user_id=admin.id,
        action=LogAction.DELETE_ACCOUNT,
        message=f"Admin {admin.email} deleted user {user.email}",
        timestamp=datetime.utcnow(),
        log_type=LogType.WARNING
    )
    db.add(log_entry)
    db.commit()
    
    return {"message": "User deleted successfully"}
