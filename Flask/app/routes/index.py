from flask import Blueprint, flash, request, session, redirect, url_for, render_template, jsonify, current_app
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from app.services.auth_service import AuthService
from app.repositories.user_repository import UserRepository
import threading
from app.services.ai_service import HealthAgent
from app.utils.decorators import login_required

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
            from app.models.user import User
            if User.query.filter_by(email=email).first():
                flash("Este e-mail já está em uso. Faça login ou tente outro.")
                return render_template('register.html')
            if User.query.filter_by(username=username).first():
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
        created_fb = False
        firebase_user = None
        user_id = session.get('user_id')
        
        try:
            if user_type == 'patient':
                # Função auxiliar para processar listas como strings separadas por vírgula
                def get_csv_list(field_name):
                    items = request.form.getlist(field_name)
                    return ",".join(items) if items else None
                
                def get_int(field_name):
                    val = request.form.get(field_name)
                    return int(val) if val and val.isdigit() else None

                # Captura campos simples e limpa string vazia para nulo
                data = {
                    'date_of_birth': request.form.get('date_of_birth') or None,
                    'gender': request.form.get('gender') or None,
                    'cpf': request.form.get('cpf') or None,
                    'marital_status': request.form.get('marital_status') or None,
                    'nationality': request.form.get('nationality') or None,
                    'education_level': request.form.get('education_level') or None,
                    
                    'caregiver_name': request.form.get('caregiver_name') or None,
                    'caregiver_phone': request.form.get('caregiver_phone') or None,
                    
                    'cep': request.form.get('cep') or None,
                    'street': request.form.get('street') or None,
                    'number': request.form.get('number') or None,
                    'neighborhood': request.form.get('neighborhood') or None,
                    'city': request.form.get('city') or None,
                    'state': request.form.get('state') or None,
                    'zone': request.form.get('zone') or None,
                    
                    'num_residents': get_int('num_residents'),
                    'has_potable_water': request.form.get('has_potable_water') == 'yes',
                    'has_sanitation': request.form.get('has_sanitation') == 'yes',
                    'has_garbage_collection': request.form.get('has_garbage_collection') == 'yes',
                    'has_electricity': request.form.get('has_electricity') == 'yes',
                    'has_internet': request.form.get('has_internet') == 'yes',
                    
                    'financially_dependent': request.form.get('financially_dependent') == 'yes',
                    
                    'chronic_conditions': get_csv_list('chronic_conditions'),
                    
                    'mobility_status': request.form.get('mobility_status') or None,
                    'can_bathe_alone': request.form.get('can_bathe_alone') == 'yes',
                    'can_dress_alone': request.form.get('can_dress_alone') == 'yes',
                    'can_eat_alone': request.form.get('can_eat_alone') == 'yes',
                    
                    'perceived_memory': request.form.get('perceived_memory') or None,
                    'mental_diagnoses': get_csv_list('mental_diagnoses'),
                    
                    'physical_activity_frequency': request.form.get('physical_activity_frequency') or None,
                    'sleep_quality': request.form.get('sleep_quality') or None,
                    'alcohol_consumption': request.form.get('alcohol_consumption') or None,
                    'smoking': request.form.get('smoking') or None,
                    
                    'frequent_visits': request.form.get('frequent_visits') == 'yes',
                    'community_activities': request.form.get('community_activities') == 'yes',
                }
            
                # Usuário já foi criado no BD local no passo 1.
                UserRepository.create_patient_profile(user_id, data)
                
            elif user_type == 'health_agent':
                data = {
                    'gender': request.form.get('gender'),
                    'phone_number': request.form.get('phone_number'),
                    'cep': request.form.get('cep'),
                    'state': request.form.get('state'),
                    'municipio': request.form.get('municipio'),
                    'ubs': request.form.get('ubs'),
                    'microarea': request.form.get('microarea'),
                    'cbo': request.form.get('cbo'),
                    'simet_codigo_municipio': request.form.get('simet_codigo_municipio')
                }
                
                print(f"[DEBUG] Criando perfil de ACS para user_id: {user_id}")
                UserRepository.create_agent_profile(user_id, data)
            
            flash("Cadastro concluído com sucesso!")
            
            # Redireciona para o dashboard do usuário
            session['is_active'] = True
            if user_type == 'patient':
                return redirect(url_for('patient.dashboard'))
            elif user_type == 'health_agent':
                return redirect(url_for('agent.dashboard'))

        except Exception as e:
            flash(f"Erro ao salvar dados complementares: {str(e)}", "error")
            print(f"Completion error: {str(e)}")
            import traceback
            traceback.print_exc()

    # Renderiza o template apropriado com base no tipo de usuário
    if user_type == 'patient':
        return render_template('register_patient_complete.html')
    elif user_type == 'health_agent':
        return render_template('register_agent_complete.html')
    else:
        return redirect(url_for('index.index'))

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

