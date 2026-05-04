import os

with open("app/services/auth_service.py", "a", encoding="utf-8") as f:
    f.write("""
    @staticmethod
    def send_initial_verification_email(uid):
        \"\"\"
        Envia o e-mail de verificação inicial para a conta recém-criada (VERIFY_EMAIL).
        \"\"\"
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
""")
