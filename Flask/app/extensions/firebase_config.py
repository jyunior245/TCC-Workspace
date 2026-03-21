import pyrebase
import firebase_admin
from firebase_admin import credentials, auth as admin_auth
import os
from dotenv import load_dotenv

load_dotenv()

# Configuração para Pyrebase (Client SDK - Usado para Login)
config = {
  "apiKey": os.getenv("FIREBASE_API_KEY"),
  "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN"),
  "databaseURL": os.getenv("FIREBASE_DATABASE_URL"),
  "projectId": os.getenv("FIREBASE_PROJECT_ID"),
  "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET"),
  "messagingSenderId": os.getenv("FIREBASE_MESSAGING_SENDER_ID"),
  "appId": os.getenv("FIREBASE_APP_ID"),
  "measurementId": os.getenv("FIREBASE_MEASUREMENT_ID")
}

# Filtra as configurações vazias
config = {k: v for k, v in config.items() if v}

# 1. Inicializar Firebase Admin SDK (Privilegiado - Usado para Criar Usuários)
auth_admin = None
try:
    cred_path = os.getenv("FIREBASE_ADMIN_SDK_PATH", "./firebase-key.json")
    if os.path.exists(cred_path):
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        auth_admin = admin_auth
        print("Firebase Admin SDK inicializado com sucesso.")
    else:
        print(f"AVISO: Arquivo de credenciais Admin não encontrado em {cred_path}")
except Exception as e:
    print(f"Erro ao inicializar Firebase Admin: {e}")

# 2. Inicializar Pyrebase (Client)
auth = None
db = None
try:
    if config:
        firebase = pyrebase.initialize_app(config)
        auth = firebase.auth()
        db = firebase.database()
        print("Pyrebase inicializado com sucesso.")
except Exception as e:
    print(f"Erro ao inicializar Pyrebase: {e}")
