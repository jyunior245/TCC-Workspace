import logging
logger = logging.getLogger(__name__)
import requests
from flask import Blueprint, request, jsonify, session, url_for, current_app
from app.services.registration_agent import registration_agent
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
import json
import sys
import re
import os
import redis
from app.services.cnes_service import CNESService
from app.services.registration_service import RegistrationService
from app.models.patient import Patient


registration_api_bp = Blueprint('registration_api', __name__)

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = None
try:
    redis_client = redis.from_url(redis_url)
except Exception as e:
    logger.error(f"Erro ao conectar ao Redis: {e}", exc_info=True)

def get_reg_state(session_id):
    if not redis_client or not session_id: return None
    data = redis_client.get(f"reg_state:{session_id}")
    return json.loads(data) if data else None

def save_reg_state(session_id, state):
    if redis_client and session_id:
        redis_client.setex(f"reg_state:{session_id}", 3600, json.dumps(state))

def clear_reg_state(session_id):
    if redis_client and session_id:
        redis_client.delete(f"reg_state:{session_id}")


@registration_api_bp.route('/api/check_cpf', methods=['POST'])
def check_cpf():
    data = request.get_json()
    if not data or 'cpf' not in data:
        return jsonify({'error': 'CPF ausente'}), 400
    
    cpf = data['cpf']
    exists = Patient.query.filter_by(cpf=cpf).first() is not None
    
    return jsonify({'exists': exists})

@registration_api_bp.route('/api/ubs', methods=['GET'])
def get_ubs():
    ibge_code = request.args.get('ibge')
    logger.info(f"\n[ROUTE-LOG] Chamada para /api/ubs?ibge={ibge_code}")
    sys.stdout.flush()
    
    if not ibge_code:
        return jsonify({'error': 'Código IBGE ausente'}), 400

    ubs_list, fonte = CNESService.fetch_ubs(ibge_code)
    
    if ubs_list is None:
        return jsonify({'error': 'Erro ao consultar base de UBS'}), 500

    return jsonify({'ubs': ubs_list, 'fonte': fonte})

@registration_api_bp.route('/api/registration_chat/start', methods=['POST'])
def start_registration():
    # Inicia a sessão completamente zerada para um novo cadastro
    state = {
        'current_step': 0,
        'collected_data': {},
        'sub_state': 'ASKING',
        'temp_val': None
    }
    
    session_id = uuid.uuid4().hex
    session['reg_session_id'] = session_id
    save_reg_state(session_id, state)
    
    first_question = registration_agent.get_question_for_step(0)
    audio_b64 = current_app.extensions['services'].voice_service.generate_base64_audio(first_question)
    
    return jsonify({
        'response': first_question,
        'audio_b64': audio_b64,
        'status': 'IN_PROGRESS',
        'progress': 0
    })

@registration_api_bp.route('/api/registration_chat/cancel', methods=['POST'])
def cancel_registration():
    session_id = session.pop('reg_session_id', None)
    if session_id:
        clear_reg_state(session_id)
    return jsonify({'status': 'CANCELLED'})

@registration_api_bp.route('/api/registration_chat/message', methods=['POST'])
def chat_message():
    data = request.get_json()
    user_message = data.get('message', '')
    
    session_id = session.get('reg_session_id')
    state = get_reg_state(session_id)
    if not state:
        return jsonify({'error': 'Conversa não iniciada.'}), 400
        
    result = registration_agent.handle_chat_interaction(user_message, state, current_app.extensions['services'].voice_service)
    
    if result.get('state_changed'):
        save_reg_state(session_id, state)
        session.modified = True
        
    if not result.get('continue'):
        return jsonify({
            'response': result.get('response', ''),
            'audio_b64': result.get('audio_b64', ''),
            'status': result.get('status', 'IN_PROGRESS'),
            'progress': result.get('progress', 0)
        })
    
    next_step = state['current_step']
    total_steps = len(registration_agent.fields_sequence)
    
    if next_step < total_steps:
        # Fazer próxima pergunta
        next_q = registration_agent.get_question_for_step(next_step)
        progress_pct = int((next_step / total_steps) * 100)
        
        audio_b64 = current_app.extensions['services'].voice_service.generate_base64_audio(next_q)
        return jsonify({
            'response': next_q,
            'audio_b64': audio_b64,
            'status': 'IN_PROGRESS',
            'progress': progress_pct
        })
    else:
        # FIM! Processar persistência no BD final
        collected = state['collected_data']
    
        response_json = RegistrationService.finalize_voice_registration(
            collected, 
            session, 
            session_id, 
            current_app.extensions['services'].voice_service
        )
        
        # Limpa o state
        session.pop('reg_session_id', None)
        clear_reg_state(session_id)
        
        return response_json


@registration_api_bp.route('/api/profissional_info', methods=['GET'])
def get_profissional_info():
    """
    Busca informações do profissional de saúde (CBO).
    """
    cpf = request.args.get('cpf')
    if not cpf:
        return jsonify({'error': 'CPF ausente'}), 400

    # =========================================================================
    # BLOCO DE TESTES (MOCK) - ATIVO
    # Descomente o bloco CNES abaixo e comente este bloco MOCK quando for para produção.
    # =========================================================================
    '''return jsonify({
        'cbo': '5151-05',
        'cbo_descricao': 'Agente comunitário de saúde',
        'microarea': '', # Inexistente em API pública, requer input manual do ACS
        'fonte': 'mock_tests'
    })'''

    # =========================================================================
    # BLOCO CNES SOAP - INATIVO (Descomente quando o sistema estiver pronto)
    # =========================================================================
    
    # =========================================================================
    # BLOCO CNES SOAP - INATIVO (Descomente quando o sistema estiver pronto)
    # =========================================================================
    
    info = CNESService.get_profissional_info(cpf)
    return jsonify(info)
    
