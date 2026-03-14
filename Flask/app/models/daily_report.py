from app.extensions.sql_alchemy import db
from datetime import datetime

class DailyReport(db.Model):
    __tablename__ = 'daily_reports'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    patient_id = db.Column(db.String(128), db.ForeignKey('patients.id'), nullable=False)
    date = db.Column(db.Date, nullable=False) # The specific day this report covers
    content = db.Column(db.Text, nullable=False) # The AI generated summary
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    patient = db.relationship('Patient', backref=db.backref('daily_reports', lazy=True))

    # A patient has only one report per day
    __table_args__ = (db.UniqueConstraint('patient_id', 'date', name='uq_patient_date'),)

    def __repr__(self):
        return f'<DailyReport patient={self.patient_id} date={self.date}>'
