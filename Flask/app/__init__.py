from flask import Flask 
from app.routes.index import index_bp
from app.routes.index import login_bp
from app.routes.index import register_bp
from app.models import init_db

def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.secret_key="supersecretkey"
    
    init_db()

    app.register_blueprint(index_bp)
    app.register_blueprint(login_bp)
    app.register_blueprint(register_bp)

    return app
