import requests
from flask import Blueprint, request, jsonify, session, url_for
from app.services.registration_agent import registration_agent
from app.repositories.user_repository import UserRepository
from app.services.voice_service import VoiceService
from app.services.auth_service import AuthService
import json
import sys
import re

registration_api_bp = Blueprint('registration_api', __name__)
voice = VoiceService(init_pygame=False)

# ---------------------------------------------------------------------------
# SOA-CNES SOAP Integration (via Zeep)
# ---------------------------------------------------------------------------

# Endpoint de homologação do CnesService (que contém consultarEstabelecimentoSaudePorMunicipio)
_CNES_WSDL_URL = "https://servicoshm.saude.gov.br/cnes/CnesService/v1r0?wsdl"

# Tipos de estabelecimento que correspondem a UBS
# 01 = Posto de Saúde | 02 = Centro de Saúde / Unidade Básica de Saúde
_CNES_UBS_TIPOS = {'01', '02'}

# Cache em memória: { "2208403": ["UBS CENTRO", "UBS REDONDA", ...] }
_ubs_cache: dict = {}

def fetch_ubs_from_cnes(ibge_code: str) -> list:
    """
    Consulta a API SOAP do SOA-CNES usando a biblioteca Zeep.
    Retorna nomes de UBS de um município com LOGS detalhados.
    """
    # pyrefly: ignore [missing-import]
    from zeep import Client, Settings
    # pyrefly: ignore [missing-import]
    from zeep.wsse.username import UsernameToken
    # pyrefly: ignore [missing-import]
    from zeep.plugins import HistoryPlugin
    # pyrefly: ignore [missing-import]
    from lxml import etree
    
    history = HistoryPlugin()
    ibge_6 = str(ibge_code)[:6]
    print(f"\n[SOA-CNES-DEBUG] === INICIANDO CONSULTA IBGE {ibge_6} ===")
    sys.stdout.flush()

    try:
        # pyrefly: ignore [missing-import]
        from zeep.transports import Transport
        
        # pyrefly: ignore [unexpected-keyword]
        settings = Settings(strict=False, xml_huge_tree=True)
        transport = Transport(timeout=15)

        client = Client(
            wsdl=_CNES_WSDL_URL,
            # Zeep 4.x não aceita use_nonce/use_created nativamente no init
            wsse=UsernameToken('CNES.PUBLICO', 'cnes#2015public'),
            settings=settings,
            transport=transport,
            plugins=[history]
        )
        
        # Usa CnesServicePort que é SOAP 1.2, conforme esperado pelo SOA-CNES
        service = client.bind('CnesService', 'CnesServicePort')
        
        print(f"[SOA-CNES-DEBUG] Chamando consultarEstabelecimentoSaudePorMunicipio...")
        response = service.consultarEstabelecimentoSaudePorMunicipio(
            Municipio={'codigoMunicipio': ibge_6}
        )
        
        # Log do XML Enviado
        if history.last_sent:
            xml_sent = etree.tostring(history.last_sent["envelope"], pretty_print=True).decode()
            print(f"[SOA-CNES-DEBUG] XML ENVIADO:\n{xml_sent}")

        # Log do XML Recebido
        if history.last_received:
            xml_received = etree.tostring(history.last_received["envelope"], pretty_print=True).decode()
            print(f"[SOA-CNES-DEBUG] XML RECEBIDO:\n{xml_received}")

        if not response:
            print(f"[SOA-CNES-DEBUG] API retornou vazio ou None.")
            return []

        print(f"[SOA-CNES-DEBUG] Tipo da resposta: {type(response)}")
        
        ubs_names = []
        # A resposta pode vir encapsulada de várias formas no Zeep (lista, dict, objeto)
        items = response if isinstance(response, list) else [response]
        
        for item in items:
            lista_estabs = []
            if hasattr(item, 'DadosBasicosEstabelecimento') and item.DadosBasicosEstabelecimento:
                lista_estabs = item.DadosBasicosEstabelecimento
            elif isinstance(item, dict) and 'DadosBasicosEstabelecimento' in item:
                lista_estabs = item['DadosBasicosEstabelecimento']
            elif hasattr(item, 'EstabelecimentoSaude') and item.EstabelecimentoSaude:
                lista_estabs = item.EstabelecimentoSaude
            else:
                lista_estabs = [item]
                
            for estab in lista_estabs:
                # Tipo de Unidade (geralmente não vem nessa operação, mas mantemos como fallback)
                tipo_unidade = getattr(estab, 'tipoUnidade', None)
                tipo_codigo = None
                if tipo_unidade and hasattr(tipo_unidade, 'codigo'):
                    tipo_codigo = str(tipo_unidade.codigo).strip().zfill(2)
                
                # Nome (prioridade Fantasia)
                nome = None
                nome_f = estab.get('NomeFantasia') if hasattr(estab, 'get') else getattr(estab, 'NomeFantasia', None)
                if nome_f:
                    nome = nome_f.get('Nome') if hasattr(nome_f, 'get') else getattr(nome_f, 'Nome', None)
                    
                if not nome:
                    nome_e = estab.get('NomeEmpresarial') if hasattr(estab, 'get') else getattr(estab, 'NomeEmpresarial', None)
                    if nome_e:
                        nome = nome_e.get('Nome') if hasattr(nome_e, 'get') else getattr(nome_e, 'Nome', None)
                    
                if nome:
                    nome = str(nome).strip()
                    # Log opcional dos 3 primeiros nomes
                    if len(ubs_names) < 3:
                        print(f"[SOA-CNES-DEBUG] Encontrada: {nome} (Tipo: {tipo_codigo})")
                    
                    if tipo_codigo in _CNES_UBS_TIPOS:
                        ubs_names.append(nome)
                    elif tipo_codigo is None:
                        nome_upper = nome.upper()
                        if any(kw in nome_upper for kw in ['UBS', 'CENTRO DE SAUDE', 'POSTO', 'UNIDADE BASICA', 'USF', 'PSF', 'FARMACIA', 'CLINICA']):
                            ubs_names.append(nome)

        print(f"[SOA-CNES-DEBUG] Total final filtrado: {len(ubs_names)} UBS")
        return ubs_names

    except Exception as e:
        print(f"[SOA-CNES-DEBUG] !!! ERRO NA CHAMADA !!!")
        print(f"[SOA-CNES-DEBUG] Mensagem: {str(e)}")
        
        if history.last_sent:
             print(f"[SOA-CNES-DEBUG] XML ENVIADO NO ERRO:\n{etree.tostring(history.last_sent['envelope'], pretty_print=True).decode()}")
        if history.last_received:
             print(f"[SOA-CNES-DEBUG] XML RECEBIDO NO ERRO (PODE CONTER O FAULT):\n{etree.tostring(history.last_received['envelope'], pretty_print=True).decode()}")
             
        raise e

@registration_api_bp.route('/api/check_cpf', methods=['POST'])
def check_cpf():
    data = request.get_json()
    if not data or 'cpf' not in data:
        return jsonify({'error': 'CPF ausente'}), 400
    
    cpf = data['cpf']
    from app.models.patient import Patient
    exists = Patient.query.filter_by(cpf=cpf).first() is not None
    
    return jsonify({'exists': exists})

@registration_api_bp.route('/api/ubs', methods=['GET'])
def get_ubs():
    import os
    import csv
    ibge_code = request.args.get('ibge')
    print(f"\n[ROUTE-LOG] Chamada para /api/ubs?ibge={ibge_code}")
    sys.stdout.flush()
    
    if not ibge_code:
        return jsonify({'error': 'Código IBGE ausente'}), 400

    # 1. Cache em memória
    if ibge_code in _ubs_cache:
        print(f"[SOA-CNES] Cache hit para IBGE {ibge_code} ({len(_ubs_cache[ibge_code])} UBS)")
        return jsonify({'ubs': _ubs_cache[ibge_code], 'fonte': 'cache'})

    # 2. API SOAP do SOA-CNES
    try:
        ubs_list = fetch_ubs_from_cnes(ibge_code)
        if ubs_list:
            _ubs_cache[ibge_code] = ubs_list
            return jsonify({'ubs': ubs_list, 'fonte': 'api_cnes'})
        print(f"[SOA-CNES] API retornou lista vazia para IBGE {ibge_code}, tentando CSV.")
    except Exception as e:
        print(f"[SOA-CNES] Falha na chamada SOAP: {e}. Usando fallback CSV.")

    # 3. Fallback: CSV local
    ubs_list = []
    # Como este arquivo roda a partir do pacote app, podemos acessar app/data/ubs_cnes.csv
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_path = os.path.join(base_dir, 'data', 'ubs_cnes.csv')
    
    try:
        if os.path.exists(csv_path):
            with open(csv_path, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get('codigo_ibge') == ibge_code:
                        ubs_list.append(row.get('nome_ubs'))
        else:
            print(f"[SOA-CNES] CSV não encontrado em {csv_path}")
    except Exception as e:
        print(f"[SOA-CNES] Erro ao ler CSV: {e}")
        return jsonify({'error': 'Erro ao consultar base de UBS'}), 500

    if ubs_list:
        _ubs_cache[ibge_code] = ubs_list

    return jsonify({'ubs': ubs_list, 'fonte': 'csv_fallback'})

@registration_api_bp.route('/api/registration_chat/start', methods=['POST'])
def start_registration():
    # Inicia a sessão completamente zerada para um novo cadastro
    session['reg_state'] = {
        'current_step': 0,
        'collected_data': {},
        'sub_state': 'ASKING',
        'temp_val': None
    }
    
    first_question = registration_agent.get_question_for_step(0)
    audio_b64 = voice.generate_base64_audio(first_question)
    
    return jsonify({
        'response': first_question,
        'audio_b64': audio_b64,
        'status': 'IN_PROGRESS',
        'progress': 0
    })

@registration_api_bp.route('/api/registration_chat/cancel', methods=['POST'])
def cancel_registration():
    session.pop('reg_state', None)
    return jsonify({'status': 'CANCELLED'})

@registration_api_bp.route('/api/registration_chat/message', methods=['POST'])
def chat_message():
    data = request.get_json()
    user_message = data.get('message', '')
    
    state = session.get('reg_state')
    if not state:
        return jsonify({'error': 'Conversa não iniciada.'}), 400
        
    result = registration_agent.handle_chat_interaction(user_message, state, voice)
    
    if result.get('state_changed'):
        session.modified = True
        
    if not result.get('continue'):
        return jsonify({
            'response': result.get('response', ''),
            'audio_b64': result.get('audio_b64', ''),
            'status': result.get('status', 'IN_PROGRESS'),
            'progress': result.get('progress', 0)
        })
    
    next_step = state['current_step']
    total_steps = len(registration_agent.fields_sequence)
    
    if next_step < total_steps:
        # Fazer próxima pergunta
        next_q = registration_agent.get_question_for_step(next_step)
        progress_pct = int((next_step / total_steps) * 100)
        
        audio_b64 = voice.generate_base64_audio(next_q)
        return jsonify({
            'response': next_q,
            'audio_b64': audio_b64,
            'status': 'IN_PROGRESS',
            'progress': progress_pct
        })
    else:
        # FIM! Processar persistência no BD final
        collected = state['collected_data']
    
        
        # --- AUTO CEP FETCH ---
        if 'cep' not in collected and 'state' in collected and 'city' in collected:
            state_uf = str(collected['state']).strip()
            city_name = str(collected['city']).strip()
            if state_uf and city_name:
                try:
                    import requests
                    resp = requests.get(f"https://viacep.com.br/ws/{state_uf}/{city_name}/Centro/json/", timeout=5)
                    if resp.status_code == 200:
                        data = resp.json()
                        if data and isinstance(data, list) and len(data) > 0:
                            collected['cep'] = data[0].get('cep', '').replace('-', '')
                except Exception as e:
                    print(f"Erro ao buscar CEP autônomo: {e}")
        # ----------------------
        
        import uuid
        unique_suffix = uuid.uuid4().hex[:8]
        
        # O .get() retorna None se a chave existir mas o valor for None. 
        # O "or" garante que peguemos o valor default nesse caso.
        email = collected.get('email') or f"voz_{unique_suffix}@example.com"
        password = collected.get('password') or "123Mudar!@" 
        name = collected.get('name') or 'Usuário Voz'
        
        try:
            # Verifica se e-mail já existe no banco local antes de ir pro Firebase
            from app.models.user import User
            if User.query.filter_by(email=email).first():
                msg_erro = "Esse e-mail já consta no nosso banco de dados. Tente fazer login ou use outro e-mail."
                return jsonify({'response': msg_erro, 'audio_b64': voice.generate_base64_audio(msg_erro), 'status': 'ERROR'})

            # 1. Firebase
            try:
                fb_user = AuthService.create_firebase_user(email, password)
                user_id = fb_user['localId']
            except Exception as e:
                msg_erro = f"Puxa, tivemos um erro ao salvar na nuvem: {str(e)}. Vamos tentar de novo mais tarde?"
                return jsonify({'response': msg_erro, 'audio_b64': voice.generate_base64_audio(msg_erro), 'status': 'ERROR'})

            # 2. Local BD User
            # Evitar conflito de unique_username caso duas pessoas usem prefixos de email iguais
            base_username = email.split('@')[0][:40]
            username = f"{base_username}_{unique_suffix}"
            UserRepository.create_user(user_id, name, username, email, 'patient')
            
            # 3. Local BD Profile
            patient_data = {k: v for k, v in collected.items() if k not in ['name', 'email', 'password'] and v is not None}
            UserRepository.create_patient_profile(user_id, patient_data)
            
            # 4. Login Session
            session['user_id'] = user_id
            session['user_type'] = 'patient'
            session['user_name'] = name
            session['is_active'] = True
            session.pop('reg_state', None)
            
            final_message = "Prontinho! Finalizamos o seu cadastro. Todas as informações foram salvas com sucesso e você está logado. Bem-vindo!"
            audio_b64 = voice.generate_base64_audio(final_message)
            
            return jsonify({
                'response': final_message,
                'audio_b64': audio_b64,
                'status': 'FINISHED',
                'progress': 100,
                'redirect_url': url_for('patient.dashboard')
            })
            
        except Exception as db_err:
             print(f"Erro BD final: {db_err}")
             import traceback
             with open("reg_error_trace.txt", "w") as f:
                 f.write(traceback.format_exc())
             return jsonify({'response': "Ocorreu um erro interno no banco de dados ao salvar seu cadastro final. Nossa equipe foi notificada.", 'status': 'ERROR'})


@registration_api_bp.route('/api/profissional_info', methods=['GET'])
def get_profissional_info():
    """
    Busca informações do profissional de saúde (CBO).
    """
    cpf = request.args.get('cpf')
    if not cpf:
        return jsonify({'error': 'CPF ausente'}), 400

    # =========================================================================
    # BLOCO DE TESTES (MOCK) - ATIVO
    # Descomente o bloco CNES abaixo e comente este bloco MOCK quando for para produção.
    # =========================================================================
    '''return jsonify({
        'cbo': '5151-05',
        'cbo_descricao': 'Agente comunitário de saúde',
        'microarea': '', # Inexistente em API pública, requer input manual do ACS
        'fonte': 'mock_tests'
    })'''

    # =========================================================================
    # BLOCO CNES SOAP - INATIVO (Descomente quando o sistema estiver pronto)
    # =========================================================================
    
    try:
        # pyrefly: ignore [missing-import]
        from zeep import Client, Settings
        # pyrefly: ignore [missing-import]
        from zeep.wsse.username import UsernameToken
        # pyrefly: ignore [missing-import]
        from zeep.transports import Transport
        
        cpf_clean = "".join(filter(str.isdigit, cpf))
        
        _PROFISSIONAL_WSDL_URL = "https://servicoshm.saude.gov.br/cnes/ProfissionalSaudeService/v1r0?wsdl"
        # pyrefly: ignore [unexpected-keyword]
        settings = Settings(strict=False, xml_huge_tree=True)
        transport = Transport(timeout=15)
        
        client = Client(
            wsdl=_PROFISSIONAL_WSDL_URL,
            wsse=UsernameToken('CNES.PUBLICO', 'cnes#2015public'),
            settings=settings,
            transport=transport
        )
        
        service = client.bind('ProfissionalSaudeService', 'ProfissionalSaudeServicePort')
        
        response = service.consultarProfissionalSaude(
            FiltroPesquisaProfissionalSaude={
                'CPF': {'numeroCPF': cpf_clean}
            }
        )
        
        cbo_codigo = "5151-05" # Default fallback
        cbo_descricao = "Agente comunitário de saúde"
        
        if hasattr(response, 'ProfissionalSaude') and response.ProfissionalSaude:
            prof = response.ProfissionalSaude
            cbo_obj = getattr(prof, 'CBO', None)
            if cbo_obj:
                cbo_codigo = getattr(cbo_obj, 'codigoCBO', cbo_codigo)
                cbo_descricao = getattr(cbo_obj, 'descricaoCBO', cbo_descricao)
                
        return jsonify({
            'cbo': cbo_codigo,
            'cbo_descricao': cbo_descricao,
            'microarea': '', # Requer input manual do usuário, sem API
            'fonte': 'api_cnes'
        })
        
    except Exception as e:
        print(f"[SOA-CNES] Erro ao buscar CBO para CPF {cpf}: {str(e)}")
        return jsonify({
            'cbo': '5151-05',
            'cbo_descricao': 'Agente comunitário de saúde',
            'microarea': '',
            'fonte': 'fallback_cnes_error'
        })
    
