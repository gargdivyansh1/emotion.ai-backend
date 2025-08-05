from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import users, video_ws, admin, reports, auth, notification, logs, feedback, emotion, two_factor
from app.database import engine, Base
from app.routes.video_ws import router as websocket_router

app = FastAPI(
    title="Emotion Recognition API",
    description="Backend for real-time emotion tracking and analytics",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://emotion-ai-pi.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth.router)

app.include_router(users.router)

app.include_router(feedback.router)

app.include_router(admin.router)

app.include_router(notification.router)

app.include_router(logs.router)

app.include_router(reports.router) 

app.include_router(emotion.router)

app.include_router(two_factor.router)

app.include_router(websocket_router)


