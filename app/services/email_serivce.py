from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from app.config import settings
from typing import List
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv
import os

load_dotenv()

conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_STARTTLS=True,  
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
)

async def send_email(subject: str, recipients: List[str], body: str, attachments: List[str] = None):
    message = MessageSchema(
        subject=subject,
        recipients=recipients,
        body=body,
        subtype="html",
        attachments=attachments or []
    )

    fm = FastMail(conf)
    await fm.send_message(message)
    

async def send_email_otp(to_email, message):
    msg = MIMEText(message)
    msg["Subject"] = "Your OTP Code"
    msg["From"] = os.getenv("MAIL_USERNAME")
    msg["To"] = to_email

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(os.getenv("MAIL_USERNAME"), os.getenv("MAIL_PASSWORD"))
        server.sendmail(os.getenv("MAIL_USERNAME"), to_email, msg.as_string())
