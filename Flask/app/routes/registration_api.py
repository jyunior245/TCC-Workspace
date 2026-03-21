import requests
from flask import Blueprint, request, jsonify, session, url_for
from app.services.registration_agent import registration_agent
from app.repositories.user_repository import UserRepository
from app.services.voice_service import VoiceService
from app.services.auth_service import AuthService
import json

registration_api_bp = Blueprint('registration_api', __name__)
voice = VoiceService(init_pygame=False)

@registration_api_bp.route('/api/check_cpf', methods=['POST'])
def check_cpf():
    data = request.get_json()
    if not data or 'cpf' not in data:
        return jsonify({'error': 'CPF ausente'}), 400
    
    cpf = data['cpf']
    from app.models.patient import Patient
    exists = Patient.query.filter_by(cpf=cpf).first() is not None
    
    return jsonify({'exists': exists})

@registration_api_bp.route('/api/registration_chat/start', methods=['POST'])
def start_registration():
    # Inicia a sessão completamente zerada para um novo cadastro
    session['reg_state'] = {
        'current_step': 0,
        'collected_data': {}
    }
    
    first_question = registration_agent.get_question_for_step(0)
    audio_b64 = voice.generate_base64_audio(first_question)
    
    return jsonify({
        'response': first_question,
        'audio_b64': audio_b64,
        'status': 'IN_PROGRESS',
        'progress': 0
    })

@registration_api_bp.route('/api/registration_chat/cancel', methods=['POST'])
def cancel_registration():
    session.pop('reg_state', None)
    return jsonify({'status': 'CANCELLED'})

@registration_api_bp.route('/api/registration_chat/message', methods=['POST'])
def chat_message():
    data = request.get_json()
    user_message = data.get('message', '')
    
    state = session.get('reg_state')
    if not state:
        return jsonify({'error': 'Conversa não iniciada.'}), 400
        
    current_step = state['current_step']
    total_steps = len(registration_agent.fields_sequence)
    
    # Processa via AI
    extracted_val = registration_agent.process_step(user_message, current_step)
    
    field_key = registration_agent.get_field_key_for_step(current_step)
    
    # Salva o valor. Note que se a IA falhou em extrair de um input lixo, extraiu None.
    # Mas como o usuário respondeu algo, nós avançamos para não prendê-lo infinitamente.
    # (Poderíamos forçar re-perguntar, mas para evitar loop, assumimos o None se inválido)
    state['collected_data'][field_key] = extracted_val
    state['current_step'] += 1
    session.modified = True # Salva o state
    
    next_step = state['current_step']
    
    if next_step < total_steps:
        # Fazer próxima pergunta
        next_q = registration_agent.get_question_for_step(next_step)
        progress_pct = int((next_step / total_steps) * 100)
        
        audio_b64 = voice.generate_base64_audio(next_q)
        return jsonify({
            'response': next_q,
            'audio_b64': audio_b64,
            'status': 'IN_PROGRESS',
            'progress': progress_pct
        })
    else:
        # FIM! Processar persistência no BD final
        collected = state['collected_data']
    
        
        # --- AUTO CEP FETCH ---
        if 'cep' not in collected and 'state' in collected and 'city' in collected:
            state_uf = str(collected['state']).strip()
            city_name = str(collected['city']).strip()
            if state_uf and city_name:
                try:
                    import requests
                    resp = requests.get(f"https://viacep.com.br/ws/{state_uf}/{city_name}/Centro/json/", timeout=5)
                    if resp.status_code == 200:
                        data = resp.json()
                        if data and isinstance(data, list) and len(data) > 0:
                            collected['cep'] = data[0].get('cep', '').replace('-', '')
                except Exception as e:
                    print(f"Erro ao buscar CEP autônomo: {e}")
        # ----------------------
        
        import uuid
        unique_suffix = uuid.uuid4().hex[:8]
        
        # O .get() retorna None se a chave existir mas o valor for None. 
        # O "or" garante que peguemos o valor default nesse caso.
        email = collected.get('email') or f"voz_{unique_suffix}@example.com"
        password = collected.get('password') or "123Mudar!@" 
        name = collected.get('name') or 'Usuário Voz'
        
        try:
            # Verifica se e-mail já existe no banco local antes de ir pro Firebase
            from app.models.user import User
            if User.query.filter_by(email=email).first():
                msg_erro = "Esse e-mail já consta no nosso banco de dados. Tente fazer login ou use outro e-mail."
                return jsonify({'response': msg_erro, 'audio_b64': voice.generate_base64_audio(msg_erro), 'status': 'ERROR'})

            # 1. Firebase
            try:
                fb_user = AuthService.create_firebase_user(email, password)
                user_id = fb_user['localId']
            except Exception as e:
                msg_erro = f"Puxa, tivemos um erro ao salvar na nuvem: {str(e)}. Vamos tentar de novo mais tarde?"
                return jsonify({'response': msg_erro, 'audio_b64': voice.generate_base64_audio(msg_erro), 'status': 'ERROR'})

            # 2. Local BD User
            # Evitar conflito de unique_username caso duas pessoas usem prefixos de email iguais
            base_username = email.split('@')[0][:40]
            username = f"{base_username}_{unique_suffix}"
            UserRepository.create_user(user_id, name, username, email, 'patient')
            
            # 3. Local BD Profile
            patient_data = {k: v for k, v in collected.items() if k not in ['name', 'email', 'password'] and v is not None}
            UserRepository.create_patient_profile(user_id, patient_data)
            
            # 4. Login Session
            session['user_id'] = user_id
            session['user_type'] = 'patient'
            session['user_name'] = name
            session['is_active'] = True
            session.pop('reg_state', None)
            
            final_message = "Prontinho! Finalizamos o seu cadastro. Todas as informações foram salvas com sucesso e você está logado. Bem-vindo!"
            audio_b64 = voice.generate_base64_audio(final_message)
            
            return jsonify({
                'response': final_message,
                'audio_b64': audio_b64,
                'status': 'FINISHED',
                'progress': 100,
                'redirect_url': url_for('patient.dashboard')
            })
            
        except Exception as db_err:
             print(f"Erro BD final: {db_err}")
             import traceback
             with open("reg_error_trace.txt", "w") as f:
                 f.write(traceback.format_exc())
             return jsonify({'response': "Ocorreu um erro interno no banco de dados ao salvar seu cadastro final. Nossa equipe foi notificada.", 'status': 'ERROR'})

