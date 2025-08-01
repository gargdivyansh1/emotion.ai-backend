from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Log
from app.schemas import UserResponse, UserUpdateRequest, UserDeleteRequest, PublicUserData, LogType
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

# correct --
@router.put("/update", status_code=status.HTTP_200_OK)
async def update_user(
    update_data: UserUpdateRequest, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    
    print(update_data)
    if not verify_password(update_data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = "Incorrect current password"
        )
    
    update_dict = {}

    if update_data.new_username is not None:
        existing_user = db.query(User).filter(
            User.username == update_data.new_username,
            User.id != current_user.id
        ).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
        update_dict["username"] = update_data.new_username

    if update_data.new_email is not None:
        existing_email = db.query(User).filter(
            User.email == update_data.new_email,
            User.id != current_user.id
        ).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use"
            )
        update_dict["email"] = update_data.new_email

    if update_data.new_password or update_data.confirm_password:
        if update_data.new_password != update_data.confirm_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password and confirm password do not match"
            )
        update_dict["password_hash"] = hash_password(update_data.new_password)

    if update_dict:
        update_dict["updated_at"] = datetime.utcnow()
        db.query(User).filter(User.id == current_user.id).update(update_dict)
        db.commit()

    return {"message": "User updated successfully"}   

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

@router.post("/increment-session")
async def increment_session_count(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        sessions_taken = user.number_of_session_taken
        sessions_allotted = user.number_of_alloted_sessions

        if sessions_taken < sessions_allotted:
            user.number_of_session_taken += 1
            db.commit()
            db.refresh(user)
            return {
                "message": "Session count incremented",
                "number_of_sessions": user.number_of_session_taken
            }
        else:
            return {
                "message": "Session limit reached",
                "number_of_sessions": user.number_of_session_taken,
                "max_sessions_allowed": user.number_of_alloted_sessions
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred while incrementing session: {str(e)}")

# correct --
@router.delete('/delete-profile', status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(
    delete_data: UserDeleteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):    
    if not verify_password(delete_data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect current password"
        )
    
    try:
        db.delete(current_user)
        db.commit()
        
        return None
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting user: {str(e)}"
        )