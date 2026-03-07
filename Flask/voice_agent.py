import sys
import os
from flask import Flask
from dotenv import load_dotenv

sys.path.append(os.getcwd())
_basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(os.path.dirname(_basedir), '.env'))

from app.services.ai_service import HealthAgent
from app.services.voice_service import VoiceService
from app.extensions.sql_alchemy import db
from app.models.user import User

def create_test_app():
    app = Flask(__name__)
    if os.getenv('RUNNING_IN_DOCKER'):
        os.environ['DB_HOST'] = 'db'
    elif os.getenv('DB_HOST') == 'db':
        os.environ['DB_HOST'] = 'localhost'

    db_host = os.getenv("DB_HOST", "localhost")
    db_user = os.getenv("POSTGRES_USER", "postgres")
    db_password = os.getenv("POSTGRES_PASSWORD", "password")
    db_name = os.getenv("DATABASE_NAME", "postgres")
    
    from urllib.parse import quote_plus
    safe_password = quote_plus(db_password)
    
    app.config['SQLALCHEMY_DATABASE_URI'] = f"postgresql://{db_user}:{safe_password}@{db_host}:5432/{db_name}"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    return app

def ensure_test_user(user_id):
    user = User.query.get(user_id)
    if not user:
        print(f"👤 Criando usuário de teste '{user_id}' no banco...")
        new_user = User(
            id=user_id,
            name="Usuário de Teste Voz",
            username=f"test_voz_{user_id}",
            email=f"{user_id}_voz@teste.com",
            user_type="patient",
            is_active=True
        )
        db.session.add(new_user)
        db.session.commit()

def main():
    app = create_test_app()
    
    with app.app_context():
        db.create_all()
        current_user_id = input("🆔 Digite um ID de Usuário para teste (ex: user_voice): ") or "user_voice"
        ensure_test_user(current_user_id)
        
        print("🤖 Inicializando Agente de Saúde Auditivo...")
        agent = HealthAgent()
        voice = VoiceService()
        
        welcome_msg = f"Olá! Agente pronto para o usuário {current_user_id}. Pode começar a falar."
        print(f"✅ {welcome_msg}")
        voice.speak("Agente pronto. Pode começar a falar.")
        
        while True:
            print("\n🗣️ Preparando para ouvir...")
            user_input = voice.listen()
            
            if not user_input:
                continue
                
            print(f"👴 Você disse: {user_input}")
            
            if user_input.lower() in ['sair', 'encerrar', 'tchau', 'fechar', 'exit', 'quit']:
                print("👋 Encerrando assistente de voz.")
                voice.speak("Espero ter ajudado. Até logo!")
                break
                
            print("🔍 Analisando intenção e buscando contexto no agente...")
            
            # Gera a resposta do agente usando a inteligência existente
            response = agent.get_response(user_input, user_id=current_user_id)
            
            print(f"\n🤖 Assistente: {response}\n")
            print("🔊 Falando a resposta...")
            voice.speak(response)
            print("-" * 50)

if __name__ == "__main__":
    main()
