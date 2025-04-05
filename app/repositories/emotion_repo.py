from sqlalchemy.orm import Session 
from sqlalchemy import desc, and_ 
from datetime import datetime
from app.models import EmotionData, EmotionTrend, EmotionAccuracy, EmotionType
import logging
from collections import defaultdict
from app.models import Report, User, ReportType, ExportFormat, Log, LogType, LogAction, User
from typing import List, Optional
from app.utils.auth import get_current_user, admin_required
from fastapi import Depends
from app.database import get_db
from fastapi import HTTPException


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def save_emotion(db: Session, user_id: int, session_id : str, emotion: str, intensity: float):

    try:
        emotion = emotion.strip().upper()
        if emotion == "SURPRISE":
            emotion = "SURPRISED"
        if emotion not in EmotionType.__members__:
            valid_emotions = list(EmotionType.__members__.keys())
            logger.error(f"Invalid emotion type: {emotion}. Available types: {valid_emotions}")
            raise ValueError(f"Invalid emotion type: {emotion}")
        
        intensity = float(intensity)

        new_emotion_data = EmotionData(
            user_id=user_id,
            emotion=EmotionType[emotion].value, 
            session_id = str(session_id),
            timestamp = datetime.utcnow(),
            intensity=intensity,
        )
        
        db.add(new_emotion_data)
        db.commit()  
        db.refresh(new_emotion_data)  

        logger.info(f"Emotion data for user {user_id}: {emotion} (intensity: {intensity} saved.")
        
        return new_emotion_data
    
    except ValueError as ve:
        logger.error(f"Error saving emotion data for the user {user_id}: {str(e)}")
        db.rollback()
        raise ve

    except Exception as e:
        logger.error(f"Error saving emotion data for user {user_id}: {str(e)}")
        db.rollback()  
        raise Exception("Error saving emotion data to the database.")

def save_emotion_trend(db: Session,user_id: int, session_id : str, period_start: datetime, period_end: datetime):
    try:
        emotion_data = db.query(EmotionData).filter(
            EmotionData.user_id == user_id,
            EmotionData.session_id == str(session_id)
        ).all()

        if not emotion_data:
            logger.warning(f" No emotion data found for user {user_id} from {period_start} to {period_end}.")
            return None  

        emotion_summary = defaultdict(lambda: {'count': 0, 'total_confidence': 0.0})

        for entry in emotion_data:
            emotion_summary[entry.emotion]['count'] += 1
            emotion_summary[entry.emotion]['total_confidence'] += entry.intensity

        for emotion, data in emotion_summary.items():
            if data['count'] > 0:
                data['average_confidence'] = data['total_confidence'] / data['count']
            else:
                data['average_confidence'] = 0.0

        average_confidence = (
            sum(data['average_confidence'] for data in emotion_summary.values()) / len(emotion_summary)
            if emotion_summary else 0.0
        )

        emotion_summary_dict = {emotion: {
            "count": data["count"],
            "average_confidence": data["average_confidence"],
        } for emotion, data in emotion_summary.items()}

        new_trend = EmotionTrend(
            user_id=user_id,
            period_start=period_start,
            period_end=period_end,
            session_id= str(session_id),
            emotion_summary=emotion_summary_dict,  
            average_intensity=average_confidence
        )

        db.add(new_trend)
        db.commit()
        db.refresh(new_trend)

        user = db.query(User).filter(User.id == user_id).first()

        log_entry = Log(
        user_id=user_id,
        action = LogAction.SAVING_EMOTION_TREND,
        message=f"User {user.email} saved emotion trend",
        timestamp=datetime.utcnow(),
        log_type=LogType.INFO
        )

        db.add(log_entry)
        db.commit()

        print("trend saved")

        logger.info(f" Emotion trend for user {user_id} from {period_start} to {period_end} saved.")

        return new_trend  

    except Exception as e:
        db.rollback()
        logger.error(f" Error saving emotion trend for user {user_id}: {str(e)}")
        return None  

def get_all_emotion_trend_by_user(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),   
):
    trend = db.query(EmotionTrend).filter(
        EmotionTrend.user_id == user.id,
    ).all()

    if not trend:
        logger.warning(f" No emotion trend found for user {user.id}.")
        return None  
    
    log_entry = Log(
        user_id=user.id,
        action=LogAction.GET_ALL_TRENDS,
        message=f"User {user.email} retrieved all emotion trends.",
        timestamp=datetime.utcnow(),
        log_type=LogType.INFO
    )
    db.add(log_entry)
    db.commit()

    return trend

def user_get_emotion_by_trend_id(
    trend_id: int,
    user: User = Depends(get_current_user),     
    db: Session = Depends(get_db)
):
    query = db.query(EmotionTrend).filter(
        EmotionTrend.id == trend_id,
        EmotionTrend.user_id == user.id
    ).first()       

    if not query:           
        logger.warning(f" Emotion trend with ID {trend_id} not found for user {user.id}.")
        return None

    log_entry = Log(
        user_id=user.id,
        action=LogAction.GET_TREND_BY_ID,
        message=f"User {user.email} retrieved emotion trend with ID {trend_id}.",
        timestamp=datetime.utcnow(),
        log_type=LogType.INFO
    )

    db.add(log_entry)
    db.commit()

    return query

def save_report(
        user_id: int, 
        file_path: str, 
        db: Session,
        session_id : str,
        first_timestamp: datetime,
        emotion_counts: dict,
        dominant_emotion: str = None,
        comparison_data: Optional[dict] = None,
        admin_notes: Optional[str] = None,
        report_type: ReportType = ReportType.EMOTION_TRACKING,
        ):
    if not file_path:
        raise ValueError("File path cannot be empty")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError(f"User with ID {user_id} not found in the database.")
    
    try:
        report = Report(
            user_id=user.id, 
            file_path=file_path, 
            report_type=report_type, 
            session_id = session_id,
            generated_at = first_timestamp,
            emotion_summary=emotion_counts,
            comparison_data=None,  
            export_format= ExportFormat.PDF,
            admin_notes = f"User is having {dominant_emotion} emotion.",
            )
        db.add(report)
        db.commit()
        db.refresh(report) 

        log_entry = Log(
        user_id=user_id,
        action=LogAction.SAVE_REPORT,
        message=f"User {user.email} saved a report with file path {file_path}",
        timestamp=datetime.utcnow(),
        log_type=LogType.INFO
        )

        db.add(log_entry)
        db.commit()

        print("report saved")

        return report

    except Exception as e:
        db.rollback()  
        print(f"Error while saving report: {e}")
    
        return None
    
def get_all_reports_by_user(
    user: User = Depends(get_current_user), 
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
):
    query = (
        db.query(Report)
        .filter(Report.user_id == user.id)
        .order_by(desc(Report.generated_at))
        .offset(skip)
        .limit(limit)
    )

    reports = query.all()

    if not reports:
        logger.warning(f" No reports found for user {user.id}.")
        return None

    # we want to store the information in a log 
    log_entry = Log(
        user_id=user.id,
        action=LogAction.GET_ALL_REPORTS,
        message=f"User {user.email} retrieved all reports.",
        timestamp=datetime.utcnow(),
        log_type=LogType.INFO
    )
    db.add(log_entry)
    db.commit()

    print(reports)

    return reports

def admin_get_all_reports_by_user_id(
    admin: User = Depends(admin_required),
    user_id: int = None,
    db: Session = Depends(get_db),
):
    skip: int = 0,
    limit: int = 100,   

    query = db.query(Report).filter(Report.user_id == user_id).order_by(desc(Report.generated_at)).all()  

    if not query:
        raise HTTPException(status_code=404 , detail= f"THE report the user {user_id} is not found")

    log_entry = Log(  
        user_id=admin.id,
        action=LogAction.GET_ALL_REPORTS,
        message=f"Admin {admin.email} retrieved all reports for user {user_id}.",
        timestamp=datetime.utcnow(),
        log_type=LogType.INFO
    )
    db.add(log_entry)       
    db.commit()

    print(query)

    return query      
    
def get_report_by_id_user(
    report_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    report = db.query(Report).filter(
        Report.id == report_id,
        Report.user_id == user.id
    ).first()

    if not report:
        raise ValueError(f"Report with ID {Report.id} not found for user {user.id}.")

    log_entry = Log(
        user_id=user.id,
        action=LogAction.GET_REPORT_BY_ID,
        message=f"User {user.email} retrieved report with ID {report_id}.",
        timestamp=datetime.utcnow(),
        log_type=LogType.INFO
    )
    db.add(log_entry)
    db.commit()

    print(report)

    return report
    
def admin_get_all_emotion_records_user_id(
    admin: User = Depends(admin_required),
    db: Session = Depends(get_db),
    user_id: int = None,
    skip: int = 0,
    limit: int = 100,
):
    if limit <= 0:
        limit = 100  
    if skip < 0:
        skip = 0  

    query = db.query(EmotionData).filter(EmotionData.user_id == user_id).order_by(desc(EmotionData.timestamp))

    query = query.offset(skip).limit(limit).all()

    log_entry = Log(
        user_id=admin.id,
        action=LogAction.GET_ALL_RECORDS,
        message=f"Admin {admin.email} retrieved all emotion records for user {user_id}.",
        timestamp=datetime.utcnow(),
        log_type=LogType.INFO
    )
    
    db.add(log_entry)
    db.commit()

    return query

def admin_get_all_emotion_trends_user_id(
    admin: User = Depends(admin_required),
    db: Session = Depends(get_db),
    user_id: int = None,
    skip: int = 0,
    limit: int = 100,
):
    if limit <= 0:
        limit = 100  
    if skip < 0:
        skip = 0  

    query = db.query(EmotionTrend).filter(EmotionTrend.user_id == user_id).order_by(desc(EmotionTrend.period_start))

    query = query.offset(skip).limit(limit).all()

    log_entry = Log(
        user_id=admin.id,
        action=LogAction.GET_ALL_TRENDS,
        message=f"Admin {admin.email} retrieved all emotion trends for user {user_id}.",
        timestamp=datetime.utcnow(),
        log_type=LogType.INFO
    )
    
    db.add(log_entry)
    db.commit()

    return query

def get_filtered_reports(
        user : User = Depends(get_current_user),
        start_date: str = None, 
        end_date: str = None, 
        db: Session = None
    ):
    filters = [Report.user_id == user.id]

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
        user_id=user.id,
        action=LogAction.GET_FILTERED_REPORTS,
        message=f"User {user.email} retrieved filtered reports.",
        timestamp=datetime.utcnow(),
        log_type=LogType.INFO
    )

    db.add(log_entry)
    db.commit()

    return query

def get_emotion_data_by_period(
    db: Session, 
    user_id: int, 
    start_date: str, 
    end_date: str
):
    return db.query(EmotionData).filter(
        EmotionData.user_id == user_id,
        EmotionData.timestamp >= datetime.strptime(start_date, "%Y-%m-%d"),
        EmotionData.timestamp <= datetime.strptime(end_date, "%Y-%m-%d")
    ).all()