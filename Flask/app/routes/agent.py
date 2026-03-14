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

@agent_bp.route('/triage', methods=['GET'])
def triage():
    if 'user_id' not in session or session.get('user_type') != 'health_agent':
        return jsonify({"success": False, "message": "Acesso negado"}), 403

    agent_id = session['user_id']
    linked_patients = UserRepository.get_linked_patients(agent_id)
    
    from app.models.daily_report import DailyReport
    
    triage_results = []
    
    for patient in linked_patients:
        # Busca os 5 ultimos relatórios
        reports = DailyReport.query.filter_by(patient_id=patient.id).order_by(DailyReport.date.desc()).limit(5).all()
        
        if not reports:
            triage_results.append({
                "patient_id": patient.id,
                "name": patient.user.name,
                "nivel": "SEM DADOS",
                "justificativa": "Paciente não possui relatórios gerados recentemente para análise de triagem.",
                "weight": 0
            })
            continue
            
        # Concatena o conteudo dos relatórios
        history_text = "\n\n".join([f"Data: {r.date}\n{r.content}" for r in reports])
        
        # Analisa a triagem
        triage_data = ai_svc.analyze_patient_triage(history_text)
        nivel = triage_data.get("nivel", "BAIXA")
        
        weight = 1
        if nivel == "ALTA": weight = 3
        elif nivel == "MÉDIA" or nivel == "MEDIA": weight = 2
        else: weight = 1
        
        triage_results.append({
            "patient_id": patient.id,
            "name": patient.user.name,
            "nivel": nivel,
            "justificativa": triage_data.get("justificativa", "Sem justificativa detalhada."),
            "weight": weight
        })
        
    # Ordena: Maior peso (ALTA) primeiro, seguido de MÉDIA, BAIXA, SEM DADOS
    triage_results.sort(key=lambda x: x["weight"], reverse=True)
    
    return jsonify({"success": True, "triage_list": triage_results})

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

@agent_bp.route('/download_report/<int:report_id>', methods=['GET'])
def download_report(report_id):
    if 'user_id' not in session or session.get('user_type') != 'health_agent':
        return jsonify({"success": False, "message": "Acesso negado"}), 403

    from app.models.daily_report import DailyReport
    report = DailyReport.query.get_or_404(report_id)
    
    # Valida se o paciente pertence a este ACS
    agent_id = session['user_id']
    patient = UserRepository.get_user_by_id(report.patient_id)
    if not patient or not patient.patient_profile or patient.patient_profile.agent_id != agent_id:
        return jsonify({"success": False, "message": "Paciente não vinculado."}), 403

    import markdown
    from flask_weasyprint import HTML, render_pdf
    
    # Converte o markdown para HTML
    html_content = markdown.markdown(report.content)
    
    # Template HTML básico para o PDF
    pdf_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Relatório de Saúde - {report.date.strftime('%d/%m/%Y')}</title>
        <style>
            @page {{
                size: A4;
                margin: 2cm;
            }}
            body {{
                font-family: 'Helvetica', 'Arial', sans-serif;
                color: #333;
                line-height: 1.6;
            }}
            .header {{
                text-align: center;
                border-bottom: 2px solid #006c4b;
                padding-bottom: 10px;
                margin-bottom: 30px;
            }}
            .header h1 {{
                color: #006c4b;
                margin: 0;
            }}
            .header p {{
                color: #666;
                margin: 5px 0 0 0;
            }}
            .patient-info {{
                background-color: #f7fbf2;
                border: 1px solid #dce5dd;
                padding: 15px;
                border-radius: 8px;
                margin-bottom: 20px;
            }}
            .content h1, .content h2, .content h3 {{
                color: #006c4b;
                margin-top: 20px;
            }}
            .content strong {{
                color: #006c4b;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Relatório de Saúde Diário</h1>
            <p><strong>Data:</strong> {report.date.strftime('%d/%m/%Y')}</p>
        </div>
        <div class="patient-info">
            <p><strong>Paciente:</strong> {patient.name}</p>
            <p><strong>Código SUS/Identificação:</strong> {patient.patient_profile.patient_code}</p>
        </div>
        <div class="content">
            {html_content}
        </div>
    </body>
    </html>
    """
    
    # Gera e retorna o PDF
    filename = f"Relatorio_Saude_{patient.name.replace(' ', '_')}_{report.date.strftime('%Y%m%d')}.pdf"
    return render_pdf(HTML(string=pdf_html), download_filename=filename)
