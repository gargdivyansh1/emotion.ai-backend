import cv2
import numpy as np
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from deepface import DeepFace
from app.utils.jwt import decode_access_token
from app.database import get_db
from app.models import User, LogType, LogAction, Log
from app.repositories.emotion_repo import save_emotion
from app.services.face_recognition import detect_faces
from starlette.websockets import WebSocketState
import asyncio
from datetime import datetime
from app.repositories.emotion_repo import save_emotion_trend
import uuid
from app.services.report_service import generate_emotion_monitoring_pdf_report

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# WebSocket Router
router = APIRouter(
    prefix="/video",
    tags=["Video WebSocket"],
)

# Active WebSocket connections
active_connections = {}

async def authenticate_websocket(token: str, db: Session):
    """Authenticates user via JWT token."""
    try:
        payload = decode_access_token(token)
        return payload.get("user_id")
    except Exception as e:
        logger.error(f"WebSocket authentication failed: {str(e)}")
        return None

async def close_existing_connection(username: str):
    """Closes any existing WebSocket connection for a user."""
    if username in active_connections:
        await active_connections[username].close()
        logger.info(f"Closed existing connection for {username}")

@router.websocket("/ws/video")
async def video_websocket(websocket: WebSocket,background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Handles real-time emotion analysis via WebSocket."""
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008)
        return

    user_id = await authenticate_websocket(token, db)
    if not user_id:
        await websocket.close(code=1008)
        return

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        await websocket.close(code=1008)
        return

    await close_existing_connection(user.username)
    active_connections[user.username] = websocket

    logger.info(f"{user.username} connected.")
    await websocket.accept()

    period_start = datetime.utcnow()
    monitoring_duration = 10  
    period_end = None  
    session_id = str(uuid.uuid4())

    try:
        while True:
            try:
                frame_bytes = await websocket.receive_bytes()
                if not isinstance(frame_bytes, bytes):
                    logger.error("Received invalid data type instead of bytes.")
                    continue
                if not frame_bytes:
                    logger.warning("Received empty frame data. Skipping frame.")
                    continue

                np_arr = np.frombuffer(frame_bytes, np.uint8)
                frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

                if frame is None:
                    raise ValueError("Invalid image data received")

            except ValueError as ve:
                logger.error(f"Invalid frame received: {str(ve)}")
                await websocket.send_json({"error": "Invalid frame data received"})
                continue
            except WebSocketDisconnect as e:
                logger.warning(f"WebSocket disconnected: {e.code} - {e.reason}")
                break
            except Exception as e:
                logger.error(f"Unexpected error while receiving frame: {str(e)}")
                break

            faces = detect_faces(frame)

            if not faces:
                await websocket.send_json({"emotion": "no_faces", "confidence": 0})
                continue  

            dominant_emotion, confidence = "unknown", 0
            try:
                result = DeepFace.analyze(frame, actions=['emotion'], enforce_detection=False)
                if isinstance(result, list) and len(result) > 0:
                    first_result = result[0]
                    dominant_emotion = first_result.get("dominant_emotion", "unknown")
                    confidence = float(first_result.get("emotion", {}).get(dominant_emotion, 0))
            except Exception as e:
                logger.error(f"Emotion detection failed: {str(e)}")


            try:
                save_emotion(db, user.id, session_id, dominant_emotion, confidence)
            except Exception as e: 
                logger.error(f"Error saving emotion data to DB: {str(e)}")

            if websocket.application_state == WebSocketState.DISCONNECTED:
                logger.warning("Skipping send operation: WebSocket already closed.")
                break

            try:
                await websocket.send_json({
                    "emotion": dominant_emotion, 
                    "confidence": confidence, 
                })
            except Exception as e:
                logger.error(f"Error sending WebSocket response: {str(e)}")
                break

            if (datetime.utcnow() - period_start).total_seconds() >= monitoring_duration:
                period_end = datetime.utcnow() 
                logger.info(f"Monitoring session ended for user {user_id}")
                break

    except WebSocketDisconnect:
        logger.info("Client disconnected.")  
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")  
    finally:

        if websocket.application_state in [WebSocketState.CONNECTED, WebSocketState.CONNECTING]:
            try:
                await websocket.close()
            except RuntimeError:
                logger.warning("WebSocket was already closed.")

        logger.info("WebSocket connection cleanup done.")
    
        if period_end:
            from app.database import SessionLocal 

            new_db = SessionLocal()
            try:
                trend = save_emotion_trend(new_db, user.id, session_id, period_start, period_end)
                if trend:
                    logger.info(f" Emotion trend saved for user {user_id}")
                    user.number_of_session_taken += 1
                    db.commit()
                else:
                    logger.warning(f" No emotion trend saved for user {user_id}. No data found.")

                generate_emotion_monitoring_pdf_report(user.id, session_id, new_db)

                # now made a log 
                log_entry = Log(
                user_id=user_id,
                action="REPORT_CREATED",
                message=f"Report has been created and saved for the user {user_id}",
                timestamp=datetime.utcnow(),
                log_type=LogType.INFO
                )

                db.add(log_entry)
                db.commit()

            except Exception as e:
                logger.error(f" Error saving emotion trend: {str(e)}")
            finally:
                new_db.close()