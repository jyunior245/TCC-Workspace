from app.extensions.sql_alchemy import db
from datetime import datetime

class PatientContext(db.Model):
    __tablename__ = 'patient_contexts'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    patient_id = db.Column(db.String(128), db.ForeignKey('users.id'), unique=True, nullable=False)
    context_data = db.Column(db.JSON, nullable=False, default={}) 
    # context_data deve conter: nome do paciente, data da conversa, sintomas, medicações relatas, ações recomendadas, observações, etc.
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('patient_context', uselist=False))

    def __repr__(self):
        return f'<PatientContext patient_id={self.patient_id} updated={self.updated_at}>'
