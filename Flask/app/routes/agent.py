from flask import Blueprint, render_template, session, redirect, url_for, request, flash, jsonify, current_app
from itsdangerous import URLSafeTimedSerializer
from urllib.parse import quote
from app.repositories.user_repository import UserRepository
from app.services.ai_service import HealthAgent
from app.services.auth_service import AuthService
import secrets
from datetime import datetime

agent_bp = Blueprint('agent', __name__, url_prefix='/agent')
ai_svc = HealthAgent()

from app.utils.decorators import agent_required

@agent_bp.route('/dashboard')
@agent_required
def dashboard():
    if not session.get('is_active', False):
         return redirect(url_for('register.complete_registration'))

    agent_id = session['user_id']
    user = UserRepository.get_user_by_id(agent_id)
    linked_patients = UserRepository.get_linked_patients(agent_id)

    return render_template('agent_dashboard.html', patients=linked_patients, agent_name=user.name if user else "Agente")

@agent_bp.route('/link_patient', methods=['POST'])
@agent_required
def link_patient():
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

@agent_bp.route('/generate_recovery_link/<patient_id>', methods=['POST'])
@agent_required
def generate_recovery_link(patient_id):
    agent_id = session['user_id']
    patient = UserRepository.get_user_by_id(patient_id)
    
    # Check if patient exists and is linked to this agent
    if not patient or not patient.patient_profile or patient.patient_profile.agent_id != agent_id:
        return jsonify({"success": False, "message": "Paciente não vinculado ou não encontrado."}), 403

    # Generate token
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    token = serializer.dumps({'patient_id': patient_id, 'action': 'recover_password'})
    
    recovery_url = url_for('index.recover_access', token=token, _external=True)
    
    # Get caregiver info
    caregiver_name = patient.patient_profile.caregiver_name or "Familiar/Cuidador"
    caregiver_phone = patient.patient_profile.caregiver_phone or ""
    
    return jsonify({
        "success": True,
        "recovery_url": recovery_url,
        "caregiver_name": caregiver_name,
        "caregiver_phone": caregiver_phone,
        "patient_name": patient.name
    })

@agent_bp.route('/generate_report/<patient_id>', methods=['POST'])
@agent_required
def generate_report(patient_id):
    from datetime import datetime, timezone, timedelta
    from app.models.daily_report import DailyReport
    
    # Fuso horário do Brasil para evitar virada prematura do dia no servidor UTC (Docker)
    br_tz = timezone(timedelta(hours=-3))
    today = datetime.now(br_tz).date()
    
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

@agent_bp.route('/update_report/<patient_id>', methods=['POST'])
@agent_required
def update_report(patient_id):
    agent_id = session['user_id']
    patient = UserRepository.get_user_by_id(patient_id)
    if not patient or not patient.patient_profile or patient.patient_profile.agent_id != agent_id:
        return jsonify({"success": False, "message": "Paciente não vinculado."}), 403

    report_content, status_message = ai_svc.generate_daily_report(patient_id, update_existing=True)

    if report_content:
        return jsonify({"success": True, "message": status_message, "report": report_content})
    else:
        return jsonify({"success": False, "message": status_message})

@agent_bp.route('/triage', methods=['GET'])
@agent_required
def triage():
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
@agent_required
def get_history(patient_id):
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
@agent_required
def download_report(report_id):
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


@agent_bp.route('/register_assisted', methods=['GET', 'POST'])
@agent_required
def register_assisted():
    if request.method == 'POST':
        try:
            # 1. Pega os dados básicos
            name = request.form.get('name')
            username = request.form.get('username')
            email = request.form.get('email')
            cpf = request.form.get('cpf')
            
            if not email:
                # Gerar pseudo-email se não fornecido
                clean_cpf = ''.join(filter(str.isdigit, cpf))
                email = f"{clean_cpf}@tcchealth.com"
            
            # 2. Gera senha temporária forte
            temp_password = secrets.token_urlsafe(8) + "A1!"
            
            # 3. Cria Firebase User
            firebase_user = AuthService.create_firebase_user(email, temp_password)
            user_id = firebase_user['localId']
            
            # 4. Cria Postgres User
            UserRepository.create_user(user_id, name, username, email, 'patient')
            
            # 5. Coleta dados complementares do form (mesmo do paciente normal)
            dob_str = request.form.get('date_of_birth')
            dob_date = None
            if dob_str:
                dob_date = datetime.strptime(dob_str, '%Y-%m-%d').date()

            def get_csv_list(field_name):
                items = request.form.getlist(field_name)
                return ",".join(items) if items else None
            
            def get_int(field_name):
                val = request.form.get(field_name)
                return int(val) if val and val.isdigit() else None

            profile_data = {
                'date_of_birth': dob_date,
                'gender': request.form.get('gender') or None,
                'cpf': cpf,
                'marital_status': request.form.get('marital_status') or None,
                'nationality': request.form.get('nationality') or None,
                'education_level': request.form.get('education_level') or None,
                
                'caregiver_name': request.form.get('caregiver_name') or None,
                'caregiver_phone': request.form.get('caregiver_phone') or None,
                
                'cep': request.form.get('cep') or None,
                'street': request.form.get('street') or None,
                'number': request.form.get('number') or None,
                'neighborhood': request.form.get('neighborhood') or None,
                'city': request.form.get('city') or None,
                'state': request.form.get('state') or None,
                'zone': request.form.get('zone') or None,
                
                'num_residents': get_int('num_residents'),
                'has_potable_water': request.form.get('has_potable_water') == 'yes',
                'has_sanitation': request.form.get('has_sanitation') == 'yes',
                'has_garbage_collection': request.form.get('has_garbage_collection') == 'yes',
                'has_electricity': request.form.get('has_electricity') == 'yes',
                'has_internet': request.form.get('has_internet') == 'yes',
                
                'financially_dependent': request.form.get('financially_dependent') == 'yes',
                
                'chronic_conditions': get_csv_list('chronic_conditions'),
                
                'mobility_status': request.form.get('mobility_status') or None,
                'can_bathe_alone': request.form.get('can_bathe_alone') == 'yes',
                'can_dress_alone': request.form.get('can_dress_alone') == 'yes',
                'can_eat_alone': request.form.get('can_eat_alone') == 'yes',
                
                'perceived_memory': request.form.get('perceived_memory') or None,
                'mental_diagnoses': get_csv_list('mental_diagnoses'),
                
                'physical_activity_frequency': request.form.get('physical_activity_frequency') or None,
                'sleep_quality': request.form.get('sleep_quality') or None,
                'alcohol_consumption': request.form.get('alcohol_consumption') or None,
                'smoking': request.form.get('smoking') or None,
                
                'frequent_visits': request.form.get('frequent_visits') == 'yes',
                'community_activities': request.form.get('community_activities') == 'yes'
            }
            
            # 6. Cria PatientProfile
            UserRepository.create_patient_profile(user_id, profile_data)
            
            # 7. Vincula ao ACS
            agent_id = session['user_id']
            UserRepository.link_patient_to_agent(agent_id, cpf)
            
            # 8. Gera token de recuperação
            serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
            token = serializer.dumps({'patient_id': user_id, 'action': 'recover_password'})
            recovery_url = url_for('index.recover_access', token=token, _external=True)
            
            # 9. Renderiza sucesso
            return render_template(
                'agent_register_success.html',
                patient_name=name,
                patient_email=email,
                temporary_password=temp_password,
                recovery_url=recovery_url
            )
            
        except Exception as e:
            flash(f"Erro ao cadastrar paciente: {str(e)}", "error")
            print(f"Modo Assistência error: {str(e)}")
            import traceback
            traceback.print_exc()
            return redirect(url_for('agent.dashboard'))

    return render_template('agent_register_assisted.html')
