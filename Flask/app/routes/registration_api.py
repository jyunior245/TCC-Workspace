import logging
logger = logging.getLogger(__name__)
import requests
import json
import sys
import re
import os
import uuid
import traceback
from flask import Blueprint, request, jsonify, session, url_for, current_app
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.services.cnes_service import CNESService
from app.models.patient import Patient
from app.models.user import User


registration_api_bp = Blueprint('registration_api', __name__)




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
    
    if not ibge_code:
        return jsonify({'error': 'Código IBGE ausente'}), 400

    ubs_list, fonte = CNESService.fetch_ubs(ibge_code)
    
    if ubs_list is None:
        return jsonify({'error': 'Erro ao consultar base de UBS'}), 500

    return jsonify({'ubs': ubs_list, 'fonte': fonte})







@registration_api_bp.route('/api/cbo', methods=['GET'])
def get_cbo_info():
    """
    Busca informações do CBO no arquivo CSV local.
    """
    cbo = request.args.get('codigo')
    if not cbo:
        return jsonify({'error': 'Código CBO ausente'}), 400

    info = CNESService.check_cbo_local(cbo)
    if info:
        return jsonify(info)
    else:
        return jsonify({'error': 'CBO não encontrado'}), 404
