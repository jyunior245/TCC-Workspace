
from flask import Blueprint, flash, request, session, redirect, url_for, render_template
from app.services.auth_service import AuthService
from app.repositories.user_repository import UserRepository

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
            flash(f"Falha no login: {str(e)}")
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
            # 1. Cria o usuário no Firebase Authentication
            user = AuthService.create_firebase_user(email, password)
            user_id = user['localId']
            
            # 2. Cria o usuário no banco de dados local (pendente de ativação)
            try:
                UserRepository.create_user(user_id, name, username, email, user_type)
                
                # Auto-login para o usuário recém-criado
                session['user_id'] = user_id
                session['user_type'] = user_type
                session['user_name'] = name
                
                flash("Conta criada! Por favor, complete seu cadastro.")
                return redirect(url_for('register.complete_registration'))
                
            except Exception as db_error:
                # Rollback Firebase
                if 'idToken' in user:
                    AuthService.delete_firebase_user(user['idToken'])
                print(f"Database error: {db_error}")
                flash("Falha no registro (Erro de Banco de Dados). Tente novamente.")

        except Exception as e:
            flash(f"Falha no registro: {str(e)}")
            print(f"Registration error: {e}")

    return render_template('register.html')

@register_bp.route('/register/complete', methods=['GET', 'POST'])
def complete_registration():
    if 'user_id' not in session:
        return redirect(url_for('login.login'))
    
    user_type = session.get('user_type')
    user_id = session.get('user_id')

    if request.method == 'POST':
        try:
            if user_type == 'patient':
                data = {
                    'education_level': request.form.get('education_level'),
                    'income': request.form.get('income'),
                    'housing_conditions': request.form.get('housing_conditions'),
                    'sanitation_access': request.form.get('sanitation_access') == 'on',
                    'work_status': request.form.get('work_status'),
                    'family_context': request.form.get('family_context')
                }
                UserRepository.create_patient_profile(user_id, data)
                
            elif user_type == 'health_agent':
                data = {
                    'professional_training': request.form.get('professional_training'),
                    'institutional_link': request.form.get('institutional_link'),
                    'area_of_activity': request.form.get('area_of_activity'),
                    'service_time': request.form.get('service_time'),
                    'health_unit': request.form.get('health_unit'),
                    'territory_served': request.form.get('territory_served')
                }
                UserRepository.create_agent_profile(user_id, data)
            
            flash("Cadastro concluído com sucesso!")
            
            # Redireciona para o dashboard do usuário
            session['is_active'] = True
            if user_type == 'patient':
                return redirect(url_for('patient.dashboard'))
            elif user_type == 'health_agent':
                return redirect(url_for('agent.dashboard'))

        except Exception as e:
            flash(f"Erro ao salvar dados complementares: {str(e)}")
            print(f"Completion error: {e}")

    # Renderiza o template apropriado com base no tipo de usuário
    if user_type == 'patient':
        return render_template('register_patient_complete.html')
    elif user_type == 'health_agent':
        return render_template('register_agent_complete.html')
    else:
        return redirect(url_for('index.index'))

@index_bp.route('/')
def index():
    return "Hello, World!"
