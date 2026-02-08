from app.extensions.sql_alchemy import db

class HealthAgent(db.Model):
    __tablename__ = 'health_agents'

    id = db.Column(db.String(128), db.ForeignKey('users.id'), primary_key=True)
    professional_training = db.Column(db.String(100))
    institutional_link = db.Column(db.String(100))
    area_of_activity = db.Column(db.String(100))
    service_time = db.Column(db.String(50))
    health_unit = db.Column(db.String(100))
    territory_served = db.Column(db.String(100))

    user = db.relationship('User', backref=db.backref('agent_profile', uselist=False))

    def __repr__(self):
        return f'<HealthAgent {self.id}>'
