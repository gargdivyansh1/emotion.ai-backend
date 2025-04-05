from pydantic import BaseModel, EmailStr, constr, conint, Field, ConfigDict
from typing import Optional, Dict, List
from enum import Enum
from datetime import datetime, timezone
import enum

class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"

# Base schema for all users schema 
class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    role: UserRole = UserRole.USER 
    is_active: bool = True
    is_verified: bool = False
    emotion_data_access: bool = False
    can_manage_users: bool = False
    can_export_reports: bool = False

# for registering 
class UserCreate(UserBase):
    password: constr(min_length=8)
    real_time_monitoring_access: bool 

# for login
class UserLogin(UserBase):
    email: EmailStr
    password: str

# user response
class UserResponse(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True

# user updating
class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    emotion_data_access: Optional[bool] = None

    class Config:
        from_attributes = True

# user update access
class UserAccessUpdate(BaseModel):
    emotion_data_access: Optional[bool] = None
    can_export_reports: Optional[bool] = None

    class Config:
        from_attributes = True

# role update 
class RoleUpdate(BaseModel):
    role: UserRole
    
#public data 
class PublicUserData(BaseModel):
    username: str
    email: str
    is_active: bool
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True

# password reset
class PasswordResetRequests(BaseModel):
    email: EmailStr

# for changing password
class ChangePassword(BaseModel):
    old_password: str = Field(..., min_length=8, max_length=100, description="Current password")
    new_password: str = Field(..., min_length=8, max_length=100, description="New password")
    confirm_new_password: str = Field(..., min_length=8, max_length=100, description="Confirm new password")

    class Config:
        from_attributes = True

# for confirming password reset
class PasswordResetConfirm(BaseModel):
    token: str
    new_password: constr(min_length=8)

# jwt token 
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# for the creation of the emotion data 
class EmotionDataCreation(BaseModel):
    user_id: int
    timestamp: datetime = datetime.now(timezone.utc)
    emotion: str

    class Config:
        from_attributes = True

# for reding of the emotion data 
class EmotionDataOut(BaseModel):
    id: int
    user_id: int
    timestamp: datetime
    emotion: str

    class Config:
        from_attributes = True

# for updatig 
class EmotionDataUpdata(BaseModel):
    emotion: Optional[str] = None
    timestamps: Optional[datetime] = None

    class Config:
        from_attributes = True

# for filtering the emotions
class EmotionDataFilter(BaseModel):
    user_id: Optional[int] = None
    emotion: Optional[str] = None
    start_timestamp: Optional[datetime] = None
    end_timestamp: Optional[datetime] = None

    class Config:
        from_attributes = True

class LogType(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"

class LogAction(str, enum.Enum):
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    REGISTER = "REGISTER"
    VIEW_PROFILE = "VIEW_PROFILE"
    UPDATE_PROFILE = "UPDATE_PROFILE"
    DELETE_ACCOUNT = "DELETE_ACCOUNT"
    CHANGE_PASSWORD = "CHANGE_PASSWORD"
    VIEW_PUBLIC_PROFILE = "VIEW_PUBLIC_PROFILE"
    VIEW_USERS = "VIEW_USERS"
    UPDATE_USER_ROLE = "UPDATE_USER_ROLE"
    MANAGE_USER_ACCESS = "MANAGE_USER_ACCESS"
    GIVE_FEEDBACK = "GIVE_FEEDBACK"
    DELETE_FEEDBACK = "DELETE_FEEDBACK"
    VIEW_TREND = "VIEW_TREND"
    SAVE_EMOTION_TREND = "SAVE_EMOTION_TREND" 
    SAVE_REPORT = "SAVE_REPORT"
    GET_ALL_REPORTS = "GET_ALL_REPORTS"
    GET_REPORT_BY_ID = "GET_REPORT_BY_ID"
    GET_ALL_RECORDS = "GET_ALL_RECORDS"
    GET_FILTERED_REPORTS = "GET_FILTERED_REPORTS"
    GET_ALL_TRENDS = "GET_ALL_TRENDS"
    GET_TREND_BY_ID = "GET_TREND_BY_ID"
    GET_ONE_RECORD = "GET_ONE_RECORD"
    EMAIL_SENT = "EMAIL_SENT"
    REPORT_CREATED = "REPORT_CREATED"

#creating log
class LogCreate(BaseModel):
    user_id: int
    action: str
    message: str
    timestamp: datetime = datetime.now(timezone.utc)
    updated_at : datetime 
    created_at : datetime

    class Config:
        from_attributes = True

# for getting value 
class LogOut(LogCreate):
    id: int
    log_type: str = Field(..., description="Type of log (info, warning, error)")

# feedback type
class FeedbackType(str, Enum):
    BUG = "bug"
    FEATURE_REQUEST = "feature_request"
    SUGGESTION = "suggestion"

# user feedback create
class UserFeedbackCreate(BaseModel):
    feedback_type: FeedbackType
    message: str
    rating: Optional[int] = None  
    created_at: datetime = datetime.now(timezone.utc)

    class Config:
        from_attributes = True

# user feedback out
class UserFeedbackOut(UserFeedbackCreate):
    id: int

#emotion trend
class EmotionTrendCreate(BaseModel):
    user_id: int
    emotion: str  
    trend_start_date: datetime
    trend_end_date: datetime
    average_emotion_score: float

    class Config:
        from_attributes = True

# for out
class EmotionTrendOut(EmotionTrendCreate):
    id: int

class NotificationStatus(str, enum.Enum):
    SENT = "sent"
    PENDING = "pending"
    FAILED = "failed"

class NotificationType(str, enum.Enum):
    EMOTION_REPORT = "Emotion Report"
    INFORMATIVE = "Informative"

# for notification 
class NotificationCreate(BaseModel):
    user_id : int
    title: str 
    message: str 
    notification_type: NotificationType = NotificationType.INFORMATIVE
    status: str = NotificationStatus.PENDING

class NotificationForAll(BaseModel):
    title: str 
    message: str 
    notification_type: NotificationType = NotificationType.INFORMATIVE
    status: str = NotificationStatus.PENDING

NotificationCreate.model_rebuild()

# for out
class NotificationOut(NotificationCreate):
    id: int

    class Config:
        from_attributes = True

class NotificationOutNew(BaseModel):
    title: str
    message: str
    sent_at: datetime

    class Config:
        from_attributes = True


class ReportType(str, Enum):
    EMOTION_TRACKING = "emotion_tracking"

class ExportStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"

class ExportFormat(str, Enum):
    PDF = "pdf"

# Base schema for reports
class ReportBase(BaseModel):
    report_type: ReportType
    emotion_summary: Optional[Dict[str, conint(ge=0, le=100)]] = None
    comparison_data: Optional[Dict] = None
    export_status: ExportStatus = ExportStatus.PENDING
    export_format: Optional[ExportFormat] = None
    admin_notes: Optional[str] = None

# for creating reports 
class ReportCreate(ReportBase):
    user_id: int

# for returning the data
class ReportResponse(ReportBase):
    id: int
    user_id: int
    generated_at: datetime

    class Config:
        from_attributes = True

# for updating the report
class ReportUpdate(BaseModel):
    export_status: Optional[ExportStatus] = None
    export_format: Optional[ExportFormat] = None
    admin_notes: Optional[str] = None

    class Config:
        from_attributes = True

# for forcasting 
class Prediction(BaseModel):
    ds: set
    yhat: float

class EmotionForecast(BaseModel):
    daily: List[Prediction]
    weekly: List[Prediction]
    monthly: List[Prediction]

class ForecastResponse(BaseModel):
    forecast: Dict[str, EmotionForecast]