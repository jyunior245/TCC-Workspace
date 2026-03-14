
from app.extensions.sql_alchemy import db
from app.models.user import User
from app.models.patient import Patient
from app.models.agent import HealthAgent

class UserRepository:
    @staticmethod
    def create_user(user_id, name, username, email, user_type):
        try:
            new_user = User(
                id=user_id,
                name=name,
                username=username,
                email=email,
                user_type=user_type,
                is_active=False # False até o registro complementar
            )
            db.session.add(new_user)
            db.session.commit()
            return new_user
        except Exception as e:
            db.session.rollback()
            raise Exception(f"Database Error: {str(e)}")

    @staticmethod
    def get_user_by_id(user_id):
        return User.query.get(user_id)

    @staticmethod
    def activate_user(user_id):
        user = User.query.get(user_id)
        if user:
            user.is_active = True
            db.session.commit()
            return user
        return None

    @staticmethod
    def _generate_patient_code(length=6):
        import random
        import string
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
            # Check if code already exists to ensure uniqueness
            if not Patient.query.filter_by(patient_code=code).first():
                return code

    @staticmethod
    def create_patient_profile(user_id, data):
        try:
            patient_code = UserRepository._generate_patient_code()
            profile = Patient(id=user_id, patient_code=patient_code, **data)
            db.session.add(profile)
            # Também ativa o usuário
            user = User.query.get(user_id)
            if user:
                user.is_active = True
            db.session.commit()
            return profile
        except Exception as e:
            db.session.rollback()
            raise Exception(f"Database Error (Patient Profile): {str(e)}")

    @staticmethod
    def create_agent_profile(user_id, data):
        try:
            profile = HealthAgent(id=user_id, **data)
            db.session.add(profile)
            # Também ativa o usuário
            user = User.query.get(user_id)
            if user:
                user.is_active = True
            db.session.commit()
            return profile
        except Exception as e:
            db.session.rollback()
            raise Exception(f"Database Error (Agent Profile): {str(e)}")

    @staticmethod
    def link_patient_to_agent(agent_id, patient_code):
        try:
            patient = Patient.query.filter_by(patient_code=patient_code.upper()).first()
            if not patient:
                return False, "Código de paciente inválido ou não encontrado."
            
            if patient.agent_id:
                if patient.agent_id == agent_id:
                     return False, "Paciente já está vinculado a você."
                return False, "Paciente já está vinculado a outro ACS."
                
            patient.agent_id = agent_id
            db.session.commit()
            return True, "Paciente vinculado com sucesso."
        except Exception as e:
            db.session.rollback()
            return False, f"Erro ao vincular paciente: {str(e)}"

    @staticmethod
    def get_linked_patients(agent_id):
        # Retorna lista de perfis de pacientes vinculados a esse ACS
        return Patient.query.filter_by(agent_id=agent_id).all()
