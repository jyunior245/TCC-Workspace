from app.repositories.user_repository import UserRepository
from app.extensions.firebase_config import auth_admin
from app.extensions.sql_alchemy import db
from app.models.user import User

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
