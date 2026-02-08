from app.extensions.sql_alchemy import db

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.String(128), primary_key=True) # Firebase UID
    name = db.Column(db.String(100))
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    user_type = db.Column(db.String(20), nullable=False)  # "Patient" or "Health Agent"
    is_active = db.Column(db.Boolean, default=False) # Apenas usuários ativos após registro complementar

    def __repr__(self):
        return f'<User {self.username}>'
