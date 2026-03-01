from app.extensions.sql_alchemy import db
from app.models.user import User
from app.models.chat_history import ChatHistory

def init_db():
    db.create_all()
