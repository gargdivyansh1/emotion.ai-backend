from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from fastapi.responses import FileResponse
from typing import Literal, Optional
from app.database import get_db
import os
from fastapi import HTTPException
from app.utils.auth import get_current_user
from app.repositories.emotion_repo import  get_all_reports_by_user, get_report_by_id_user, get_filtered_reports
from app.utils.auth import admin_required
from app.models import Report ,LogAction, LogType, Log
from datetime import datetime, date
from sqlalchemy import desc, and_, func
from app.models import User, ExportStatus
import asyncio
from PyPDF2 import PdfMerger, PdfReader
import tempfile
import logging
from app.services.email_serivce import send_email
from app.schemas import EmotionReportListResponse

logger = logging.getLogger(__name__)

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

# @router.get("/one_report/admin_getting_all_reports_of_user")
# def admin_getting_all_reports_of_user(
#     user_id: int, 
#     db: Session = Depends(get_db),
#     admin: User = Depends(admin_required)
# ):
#     reports = admin_get_all_reports_by_user_id(admin,user_id, db)

#     if not reports:
#         raise HTTPException(status_code=404, detail="No reports found for the given user.")     
    
#     return reports

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





# correct --
@router.get("/", response_model=EmotionReportListResponse)
def get_all_reports(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = Query(0, description="Number of records to skip"),
    limit: int = Query(1000, description="Number of records to return"),
):
    reports = get_all_reports_by_user(user, db, skip, limit)

    if not reports:
        return {"reports": [], "total": 0}
    
    total = db.query(func.count(Report.id)).filter(Report.user_id == user.id).scalar()
    
    data = {"reports": reports , "total": total}

    return data

# correct --
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

# correct --
@router.get("/export/pdf/emotion")
async def export_emotion_pdf(
    report_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
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

    return FileResponse(file_path, media_type='application/pdf', filename=os.path.basename(file_path))
    
## correct --
@router.get('/export/pdf/all-emotions', response_description="Combined PDF of all emotion reports")
async def export_all_emotions_pdf(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    try:
        reports = db.query(Report).filter(
            Report.user_id == user.id,
            Report.file_path.isnot(None)  
        ).all()

        if not reports:
            logger.warning(f"No reports found for user {user.id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="No reports found for your account."
            )
        
        merger = PdfMerger()
        valid_reports = []
        temp_file_path = None

        try:
            for report in reports:
                try:
                    if os.path.exists(report.file_path):
                        with open(report.file_path, 'rb') as f:
                            PdfReader(f)  
                        merger.append(report.file_path)
                        valid_reports.append(report)
                        logger.debug(f"Added report {report.id} to merge")
                except Exception as e:
                    logger.error(f"Invalid PDF {report.file_path}: {str(e)}")
                    continue

            if not valid_reports:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="No valid PDF reports could be processed"
                )

            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                temp_file_path = temp_file.name

            merger.write(temp_file_path)
            logger.info(f"Merged {len(valid_reports)} reports into {temp_file_path}")

            filename = f'emotion_reports_{user.username}_{datetime.now().strftime("%Y-%m-%d")}.pdf'

            log_entry = Log(
                user_id=user.id,
                action="EMAIL_SENT",
                message=f"Exported {len(valid_reports)} reports as PDF",
                timestamp=datetime.utcnow(),
                log_type=LogType.INFO
            )
            db.add(log_entry)
            db.commit()

            return FileResponse(
                temp_file_path,
                media_type='application/pdf',
                filename=filename,
                headers={
                    'Content-Disposition': f'attachment; filename="{filename}"',
                    'X-File-Report-Count': str(len(valid_reports))
                }
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"PDF processing failed: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate combined report"
            )
        finally:
            merger.close()

    except Exception as e:
        logger.error(f"Endpoint error: {str(e)}", exc_info=True)
        raise


@router.get("/get_filtered_reports")
async def get_filtered_reports_route(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    reports = get_filtered_reports(
        start_date=start_date.isoformat() if start_date else None,
        end_date=end_date.isoformat() if end_date else None,
        user=current_user,
        db=db
    )
    return {"reports": reports}

