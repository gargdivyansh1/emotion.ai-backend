from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import users, video_ws, admin, reports, auth, notification, logs, feedback, emotion_forecast, emotion
from app.database import engine, Base
#from app.middleware.rate_limiter import RateLimiterMiddleware
from app.core.events import start_event, shutdown_event

from app.routes.video_ws import router as websocket_router

# Configure CORS
origins = [
    "http://localhost:5173",  # Your frontend origin
    "http://127.0.0.1:5173",
]


# Initialize FastAPI App
app = FastAPI(
    title="Emotion Recognition API",
    description="Backend for real-time emotion tracking and analytics",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# app.add_middleware(RateLimiterMiddleware, max_requests=100, window_seconds=60)

# Include Routes
app.include_router(auth.router)

app.include_router(users.router)

app.include_router(feedback.router)

app.include_router(admin.router)

app.include_router(notification.router)

app.include_router(logs.router)

app.include_router(reports.router) 

app.include_router(emotion_forecast.router)

app.include_router(emotion.router)

app.include_router(websocket_router)




# Lifecycle Events
@app.on_event("startup")
def startup():
    start_event

@app.on_event("shutdown")
def shutdown():
    """Handle shutdown cleanup."""
    shutdown_event()

# @app.on_event("startup")
# async def startup_event():
#     await start_scheduler()
