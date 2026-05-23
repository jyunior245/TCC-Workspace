from flask import Blueprint, request, session, redirect, url_for, render_template, flash
from app.services.auth_service import AuthService
from app.repositories.user_repository import UserRepository

login_bp = Blueprint('login', __name__)

@login_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form["email"]
        password = request.form["password"]

        try:
            # 1. Authentica com o firebase 
            user = AuthService.login_firebase_user(email, password)
            user_id = user['localId']
            
            # 2. Pega os dados do usuário no banco de dados local
            user_data = UserRepository.get_user_by_id(user_id)
            
            if user_data:
                session['user_id'] = user_id
                session['user_type'] = user_data.user_type
                session['user_name'] = user_data.name
                session['is_active'] = user_data.is_active
                
                # Checa se o usuário está ativo
                if not user_data.is_active:
                    flash("Por favor, complete seu cadastro.")
                    return redirect(url_for('register.complete_registration'))

                if user_data.user_type == 'patient':
                    return redirect(url_for('patient.dashboard'))
                elif user_data.user_type == 'health_agent':
                    return redirect(url_for('agent.dashboard'))
                else:
                    return redirect(url_for('index.index'))
            else:
                 flash("Usuário não encontrado no banco de dados local.")

        except Exception as e:
            flash(f"Não conseguimos entrar: {str(e)}", "error")
            print(f"Login error: {e}")

    return render_template('login.html')

@login_bp.route('/logout')
def logout():
    session.clear()
    flash("Sessão encerrada.")
    return redirect(url_for('login.login'))

@login_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        if not email:
            flash("Por favor, informe seu e-mail.", "error")
        else:
            try:
                AuthService.send_password_reset_email(email)
                flash("Se esse e-mail estiver cadastrado, você receberá um link para redefinir sua senha.", "success")
                return redirect(url_for('login.login'))
            except Exception as e:
                # Ocultar o erro real por segurança, mas se quiser pode mostrar str(e)
                flash("Houve um problema ao enviar o e-mail de recuperação. Tente novamente.", "error")
    return render_template('forgot_password.html')
