from app.extensions.firebase_config import auth, auth_admin
from app.extensions.sql_alchemy import db as sq_db
from app.models.user import User
import json
import firebase_admin.exceptions

class AuthService:
    @staticmethod
    def _parse_firebase_error(e):
        # Captura erros do Firebase Admin (SDK Oficial)
        if isinstance(e, firebase_admin.exceptions.FirebaseError):
            return f"Erro Administrativo Firebase: {str(e)}"
            
        try:
            # Pyrebase levanta uma exceção requests.exceptions.HTTPError
            error_json = json.loads(e.args[1])
            print(f"--- DEBUG FIREBASE ERROR: {error_json}")
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
            if auth_admin:
                # Usar Admin SDK para evitar restrições de sign-up público / ADMIN_ONLY_OPERATION
                user_record = auth_admin.create_user(email=email, password=password)
                return {'localId': user_record.uid}
            else:
                # Fallback para Pyrebase (Client)
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
    def send_password_reset_email(email):
        """Sends a password reset email via Pyrebase."""
        try:
            auth.send_password_reset_email(email)
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

    @staticmethod
    def admin_update_user_email(uid, new_email):
        """Updates a user's email directly via Admin SDK without requiring old password/re-auth."""
        try:
            from app.extensions.firebase_config import auth_admin
            if auth_admin:
                auth_admin.update_user(uid, email=new_email)
                return True
            else:
                raise Exception("Admin SDK not configured for user update.")
        except Exception as e:
            error_msg = AuthService._parse_firebase_error(e)
            raise Exception(f"Erro ao atualizar e-mail no Firebase: {error_msg}")

    @staticmethod
    def admin_update_user_password(uid, new_password):
        """Updates a user's password directly via Admin SDK without requiring old password."""
        try:
            from app.extensions.firebase_config import auth_admin
            if auth_admin:
                auth_admin.update_user(uid, password=new_password)
                return True
            else:
                raise Exception("Admin SDK not configured for user update.")
        except Exception as e:
            error_msg = AuthService._parse_firebase_error(e)
            raise Exception(f"Erro ao atualizar senha no Firebase: {error_msg}")

    @staticmethod
    def delete_user_by_uid(uid):
        """Deletes a user directly via Admin SDK using UID."""
        try:
            from app.extensions.firebase_config import auth_admin
            if auth_admin:
                auth_admin.delete_user(uid)
                print(f"User {uid} deleted successfully from Firebase via Admin SDK.")
            else:
                raise Exception("Admin SDK not configured for user deletion.")
        except Exception as e:
            raise Exception(f"Erro ao excluir conta do Firebase: {error_msg}")

    @staticmethod
    def send_verification_for_new_email(uid, new_email):
        """
        Gera um token customizado, troca por um idToken via REST API e dispara
        o processo VERIFY_AND_CHANGE_EMAIL do Firebase para enviar um e-mail de
        confirmação ao novo endereço. O e-mail só será alterado quando o usuário
        clicar no link.
        """
        import os
        import requests
        from app.extensions.firebase_config import auth_admin
        
        try:
            if not auth_admin:
                raise Exception("Admin SDK not configured.")

            # 1. Gerar Custom Token para o usuário atual
            custom_token = auth_admin.create_custom_token(uid).decode('utf-8')
            api_key = os.getenv("FIREBASE_API_KEY")
            
            if not api_key:
                raise Exception("FIREBASE_API_KEY não configurada no ambiente.")

            # 2. Trocar Custom Token por ID Token
            res = requests.post(
                f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken?key={api_key}",
                json={"token": custom_token, "returnSecureToken": True}
            )
            
            if res.status_code != 200:
                raise Exception(f"Falha ao obter ID Token: {res.text}")
                
            id_token = res.json().get('idToken')

            # 3. Disparar VERIFY_AND_CHANGE_EMAIL
            res_verify = requests.post(
                f"https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key={api_key}",
                json={
                    "requestType": "VERIFY_AND_CHANGE_EMAIL",
                    "idToken": id_token,
                    "newEmail": new_email
                }
            )
            
            if res_verify.status_code != 200:
                raise Exception(f"Falha ao enviar e-mail de verificação: {res_verify.text}")
                
            return True
            
        except Exception as e:
            raise Exception(f"Erro no fluxo de verificação de e-mail: {str(e)}")

    @staticmethod
    def send_initial_verification_email(uid):
        """
        Envia o e-mail de verificação inicial para a conta recém-criada (VERIFY_EMAIL).
        """
        import os
        import requests
        from app.extensions.firebase_config import auth_admin
        
        try:
            if not auth_admin:
                raise Exception("Admin SDK not configured.")

            custom_token = auth_admin.create_custom_token(uid).decode('utf-8')
            api_key = os.getenv("FIREBASE_API_KEY")
            
            if not api_key:
                raise Exception("FIREBASE_API_KEY não configurada no ambiente.")

            res = requests.post(
                f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken?key={api_key}",
                json={"token": custom_token, "returnSecureToken": True}
            )
            
            if res.status_code != 200:
                raise Exception(f"Falha ao obter ID Token: {res.text}")
                
            id_token = res.json().get('idToken')

            res_verify = requests.post(
                f"https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key={api_key}",
                json={
                    "requestType": "VERIFY_EMAIL",
                    "idToken": id_token
                }
            )
            
            if res_verify.status_code != 200:
                raise Exception(f"Falha ao enviar e-mail de verificação: {res_verify.text}")
                
            return True
            
        except Exception as e:
            raise Exception(f"Erro no fluxo de verificação de e-mail inicial: {str(e)}")
