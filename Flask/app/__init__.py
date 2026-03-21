from flask import Flask 
import os
from app.routes.index import index_bp
from app.routes.index import login_bp
from app.routes.index import register_bp
from app.routes.patient import patient_bp
from app.routes.agent import agent_bp
from app.routes.chat import chat_bp
from app.extensions import db
from app.extensions.google_auth import init_google_auth
from app.routes.auth_google import auth_google_bp
from app.models import init_db
from dotenv import load_dotenv

def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.secret_key="supersecretkey"

    # Load .env from parent directory
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    load_dotenv(os.path.join(base_dir, '.env'))
    
    # Configurações do banco de dados
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DATABASE_NAME", "postgres")
    
    # Prioridade para DB_URL (Docker) ou constrói a partir dos componentes
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DB_URL") or f"postgresql://{user}:{password}@{host}:{port}/{db_name}"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = os.path.join('app', 'static', 'uploads')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

    # Inicializar extensões
    db.init_app(app)
    init_google_auth(app)

    with app.app_context():
        init_db()

    # Registro de Blueprints
    app.register_blueprint(index_bp)
    app.register_blueprint(login_bp)
    app.register_blueprint(register_bp)
    app.register_blueprint(patient_bp)
    app.register_blueprint(agent_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(auth_google_bp)
    
    from app.routes.registration_api import registration_api_bp
    app.register_blueprint(registration_api_bp)

    return app
