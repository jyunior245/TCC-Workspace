from flask import Blueprint, flash, request, session, redirect, url_for
from flask import render_template
import bcrypt
import requests
from app.extensions import db
from app.models.user import User

index_bp = Blueprint('index', __name__)
login_bp = Blueprint('login', __name__)
register_bp = Blueprint('register', __name__)


@login_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()

        if user and bcrypt.checkpw(password.encode(), user.password.encode()):
            session['user_id'] = user.id
            session['user_type'] = user.user_type
            
            if user.user_type == 'patient':
                return redirect(url_for('patient.dashboard'))
            elif user.user_type == 'health_agent':
                return redirect(url_for('agent.dashboard'))
            else:
                return render_template("index.html") # Default fallback

        flash("Invalid Credentials")

    return render_template('login.html')

@register_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form["name"]
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        user_type = request.form["user_type"]

        hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        
        new_user = User(
            name=name, 
            username=username, 
            email=email, 
            password=hashed_password,
            user_type=user_type
        )
        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('login.login'))

    return render_template('register.html')

@index_bp.route('/')
def index():
    print("Index route accessed")
    return "Hello, World!"

