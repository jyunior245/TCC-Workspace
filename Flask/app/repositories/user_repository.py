
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
    def create_patient_profile(user_id, data):
        try:
            profile = Patient(id=user_id, **data)
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
