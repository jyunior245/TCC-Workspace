from flask import Blueprint, render_template, session, redirect, url_for, request, jsonify
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService

patient_bp = Blueprint('patient', __name__, url_prefix='/patient')

from app.utils.decorators import patient_required

@patient_bp.route('/dashboard')
@patient_required
def dashboard():
    # Checa se o usuário está ativo
    if not session.get('is_active', False):
         return redirect(url_for('register.complete_registration'))
         
    # Fetch patient profile to get the patient_code and email
    user = UserRepository.get_user_by_id(session['user_id'])
    
    # --- Sincronização de E-mail (Verificação Pendente) ---
    try:
        from app.extensions.firebase_config import auth_admin
        if auth_admin:
            firebase_user = auth_admin.get_user(session['user_id'])
            # Se o e-mail no Firebase for diferente do Postgres e estiver verificado
            if firebase_user.email != user.email and firebase_user.email_verified:
                UserRepository.update_user_email(session['user_id'], firebase_user.email)
                user.email = firebase_user.email  # Atualiza o objeto em memória para refletir na UI imediatamente
    except Exception as e:
        print(f"Erro ao checar sincronização de e-mail com Firebase: {e}")
    # ------------------------------------------------------
    
    patient_code = user.patient_profile.patient_code if user and user.patient_profile else None
    
    # Checar se é um pseudo-email do Modo de Assistência
    is_pseudo_email = False
    if user and user.email and user.email.endswith('@tcchealth.com'):
        is_pseudo_email = True
         
    return render_template('patient_dashboard.html', patient_code=patient_code, is_pseudo_email=is_pseudo_email)

@patient_bp.route('/update_email', methods=['POST'])
@patient_required
def update_email():
    data = request.get_json()
    new_email = data.get('new_email')
    
    if not new_email or '@' not in new_email:
        return jsonify({'status': 'error', 'message': 'E-mail inválido.'}), 400
        
    try:
        user_id = session.get('user_id')
        
        # O fluxo de envio enviará um e-mail com um link para o usuário confirmar o novo endereço.
        # O banco de dados SÓ será atualizado na rota do dashboard após a verificação ocorrer com sucesso.
        AuthService.send_verification_for_new_email(user_id, new_email)
        
        return jsonify({'status': 'success', 'message': 'E-mail de verificação enviado! Verifique sua caixa de entrada.'}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@patient_bp.route('/check_email_sync', methods=['GET'])
@patient_required
def check_email_sync():
    """Endpoint para o frontend fazer polling e verificar se o e-mail foi confirmado e sincronizado"""
    user_id = session.get('user_id')
    user = UserRepository.get_user_by_id(user_id)
    
    try:
        from app.extensions.firebase_config import auth_admin
        if auth_admin:
            firebase_user = auth_admin.get_user(user_id)
            if firebase_user.email != user.email and firebase_user.email_verified:
                # O e-mail foi alterado e verificado no Firebase, vamos sincronizar no Postgres
                UserRepository.update_user_email(user_id, firebase_user.email)
                return jsonify({'synced': True}), 200
    except Exception as e:
        print(f"Erro no polling de e-mail: {e}")
        
    return jsonify({'synced': False}), 200
