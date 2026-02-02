from flask import Flask 
import os
from app.routes.index import index_bp
from app.routes.index import login_bp
from app.routes.index import register_bp
from app.routes.patient import patient_bp
from app.routes.agent import agent_bp
from app.extensions import db
from app.models import init_db

def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.secret_key="supersecretkey"

    # Database Configuration
    db_host = os.getenv("DB_HOST", "localhost")
    db_user = os.getenv("POSTGRES_USER", "postgres")
    db_password = os.getenv("POSTGRES_PASSWORD", "password")
    db_name = os.getenv("DATABASE_NAME", "postgres")
    
    app.config['SQLALCHEMY_DATABASE_URI'] = f"postgresql://{db_user}:{db_password}@{db_host}:5432/{db_name}"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    
    with app.app_context():
        init_db()

    app.register_blueprint(index_bp)
    app.register_blueprint(login_bp)
    app.register_blueprint(register_bp)
    app.register_blueprint(patient_bp)
    app.register_blueprint(agent_bp)

    return app

