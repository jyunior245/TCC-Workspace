from flask import Blueprint, flash, request, session, redirect, url_for, render_template, jsonify, current_app
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from app.services.auth_service import AuthService
from app.repositories.user_repository import UserRepository
import threading
from app.utils.decorators import login_required

index_bp = Blueprint('index', __name__)

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

