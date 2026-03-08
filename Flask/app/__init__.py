from flask import Flask 
import os
from app.routes.index import index_bp
from app.routes.index import login_bp
from app.routes.index import register_bp
from app.routes.patient import patient_bp
from app.routes.agent import agent_bp
from app.routes.chat import chat_bp
from app.routes.api import api_bp
from app.extensions import db
from app.models import init_db
from dotenv import load_dotenv

def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.secret_key="supersecretkey"

    load_dotenv('.env')
    

    # Configuração do banco de dados
    db_host = os.getenv("DB_HOST")
    db_user = os.getenv("POSTGRES_USER")
    db_password = os.getenv("POSTGRES_PASSWORD")
    db_name = os.getenv("DATABASE_NAME")
    
    # Escapa caracteres especiais na senha (como o @)
    from urllib.parse import quote_plus
    safe_password = quote_plus(db_password)
    
    app.config['SQLALCHEMY_DATABASE_URI'] = f"postgresql://{db_user}:{safe_password}@{db_host}:5432/{db_name}"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    with app.app_context():
        init_db()
        
        # --- INICIALIZAÇÃO DO RAG ---
        from app.services.rag_service import rag_service
        print("🚀 Inicializando banco de dados vetorial...")
        rag_service.load_pdf_protocols()
    

    app.register_blueprint(index_bp)
    app.register_blueprint(login_bp)
    app.register_blueprint(register_bp)
    app.register_blueprint(patient_bp)
    app.register_blueprint(agent_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(api_bp)

    return app

