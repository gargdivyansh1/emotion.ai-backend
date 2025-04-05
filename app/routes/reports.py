from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from fastapi.responses import FileResponse
from typing import Literal
from app.database import get_db
import os
from fastapi import HTTPException
from app.utils.auth import get_current_user
from app.repositories.emotion_repo import  get_all_reports_by_user, get_report_by_id_user, get_filtered_reports, admin_get_all_reports_by_user_id
from app.utils.auth import admin_required
from app.models import Report ,LogAction, LogType, Log
from datetime import datetime
from sqlalchemy import desc, and_
from app.models import User, ExportStatus
import asyncio
from app.services.email_serivce import send_email

router = APIRouter(prefix="/reports", tags=["Reports"])

# sending email to the user containing report 
# it is for the 1 day 
# this is called when the user export the pdf

@router.get("/admin_getting_all_reports")
def admin_wants_all_reports(
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required)
):
    reports = db.query(Report).all()
    
    if not reports:
        raise HTTPException(status_code=404, detail="NO report is found.")
    
    log_entry = Log(
        user_id=admin.id,
        action=LogAction.GET_FILTERED_REPORTS,
        message=f"Admin {admin.email} retrieved filtered reports of all users.",
        timestamp=datetime.utcnow(),
        log_type=LogType.INFO
    )

    db.add(log_entry)
    db.commit()

    print(reports)
    
    return reports 

@router.get("/one_report/admin_getting_all_reports_of_user")
def admin_getting_all_reports_of_user(
    user_id: int, 
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required)
):
    reports = admin_get_all_reports_by_user_id(admin,user_id, db)

    if not reports:
        raise HTTPException(status_code=404, detail="No reports found for the given user.")     
    
    return reports

@router.get("/admin_getting_filterd_reports")
def admin_get_filtered_reports_route(
    user_id: int, 
    start_date: str = None, 
    end_date: str = None, 
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required)
):
    filters = [Report.user_id == user_id]

    if start_date:
        try:
            filters.append(Report.created_at >= datetime.strptime(start_date, "%Y-%m-%d"))
        except ValueError:
            raise ValueError(f"Invalid start date format: {start_date}")

    if end_date:
        try:
            filters.append(Report.created_at <= datetime.strptime(end_date, "%Y-%m-%d"))
        except ValueError:
            raise ValueError(f"Invalid end date format: {end_date}")

    query = db.query(Report).filter(and_(*filters)).order_by(desc(Report.created_at)).all()

    # not store the value in the log
    log_entry = Log(
        user_id=admin.id,
        action=LogAction.GET_FILTERED_REPORTS,
        message=f"Admin {admin.email} retrieved filtered reports of user {user_id}.",
        timestamp=datetime.utcnow(),
        log_type=LogType.INFO
    )

    db.add(log_entry)
    db.commit()

    return query

@router.get("/total/count_reports_for_user")
def counting(
    user : User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    count = db.query(Report).filter(Report.user_id == user.id).count()
    
    return {"Total count of the reports" : count}

@router.get("/")
def get_all_reports(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = Query(0, description="Number of records to skip"),
    limit: int = Query(10, description="Number of records to return"),
    sort_by: Literal["date", "accuracy"] = Query("date", description="Sort by 'date' or 'accuracy'"),
):
    reports = get_all_reports_by_user(user, db, skip, limit)

    if not reports:
        return {"reports": [], "total": 0}

    return reports

@router.get("/{report_id}")
def get_report_by_id(
    report_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    report = get_report_by_id_user(report_id, user, db)

    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")

    return report

@router.get("/export/pdf/emotion")
async def export_emotion_pdf(
    report_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # we had already saved the report in the database, so we can get the file path from the database
    # then we can return the file response
    report = get_report_by_id_user(report_id, user, db)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")     

    # find the dominant emotino 
    emotions = report.emotion_summary
    dominant_emotion = "NEUTRAL"
    max_score = 0

    for key, value in emotions.items():
        if value >= max_score:
            dominant_emotion = key
            max_score = value
    
    file_path = report.file_path
    if not os.path.exists(file_path):
        report.export_status = ExportStatus.FAILED
        raise HTTPException(status_code=404, detail="File not found.")
    
    # send the email here which contain the report 
    email_subject = "Your Emotion Monitoring Report"
    email_body = f"""
    <h3>Hello {user.username},</h3>
    <p>Please find attached your emotion report for session <strong>{report.session_id}</strong>.</p>
    <p>Dominant Emotion: <b>{dominant_emotion}</b></p>
    <p>Stay balanced and take care!</p>
    """
    asyncio.create_task(send_email(
        subject=email_subject,
        recipients=[user.email],
        body=email_body,
        attachments=[file_path]
    ))

    # now made a log 
    log_entry = Log(
    user_id=user.id,
    action="EMAIL_SENT",
    message=f"EMAIL of the report has been sent to the user {user.email}",
    timestamp=datetime.utcnow(),
    log_type=LogType.INFO
    )

    db.add(log_entry)
    report.export_status = ExportStatus.COMPLETED
    db.commit()

    #make user download the file
    return FileResponse(file_path, media_type='application/pdf', filename=os.path.basename(file_path))
    
@router.get("/get_filtered_reports")
def get_filtered_reports_route(
    user: User = Depends(get_current_user),
    start_date: str = None, 
    end_date: str = None, 
    db: Session = Depends(get_db)
):
    reports = get_filtered_reports(user.id, start_date, end_date, db)
    if not reports:
        raise HTTPException(status_code=404, detail="No reports found for the given criteria.")
    
    return reports

