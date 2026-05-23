from flask import Blueprint, request, session, redirect, url_for, render_template, flash, jsonify
from app.services.auth_service import AuthService
from app.repositories.user_repository import UserRepository
from app.services.registration_service import RegistrationService
from app.utils.decorators import login_required

register_bp = Blueprint('register', __name__)

@register_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form["name"]
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        user_type = request.form["user_type"]

        try:
            # Verifica localmente se já existe antes de prosseguir
            if UserRepository.get_user_by_email(email):
                flash("Este e-mail já está em uso. Faça login ou tente outro.")
                return render_template('register.html')
            if UserRepository.get_user_by_username(username):
                flash("Nome de usuário indisponível. Escolha outro.")
                return render_template('register.html')

            # Cria o usuário no Firebase e no BD Local como Inativo
            firebase_user = AuthService.create_firebase_user(email, password)
            user_id = firebase_user['localId']
            
            UserRepository.create_user(user_id, name, username, email, user_type)

            session['user_id'] = user_id
            session['user_type'] = user_type
            session['user_name'] = name
            session['is_active'] = False
            session.permanent = True

            flash("Certo! Agora complete seus dados para finalizar a criação da conta.")
            return redirect(url_for('register.complete_registration'))

        except Exception as e:
            flash(f"Puxa, tivemos um problema: {str(e)}", "error")
            print(f"Registration error: {e}")

    return render_template('register.html')

@register_bp.route('/register/complete', methods=['GET', 'POST'])
@login_required
def complete_registration():
    user_type = session.get('user_type')

    if request.method == 'POST':
        user_id = session.get('user_id')
        
        try:
            if user_type == 'patient':
                RegistrationService.process_patient_completion(user_id, request.form)
            elif user_type == 'health_agent':
                RegistrationService.process_agent_completion(user_id, request.form)
            
            # Verifica se o e-mail foi confirmado
            success, next_step = RegistrationService.check_and_activate_user(user_id)
            if not success:
                session['is_active'] = False
                flash("Cadastro salvo! Por favor, verifique seu e-mail para continuar.")
                if user_type in ['patient', 'health_agent']:
                    return redirect(url_for('register.verify_pending'))
            else:
                session['is_active'] = True
                flash("Cadastro concluído com sucesso!")
                if user_type == 'patient':
                    return redirect(url_for('patient.dashboard'))
                elif user_type == 'health_agent':
                    return redirect(url_for('agent.dashboard'))

        except Exception as e:
            flash(f"Erro ao salvar dados complementares: {str(e)}", "error")
            print(f"Completion error: {str(e)}")

    # Checa se o usuário já preencheu o perfil, mas falta verificar e-mail
    user_id = session.get('user_id')
    profile_exists, is_active = RegistrationService.has_completed_profile(user_id, user_type)

    if profile_exists and not is_active:
        verified, _ = RegistrationService.verify_pending_status(user_id)
        if not verified:
            if user_type in ['patient', 'health_agent']:
                return redirect(url_for('register.verify_pending'))
        else:
            session['is_active'] = True
            if user_type == 'patient':
                return redirect(url_for('patient.dashboard'))
            elif user_type == 'health_agent':
                return redirect(url_for('agent.dashboard'))

    # Renderiza o template apropriado com base no tipo de usuário (primeira vez)
    if user_type == 'patient':
        return render_template('register_patient_complete.html')
    elif user_type == 'health_agent':
        return render_template('register_agent_complete.html')
    else:
        return redirect(url_for('index.index'))

@register_bp.route('/verify_pending', methods=['GET'])
@login_required
def verify_pending():
    user_id = session.get('user_id')
    user_type = session.get('user_type')
    
    verified, email_to_verify = RegistrationService.verify_pending_status(user_id)
    
    if verified:
        session['is_active'] = True
        if user_type == 'patient':
            return redirect(url_for('patient.dashboard'))
        elif user_type == 'health_agent':
            return redirect(url_for('agent.dashboard'))
        else:
            return redirect(url_for('index.index'))

    return render_template('verify_pending.html', email_to_verify=email_to_verify)

@register_bp.route('/send_registration_verification', methods=['POST'])
@login_required
def send_registration_verification():
    user_id = session.get('user_id')
    try:
        AuthService.send_initial_verification_email(user_id)
        return jsonify({'status': 'success'})
    except Exception as e:
        print(f"Erro ao enviar email de verificação: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 400

@register_bp.route('/check_registration_verification', methods=['GET'])
@login_required
def check_registration_verification():
    user_id = session.get('user_id')
    try:
        verified, _ = RegistrationService.verify_pending_status(user_id)
        if verified:
            session['is_active'] = True
            return jsonify({'verified': True})
            
    except Exception as e:
        print(f"Erro ao verificar email: {e}")
        
    return jsonify({'verified': False})
