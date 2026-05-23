from flask import Blueprint, flash, request, session, redirect, url_for, render_template, jsonify, current_app
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from app.services.auth_service import AuthService
from app.repositories.user_repository import UserRepository
import threading
from app.services.ai_service import HealthAgent
from app.utils.decorators import login_required
from app.services.registration_service import RegistrationService

agent = HealthAgent()

index_bp = Blueprint('index', __name__)
login_bp = Blueprint('login', __name__)
register_bp = Blueprint('register', __name__)

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
            print(f"Login error: {e}")

    return render_template('login.html')

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

@index_bp.route('/recover-access/<token>', methods=['GET', 'POST'])
def recover_access(token):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        # Link expira em 30 minutos (1800 segundos)
        data = serializer.loads(token, max_age=1800)
    except SignatureExpired:
        flash("O link de recuperação expirou. Solicite um novo ao Agente de Saúde.", "error")
        return redirect(url_for('login.login'))
    except BadSignature:
        flash("Link de recuperação inválido.", "error")
        return redirect(url_for('login.login'))
        
    patient_id = data.get('patient_id')
    if not patient_id or data.get('action') != 'recover_password':
        flash("Link inválido.", "error")
        return redirect(url_for('login.login'))

    if request.method == 'POST':
        cpf = request.form.get('cpf')
        # dob format from HTML date input is usually YYYY-MM-DD
        dob_str = request.form.get('dob')
        new_password = request.form.get('password')
        
        if not cpf or not dob_str or not new_password:
            flash("Todos os campos são obrigatórios.", "error")
            return render_template('patient_recovery.html', token=token)
            
        # Clean CPF
        cpf = ''.join(filter(str.isdigit, cpf))
        
        # Verify against DB
        patient = UserRepository.get_user_by_id(patient_id)
        if not patient or not patient.patient_profile:
            flash("Paciente não encontrado.", "error")
            return redirect(url_for('login.login'))
            
        # Parse DB values
        db_cpf = ''.join(filter(str.isdigit, patient.patient_profile.cpf)) if patient.patient_profile.cpf else ""
        db_dob = patient.patient_profile.date_of_birth.strftime('%Y-%m-%d') if patient.patient_profile.date_of_birth else ""
        
        # Handle possible DD/MM/YYYY format if browser fell back to text input
        if dob_str and '/' in dob_str:
            parts = dob_str.split('/')
            if len(parts) == 3:
                # Assuming DD/MM/YYYY
                dob_str = f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"

        if cpf != db_cpf or dob_str != db_dob:
            flash("Dados incorretos. A recuperação de senha exige confirmação exata da identidade.", "error")
            return render_template('patient_recovery.html', token=token)
            
        # All good, update password
        try:
            AuthService.admin_update_user_password(patient_id, new_password)
            flash("Senha alterada com sucesso! Você já pode entrar com sua nova senha.", "success")
            return redirect(url_for('login.login'))
        except Exception as e:
            flash(str(e), "error")
            
    return render_template('patient_recovery.html', token=token)

@index_bp.route('/delete_account', methods=['POST'])
@login_required
def delete_account():
    user_id = session['user_id']
    try:
        # 1. Deleta do Banco de Dados local e histórico
        success, message = UserRepository.delete_user_completely(user_id)
        if not success:
            return jsonify({'status': 'error', 'message': message}), 400
            
        # 2. Deleta do Firebase via Admin SDK (limpa até vínculos Google OAuth)
        AuthService.delete_user_by_uid(user_id)
        
        # 3. Limpa sessão do Flask
        session.clear()
        
        return jsonify({'status': 'success', 'message': 'Conta e dados apagados com sucesso.', 'redirect_url': url_for('login.login')})
    except Exception as e:
        print(f"Erro ao deletar conta: {e}")
        return jsonify({'status': 'error', 'message': f'Erro ao deletar conta: {str(e)}'}), 500

@index_bp.route('/')
def index():
    return redirect(url_for('login.login'))

