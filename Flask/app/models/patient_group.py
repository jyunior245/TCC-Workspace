from app.extensions.sql_alchemy import db
from datetime import datetime
import uuid

# Tabela de Associação (Many-to-Many) entre Patient e PatientGroup
patient_group_members = db.Table('patient_group_members',
    db.Column('group_id', db.String(128), db.ForeignKey('patient_groups.id', ondelete='CASCADE'), primary_key=True),
    db.Column('patient_id', db.String(128), db.ForeignKey('patients.id', ondelete='CASCADE'), primary_key=True)
)

class PatientGroup(db.Model):
    __tablename__ = 'patient_groups'

    id = db.Column(db.String(128), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    agent_id = db.Column(db.String(128), db.ForeignKey('health_agents.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relacionamento com os pacientes (Many-to-Many)
    patients = db.relationship('Patient', secondary=patient_group_members, backref=db.backref('groups', lazy='dynamic'))

    def __repr__(self):
        return f'<PatientGroup {self.name} (Agent: {self.agent_id})>'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'agent_id': self.agent_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
