from app.extensions.sql_alchemy import db
from app.models.user import User
from app.models.chat_history import ChatHistory
from app.models.daily_report import DailyReport
from app.models.patient_context import PatientContext

def init_db():
    db.create_all()
