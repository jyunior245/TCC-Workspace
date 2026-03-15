from flask import Blueprint, flash, request, session, redirect, url_for, render_template, jsonify
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
                # Função auxiliar para processar listas como strings separadas por vírgula
                def get_csv_list(field_name):
                    items = request.form.getlist(field_name)
                    return ",".join(items) if items else None
                
                def get_int(field_name):
                    val = request.form.get(field_name)
                    return int(val) if val and val.isdigit() else None

                # Captura campos simples e limpa string vazia para nulo
                data = {
                    # Identificação Básica
                    'date_of_birth': request.form.get('date_of_birth') or None,
                    'gender': request.form.get('gender') or None,
                    'cpf': request.form.get('cpf') or None,
                    'rg': request.form.get('rg') or None,
                    'marital_status': request.form.get('marital_status') or None,
                    'nationality': request.form.get('nationality') or None,
                    'education_level': request.form.get('education_level') or None,
                    'work_status': request.form.get('work_status') or None,
                    'has_whatsapp': request.form.get('has_whatsapp') == 'yes',
                    
                    # Cuidador / Emergência
                    'caregiver_name': request.form.get('caregiver_name') or None,
                    'caregiver_phone': request.form.get('caregiver_phone') or None,
                    
                    # Endereço e Moradia
                    'cep': request.form.get('cep') or None,
                    'street': request.form.get('street') or None,
                    'number': request.form.get('number') or None,
                    'neighborhood': request.form.get('neighborhood') or None,
                    'city': request.form.get('city') or None,
                    'state': request.form.get('state') or None,
                    'reference_point': request.form.get('reference_point') or None,
                    'zone': request.form.get('zone') or None,
                    'housing_type': request.form.get('housing_type') or None,
                    'housing_status': request.form.get('housing_status') or None,
                    'num_residents': get_int('num_residents'),
                    'has_potable_water': request.form.get('has_potable_water') == 'yes',
                    'has_sanitation': request.form.get('has_sanitation') == 'yes',
                    'has_garbage_collection': request.form.get('has_garbage_collection') == 'yes',
                    'has_electricity': request.form.get('has_electricity') == 'yes',
                    'has_internet': request.form.get('has_internet') == 'yes',
                    
                    # Socioeconômico
                    'income': request.form.get('income') or None,
                    'income_source': request.form.get('income_source') or None,
                    'social_benefits': get_csv_list('social_benefits'),
                    'food_insecurity': request.form.get('food_insecurity') or None,
                    'financially_dependent': request.form.get('financially_dependent') == 'yes',
                    
                    # Saúde Geral e Histórico
                    'chronic_conditions': get_csv_list('chronic_conditions'),
                    # 'past_surgeries': get_csv_list('past_surgeries'),
                    # 'recent_hospitalizations': get_csv_list('recent_hospitalizations'),
                    # 'medication_allergies': get_csv_list('medication_allergies'),
                    # 'takes_medication': request.form.get('takes_medication') == 'yes',
                    # 'medication_adherence': request.form.get('medication_adherence') or None,
                    
                    # Indicadores Físicos
                    'weight': request.form.get('weight') or None,
                    'height': request.form.get('height') or None,
                    'mobility_status': request.form.get('mobility_status') or None,
                    'functional_capacity': get_csv_list('functional_capacity'),
                    
                    # Saúde Mental e Cognitiva
                    'perceived_memory': request.form.get('perceived_memory') or None,
                    'mental_diagnoses': get_csv_list('mental_diagnoses'),
                    
                    # Hábitos de Vida
                    'physical_activity_frequency': request.form.get('physical_activity_frequency') or None,
                    'sleep_quality': request.form.get('sleep_quality') or None,
                    'alcohol_consumption': request.form.get('alcohol_consumption') or None,
                    'smoking': request.form.get('smoking') or None,
                    'diet_quality': request.form.get('diet_quality') or None,
                    
                    # Rede de Apoio
                    'lives_alone': request.form.get('lives_alone') == 'yes',
                    'has_close_family': request.form.get('has_close_family') == 'yes',
                    'frequent_visits': request.form.get('frequent_visits') == 'yes',
                    'community_activities': request.form.get('community_activities') == 'yes',
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

@login_bp.route('/logout')
def logout():
    session.clear()
    flash("Sessão encerrada.")
    return redirect(url_for('login.login'))


@index_bp.route('/')
def index():
    return redirect(url_for('login.login'))

