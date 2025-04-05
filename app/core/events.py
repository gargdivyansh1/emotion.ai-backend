from app.database import engine
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
#from app.services.report_service import send_weekly_accuracy_report
from app.database import get_db
from app.models import Base

async def shutdown_event():
    await engine.dispose()

async def start_event():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# async def start_scheduler():
#     scheduler = BackgroundScheduler()
#     scheduler.start()

#     scheduler.add_job(
#         send_weekly_accuracy_report,
#         IntervalTrigger(weeks=1, start_date=datetime.now()),
#         args=["user", get_db]
#     )