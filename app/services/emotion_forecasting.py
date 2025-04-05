import pandas as pd
import numpy as np
from prophet import Prophet
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.models import EmotionData

def get_emotion_forecast(user_id: int, db: Session, days_ahead: int = 7):
    records = (
        db.query(EmotionData.timestamp, EmotionData.emotion)
        .filter(EmotionData.user_id == user_id)
        .all()
    )

    if not records:
        return {"error": "No emotion data available for forecasting."}

    # Prepare DataFrame
    df = pd.DataFrame(records, columns=["timestamp", "emotion"])
    df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.floor("D")
    df["count"] = 1
    df = df.groupby(["timestamp", "emotion"]).sum().reset_index()

    emotions = df["emotion"].unique()
    forecasts = {}

    for emotion in emotions:
        emotion_df = df[df["emotion"] == emotion][["timestamp", "count"]].rename(columns={"timestamp": "ds", "count": "y"})

        if len(emotion_df) < 2:
            forecasts[emotion] = {"error": "Not enough data for forecasting."}
            continue

        model = Prophet()
        model.fit(emotion_df)

        # Create large enough future to slice from
        total_future = model.make_future_dataframe(periods=90)  # ~3 months of days
        forecast = model.predict(total_future)[["ds", "yhat"]]

        forecast_daily = forecast.tail(days_ahead)
        forecast_weekly = forecast.set_index("ds").resample("W").mean().tail(4).reset_index()
        forecast_monthly = forecast.set_index("ds").resample("M").mean().tail(3).reset_index()

        forecasts[emotion] = {
            "daily": forecast_daily.to_dict(orient="records"),
            "weekly": forecast_weekly.to_dict(orient="records"),
            "monthly": forecast_monthly.to_dict(orient="records"),
        }

    return {"forecast": forecasts}
