from flask import Blueprint, render_template, session, redirect, url_for, request, flash, jsonify
from app.repositories.user_repository import UserRepository
from app.services.ai_service import HealthAgent

agent_bp = Blueprint('agent', __name__, url_prefix='/agent')
ai_svc = HealthAgent()

@agent_bp.route('/dashboard')
def dashboard():
    if 'user_id' not in session or session.get('user_type') != 'health_agent':
        return redirect(url_for('login.login'))
        
    if not session.get('is_active', False):
         return redirect(url_for('register.complete_registration'))

    agent_id = session['user_id']
    user = UserRepository.get_user_by_id(agent_id)
    linked_patients = UserRepository.get_linked_patients(agent_id)

    return render_template('agent_dashboard.html', patients=linked_patients, agent_name=user.name if user else "Agente")

@agent_bp.route('/link_patient', methods=['POST'])
def link_patient():
    if 'user_id' not in session or session.get('user_type') != 'health_agent':
        return jsonify({"success": False, "message": "Não autorizado"}), 401

    patient_code = request.form.get('patient_code')
    if not patient_code:
        flash("Código do paciente é obrigatório.", "error")
        return redirect(url_for('agent.dashboard'))

    success, message = UserRepository.link_patient_to_agent(session['user_id'], patient_code)
    
    if success:
        flash(message, "success")
    else:
        flash(message, "error")

    return redirect(url_for('agent.dashboard'))

@agent_bp.route('/generate_report/<patient_id>', methods=['POST'])
def generate_report(patient_id):
    if 'user_id' not in session or session.get('user_type') != 'health_agent':
        return jsonify({"success": False, "message": "Acesso negado"}), 403

    from datetime import date
    from app.models.daily_report import DailyReport
    
    today = date.today()
    
    # Check if report already exists for today
    existing = DailyReport.query.filter_by(patient_id=patient_id, date=today).first()
    if existing:
        return jsonify({
            "success": False, 
            "message": "Já existe um relatório gerado para este paciente hoje.",
            "already_exists": True,
            "report": existing.content
        })

    # Valida se o paciente pertence a este ACS
    agent_id = session['user_id']
    patient = UserRepository.get_user_by_id(patient_id)
    if not patient or not patient.patient_profile or patient.patient_profile.agent_id != agent_id:
        return jsonify({"success": False, "message": "Paciente não vinculado."}), 403

    # Gera o relatório usando a IA
    report_content, status_message = ai_svc.generate_daily_report(patient_id)

    if report_content:
        return jsonify({"success": True, "message": status_message, "report": report_content})
    else:
        return jsonify({"success": False, "message": status_message})

@agent_bp.route('/history/<patient_id>', methods=['GET'])
def get_history(patient_id):
    if 'user_id' not in session or session.get('user_type') != 'health_agent':
        return jsonify({"success": False, "message": "Acesso negado"}), 403

    from app.models.daily_report import DailyReport
    reports = DailyReport.query.filter_by(patient_id=patient_id).order_by(DailyReport.date.desc()).all()
    
    history_data = [
        {
            "id": r.id,
            "date": r.date.strftime('%d/%m/%Y'),
            "content": r.content
        } for r in reports
    ]
    
    return jsonify({"success": True, "history": history_data})
