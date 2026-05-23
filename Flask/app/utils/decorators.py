from functools import wraps
from flask import session, redirect, url_for, flash, request, jsonify
from app.repositories.user_repository import UserRepository
from app.extensions.firebase_config import auth_admin
from firebase_admin._auth_utils import UserNotFoundError
from app.services.auth_service import AuthService
import logging

logger = logging.getLogger(__name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json:
                return jsonify({'success': False, 'message': 'Não autenticado'}), 401
            flash("Por favor, faça login para acessar esta página.", "error")
            return redirect(url_for('login.login'))
            
        uid = session['user_id']
        
        # 1. Validação Server-Side: Busca forçada no Postgres (ignora cache da memória)
        user = UserRepository.get_user_by_id_forced(uid)
        
        # 2. Busca no Firebase
        firebase_exists = False
        try:
            if auth_admin:
                auth_admin.get_user(uid)
                firebase_exists = True
        except Exception as e:
            # Em caso de erro de rede, Firebase_exists = True para evitar deleção acidental
            # Mas se for UserNotFoundError, confirmamos que ele não existe
            if type(e).__name__ == 'UserNotFoundError':
                firebase_exists = False
            else:
                firebase_exists = True

        # 3. Sincronização Bidirecional
        if not user and firebase_exists:
            # Apagado do Postgres, mas vivo no Firebase -> Deleta do Firebase
            try:
                AuthService.delete_user_by_uid(uid)
                logger.info(f"SYNC BIDIRECIONAL: Usuário {uid} apagado do Firebase com sucesso.")
            except Exception as e:
                logger.error(f"SYNC BIDIRECIONAL ERRO NO FIREBASE: {e}", exc_info=True)
            firebase_exists = False
            
        elif user and not firebase_exists:
            # Apagado do Firebase, mas vivo no Postgres -> Deleta do Postgres
            try:
                UserRepository.delete_user_completely(uid)
            except Exception as e:
                logger.error(f"[AUTH][ERROR] Falha ao deletar usuário do Postgres completamente: {e}", exc_info=True)
            user = None

        if not user or not firebase_exists:
            session.clear()
            if request.is_json:
                return jsonify({'success': False, 'message': 'Sessão inválida'}), 401
            flash("Sua conta não foi encontrada ou foi excluída.", "error")
            return redirect(url_for('login.login'))
            
        return f(*args, **kwargs)
    return decorated_function

def agent_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if session.get('user_type') != 'health_agent':
            if request.is_json:
                return jsonify({'success': False, 'message': 'Acesso negado'}), 403
            flash("Acesso restrito a Agentes de Saúde.", "error")
            return redirect(url_for('index.index'))
        return f(*args, **kwargs)
    return decorated_function

def patient_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if session.get('user_type') != 'patient':
            if request.is_json:
                return jsonify({'success': False, 'message': 'Acesso negado'}), 403
            flash("Acesso restrito a Pacientes.", "error")
            return redirect(url_for('index.index'))
        return f(*args, **kwargs)
    return decorated_function
