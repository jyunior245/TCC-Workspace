from app.extensions.sql_alchemy import db
from app.models.patient_context import PatientContext
from datetime import datetime

class PatientContextRepository:
    @staticmethod
    def get_context_by_patient(patient_id):
        return PatientContext.query.filter_by(patient_id=patient_id).first()

    @staticmethod
    def create_context(patient_id, context_data):
        new_context = PatientContext(patient_id=patient_id, context_data=context_data)
        db.session.add(new_context)
        db.session.commit()
        return new_context

    @staticmethod
    def update_context(patient_context, context_data):
        patient_context.context_data = context_data
        patient_context.updated_at = datetime.utcnow()
        db.session.commit()
        return patient_context
