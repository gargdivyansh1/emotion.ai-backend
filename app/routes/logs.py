from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from app.database import get_db
from app.models import Log, LogType
from app.schemas import LogOut
from app.models import User
from app.utils.auth import admin_required

router = APIRouter(prefix="/logs", tags=["Logs"])

# for getting all logs
@router.get("/" , response_model=List[LogOut])
def get_logs(
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    log_type: Optional[LogType] = Query(None, description="Filter by log type"),
    start_date: Optional[datetime] = Query(None, description="Start date for filtering"),
    end_date: Optional[datetime] = Query(None, description="End date for filtering")
):
    query = db.query(Log)

    if user_id:
        query = query.filter(Log.user_id == user_id)
    if log_type:
        query = query.filter(Log.log_type == log_type)
    if start_date:
        query = query.filter(Log.timestamp >= start_date)
    if end_date:
        query = query.filter(Log.timestamp <= end_date)

    logs = query.order_by(Log.timestamp.desc()).all()
    return logs

@router.get("/{log_id}")
def get_log_by_id(
    log_id: int, 
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required)
):
    db_log = db.query(Log).filter(Log.id == log_id).first()

    if not db_log:
        raise HTTPException(status_code=404, detail="Log not found")
    
    return db_log

# for clear all logs
@router.delete("/clear")
def clear_all_logs(
    db: Session = Depends(get_db),
    admin : User = Depends(admin_required)
):
    deleted_count = db.query(Log).all()
    counting = 0 
    if not deleted_count:
        return {"message": "No logs to delete."}

    for log in deleted_count:  
        db.delete(log)
        counting = counting + 1
        
    db.commit()

    return {"message": f"{counting} logs deleted successfully"}

# for deleting the specific log
@router.delete("/{log_id}")
def delete_log(
    log_id: int,
    db : Session = Depends(get_db), 
    admin: User = Depends(admin_required)
):
    log = db.query(Log).filter(Log.id == log_id).first()

    if not log:
        raise HTTPException(status_code=404, detail="Log not found")

    db.delete(log)
    db.commit()

    return {"message": "Log deleted successfully"}

