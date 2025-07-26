from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional, Literal
from datetime import datetime
from app.database import get_db
from app.models import UserFeedback, User, UserRole, Log, LogType
from app.utils.auth import get_current_user, admin_required
from app.schemas import UserFeedbackCreate, UserFeedbackOut
from app.models import FeedbackType

router = APIRouter(prefix="/feedback", tags=["Feedback"])

@router.post("/", response_model=UserFeedbackOut)
def submit_feedback(
    feedback_data: UserFeedbackCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    new_feedback = UserFeedback(
        user_id=user.id,
        feedback_type = feedback_data.feedback_type,
        message = feedback_data.message,
        created_at=datetime.utcnow(),
        rating = feedback_data.rating,
    )

    db.add(new_feedback)
    db.commit()
    db.refresh(new_feedback)

    log_entry = Log(
        user_id=user.id,
        action="GIVE_FEEDBACK",
        message=f"User: {user.email} made the feedback: {feedback_data.message}",
        timestamp=datetime.utcnow(),
        log_type=LogType.INFO
    )
    db.add(log_entry)
    db.commit()

    return new_feedback

@router.get("/", response_model=List[UserFeedbackOut])
def get_all_feedback(
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required),
    feedback_type: Optional[FeedbackType] = Query(None, description="Filter by feedback type"),
    skip: int = Query(0, description="Number of records to skip"),
    limit: int = Query(10, description="Number of records to return"),
    sort_by: Optional[Literal["date", "rating"]] = Query("date", description="Sort by 'date' or 'rating'")
):
    
    check_admin = db.query(User).filter(User.role == admin.role).all()  

    if not check_admin:
        raise HTTPException(status_code=403, detail="No admin user found")
    
    query = db.query(UserFeedback)

    if feedback_type:
        query = query.filter(UserFeedback.feedback_type == feedback_type)
    
    if sort_by == "rating":
        query = query.order_by(desc(UserFeedback.rating))
    else:
        query = query.order_by(desc(UserFeedback.created_at))   

    feedback_list = query.filter().offset(skip).limit(limit).all()

    print(feedback_list)
    return feedback_list

@router.get("/my-feedback", response_model=List[UserFeedbackOut])
def get_user_feedback(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    skip: int = Query(0, description="Number of records to skip"),
    limit: int = Query(10, description="Number of records to return"),
):
    user = db.query(User).filter(User.id == user.id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    feedback_list = db.query(UserFeedback).filter(UserFeedback.user_id == user.id).offset(skip).limit(limit).all()

    return feedback_list

@router.delete("/delete-feedback-user/{feedback_id}")
def delete_feedback(
    feedback_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    feedback = db.query(UserFeedback).filter(UserFeedback.id == feedback_id).first()
    
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")

    if user.id != feedback.user_id and user.role.lower() != UserRole.ADMIN: # type: ignore
        raise HTTPException(status_code=403, detail="Not authorized to delete this feedback")

    db.delete(feedback)

    log_entry = Log(
        user_id=user.id,
        action="DELETE_FEEDBACK",
        message=f"User: {user.email} delete the feedback: {feedback.id}",
        timestamp=datetime.utcnow(),
        log_type=LogType.WARNING
    )
    db.add(log_entry)
    db.commit()

    return {"message": "Feedback deleted successfully"}

@router.delete("/delete-feedback-admin/{feedback_id}")
def delete_feedback_admin(
    feedback_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required)
):

    check_admin = db.query(User).filter(User.role == admin.role).all()  

    if not check_admin:
        raise HTTPException(status_code=403, detail="No admin user found")
    
    feedback = db.query(UserFeedback).filter(UserFeedback.id == feedback_id).first()
    
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")

    db.delete(feedback)
    
    log_entry = Log(
        user_id=admin.id,
        action="DELETE_FEEDBACK",
        message=f"Admin: {admin.email} delete the feedback: {feedback.id}",
        timestamp=datetime.utcnow(),
        log_type=LogType.WARNING
    )
    db.add(log_entry)
    db.commit()

    return {"message": "Feedback deleted successfully"}
