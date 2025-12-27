from flask import Flask 
from app.routes.index import index_bp, voice_bp
# from app.models import init_db # Database management moved to NestJS/TypeORM mostly, but Flask might need read access.

def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.secret_key="supersecretkey"
    
    # init_db() # Disabled for now to avoid conflicts with NestJS/TypeORM migration

    app.register_blueprint(index_bp)
    app.register_blueprint(voice_bp)

    return app
