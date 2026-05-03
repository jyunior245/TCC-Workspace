
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
        from sqlalchemy.exc import IntegrityError
        try:
            profile = Patient.query.get(user_id)
            if profile:
                # Update existing profile
                for key, value in data.items():
                    setattr(profile, key, value)
            else:
                # Create new profile
                patient_code = UserRepository._generate_patient_code()
                profile = Patient(id=user_id, patient_code=patient_code, **data)
                db.session.add(profile)
            
            # Também ativa o usuário
            user = User.query.get(user_id)
            if user:
                user.is_active = True
            db.session.commit()
            return profile
        except IntegrityError as e:
            db.session.rollback()
            error_msg = str(e).lower()
            if "patients_cpf_key" in error_msg or "cpf" in error_msg:
                raise Exception("Este CPF já está cadastrado no sistema.")
            raise Exception(f"Erro de integridade de dados: {str(e)}")
        except Exception as e:
            db.session.rollback()
            raise Exception(f"Database Error (Patient Profile): {str(e)}")

    @staticmethod
    def create_agent_profile(user_id, data):
        try:
            profile = HealthAgent.query.get(user_id)
            if profile:
                # Update existing profile
                for key, value in data.items():
                    setattr(profile, key, value)
            else:
                # Create new profile
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

    @staticmethod
    def delete_user_completely(user_id):
        try:
            from app.models.chat_history import ChatHistory
            
            # 1. Recuperar usuário
            user = User.query.get(user_id)
            if not user:
                return False, "Usuário não encontrado no banco de dados local."
            
            # 2. Apagar históricos de chat pendentes referentes a esse usuário
            ChatHistory.query.filter_by(user_id=user_id).delete()
            
            # 3. Apagar o perfil complementar associado
            if user.user_type == 'patient':
                Patient.query.filter_by(id=user_id).delete()
            elif user.user_type == 'health_agent':
                HealthAgent.query.filter_by(id=user_id).delete()
                
            # 4. Apagar o usuário mestre
            db.session.delete(user)
            db.session.commit()
            return True, "Todos os dados locais foram excluídos com sucesso."
        except Exception as e:
            db.session.rollback()
            raise Exception(f"Falha ao apagar dados do banco de dados: {str(e)}")
