## 1. AI Accuracy Service
# Report Trend Service custom model training of AI

# model
# class AIAccuracyReport(Base):
#     __tablename__ = "ai_accuracy_reports"

#     id = Column(Integer, primary_key=True, index=True)
#     user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
#     predicted_emotion = Column(Enum(EmotionType), nullable=False)
#     actual_emotion = Column(Enum(EmotionType), nullable=False)
#     accuracy_score = Column(Float, nullable=False)
#     timestamp = Column(TIMESTAMP, server_default=func.now())

#     created_at = Column(TIMESTAMP, server_default=func.now())
#     updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

#     user = relationship("User", back_populates="ai_accuracy_reports")

#     __table_args__ = (
#         Index('ix_ai_accuracy_reports_user_id', 'user_id'),
#         Index('ix_ai_accuracy_reports_timestamp', 'timestamp'),
#         Index('ix_ai_accuracy_reports_predicted_emotion', 'predicted_emotion'),
#         Index('ix_ai_accuracy_reports_actual_emotion', 'actual_emotion'),
#         Index('ix_ai_accuracy_reports_accuracy_score', 'accuracy_score'),
#     )

#     def __repr__(self):
#         return f"<AIAccuracyReport {self.user_id} - {self.predicted_emotion} vs {self.actual_emotion}>"
    
#schema
# for ai accuracy
# class AIAccuracyReportCreate(BaseModel):
#     user_id: int
#     predicted_emotion: str
#     start_date: datetime
#     actual_emotion: str
#     end_date: datetime
#     accuracy_percentage: float  
#     ai_model_version: str 

#     class Config:
#         from_attributes = True

# # for out
# class AIAccuracyReportOut(AIAccuracyReportCreate):
#     id: int
#     generated_at: datetime = datetime.now(timezone.utc)

#     class Config:
#         from_attributes: True


# # for adminaction
# class AdminActionCreate(BaseModel):
#     admin_id: int
#     action: str
#     target_user_id: Optional[int] = None  
#     description: Optional[str] = None  
#     timestamp: datetime = datetime.now(timezone.utc)

#     class Config:
#         from_attributes = True

# # for respoonse
# class AdminActionOut(AdminActionCreate):
#     id: int

## routes
# from fastapi import APIRouter, Depends, Query, HTTPException
# from sqlalchemy.orm import Session
# from app.database import get_db
# from app.models import AIAccuracyReport, User
# from app.schemas import AIAccuracyReportCreate, AIAccuracyReportOut
# from app.utils.jwt import decode_access_token
# from datetime import datetime
# from app.utils.auth import get_current_user
# from app.services.report_service import generate_ai_accuracy_pdf_report, generate_ai_accuracy_csv_report

# router = APIRouter(prefix="/ai-accuracy-reports", tags=["AI Accuracy Reports"])

# @router.post("/", response_model=AIAccuracyReportOut)
# def create_ai_accuracy_report(
#     data: AIAccuracyReportCreate, db: Session = Depends(get_db)
# ):
#     new_report = AIAccuracyReport(
#         user_id=data.user_id,
#         predicted_emotion=data.predicted_emotion,
#         actual_emotion=data.actual_emotion,
#         accuracy_score=data.accuracy_percentage,
#         ai_model_version=data.ai_model_version,
#     )
#     db.add(new_report)
#     db.commit()
#     db.refresh(new_report)
#     return new_report

# @router.get("/", response_model=list[AIAccuracyReportOut])
# def get_ai_accuracy_reports(
#     db: Session = Depends(get_db),
#     user: User = Depends(get_current_user),
#     start_date: datetime = Query(None, description="Start date (YYYY-MM-DD)"),
#     end_date: datetime = Query(None, description="End date (YYYY-MM-DD)")
# ):

#     query = db.query(AIAccuracyReport).filter(AIAccuracyReport.user_id == user.id)

#     if start_date:
#         query = query.filter(AIAccuracyReport.timestamp >= start_date)
    
#     if end_date:
#         query = query.filter(AIAccuracyReport.timestamp <= end_date)

#     reports = query.all()
    
#     if not reports:
#         raise HTTPException(status_code=404, detail="No reports found")
    
#     return reports

# @router.get("/{report_id}", response_model=AIAccuracyReportOut)
# def get_ai_accuracy_report_by_id(
#     report_id: int, db: Session = Depends(get_db)
# ):
#     report = db.query(AIAccuracyReport).filter(AIAccuracyReport.id == report_id).first()
    
#     if not report:
#         raise HTTPException(status_code=404, detail="Report not found")
    
#     return report

# @router.get("/export/pdf")
# def export_pdf(
#     user: User = Depends(get_current_user), 
#     db: Session = Depends(get_db),
#     start_date: str = Query(None, description="Start date (YYYY-MM-DD)"),
#     end_date: str = Query(None, description="End date (YYYY-MM-DD)")
# ):
#     """Generate PDF for AI accuracy reports based on date filters."""
#     return generate_ai_accuracy_pdf_report(db, user.id, start_date, end_date)

# @router.get("/export/csv")
# def export_pdf(
#     user: User = Depends(get_current_user), 
#     db: Session = Depends(get_db),
#     start_date: str = Query(None, description="Start date (YYYY-MM-DD)"),
#     end_date: str = Query(None, description="End date (YYYY-MM-DD)")
# ):
#     """Generate PDF for AI accuracy reports based on date filters."""
#     return generate_ai_accuracy_csv_report(db, user.id, start_date, end_date)

# @router.get("/export/csv/ai_accuracy")
# def export_ai_accuracy_csv(
#     user: User = Depends(get_current_user),
#     db: Session = Depends(get_db),
#     start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
#     end_date: str = Query(..., description="End date (YYYY-MM-DD)")
# ):
#     try:
#         # Generate the CSV report for AI accuracy
#         return generate_ai_accuracy_csv_report(db, user.id, start_date, end_date)
#     except ValueError as e:
#         raise HTTPException(status_code=400, detail=str(e))

# @router.get("/export/pdf/ai_accuracy")
# def export_ai_accuracy_pdf(
#     user: User = Depends(get_current_user),
#     db: Session = Depends(get_db),
#     start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
#     end_date: str = Query(..., description="End date (YYYY-MM-DD)")
# ):
#     try:
#         # Generate the PDF report for AI accuracy
#         return generate_ai_accuracy_pdf_report(db, user.id, start_date, end_date)
#     except ValueError as e:
#         raise HTTPException(status_code=400, detail=str(e))

# app/services/ai_accuracy_service.py

# from datetime import datetime, timedelta
# import pandas as pd
# from app.models import EmotionData
# from app.services.emotion_forecasting import get_emotion_forecast
# from app.repositories.emotion_repo import store_accuracy_results
# from sqlalchemy.orm import Session

# def compare_predictions(user_id: int, db: Session, days_ahead: int = 7):
#     end_date = datetime.utcnow()
#     start_date = end_date - timedelta(days=days_ahead)
    
#     # Get AI emotion forecast
#     predictions = get_emotion_forecast(user_id, db, days_ahead).get("forecast", {})

#     if not predictions:
#         return {"error": "No AI predictions available for comparison."}

#     actual_records = db.query(EmotionData).filter(
#         EmotionData.user_id == user_id,
#         EmotionData.timestamp >= start_date,
#         EmotionData.timestamp < end_date
#     ).all()

#     if not actual_records:
#         return {"error": "No actual emotion data available for comparison."}

#     # Convert actual records to DataFrame
#     actual_df = pd.DataFrame(
#         [(r.timestamp, r.emotion) for r in actual_records], columns=["timestamp", "emotion"]
#     )
#     actual_df["count"] = 1
#     actual_df = actual_df.groupby(["timestamp", "emotion"]).sum().reset_index()

#     accuracy_results = {}

#     for emotion, predicted_values in predictions.items():
#         predicted_df = pd.DataFrame(predicted_values)
#         predicted_df["timestamp"] = pd.to_datetime(predicted_df["ds"])
#         predicted_df = predicted_df[["timestamp", "yhat"]]

#         if not actual_df.empty:
#             merged_df = pd.merge(predicted_df, actual_df, on="timestamp", how="left").fillna(0)
#         else:
#             continue

#         # Prevent division by zero and calculate accuracy
#         merged_df["accuracy"] = merged_df.apply(
#             lambda row: 1 - abs(row["yhat"] - row["count"]) / (row["count"] + 1) if row["count"] > 0 else 0,
#             axis=1
#         )

#         avg_accuracy = merged_df["accuracy"].mean()
#         accuracy_results[emotion] = round(avg_accuracy * 100, 2)

#     # Store accuracy results in the database
#     store_accuracy_results(user_id, accuracy_results, db)

#     return {"accuracy_results": accuracy_results}




# 2. import cv2
# import numpy as np
# import dlib

# # Load Haar Cascade for face detection
# face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

# if not face_cascade.load(cv2.data.haarcascades + "haarcascade_frontalface_default.xml"):
#     raise IOError("Error loading Haar Cascade XML file. Check OpenCV installation.")

# # Load dlib's pre-trained facial landmark predictor
# predictor_path = "shape_predictor_68_face_landmarks.dat"
# detector = dlib.get_frontal_face_detector()
# predictor = dlib.shape_predictor(predictor_path)

# def detect_faces_and_landmarks(image: np.ndarray, scale_factor: float = 1.1, min_neighbors: int = 5, min_size: tuple = (30, 30)):
#     # Validate image input
#     if image is None or not isinstance(image, np.ndarray) or image.size == 0:
#         raise ValueError("Invalid image input. Ensure it's a non-empty NumPy array.")

#     # Convert image to grayscale
#     gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
#     # Detect faces using Haar cascade
#     faces = face_cascade.detectMultiScale(gray, scaleFactor=scale_factor, minNeighbors=min_neighbors, minSize=min_size)

#     for (x, y, w, h) in faces:
#         # Draw face bounding box
#         cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 2)  

#         # Convert OpenCV face detection to dlib rectangle
#         dlib_rect = dlib.rectangle(x, y, x + w, y + h)

#         # Detect facial landmarks
#         shape = predictor(gray, dlib_rect)

#         # Draw facial landmarks
#         for i in range(68):  # 68 landmark points
#             landmark_x, landmark_y = shape.part(i).x, shape.part(i).y
#             cv2.circle(image, (landmark_x, landmark_y), 2, (0, 0, 255), -1)  # Red dots

#     return image

# # Capture video from webcam
# cap = cv2.VideoCapture(0)

# while True:
#     ret, frame = cap.read()
#     if not ret:
#         break

#     # Detect faces and draw rectangles & landmarks
#     frame_with_faces = detect_faces_and_landmarks(frame)

#     # Display the frame
#     cv2.imshow("Face Detection with Landmarks", frame_with_faces)

#     # Press 'q' to exit the loop
#     if cv2.waitKey(1) & 0xFF == ord("q"):
#         break

# # Release the capture and close windows
# cap.release()
# cv2.destroyAllWindows()


# 3 def generate_emotion_monitoring_csv_report(db: Session, user_id: int, start_date: str, end_date: str):
#     data = db.query(EmotionData).filter(
#         EmotionData.user_id == user_id,
#         EmotionData.timestamp >= start_date,
#         EmotionData.timestamp <= end_date
#     ).all()

#     if not data:
#         raise ValueError("No emotion data found for the given user and date range.")
    
#     # Prepare CSV in memory
#     output = StringIO()
#     csv_writer = csv.writer(output)
    
#     # Column Headers
#     csv_writer.writerow(["ID", "Emotion", "Intensity", "AI Accuracy", "Timestamp"])

#     # Write data rows
#     for record in data:
#         csv_writer.writerow([record.id, record.emotion, record.intensity, record.ai_accuracy, record.timestamp])

#     output.seek(0)
#     return StreamingResponse(output, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=emotion_monitoring_report.csv"})


# 3 . 
# def generate_ai_accuracy_csv_report(db: Session, user_id: int, start_date: str, end_date: str):
#     reports = db.query(AIAccuracyReport).filter(
#         AIAccuracyReport.user_id == user_id,
#         AIAccuracyReport.timestamp >= start_date,
#         AIAccuracyReport.timestamp <= end_date
#     ).all()

#     if not reports:
#         raise ValueError("No reports found for the given user and date range.")
    
#     # Prepare CSV in memory
#     output = StringIO()
#     csv_writer = csv.writer(output)
    
#     # Column Headers
#     csv_writer.writerow(["ID", "Predicted Emotion", "Actual Emotion", "Accuracy Score", "Timestamp"])

#     # Write data rows
#     for report in reports:
#         csv_writer.writerow([report.id, report.predicted_emotion, report.actual_emotion, report.accuracy_score, report.timestamp])

#     output.seek(0)
#     return StreamingResponse(output, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=ai_accuracy_report.csv"})



# async def send_weekly_accuracy_report(user, db: Session):
    
#     end_date = datetime.utcnow()
#     start_date = end_date - timedelta(weeks=1)  # Last week's range

#     start_date_str = start_date.strftime("%Y-%m-%d")
#     end_date_str = end_date.strftime("%Y-%m-%d")
    
#     # Generate the AI accuracy report as a PDF
#     try:
#         pdf_response = await generate_ai_accuracy_pdf_report(db, user.id, start_date=start_date_str, end_date=end_date_str)
#         pdf_content = pdf_response.body
#         pdf_filename = "ai_accuracy_report.pdf"
#     except ValueError as e:
#         # Handle error if no reports found or any issues during PDF generation
#         return {"error": str(e)}

#     # Email content
#     email_body = "<h2>Your Weekly AI Emotion Accuracy Report</h2><p>Attached is your detailed report for the week from {start_date_str} to {end_date_str}.</p>"

#     # Send the email with the PDF attachment
#     await send_email(
#         subject="Your Weekly Emotion Accuracy Report 📊",
#         recipients=[user.email],
#         body=email_body,
#         attachments=[(pdf_filename, pdf_content)]
#     )




# async def send_comparison_report(user, db: Session):
    # Get the current date and calculate the past week
    # end_date = datetime.utcnow()
    # start_date = end_date - timedelta(weeks=1)  # Last week's range

    # start_date_str = start_date.strftime("%Y-%m-%d")
    # end_date_str = end_date.strftime("%Y-%m-%d")

    # # Call compare_predictions to get the AI accuracy results
    # accuracy_results = compare_predictions(user.id, db, days_ahead=7)  # You can adjust days_ahead as necessary

    # if "error" in accuracy_results:
    #     return {"error": accuracy_results["error"]}

    # # Prepare the comparison data to send in the email
    # comparison_data = ""
    # for emotion, accuracy in accuracy_results["accuracy_results"].items():
    #     comparison_data += f"Emotion: {emotion}\nAccuracy: {accuracy}%\n\n"

    # Email body content
    # email_body = f"""
    # <h2>Your AI Emotion Prediction vs. Actual Comparison Report</h2>
    # <p>Here is the comparison for your emotions from {start_date_str} to {end_date_str}:</p>
    # <pre>{comparison_data}</pre>
    # """

    # # Send the email with the comparison data
    # await send_email(
    #     subject="Your AI Emotion Prediction vs. Actual Comparison 📊",
    #     recipients=[user.email],
    #     body=email_body,
    # )