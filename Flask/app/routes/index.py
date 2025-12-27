from flask import Blueprint, flash, request, session
from flask import render_template
import bcrypt
import requests
from app.database import get_db_connection

index_bp = Blueprint('index', __name__)
login_bp = Blueprint('login', __name__)
register_bp = Blueprint('register', __name__)

@index_bp.route('/')
def index():
    print("Index route accessed")
    return "Hello, World!"

@login_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT id, password FROM users WHERE email=%s", (email,))
        user = cur.fetchone()

        cur.close()
        conn.close()

        if user and bcrypt.checkpw(password.encode(), user[1].encode()):
            session['user_id'] = user[0]
            return render_template("index.html")
        flash("Invalid Credentials")

    return render_template('login.html')

@register_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form["name"]
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            "INSERT INTO users (name, username, email, password) VALUES (%s, %s, %s, %s)",
            (name, username, email, hashed_password)
        )

        conn.commit()
        cur.close() 
        conn.close()

        return render_template('login.html')

    return render_template('register.html')
