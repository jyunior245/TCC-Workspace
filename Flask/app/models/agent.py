from app.extensions.sql_alchemy import db

class HealthAgent(db.Model):
    __tablename__ = 'health_agents'

    id = db.Column(db.String(128), db.ForeignKey('users.id'), primary_key=True)
    gender = db.Column(db.String(20), nullable=False)
    phone_number = db.Column(db.String(20), nullable=False)
    cep = db.Column(db.String(20), nullable=False)
    state = db.Column(db.String(2), nullable=False)
    municipio = db.Column(db.String(100), nullable=False)
    ubs = db.Column(db.String(100), nullable=False)
    microarea = db.Column(db.String(50), nullable=False)
    cbo = db.Column(db.String(50), nullable=False)
    simet_codigo_municipio = db.Column(db.String(50), nullable=False)

    user = db.relationship('User', backref=db.backref('agent_profile', uselist=False))

    def __repr__(self):
        return f'<HealthAgent {self.id}>'
