from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from datetime import datetime
from typing import List
from app.utils.auth import get_current_user
from app.models import User, EmotionTrend, Log, LogType, EmotionData
from app.schemas import EmotionSummary
from typing import Optional, Dict
from app.utils.auth import admin_required
from sqlalchemy import desc
from datetime import datetime, timedelta

def get_start_of_day(dt: datetime):
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)

router = APIRouter(
    prefix="/emotion", tags=["Emotion"]
)

# get the latest emotion trend
@router.get("/user/latest-trend")
def get_user_emotion_trend_by_id(
    current_user: User = Depends(get_current_user),  
    db: Session = Depends(get_db)
):
    trend = db.query(EmotionTrend).filter(
        EmotionTrend.user_id == current_user.id
    ).first()

    if not trend:
        raise HTTPException(status_code=404, detail="Emotion trend not found.")
    

    log_entry = Log(
        user_id=current_user.id,
        action="VIEW_TREND",
        message=f"User {current_user.email} viewed their latest trend",
        timestamp=datetime.utcnow(),
        log_type=LogType.INFO
    )
    db.add(log_entry)
    db.commit()

    print(trend)

    return trend

# getting the latest emotion data
@router.get("/latest/emotion-data/user")
async def get_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    trend = db.query(EmotionTrend).filter(
        EmotionTrend.user_id == current_user.id
    ).first()

    if not trend:
        raise HTTPException(status_code=200, detail="Emotion trend not found.")

    session_id = trend.session_id

    data = db.query(EmotionData).filter(EmotionData.session_id == session_id).all()

    if not data:
        raise HTTPException(status_code=404, detail=f"No emotion data found for session {session_id}")

    return data

# user getting the emotion trends 
@router.get("/user/emotions-trends")
def get_user_trends(
    current_user: User = Depends(get_current_user),
    period_start: Optional[datetime] = None,
    period_end: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    query = db.query(EmotionTrend).filter(EmotionTrend.user_id == current_user.id)

    if period_start and period_end:
        query = query.filter(EmotionTrend.period_start >= period_start, EmotionTrend.period_end <= period_end)


    trends = query.all()

    if not trends:
        raise HTTPException(status_code=404, detail="No emotion trends found for this user.")
    
    log_entry = Log(
        user_id=current_user.id,
        action="VIEW_TREND",
        message=f"User {current_user.email} viewed their all trends.",
        timestamp=datetime.utcnow(),
        log_type=LogType.INFO
    )
    db.add(log_entry)
    db.commit()

    print(trends)
    
    return trends

# for getting 7 onlu 
@router.get("/user/emotions-trends-seven")
def get_user_trends(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    trends = (
        db.query(EmotionTrend)
        .filter(EmotionTrend.user_id == current_user.id)
        .order_by(EmotionTrend.created_at.desc()) 
        .limit(7)
        .all()
    )

    if not trends:
        raise HTTPException(status_code=200, detail="No emotion trends found for this user.")

    print(trends)
    
    return trends

# user can get the specific trend summary 
@router.get("/user/emotion-trend/{trend_id}")
def get_user_emotion_trend_by_id(
    trend_id: int,  
    current_user: User = Depends(get_current_user),  
    db: Session = Depends(get_db)
):
    trend = db.query(EmotionTrend).filter(
        EmotionTrend.id == trend_id,
        EmotionTrend.user_id == current_user.id
    ).first()

    if not trend:
        raise HTTPException(status_code=404, detail="Emotion trend not found.")
    
    log_entry = Log(
        user_id=current_user.id,
        action="VIEW_TREND",
        message=f"User {current_user.email} viewed the trend {trend_id}",
        timestamp=datetime.utcnow(),
        log_type=LogType.INFO
    )
    db.add(log_entry)
    db.commit()

    print(trend)

    return trend

# admin getting all the emotion data of the all users
@router.get("/admin/emotion-data-all-users")
def admin_emotion_data_all_users(
    admin: User = Depends(admin_required),
    db: Session = Depends(get_db)
):
    query = db.query(EmotionData).order_by(desc(EmotionData.created_at)).all()

    log_entry = Log(
        user_id=admin.id,
        action="GET_ALL_RECORDS",
        message=f"Admin {admin.email} take the emotion data of all users.",
        timestamp=datetime.utcnow(),
        log_type=LogType.INFO
    )
    db.add(log_entry)
    db.commit()

    print(query)

    return query

@router.get("/admin/emotion-data-single-users")
def admin_emotion_data_all_users(
    user_id = int,
    admin: User = Depends(admin_required),
    db: Session = Depends(get_db)
):
    query = db.query(EmotionData).filter(user_id == EmotionData.user_id).order_by(desc(EmotionData.created_at)).all()

    log_entry = Log(
        user_id=admin.id,
        action="GET_ONE_RECORD",
        message=f"Admin {admin.email} take the emotion data user {user_id}",
        timestamp=datetime.utcnow(),
        log_type=LogType.INFO
    )
    db.add(log_entry)
    db.commit()

    print(query)

    return query

@router.get("/admin/get_emotion_trend_of_users")
def getting_users_trend(
    admin: User = Depends(admin_required),
    db: Session = Depends(get_db)
):
    query = db.query(EmotionTrend).order_by(desc(EmotionTrend.created_at)).all()

    if not query:
        raise HTTPException(status_code=404, detail="Trend not found.")
    
    return query 

@router.get("/admin/get_emotion_trends_of_one_user")
def getting_them(
    user_id : int ,
    admin : User = Depends(admin_required),
    db : Session = Depends(get_db)
):
    query = db.query(EmotionTrend).filter(EmotionTrend.user_id == user_id).order_by(desc(EmotionTrend.created_at)).all()

    if not query:
        raise HTTPException(status_code=404, detail= "No emotion trend is found for the user {user_id}")
    
    return query

@router.get("/getting_seven_days_count", response_model=List[int])
async def get_weekly_emotion_trends_count(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    today = get_start_of_day(datetime.utcnow())

    trend_count = []
    for i in range(6, -1, -1):
        day_start = today - timedelta(days=i)
        day_end = day_start + timedelta(days = 1)

        count = db.query(EmotionTrend).filter(
            EmotionTrend.user_id == user.id,
            EmotionTrend.created_at >= day_start,
            EmotionTrend.created_at < day_end
        ).count()

        trend_count.append(count)

    return trend_count

@router.get("/getting_seven_days_emotions_count", response_model=EmotionSummary)
async def get_weekly_emotion_counts(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    today = get_start_of_day(datetime.utcnow())
    seven_days_ago = today - timedelta(days=6)

    emotion_counts: Dict[str, int] = {
        "happy": 0,
        "sad": 0,
        "angry": 0,
        "neutral": 0,
        "surprised": 0,
        "fear": 0
    }

    entries = db.query(EmotionTrend).filter(
        EmotionTrend.user_id == user.id,
        EmotionTrend.created_at >= seven_days_ago
    ).all()

    for entry in entries:
        summary = entry.emotion_summary  
        print("summary", summary)

        for emotion, data in summary.items():
            if emotion in emotion_counts:
                emotion_counts[emotion] += data.get("count", 0)

    print("Final Emotion Counts:", emotion_counts)

    return emotion_counts






