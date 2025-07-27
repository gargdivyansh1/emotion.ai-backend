from sqlalchemy import Column, Integer, String, Boolean, Enum, TIMESTAMP, JSON, ForeignKey, Float, Text, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func  
from datetime import datetime
from app.database import Base
import enum
from sqlalchemy import Enum 

class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False)
    username = Column(String, unique=True, nullable=True)
    password_hash = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    # Security
    jwt_token = Column(String, nullable=True)
    password_reset_token = Column(String, nullable=True)
    two_factor_enabled = Column(Boolean, default=False)
    two_factor_secret = Column(String, nullable=True)

    # Emotion AI Permissions
    emotion_data_access = Column(Boolean, default=False)  # Admin-only
    real_time_monitoring_access = Column(Boolean, default=True)  # User-specific

    # Notifications
    notification_preferences = Column(JSON, nullable=True)

    #Admin_specific
    can_manage_users = Column(Boolean, default=False)
    can_export_reports = Column(Boolean, default=False)
    last_login = Column(TIMESTAMP, nullable=True)
    number_of_session_taken = Column(Integer, default = 0)
    number_of_alloted_sessions = Column(Integer, default = 3)

    # Relationship with Emotion Data
    emotion_data = relationship("EmotionData", back_populates="user", cascade="all, delete-orphan")
    
    # Relationship with Emotion Trend
    emotion_trends = relationship("EmotionTrend", back_populates="user", cascade="all, delete-orphan")
    
    # Relationship with Notifications
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    
    # Relationship with Logs
    logs = relationship("Log", back_populates="user", cascade="all, delete-orphan")
    
    # Relationship with User Feedback
    feedback = relationship("UserFeedback", back_populates="user", cascade="all, delete-orphan")
    
    # Relationship with Admin Actions
    admin_actions = relationship("AdminAction", back_populates="admin", cascade="all, delete-orphan")
    
    # Relationship with Reports
    reports = relationship("Report", back_populates="user", cascade="all, delete-orphan")

    # Relationship with emotionAccuracy
    emotion_accuracies = relationship("EmotionAccuracy", back_populates="user")

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"


class EmotionType(str, enum.Enum):
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    SURPRISED = "surprised"
    NEUTRAL = "neutral"
    FEAR = "fear"
    DISAPPOINTMENT = "disappointment"
    GRIEF = "grief"
    LONELINESS = "loneliness"
    MELANCHOLY = "melancholy"
    JOY = "joy"
    EXCITEMENT = "excitement"
    CONTENTMENT = "contentment"
    PRIDE = "pride"
    FRUSTRATION = "frustration"
    RAGE = "rage"
    IRRITATION = "irritation"
    ANXIETY = "anxiety"
    DREAD = "dread"
    PANIC = "panic"
    WORRY = "worry"
    AMAZEMENT = "amazement"
    ASTONISHMENT = "astonishment"
    SHOCK = "shock"
    EMBARRASSMENT = "embarrassment"
    SHAME = "shame"
    GUILT = "guilt"
    HOPE = "hope"
    DISGUST = "disgust"

class EmotionData(Base):
    __tablename__ = "emotion_data"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    session_id = Column(String, nullable= False)
    timestamp = Column(TIMESTAMP, server_default=func.now())
    emotion = Column(Enum(EmotionType), nullable=False)
    intensity = Column(Float, nullable=False)

    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="emotion_data")

    __table_args__ = (
        Index('ix_emotion_data_user_id', 'user_id'),
        Index('ix_emotion_data_timestamp', 'timestamp'),
        Index('ix_emotion_data_emotion', 'emotion')
    )

    def __repr__(self):
        return f"<EmotionData {self.user_id} - {self.emotion} ({self.intensity})>"

class EmotionTrend(Base):
    __tablename__ = "emotion_trends"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    session_id = Column(String, nullable= False)
    period_start = Column(TIMESTAMP, nullable=False)
    period_end = Column(TIMESTAMP, nullable=False)
    emotion_summary = Column(JSON, nullable=False)  
    average_intensity = Column(Float, nullable=False)

    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="emotion_trends")

    __table_args__ = (
        Index('ix_emotion_trends_user_id', 'user_id'),
        Index('ix_emotion_trends_period_start', 'period_start'),
        Index('ix_emotion_trends_period_end', 'period_end'),
    )

    def __repr__(self):
        return f"<EmotionTrend {self.user_id} - {self.period_start} to {self.period_end}>"
    
class EmotionAccuracy(Base):
    __tablename__ = "emotion_accuracies"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    emotion = Column(String, nullable=False)  # Store emotion as a string
    timestamp = Column(TIMESTAMP, server_default=func.now())
    
    user = relationship("User", back_populates="emotion_accuracies")

    def __repr__(self):
        return f"<EmotionAccuracy {self.user_id} - {self.emotion} ({self.accuracy})>"


class NotificationStatus(str, enum.Enum):
    SENT = "sent"
    PENDING = "pending"
    FAILED = "failed"
    READ = "read"
    URGENT = "urgent"

class NotificationType(str, enum.Enum):
    AI_ACCURACY = "AI Accuracy"
    EMOTION_REPORT = "Emotion Report"
    INFORMATIVE = "Informative"
    READ = "read"
    URGENT = "urgent"

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    notification_type = Column(Enum(NotificationType), nullable=False)
    title = Column(String, nullable=False)
    message = Column(String, nullable=False)
    status = Column(Enum(NotificationStatus), default=NotificationStatus.PENDING)
    is_read = Column(Boolean, default = False)
    sent_at = Column(TIMESTAMP, server_default=func.now())

    user = relationship("User", back_populates="notifications")

    def __repr__(self):
        return f"<Notification {self.user_id} - {self.notification_type}>"
    

class LogType(str, enum.Enum):
    ERROR = "error"
    INFO = "info"
    WARNING = "warning"

class LogAction(str, enum.Enum):
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    REGISTER = "REGISTER"
    VISIT = "VISIT"
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
    SAVING_EMOTION_TREND = "SAVING_EMOTION_TREND" 
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


class Log(Base):
    __tablename__ = "logs"

    id = Column(Integer, primary_key=True, index=True)
    log_type = Column(Enum(LogType), nullable=False)
    message = Column(String, nullable=False)
    timestamp = Column(TIMESTAMP, server_default=func.now())
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    action = Column(Enum(LogAction), nullable=False)

    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="logs")

    __table_args__ = (
        Index('ix_logs_user_id', 'user_id'),
        Index('ix_logs_timestamp', 'timestamp'),
        Index('ix_logs_log_type', 'log_type'),
    )

    def __repr__(self):
        return f"<Log {self.id} - {self.log_type}>"
    

class FeedbackType(str, enum.Enum):
    BUG = "bug"
    FEATURE_REQUEST = "feature_request"
    SUGGESTION = "suggestion"

class UserFeedback(Base):
    __tablename__ = "user_feedback"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    feedback_type = Column(Enum(FeedbackType), nullable=False)
    message = Column(String, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    rating = Column(Integer, nullable=True)  

    user = relationship("User", back_populates="feedback")

    def __repr__(self):
        return f"<UserFeedback {self.user_id} - {self.feedback_type}>"


class AdminAction(Base):
    __tablename__ = "admin_actions"

    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    action = Column(String, nullable=False)
    target = Column(String, nullable=False)
    timestamp = Column(TIMESTAMP, server_default=func.now())

    admin = relationship("User", back_populates="admin_actions")

    def __repr__(self):
        return f"<AdminAction {self.admin_id} - {self.action}>"


class ReportType(str, enum.Enum):
    EMOTION_TRACKING = "emotion_tracking"
    AI_ACCURACY = "ai_accuracy"

class ExportStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"

class ExportFormat(str, enum.Enum):
    PDF = "pdf"

class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index= True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    report_type = Column(Enum(ReportType), nullable=False)
    session_id = Column(String , nullable=False)
    file_path = Column(String, nullable=False)
    generated_at = Column(TIMESTAMP, server_default=func.now())

    # Emotion Tracking Reports
    emotion_summary = Column(JSON, nullable=True) 
    comparison_data = Column(JSON, nullable=True)

    # Weekly and Monthly Trends
    weekly_trend = Column(JSON, nullable=True)  
    monthly_trend = Column(JSON, nullable=True)

    # Export Status
    export_status = Column(Enum(ExportStatus), default=ExportStatus.PENDING, nullable=False)
    export_format = Column(Enum(ExportFormat), nullable=True)

    # Admin Notes
    admin_notes = Column(Text, nullable=True)

    user = relationship("User", back_populates="reports")

    def __repr__(self):
        return f"<Report {self.id} - {self.report_type} (User {self.user_id})>"