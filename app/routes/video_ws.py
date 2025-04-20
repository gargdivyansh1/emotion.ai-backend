import asyncio
import uuid
import numpy as np
import cv2
from datetime import datetime

from fastapi import APIRouter, WebSocket, Query, Depends, status
from fastapi.exceptions import HTTPException
from fastapi.websockets import WebSocketDisconnect

from sqlalchemy.orm import Session

from deepface import DeepFace
from app.utils.jwt import decode_access_token
from app.database import get_db
from app.models import User
from app.repositories.emotion_repo import save_emotion
from app.services.face_recognition import detect_faces

import logging

async def authenticate_websocket(token: str, db: Session):
    try:
        payload = decode_access_token(token)
        return payload.get("user_id")
    except Exception as e:
        logger.error(f"WebSocket authentication failed: {str(e)}")
        return None

# Logger setup
logger = logging.getLogger("emotion-websocket")
logger.setLevel(logging.INFO)

# Add constants
MAX_FRAME_SIZE = 5 * 1024 * 1024  # 5MB
MIN_CONFIDENCE = 0.3
FRAME_PROCESS_INTERVAL = 0.5  # seconds

router = APIRouter(
    prefix="/video",
    tags=["Video WebSocket"],
)

@router.websocket("/ws")
async def video_websocket(
    websocket: WebSocket,
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    await websocket.accept()
    logger.info("WebSocket connection established")

    # Authentication
    try:
        if not token:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Authentication token missing"
            )
            
        user_id = await authenticate_websocket(token, db)
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid authentication token"
            )

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
    except HTTPException as e:
        await websocket.close(code=e.status_code)
        return
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        await websocket.close(code=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return

    session_id = str(uuid.uuid4())
    await websocket.send_json({
        "status": "connected", 
        "session_id": session_id,
        "config": {
            "min_confidence": MIN_CONFIDENCE,
            "max_frame_size": MAX_FRAME_SIZE
        }
    })
    
    # Session tracking
    frame_count = 0
    last_frame_time = datetime.utcnow()
    start_time = datetime.utcnow()

    try:
        while True:
            try:
                # Receive and validate frame
                frame_bytes = await asyncio.wait_for(
                    websocket.receive_bytes(),
                    timeout=30.0
                )
                
                if len(frame_bytes) > MAX_FRAME_SIZE:
                    await websocket.send_json({
                        "error": f"Frame too large. Max {MAX_FRAME_SIZE} bytes"
                    })
                    continue

                # Process frame
                np_arr = np.frombuffer(frame_bytes, np.uint8)
                frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                
                if frame is None:
                    await websocket.send_json({"error": "Invalid image data"})
                    continue

                # Face detection
                if not detect_faces(frame, return_bounding_boxes=False):
                    await websocket.send_json({
                        "emotion": "no_face", 
                        "confidence": 0,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    continue

                # Emotion analysis
                try:
                    results = DeepFace.analyze(
                        frame, 
                        actions=['emotion'],
                        enforce_detection=False,
                        detector_backend='opencv'
                    )
                    
                    if not results or not isinstance(results, list):
                        await websocket.send_json({
                            "emotion": "unknown",
                            "confidence": 0,
                            "timestamp": datetime.utcnow().isoformat()
                        })
                        continue

                    emotion_data = results[0]
                    dominant_emotion = emotion_data.get("dominant_emotion", "unknown")
                    emotion_confidences = emotion_data.get("emotion", {})
                    confidence = float(emotion_confidences.get(dominant_emotion, 0))

                    if confidence > MIN_CONFIDENCE:
                        save_emotion(db, user.id, session_id, dominant_emotion, confidence)

                    await websocket.send_json({
                        "emotion": dominant_emotion,
                        "confidence": confidence,
                        "timestamp": datetime.utcnow().isoformat()
                    })

                except Exception as e:
                    logger.error(f"Analysis error: {str(e)}")
                    await websocket.send_json({
                        "error": "Analysis failed",
                        "details": str(e)
                    })

                # Performance tracking
                frame_count += 1
                if frame_count % 10 == 0:
                    elapsed = (datetime.utcnow() - start_time).total_seconds()
                    fps = frame_count / elapsed if elapsed > 0 else 0
                    logger.info(f"[{user.username}] FPS: {fps:.2f}")

                # Throttle processing
                await asyncio.sleep(FRAME_PROCESS_INTERVAL)

            except asyncio.TimeoutError:
                await websocket.send_json({"status": "ping"})
                continue
                
            except WebSocketDisconnect:
                logger.info("Client disconnected normally")
                break
                
            except Exception as e:
                logger.error(f"Processing error: {str(e)}")
                await websocket.send_json({
                    "error": "Processing error",
                    "details": str(e)
                })
                break

    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        
    finally:
        try:
            await websocket.close()
        except:
            pass
            
        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.info(
            f"Session ended for {user.username} | "
            f"Duration: {duration:.2f}s | "
            f"Frames: {frame_count} | "
            f"Avg FPS: {frame_count/duration if duration > 0 else 0:.2f}"
        )