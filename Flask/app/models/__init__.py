from app.extensions.sql_alchemy import db
from app.models.user import User
from app.models.chat_history import ChatHistory
from app.models.daily_report import DailyReport
from app.models.patient_context import PatientContext
from app.models.patient import Patient
from app.models.agent import HealthAgent
from app.models.patient_group import PatientGroup
def init_db():
    db.create_all()
