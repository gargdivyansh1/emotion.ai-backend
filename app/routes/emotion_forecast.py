from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.emotion_forecasting import get_emotion_forecast
from app.schemas import ForecastResponse
from app.utils.auth import get_current_user

router = APIRouter(prefix="/emotion_forecast", tags=["Emotion Forecast"])

@router.get("/", response_model=ForecastResponse)
def forecast_emotions(
    days_ahead: int = Query(7, ge=1, le=90, description="Number of days ahead to forecast"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["id"]
    forecast_result = get_emotion_forecast(user_id=user_id, db=db, days_ahead=days_ahead)

    if "error" in forecast_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=forecast_result["error"]
        )

    return forecast_result