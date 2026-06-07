from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.services.patient_group_service import PatientGroupService
from app.repositories.user_repository import UserRepository
from app.utils.decorators import agent_required

group_bp = Blueprint('groups', __name__, url_prefix='/agent/groups')
group_service = PatientGroupService()

@group_bp.route('/', methods=['GET'])
@agent_required
def list_groups():
    agent_id = session['user_id']
    groups = group_service.get_all_groups_by_agent(agent_id)
    return render_template('groups.html', groups=groups)

@group_bp.route('/create', methods=['POST'])
@agent_required
def create_group():
    agent_id = session['user_id']
    name = request.form.get('name')
    description = request.form.get('description')
    
    try:
        group_service.create_group(name, description, agent_id)
        flash("Grupo criado com sucesso!", "success")
    except Exception as e:
        flash(f"Erro ao criar grupo: {str(e)}", "error")
        
    return redirect(url_for('groups.list_groups'))

@group_bp.route('/<group_id>', methods=['GET'])
@agent_required
def group_details(group_id):
    agent_id = session['user_id']
    try:
        group = group_service.get_group(group_id, agent_id)
        
        # Obter todos os pacientes vinculados ao ACS para mostrar no select de adicionar
        all_agent_patients = UserRepository.get_linked_patients(agent_id)
        
        # Filtrar os pacientes que já estão no grupo
        group_patient_ids = [p.id for p in group.patients]
        available_patients = [p for p in all_agent_patients if p.id not in group_patient_ids]

        return render_template('group_details.html', group=group, available_patients=available_patients)
    except Exception as e:
        flash(f"Erro ao acessar grupo: {str(e)}", "error")
        return redirect(url_for('groups.list_groups'))

@group_bp.route('/<group_id>/edit', methods=['POST'])
@agent_required
def edit_group(group_id):
    agent_id = session['user_id']
    name = request.form.get('name')
    description = request.form.get('description')
    
    try:
        group_service.update_group(group_id, agent_id, name, description)
        flash("Grupo atualizado com sucesso!", "success")
    except Exception as e:
        flash(f"Erro ao atualizar grupo: {str(e)}", "error")
        
    return redirect(url_for('groups.group_details', group_id=group_id))

@group_bp.route('/<group_id>/delete', methods=['POST'])
@agent_required
def delete_group(group_id):
    agent_id = session['user_id']
    try:
        group_service.delete_group(group_id, agent_id)
        flash("Grupo excluído com sucesso!", "success")
    except Exception as e:
        flash(f"Erro ao excluir grupo: {str(e)}", "error")
        
    return redirect(url_for('groups.list_groups'))

@group_bp.route('/<group_id>/patients/add', methods=['POST'])
@agent_required
def add_patient(group_id):
    agent_id = session['user_id']
    patient_id = request.form.get('patient_id')
    
    try:
        group_service.add_patient_to_group(group_id, patient_id, agent_id)
        flash("Paciente adicionado ao grupo!", "success")
    except Exception as e:
        flash(f"Erro ao adicionar paciente: {str(e)}", "error")
        
    return redirect(url_for('groups.group_details', group_id=group_id))

@group_bp.route('/<group_id>/patients/<patient_id>/remove', methods=['POST'])
@agent_required
def remove_patient(group_id, patient_id):
    agent_id = session['user_id']
    
    try:
        group_service.remove_patient_from_group(group_id, patient_id, agent_id)
        flash("Paciente removido do grupo!", "success")
    except Exception as e:
        flash(f"Erro ao remover paciente: {str(e)}", "error")
        
    return redirect(url_for('groups.group_details', group_id=group_id))
