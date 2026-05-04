import os
from dotenv import load_dotenv
import requests
import pyrebase
import firebase_admin
from firebase_admin import credentials, auth as admin_auth

load_dotenv()

# Admin init
cred_path = "./firebase-key.json"
cred = credentials.Certificate(cred_path)
firebase_admin.initialize_app(cred)

api_key = os.getenv("FIREBASE_API_KEY")

def test_verify_flow(uid, new_email):
    print(f"Testing flow for uid: {uid}, new_email: {new_email}")
    
    # 1. Generate Custom Token
    custom_token = admin_auth.create_custom_token(uid).decode('utf-8')
    print("Custom token generated.")
    
    # 2. Exchange for ID Token
    res = requests.post(
        f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken?key={api_key}",
        json={"token": custom_token, "returnSecureToken": True}
    )
    if res.status_code != 200:
        print("Failed to get ID token:", res.text)
        return
        
    id_token = res.json()['idToken']
    print("ID token obtained.")
    
    # 3. Request VERIFY_AND_CHANGE_EMAIL
    res = requests.post(
        f"https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key={api_key}",
        json={
            "requestType": "VERIFY_AND_CHANGE_EMAIL",
            "idToken": id_token,
            "newEmail": new_email
        }
    )
    
    if res.status_code == 200:
        print("Success! Verification email sent.")
    else:
        print("Failed to send verification email:", res.text)

if __name__ == "__main__":
    # Get a test user or just pass a known UID
    # test_verify_flow("SOME_UID", "test@example.com")
    pass
