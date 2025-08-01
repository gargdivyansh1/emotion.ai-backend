from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Notification, User, NotificationStatus
from app.schemas import NotificationOut, NotificationForAll
from app.utils.auth import get_current_user, admin_required
from datetime import datetime
from typing import List, Optional
from sqlalchemy import func, and_, desc

router = APIRouter(prefix="/notifications", tags=["Notifications"])

@router.get("/", response_model=list[NotificationOut])
def get_all_notifications_user(
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, description="Number of records to skip"),
    limit: int = Query(10, description="Number of records to return")
):
    
    print(current_user)
    notifications = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id)
        .order_by(desc(Notification.sent_at))
        .offset(skip)
        .limit(limit)
        .all()
    )
    
    return notifications or []

@router.get("/{notification_id}", response_model=NotificationOut)
def get_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    notification = db.query(Notification).filter(Notification.id == notification_id, Notification.user_id == current_user.id).first()

    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    return notification

@router.put("/{notification_id}/read", response_model=NotificationOut)
def mark_notification_as_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    notification.is_read = True
    notification.status = NotificationStatus.READ
    
    db.commit()
    db.refresh(notification)

    return notification

@router.delete("/{notification_id}/delete")    
def delete_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    notification = db.query(Notification).filter(Notification.id == notification_id, Notification.user_id == current_user.id).first()

    if not notification:
        return {"message": "Notification not found"}

    db.delete(notification)
    db.commit()

    return {"message": "Notification deleted successfully"}

@router.delete("/clear") 
def delete_all_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    deleted_count = db.query(Notification)\
                     .filter(Notification.user_id == current_user.id)\
                     .delete()
    
    db.commit()

    if deleted_count == 0:
        return {"message": "No notifications found to delete"}
    
    return {"message": f"Successfully deleted {deleted_count} notifications"}


@router.get("/admin/get-all", response_model=List[NotificationOut])
def get_all_notifications(
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required),  
    skip: int = Query(0, description="Number of records to skip"),
    limit: int = Query(20, description="Number of records to return")
):
    subquery = (
        db.query(
            Notification.title,
            Notification.message,
            func.max(Notification.sent_at).label("latest_time")  
        )
        .group_by(Notification.title, Notification.message)
        .subquery()
    )

    notifications = (
        db.query(
            Notification.title,
            Notification.message,
            Notification.sent_at
        )
        .join(subquery, and_(
            Notification.title == subquery.c.title,
            Notification.message == subquery.c.message,
            Notification.sent_at == subquery.c.latest_time
        ))
        .order_by(Notification.sent_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    print(notifications)
    return [{"title": n.title, "message": n.message, "sent_at": n.sent_at} for n in notifications]

@router.post("/admin/send")
def send_notification(
    notification: NotificationForAll,
    user_id: Optional[int] = Query(None, description="User ID to send notifications to (omit to broadcast to all)"),
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required)
):
    if user_id:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        new_notification = Notification(
            user_id = user.id,
            title=notification.title,
            message=notification.message,
            notification_type=notification.notification_type.value,
            sent_at=datetime.utcnow()
        )

        db.add(new_notification)
        db.commit()
        db.refresh(new_notification)

        return new_notification
    else:

        users = db.query(User).all()

        if not users:
            return {"Message": "No users found"}
        
        for user in users:
            new_notification = Notification(
                user_id=user.id,
                title=notification.title,
                message=notification.message,
                notification_type=notification.notification_type.value,
                sent_at=datetime.utcnow()
            )

            db.add(new_notification)

        db.commit()

        return {"message": "Notification send to all users successfully"}

@router.post("/admin/broadcast")
def send_notification_to_all(
    notification: NotificationForAll,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required)  
):
    users = db.query(User).filter(
        User.is_active == True,
    ).all()

    if not users:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active users found"
        )

    notifications_to_create = []
    for user in users:
        notifications_to_create.append(
            Notification(
                user_id=user.id,
                title=notification.title,
                message=notification.message,
                notification_type=notification.notification_type.value,
                status=notification.status.value,
                sent_at=datetime.utcnow()
            )
        )
    
    try:
        db.bulk_save_objects(notifications_to_create)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create notifications: {str(e)}"
        )

    return {
        "message": f"Notification successfully sent to {len(users)} users",
        "count": len(users) 
    }

# for deleting all read or all 
@router.delete("/admin/delete/all")
def delete_all_notifications_admin(
    is_read: bool = Query(True),
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required)
):

    query = db.query(Notification)

    if is_read is not None:
        query = query.filter(Notification.is_read == is_read)

    data = query.all()

    if not data:
        return {"message": "No notifications found"}

    for notification in data:
        db.delete(notification)

    db.commit()

    return {"message": "All notifications deleted successfully"}

# for deleting one notification by admin
@router.delete("/admin/delete/one/{notification_id}")
def delete_notification_admin(
    notification_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required)
):

    notification = db.query(Notification).filter(Notification.id == notification_id).first()

    if not notification:
        return {"message": "Notification not found"}

    db.delete(notification)
    db.commit()

    return {"message": "Notification deleted successfully"}
