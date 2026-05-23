from app.repositories.user_repository import UserRepository
from app.extensions.firebase_config import auth_admin
from app.extensions.sql_alchemy import db
from app.models.user import User
import logging
import uuid
import requests
from flask import jsonify, url_for, current_app

class RegistrationService:
    @staticmethod
    def process_patient_completion(user_id, form_data):
        def get_csv_list(field_name):
            items = form_data.getlist(field_name) if hasattr(form_data, 'getlist') else []
            return ",".join(items) if items else None
        
        def get_int(field_name):
            val = form_data.get(field_name)
            return int(val) if val and val.isdigit() else None

        data = {
            'date_of_birth': form_data.get('date_of_birth') or None,
            'gender': form_data.get('gender') or None,
            'cpf': form_data.get('cpf') or None,
            'marital_status': form_data.get('marital_status') or None,
            'nationality': form_data.get('nationality') or None,
            'education_level': form_data.get('education_level') or None,
            
            'caregiver_name': form_data.get('caregiver_name') or None,
            'caregiver_phone': form_data.get('caregiver_phone') or None,
            
            'cep': form_data.get('cep') or None,
            'street': form_data.get('street') or None,
            'number': form_data.get('number') or None,
            'neighborhood': form_data.get('neighborhood') or None,
            'city': form_data.get('city') or None,
            'state': form_data.get('state') or None,
            'zone': form_data.get('zone') or None,
            
            'num_residents': get_int('num_residents'),
            'has_potable_water': form_data.get('has_potable_water') == 'yes',
            'has_sanitation': form_data.get('has_sanitation') == 'yes',
            'has_garbage_collection': form_data.get('has_garbage_collection') == 'yes',
            'has_electricity': form_data.get('has_electricity') == 'yes',
            'has_internet': form_data.get('has_internet') == 'yes',
            
            'financially_dependent': form_data.get('financially_dependent') == 'yes',
            
            'chronic_conditions': get_csv_list('chronic_conditions'),
            
            'mobility_status': form_data.get('mobility_status') or None,
            'can_bathe_alone': form_data.get('can_bathe_alone') == 'yes',
            'can_dress_alone': form_data.get('can_dress_alone') == 'yes',
            'can_eat_alone': form_data.get('can_eat_alone') == 'yes',
            
            'perceived_memory': form_data.get('perceived_memory') or None,
            'mental_diagnoses': get_csv_list('mental_diagnoses'),
            
            'physical_activity_frequency': form_data.get('physical_activity_frequency') or None,
            'sleep_quality': form_data.get('sleep_quality') or None,
            'alcohol_consumption': form_data.get('alcohol_consumption') or None,
            'smoking': form_data.get('smoking') or None,
            
            'frequent_visits': form_data.get('frequent_visits') == 'yes',
            'community_activities': form_data.get('community_activities') == 'yes',
        }
    
        UserRepository.create_patient_profile(user_id, data)

    @staticmethod
    def process_agent_completion(user_id, form_data):
        data = {
            'gender': form_data.get('gender'),
            'phone_number': form_data.get('phone_number'),
            'cep': form_data.get('cep'),
            'state': form_data.get('state'),
            'municipio': form_data.get('municipio'),
            'ubs': form_data.get('ubs'),
            'microarea': form_data.get('microarea'),
            'cbo': form_data.get('cbo'),
            'simet_codigo_municipio': form_data.get('simet_codigo_municipio')
        }
        
        UserRepository.create_agent_profile(user_id, data)

    @staticmethod
    def check_and_activate_user(user_id):
        firebase_user = auth_admin.get_user(user_id)
        is_pseudo_email = firebase_user.email and firebase_user.email.endswith('@tcchealth.com')
        
        if not is_pseudo_email and not firebase_user.email_verified:
            # Reverte a ativação
            user = UserRepository.get_user_by_id(user_id)
            if user:
                user.is_active = False
                db.session.commit()
            return False, "verify_pending"
        else:
            user = UserRepository.get_user_by_id(user_id)
            if user:
                user.is_active = True
                db.session.commit()
            return True, "dashboard"

    @staticmethod
    def verify_pending_status(user_id):
        firebase_user = auth_admin.get_user(user_id)
        is_pseudo_email = firebase_user.email and firebase_user.email.endswith('@tcchealth.com')
        
        if is_pseudo_email or firebase_user.email_verified:
            user = UserRepository.get_user_by_id(user_id)
            if user:
                user.is_active = True
                db.session.commit()
            return True, firebase_user.email
        return False, firebase_user.email

    @staticmethod
    def has_completed_profile(user_id, user_type):
        user = UserRepository.get_user_by_id(user_id)
        if not user:
            return False, False
            
        profile_exists = False
        if user_type == 'patient' and user.patient_profile:
            profile_exists = True
        elif user_type == 'health_agent' and user.agent_profile:
            profile_exists = True
            
        return profile_exists, user.is_active

    @staticmethod
    def finalize_voice_registration(collected_data, session, session_id, voice_service):

        logger = logging.getLogger(__name__)

        # --- AUTO CEP FETCH ---
        if 'cep' not in collected_data and 'state' in collected_data and 'city' in collected_data:
            state_uf = str(collected_data['state']).strip()
            city_name = str(collected_data['city']).strip()
            if state_uf and city_name:
                try:
                    resp = requests.get(f"https://viacep.com.br/ws/{state_uf}/{city_name}/Centro/json/", timeout=5)
                    if resp.status_code == 200:
                        data = resp.json()
                        if data and isinstance(data, list) and len(data) > 0:
                            collected_data['cep'] = data[0].get('cep', '').replace('-', '')
                except Exception as e:
                    logger.error(f"Erro ao buscar CEP autônomo: {e}", exc_info=True)
        # ----------------------
        
        unique_suffix = uuid.uuid4().hex[:8]
        
        email = collected_data.get('email') or f"voz_{unique_suffix}@example.com"
        password = collected_data.get('password') or "123Mudar!@" 
        name = collected_data.get('name') or 'Usuário Voz'
        
        try:
            # Verifica se e-mail já existe no banco local antes de ir pro Firebase
            if User.query.filter_by(email=email).first():
                msg_erro = "Esse e-mail já consta no nosso banco de dados. Tente fazer login ou use outro e-mail."
                return jsonify({'response': msg_erro, 'audio_b64': voice_service.generate_base64_audio(msg_erro), 'status': 'ERROR'})

            # 1. Firebase
            try:
                from app.services.auth_service import AuthService
                fb_user = AuthService.create_firebase_user(email, password)
                user_id = fb_user['localId']
            except Exception as e:
                msg_erro = f"Puxa, tivemos um erro ao salvar na nuvem: {str(e)}. Vamos tentar de novo mais tarde?"
                return jsonify({'response': msg_erro, 'audio_b64': voice_service.generate_base64_audio(msg_erro), 'status': 'ERROR'})

            # 2. Local BD User
            base_username = email.split('@')[0][:40]
            username = f"{base_username}_{unique_suffix}"
            UserRepository.create_user(user_id, name, username, email, 'patient')
            
            # 3. Local BD Profile
            patient_data = {k: v for k, v in collected_data.items() if k not in ['name', 'email', 'password'] and v is not None}
            UserRepository.create_patient_profile(user_id, patient_data)
            
            # 4. Login Session
            session['user_id'] = user_id
            session['user_type'] = 'patient'
            session['user_name'] = name
            session['is_active'] = True
            
            final_message = "Prontinho! Finalizamos o seu cadastro. Todas as informações foram salvas com sucesso e você está logado. Bem-vindo!"
            audio_b64 = voice_service.generate_base64_audio(final_message)
            
            return jsonify({
                'response': final_message,
                'audio_b64': audio_b64,
                'status': 'FINISHED',
                'progress': 100,
                'redirect_url': url_for('patient.dashboard')
            })
            
        except Exception as db_err:
             logger.error(f"Erro BD final: {db_err}", exc_info=True)
             return jsonify({'response': "Ocorreu um erro interno no banco de dados ao salvar seu cadastro final. Nossa equipe foi notificada.", 'status': 'ERROR'})
