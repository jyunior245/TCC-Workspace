from flask import Blueprint, url_for, redirect, session, flash, request, render_template
from app.extensions.google_auth import oauth
from app.repositories.user_repository import UserRepository
from app.models.user import User
from app.extensions.sql_alchemy import db
import threading
from app.services.ai_service import HealthAgent

agent = HealthAgent()

auth_google_bp = Blueprint('auth_google', __name__)

@auth_google_bp.route('/auth/google')
def login():
    redirect_uri = url_for('auth_google.callback', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@auth_google_bp.route('/auth/google/callback')
def callback():
    try:
        token = oauth.google.authorize_access_token()
        user_info = token.get('userinfo')
        if not user_info:
            flash("Falha ao obter informações do Google.")
            return redirect(url_for('login.login'))

        email = user_info.get('email')
        name = user_info.get('name')
        google_id = user_info.get('sub')
        
        # 1. Verificar se o usuário já existe pelo e-mail
        user = User.query.filter_by(email=email).first()
        
        if user:
            # Login do usuário existente
            session['user_id'] = user.id
            session['user_type'] = user.user_type
            session['user_name'] = user.name
            session['is_active'] = user.is_active
            
            if not user.is_active:
                flash("Por favor, complete seu cadastro.")
                return redirect(url_for('register.complete_registration'))
            
            if user.user_type == 'patient':
                return redirect(url_for('patient.dashboard'))
            elif user.user_type == 'health_agent':
                return redirect(url_for('agent.dashboard'))
        else:
            # 2. Novo usuário: Salvar dados temporários no session e pedir pra escolher o tipo
            # Ou podemos criar com um tipo padrão ou página intermediária.
            # Como o sistema exige user_type, vamos redirecionar para uma escolha de perfil.
            session['google_user'] = {
                'id': google_id,
                'email': email,
                'name': name
            }
            return redirect(url_for('auth_google.select_type'))

    except Exception as e:
        print(f"Callback error: {e}")
        flash("Erro durante a autenticação com o Google.")
        return redirect(url_for('login.login'))

@auth_google_bp.route('/auth/google/select-type', methods=['GET', 'POST'])
def select_type():
    if 'google_user' not in session:
        return redirect(url_for('login.login'))
    
    if request.method == 'POST':
        user_type = request.form.get('user_type')
        if user_type not in ['patient', 'health_agent']:
            flash("Tipo de usuário inválido.")
            return render_template('google_select_type.html')
        
        g_user = session['google_user']
        username = g_user['email'].split('@')[0] # Default username
        
        try:
            UserRepository.create_user(
                user_id=g_user['id'],
                name=g_user['name'],
                username=username,
                email=g_user['email'],
                user_type=user_type
            )
            
            # Login automático
            session['user_id'] = g_user['id']
            session['user_type'] = user_type
            session['user_name'] = g_user['name']
            session.pop('google_user', None)
            
            flash("Conta criada com Google! Agora, complete seu perfil.")
            return redirect(url_for('register.complete_registration'))
            
        except Exception as e:
            flash("Erro ao criar conta.")
            print(f"Error creating google user: {e}")
            
    return render_template('google_select_type.html')
