import sys
import os
from flask import Flask
from dotenv import load_dotenv

# Adiciona o diretório atual ao path para importar os serviços
sys.path.append(os.getcwd())

_basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(os.path.dirname(_basedir), '.env'))

from app.services.ai_service import HealthAgent
from app.services.rag_service import rag_service
from app.extensions.sql_alchemy import db
from app.models.user import User

# Criamos um app Flask mínimo para que o SQLAlchemy funcione fora do servidor real
def create_test_app():
    app = Flask(__name__)
    # Usa a mesma config do seu projeto real

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
    """Garante que o usuário de teste exista no banco para não dar erro de ForeignKey"""
    user = User.query.get(user_id)
    if not user:
        print(f"👤 Criando usuário de teste '{user_id}' no banco...")
        new_user = User(
            id=user_id,
            name="Usuário de Teste",
            username=f"test_{user_id}",
            email=f"{user_id}@teste.com",
            user_type="patient",
            is_active=True
        )
        db.session.add(new_user)
        db.session.commit()

def main():
    app = create_test_app()
    
    with app.app_context():
        # Cria as tabelas no banco de dados se não existirem
        db.create_all()
        
        # Simulação de um ID de usuário
        current_user_id = input("🆔 Digite um ID de Usuário para teste (ex: user1): ") or "user1"
        
        # GARANTE QUE O USUÁRIO EXISTA
        ensure_test_user(current_user_id)
        
        print("🤖 Inicializando Agente de Saúde com Memória de Longo Prazo...")
        agent = HealthAgent()
        
        print(f"✅ Agente pronto para o usuário '{current_user_id}'!")
        print("Digite sua dúvida ou 'sair' para encerrar.\n")

        while True:
            user_input = input("👴 Usuário: ")
            
            if user_input.lower() in ['sair', 'exit', 'quit']:
                break
                
            print("🔍 Analisando intenção e buscando contexto...")
            # Note que no get_response agora passamos o user_id
            response = agent.get_response(user_input, user_id=current_user_id)
            
            print(f"\n🤖 Assistente: {response}\n")
            print("-" * 50)

if __name__ == "__main__":
    main()