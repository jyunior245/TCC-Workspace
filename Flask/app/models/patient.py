from app.extensions.sql_alchemy import db

class Patient(db.Model):
    __tablename__ = 'patients'

    id = db.Column(db.String(128), db.ForeignKey('users.id'), primary_key=True)
    patient_code = db.Column(db.String(10), unique=True, nullable=True) # Unique code for ACS linking
    agent_id = db.Column(db.String(128), db.ForeignKey('health_agents.id'), nullable=True) # Linked ACS
    
    education_level = db.Column(db.String(100))
    income = db.Column(db.String(100))
    housing_conditions = db.Column(db.String(255))
    sanitation_access = db.Column(db.Boolean)
    work_status = db.Column(db.String(100))
    family_context = db.Column(db.Text)

    user = db.relationship('User', backref=db.backref('patient_profile', uselist=False))
    # Relationship to agent is handled from the Agent side or implicitly

    def __repr__(self):
        return f'<Patient {self.id} Code:{self.patient_code}>'
