from flask import Blueprint, render_template, session, redirect, url_for

patient_bp = Blueprint('patient', __name__, url_prefix='/patient')

@patient_bp.route('/dashboard')
def dashboard():
    if 'user_id' not in session or session.get('user_type') != 'patient':
        return redirect(url_for('login.login'))
    
    # Checa se o usuário está ativo
    if not session.get('is_active', False):
         return redirect(url_for('register.complete_registration'))
         
    return render_template('patient_dashboard.html')
