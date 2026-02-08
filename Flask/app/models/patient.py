from app.extensions.sql_alchemy import db

class Patient(db.Model):
    __tablename__ = 'patients'

    id = db.Column(db.String(128), db.ForeignKey('users.id'), primary_key=True)
    education_level = db.Column(db.String(100))
    income = db.Column(db.String(100))
    housing_conditions = db.Column(db.String(255))
    sanitation_access = db.Column(db.Boolean)
    work_status = db.Column(db.String(100))
    family_context = db.Column(db.Text)

    user = db.relationship('User', backref=db.backref('patient_profile', uselist=False))

    def __repr__(self):
        return f'<Patient {self.id}>'
