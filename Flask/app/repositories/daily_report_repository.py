from app.extensions.sql_alchemy import db
from app.models.daily_report import DailyReport
from datetime import datetime

class DailyReportRepository:
    @staticmethod
    def get_by_patient_and_date(patient_id, target_date):
        return DailyReport.query.filter_by(patient_id=patient_id, date=target_date).first()

    @staticmethod
    def create_report(patient_id, target_date, content):
        new_report = DailyReport(patient_id=patient_id, date=target_date, content=content)
        db.session.add(new_report)
        db.session.commit()
        return new_report

    @staticmethod
    def update_report(report, new_content):
        report.content = new_content
        report.updated_at = datetime.utcnow()
        db.session.commit()
        return report

    @staticmethod
    def get_recent_reports(patient_id, limit=5):
        return DailyReport.query.filter_by(patient_id=patient_id).order_by(DailyReport.date.desc()).limit(limit).all()

    @staticmethod
    def get_all_reports(patient_id):
        return DailyReport.query.filter_by(patient_id=patient_id).order_by(DailyReport.date.desc()).all()

    @staticmethod
    def get_report_by_id_or_404(report_id):
        return DailyReport.query.get_or_404(report_id)
