from app.extensions import db
from app.models.user import User

def init_db():
    db.create_all()
