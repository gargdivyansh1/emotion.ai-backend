import asyncio
import uuid
import logging
import cv2
import numpy as np
from sqlalchemy.orm import Session
from fastapi import Depends, WebSocket, WebSocketDisconnect, APIRouter, HTTPException
from deepface import DeepFace
from datetime import datetime
from app.services.face_recognition import detect_faces
from app.repositories.emotion_repo import save_emotion, save_emotion_trend
from app.database import get_db
from app.services.report_service import generate_emotion_monitoring_pdf_report
from app.models import User
from fastapi import Depends
import os

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv('ALGORITHM')

router = APIRouter()
logger = logging.getLogger("emotion-websocket")
logger.setLevel(logging.INFO)

MAX_FRAME_SIZE = 5 * 1024 * 1024 
MIN_CONFIDENCE = 0.3
FRAME_PROCESS_INTERVAL = 0.1
EMOTION_SAVE_INTERVAL = 2.0  

async def get_user_from_token(token: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.jwt_token == token).first()

    id = user.id # type: ignore

    return id

@router.websocket("/ws/video/")
async def video_websocket(websocket: WebSocket, db: Session = Depends(get_db)):
    await websocket.accept()

    token = websocket.query_params.get('token')

    if not token:
        await websocket.close(code=1008)
        return 
    
    id = await get_user_from_token(token, db)

    logger.info("WebSocket connection accepted")
    session_id = str(uuid.uuid4())
    start_time = datetime.utcnow()
    last_save_time = start_time
    frame_count = 0
    user_id = id

    try:
        await websocket.send_json({
            "status": "connected",
            "session_id": session_id,
            "message": "Ready to receive frames"
        })

        session_emotions = []
        unsaved_emotions = []

        while True:
            print("Waiting for frame...")
            try:
                frame_bytes = await asyncio.wait_for(
                    websocket.receive_bytes(),
                    timeout=5.0
                )

                if len(frame_bytes) > MAX_FRAME_SIZE:
                    await websocket.send_json({
                        "error": f"Frame too large. Max {MAX_FRAME_SIZE} bytes"
                    })
                    continue
                if len(frame_bytes) < 1024:
                    await websocket.send_json({
                        "error": "Frame too small"
                    })
                    continue

                np_arr = np.frombuffer(frame_bytes, np.uint8)
                frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                
                if frame is None:
                    print("Frame decoding failed")
                    await websocket.send_json({"error": "Invalid image data"})
                    continue

                if not detect_faces(frame, return_bounding_boxes=False):
                    await websocket.send_json({
                        "emotion": "no_face",
                        "confidence": 0,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    continue

                try:
                    results = DeepFace.analyze(
                        frame,
                        actions=['emotion'],
                        enforce_detection=False,
                        detector_backend='opencv'
                    )

                    if not results or not isinstance(results, list):
                        raise ValueError("Invalid analysis results")

                    emotion_data = results[0]
                    dominant_emotion = emotion_data.get("dominant_emotion", "unknown")
                    emotion_confidences = emotion_data.get("emotion", {})
                    confidence = float(emotion_confidences.get(dominant_emotion, 0))
                    current_time = datetime.utcnow()

                    emotion_record = {
                        "emotion": dominant_emotion,
                        "confidence": confidence,
                        "timestamp": current_time
                    }
                    unsaved_emotions.append(emotion_record)
                    session_emotions.append(emotion_record)

                    if (current_time - last_save_time).total_seconds() >= EMOTION_SAVE_INTERVAL:
                        try:
                            for emotion in unsaved_emotions:
                                save_emotion(
                                    db=db,
                                    user_id=user_id,
                                    session_id=session_id,
                                    emotion=emotion["emotion"],
                                    intensity=emotion["confidence"]
                                )
                            unsaved_emotions = []
                            last_save_time = current_time
                            logger.info(f"Saved emotions at {current_time}")
                        except Exception as e:
                            logger.error(f"Error saving emotions: {str(e)}")
                            db.rollback()

                    await websocket.send_json({
                        "emotion": dominant_emotion,
                        "confidence": confidence,
                        "timestamp": current_time.isoformat()
                    })

                    frame_count += 1

                except Exception as e:
                    logger.error(f"Analysis error: {str(e)}")
                    await websocket.send_json({
                        "emotion": "unknown",
                        "confidence": 0,
                        "timestamp": datetime.utcnow().isoformat()
                    })

                await asyncio.sleep(FRAME_PROCESS_INTERVAL)

            except asyncio.TimeoutError:
                try:
                    await websocket.send_json({"status": "ping"})
                except:
                    break
                continue

            except WebSocketDisconnect:
                logger.info("Client disconnected normally")
                break

            except Exception as e:
                logger.error(f"Processing error: {str(e)}")
                break

    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
    finally:
        try:
            if unsaved_emotions:
                try:
                    for emotion in unsaved_emotions:
                        save_emotion(
                            db=db,
                            user_id=user_id,
                            session_id=session_id,
                            emotion=emotion["emotion"],
                            intensity=emotion["confidence"]
                        )
                    logger.info("Saved remaining unsaved emotions")
                except Exception as e:
                    logger.error(f"Error saving remaining emotions: {str(e)}")
                    db.rollback()

            if session_emotions:
                try:
                    first_timestamp = session_emotions[0]["timestamp"]
                    last_timestamp = session_emotions[-1]["timestamp"]
                    
                    trend = save_emotion_trend(
                        db=db,
                        user_id=user_id,
                        session_id=session_id,
                        period_start=first_timestamp,
                        period_end=last_timestamp
                    )
                    if trend:
                        logger.info(f"Successfully saved emotion trend for session {session_id}")
                        try:
                            report_response = generate_emotion_monitoring_pdf_report(
                                user_id=user_id,
                                session_id=session_id,
                                db=db
                            )
                            logger.info(f"Successfully generated report for session {session_id}")
                            
                            await websocket.send_json({
                                 "status": "report_generated",
                                 "session_id": session_id
                            })
                            
                        except HTTPException as e:
                            logger.error(f"Error generating report: {str(e.detail)}")
                        except Exception as e:
                            logger.error(f"Unexpected error generating report: {str(e)}")
                    else:
                        logger.warning(f"Failed to save emotion trend for session {session_id}")
                except Exception as e:
                    logger.error(f"Error saving emotion trend: {str(e)}")
                    db.rollback()
            
            await websocket.close()
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")

        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.info(
            f"Session ended | "
            f"Duration: {duration:.2f}s | "
            f"Frames: {frame_count} | "
            f"FPS: {frame_count/max(duration, 0.1):.2f}"
        )