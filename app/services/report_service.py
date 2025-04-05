from io import StringIO, BytesIO
from fastapi import Depends, HTTPException
from fastapi.responses import StreamingResponse
from app.models import EmotionData, EmotionTrend
from sqlalchemy.orm import Session
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from typing import List
from sqlalchemy import func
from datetime import timedelta
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.piecharts import Pie
from app.models import User, ExportFormat, ExportStatus, Report
from collections import defaultdict
from app.database import get_db
import os
from app.repositories.emotion_repo import save_report 
from app.utils.auth import get_current_user
import logging
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.graphics.shapes import Drawing, String
from reportlab.graphics.charts.piecharts import Pie
from collections import defaultdict
from datetime import datetime
from io import BytesIO
import os
from reportlab.lib.colors import HexColor

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def generate_pie_chart(data):
    drawing = Drawing(300, 300)

    pie = Pie()
    pie.x = 75   # adjust x to center chart
    pie.y = 70
    pie.width = 150
    pie.height = 150

    pie.data = list(data.values())
    raw_labels = list(data.keys())
    total = sum(pie.data)

    if total > 0:
        pie.labels = [f"{(val/total)*100:.1f}% - {format_emotion_name(key)}" for key, val in zip(raw_labels, pie.data)]
    else:
        pie.labels = [format_emotion_name(label) for label in raw_labels]

    pie.sideLabels = True
    pie.simpleLabels = False

    pie.slices.strokeWidth = 1.5
    pie.slices.strokeColor = colors.black

    color_palette = [
        colors.blue, colors.green, colors.red, colors.purple,
        colors.orange, colors.brown, colors.pink, colors.gray
    ]

    for i in range(len(pie.data)):
        pie.slices[i].fillColor = color_palette[i % len(color_palette)]
        pie.slices[i].popout = 5

    title = String(85, 230, "Emotion Distribution", fontName="Helvetica-Bold", fontSize=12, fillColor=colors.black)

    drawing.add(title)
    drawing.add(pie)

    return drawing

def format_emotion_name(emotion_str):
    return str(emotion_str).split(".")[-1] if "." in str(emotion_str) else str(emotion_str)

# def generate_pie_chart(data):
#     drawing = Drawing(300, 300)
#     pie = Pie()
#     pie.x = 75  
#     pie.y = 50
#     pie.width = 150
#     pie.height = 150
#     pie.data = list(data.values())
#     raw_labels = list(data.keys())
#     total = sum(pie.data)

#     if total > 0:
#         pie.labels = [f"{(val/total)*100:.1f}% - {format_emotion_name(key)}" for key, val in zip(raw_labels, pie.data)]
#     else:
#         pie.labels = [format_emotion_name(label) for label in raw_labels]

#     pie.sideLabels = True
#     pie.simpleLabels = False
#     pie.slices.strokeWidth = 1.5
#     pie.slices.strokeColor = colors.black

#     color_palette = [
#         colors.blue, colors.green, colors.red, colors.purple,
#         colors.orange, colors.brown, colors.pink, colors.gray
#     ]

#     for i in range(len(pie.data)):
#         pie.slices[i].fillColor = color_palette[i % len(color_palette)]
#         pie.slices[i].popout = 5

#     title = String(85, 230, "Emotion Distribution", fontName="Helvetica-Bold", fontSize=12, fillColor=colors.black)
#     drawing.add(title)
#     drawing.add(pie)
#     return drawing

def generate_emotion_monitoring_pdf_report(user_id: int, session_id: str, db: Session):
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found.")

        data = db.query(EmotionData).filter(
            EmotionData.user_id == user_id, 
            EmotionData.session_id == session_id
        ).all()
        if not data:
            raise ValueError("No emotion data found for the given session.")

        first_timestamp = data[0].timestamp if data else "N/A"
        session_duration = 10

        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=30,
            leftMargin=40,
            topMargin=40,
            bottomMargin=30
        )
        elements = []
        styles = getSampleStyleSheet()
        bold_style = styles["Normal"]
        bold_style.fontName = "Helvetica-Bold"
        bold_style.fontSize = 11
        bold_style.leading = 15

        header_style = styles["Title"]
        header_style.fontSize = 18
        header_style.spaceAfter = 20

        subtitle_style = styles["Heading2"]
        subtitle_style.fontSize = 14
        subtitle_style.spaceAfter = 10

        # Header
        elements.append(Paragraph("Emotion Monitoring Report", header_style))
        elements.append(Paragraph(f"Session ID: {session_id}", bold_style))
        elements.append(Spacer(1, 20))

        # report = db.query(Report).filter(Report.session_id == session_id).first()

        # User Info Table
        user_info = [
            ["User ID:", user.id],
            # ["Report ID:", report.id],
            ["Report No.:", user.number_of_session_taken],
            ["Username:", user.username],
            ["User Email:", user.email],
            ["Account Created:", user.created_at],
            ["Session Start:", first_timestamp],
            ["Session Duration:", f"{session_duration} seconds"],
        ]
        user_table = Table(user_info, colWidths=[150, 300])
        user_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1.0, colors.black),
        ]))
        elements.append(user_table)
        elements.append(Spacer(1, 20))

        # Emotion Analysis
        emotion_counts = defaultdict(int)
        for record in data:
            emotion_counts[record.emotion] += 1
        dominant_emotion = max(emotion_counts, key=emotion_counts.get, default="N/A")

        elements.append(Paragraph(f"Dominant Emotion: <b>{format_emotion_name(dominant_emotion)}</b>", subtitle_style))
        # elements.append(Spacer(1, -5))
        
        chart = generate_pie_chart(emotion_counts)
        chart_table = Table([[chart]], colWidths=[440])  
        chart_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (1.5, -1), 'CENTER'),
        ]))
        # elements.append(Spacer(1, -5))  
        elements.append(chart_table)
        # elements.append(Spacer(1, 5))

        # Emotion Record Table
        elements.append(Paragraph("Emotion Records", subtitle_style))

        table_data = [["ID", "Emotion", "Intensity", "Timestamp"]]
        row_styles = []
        for idx, record in enumerate(data, start=1):
            table_data.append([
                record.id,
                format_emotion_name(record.emotion),
                f"{record.intensity:.2f}",
                str(record.timestamp)
            ])
            if record.emotion == dominant_emotion:
                row_styles.append(('BACKGROUND', (0, idx), (-1, idx), colors.HexColor("#dbeeff")))  # Light Blue

        emotion_table = Table(table_data, colWidths=[60, 140, 100, 160])
        emotion_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#333333")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 1.0, colors.black),
            *row_styles
        ]))
        elements.append(emotion_table)
        elements.append(Spacer(1, 30))

        # Emotion Summary Table
        elements.append(Paragraph("Emotion Count Summary", subtitle_style))
        summary_data = [["Emotion", "Count"]]
        for emo, count in emotion_counts.items():
            summary_data.append([format_emotion_name(emo), count])

        summary_table = Table(summary_data, colWidths=[200, 100])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#555555")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1.2, colors.black),
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 30))

        # Recommendation
        elements.append(Paragraph(
            "<b>Recommendation:</b> Consider mindfulness practices or guided sessions to help manage emotions and build resilience.",
            bold_style
        ))

        doc.build(elements)
        buffer.seek(0)

        if not os.path.exists("app/reports"):
            os.makedirs("app/reports")

        file_path = f"app/reports/{user.id}_emotion_report_{session_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
        with open(file_path, "wb") as f:
            f.write(buffer.getvalue())

        save_report(
            user_id=user.id,
            file_path=file_path,
            db=db,
            session_id=session_id,
            first_timestamp=first_timestamp,
            emotion_counts=emotion_counts,
            dominant_emotion=dominant_emotion,
            admin_notes=f"User is experiencing {dominant_emotion}.",
        )

        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={os.path.basename(file_path)}"}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating the PDF report: {str(e)}")
    
#generate weekly and monthly report router
# pending 
