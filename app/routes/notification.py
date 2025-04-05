from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Notification, User
from app.schemas import NotificationCreate, NotificationOut, NotificationForAll, NotificationOutNew
from app.utils.auth import get_current_user, admin_required
from datetime import datetime
from typing import List
from sqlalchemy import func, and_, desc

router = APIRouter(prefix="/notifications", tags=["Notifications"])

# for getting all the notifacation by the user
@router.get("/", response_model=list[NotificationOut])
def get_all_notifications(
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, description="Number of records to skip"),
    limit: int = Query(10, description="Number of records to return")
    ):

    query = db.query(Notification).filter(Notification.user_id == current_user.id)

    notifications = query.order_by(desc(Notification.sent_at)).offset(skip).limit(limit).all()

    if not notifications:
        return []
    
    return notifications

# for getting the specific notification 
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

# for reading the notification
@router.put("/{notification_id}/read", response_model=NotificationOut)
def mark_notification_as_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    notification = db.query(Notification).filter(Notification.id == notification_id, Notification.user_id == current_user.id).first()

    if not notification:
        return {"message": "Notification not found"}

    notification.is_read = True
    db.commit()
    db.refresh(notification)

    return notification

# for user to delete the certain nottification
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

# for deleting all the notification 
@router.delete("/clear-all-notifications-user")
def delete_all_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    notifications = db.query(Notification).filter(Notification.user_id == current_user.id).all()

    if not notifications:
        return {"message": "No notifications found"}

    for notification in notifications:
        db.delete(notification)

    db.commit()

    return {"message": "All notifications deleted successfully"}


# now admin
@router.get("/admin/get-all", response_model=List[NotificationOutNew])
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

    query = (
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
    )

    notifications = query.offset(skip).limit(limit).all()

    return [{"title": n[0], "message": n[1], "sent_at": n[2]} for n in notifications] 

@router.post("/send-notification-to-user")
def send_notification(
    notification: NotificationCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required)
):
    user = db.query(User).filter(User.id == notification.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    new_notification = Notification(
        user_id=notification.user_id,
        title=notification.title,
        message=notification.message,
        notification_type=notification.notification_type.value,
        status=notification.status,
        sent_at=datetime.utcnow()
    )

    db.add(new_notification)
    db.commit()
    db.refresh(new_notification)

    return new_notification

# send notification to all
@router.post("/send-notification-to-all-users", response_model=dict)
def send_notification_to_all(
    notification: NotificationForAll,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required)
):

    check_admin = db.query(User).filter(User.role == admin.role).all()      
    if not check_admin:
        return {"message": "No admin user found"}

    users = db.query(User).all()

    if not users:
        return {"message": "No users found"}

    for user in users:
        new_notification = Notification(
            user_id=user.id, 
            title=notification.title,
            message=notification.message,
            notification_type=notification.notification_type.value,
            status=notification.status,
            sent_at=datetime.utcnow())
        db.add(new_notification)

    db.commit()

    return {"message": "Notification sent to all users successfully"}

# for deleting all the notification by the admin
@router.delete("/admin/clear-all-notifications")
def delete_all_notifications_admin(
    is_read: bool = Query(True),
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required)
):

    check_admin = db.query(User).filter(User.role == admin.role).all()      
    if not check_admin:
        return {"message": "No admin user found"}

    notifications = db.query(Notification).filter(Notification.is_read == is_read).all()

    if not notifications:
        return {"message": "No notifications found"}

    for notification in notifications:
        db.delete(notification)

    db.commit()

    return {"message": "All notifications deleted successfully"}

# for deleting the notification by the admin 
@router.delete("/admin/{notification_id}")
def delete_notification_admin(
    notification_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required)
):

    check_admin = db.query(User).filter(User.role == admin.role).all()      
    if not check_admin:
        return {"message": "No admin user found"}

    notification = db.query(Notification).filter(Notification.id == notification_id).first()

    if not notification:
        return {"message": "Notification not found"}

    db.delete(notification)
    db.commit()

    return {"message": "Notification deleted successfully"}
