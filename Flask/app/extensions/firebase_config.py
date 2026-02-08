
import pyrebase
import os
from dotenv import load_dotenv

load_dotenv()

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

if not config:
    print("AVISO: Sem configuração do Firebase encontrada nas variáveis de ambiente.")
    print("Por favor, certifique-se de ter um arquivo .env com FIREBASE_API_KEY, etc.")

try:
    firebase = pyrebase.initialize_app(config)
    auth = firebase.auth()
    db = firebase.database()
except Exception as e:
    print(f"ERRO CRÍTICO: Falha ao inicializar o Firebase: {e}")
    # Inicializa objetos vazios para evitar erros de importação
    auth = None
    db = None