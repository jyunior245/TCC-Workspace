
from app.extensions.firebase_config import auth
from app.extensions.sql_alchemy import db as sq_db
from app.models.user import User
import json

class AuthService:
    @staticmethod
    def _parse_firebase_error(e):
        try:
            #Pyrebase levanta uma exceção requests.exceptions.HTTPError com o JSON de erro no args[1]
            # O JSON de erro contém o código de erro na chave 'error']['message']
            error_json = json.loads(e.args[1])
            error_code = error_json['error']['message']
            
            if "WEAK_PASSWORD" in error_code:
                return "A senha deve ter pelo menos 6 caracteres."
            elif "EMAIL_EXISTS" in error_code:
                return "Este e-mail já está cadastrado."
            elif "INVALID_EMAIL" in error_code:
                return "E-mail inválido."
            elif "INVALID_PASSWORD" in error_code:
                return "Senha incorreta."
            elif "USER_NOT_FOUND" in error_code:
                return "Usuário não encontrado."
            elif "PASSWORD_DOES_NOT_MEET_REQUIREMENTS" in error_code:
                return "A senha é muito fraca. Requer: minúscula, maiúscula, número e símbolo."
            elif "CONFIGURATION_NOT_FOUND" in error_code:
                return "Erro de configuração do Firebase (Verifique se Email/Senha está ativado no console)."
            else:
                return f"Erro do Firebase: {error_code}"
        except:
            return f"Erro desconhecido: {str(e)}"

    @staticmethod
    def create_firebase_user(email, password):
        """Creates a user in Firebase Auth and returns the user object."""
        try:
            user = auth.create_user_with_email_and_password(email, password)
            return user
        except Exception as e:
            error_msg = AuthService._parse_firebase_error(e)
            raise Exception(error_msg)

    @staticmethod
    def login_firebase_user(email, password):
        """Authenticates a user with Firebase Auth and returns the user object."""
        try:
            user = auth.sign_in_with_email_and_password(email, password)
            return user
        except Exception as e:
            error_msg = AuthService._parse_firebase_error(e)
            raise Exception(error_msg)

    @staticmethod
    def delete_firebase_user(id_token):
        """Deletes a user from Firebase Auth using their ID token."""
        try:
            auth.delete_user_account(id_token)
            print("Rollback: Firebase user deleted successfully.")
        except Exception as e:
            print(f"Failed to rollback Firebase user: {e}")
