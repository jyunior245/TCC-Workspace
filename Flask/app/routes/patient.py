from flask import Blueprint, render_template, session, redirect, url_for
from app.repositories.user_repository import UserRepository

patient_bp = Blueprint('patient', __name__, url_prefix='/patient')

@patient_bp.route('/dashboard')
def dashboard():
    if 'user_id' not in session or session.get('user_type') != 'patient':
        return redirect(url_for('login.login'))
    
    # Checa se o usuário está ativo
    if not session.get('is_active', False):
         return redirect(url_for('register.complete_registration'))
         
    # Fetch patient profile to get the patient_code
    user = UserRepository.get_user_by_id(session['user_id'])
    patient_code = user.patient_profile.patient_code if user and user.patient_profile else None
         
    return render_template('patient_dashboard.html', patient_code=patient_code)
