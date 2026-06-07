import logging
import os
from zeep import Client, Settings
from zeep.wsse.username import UsernameToken
from zeep.plugins import HistoryPlugin
from lxml import etree
from zeep.transports import Transport
import csv
import json
from app.extensions.redis_ext import redis_client_ext

logger = logging.getLogger(__name__)

class CNESService:
    _CNES_WSDL_URL = "https://servicoshm.saude.gov.br/cnes/CnesService/v1r0?wsdl"
    _PROFISSIONAL_WSDL_URL = "https://servicoshm.saude.gov.br/cnes/ProfissionalSaudeService/v1r0?wsdl"
    _CNES_UBS_TIPOS = {'01', '02'}
    
    # Cache em memória 
    _ubs_cache = {}

    @staticmethod
    def _get_redis():
        return redis_client_ext.client

    @staticmethod
    def fetch_ubs(ibge_code: str) -> tuple:
        """
        Retorna (lista_ubs, fonte) consultando Cache Redis (24h) -> SOAP -> CSV
        """
        
        # 1. Tentar Redis
        redis_cli = CNESService._get_redis()
        cache_key = f"ubs_ibge_{ibge_code}"
        
        if redis_cli:
            try:
                cached = redis_cli.get(cache_key)
                if cached:
                    logger.info(f"[SOA-CNES] Redis hit para IBGE {ibge_code}")
                    return json.loads(cached), 'cache_redis'
            except Exception as e:
                logger.error(f"Erro ao ler do Redis: {e}", exc_info=True)
        else:
            # Fallback mem cache
            if ibge_code in CNESService._ubs_cache:
                logger.info(f"[SOA-CNES] MemCache hit para IBGE {ibge_code}")
                return CNESService._ubs_cache[ibge_code], 'cache_mem'
                
        # 2. API SOAP do SOA-CNES
        try:
            ubs_list = CNESService._fetch_from_soap(ibge_code)
            if ubs_list:
                # Salvar no cache
                if redis_cli:
                    try:
                        redis_cli.setex(cache_key, 86400, json.dumps(ubs_list)) # 24h
                    except Exception as e:
                        logger.error(f"Erro ao salvar no Redis: {e}", exc_info=True)
                else:
                    CNESService._ubs_cache[ibge_code] = ubs_list
                return ubs_list, 'api_cnes'
            logger.info(f"[SOA-CNES] API retornou lista vazia para IBGE {ibge_code}, tentando CSV.")
        except Exception as e:
            logger.error(f"[SOA-CNES] Falha na chamada SOAP: {e}. Usando fallback CSV.", exc_info=True)

        # 3. Fallback: CSV local
        ubs_list = []
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
                logger.info(f"[SOA-CNES] CSV não encontrado em {csv_path}")
        except Exception as e:
            logger.error(f"[SOA-CNES] Erro ao ler CSV: {e}", exc_info=True)
            return None, 'error'

        if ubs_list:
            if redis_cli:
                try:
                    redis_cli.setex(cache_key, 86400, json.dumps(ubs_list)) # 24h
                except Exception as e:
                    pass
            else:
                CNESService._ubs_cache[ibge_code] = ubs_list
                
        return ubs_list, 'csv_fallback'

    @staticmethod
    def _fetch_from_soap(ibge_code: str) -> list:
        
        history = HistoryPlugin()
        ibge_6 = str(ibge_code)[:6]
        logger.debug(f"\n[SOA-CNES-DEBUG] === INICIANDO CONSULTA IBGE {ibge_6} ===")

        try:
            settings = Settings(strict=False, xml_huge_tree=True)
            transport = Transport(timeout=15)

            # Usando env vars para segurança
            cnes_user = os.getenv("CNES_USER", "CNES.PUBLICO")
            cnes_pass = os.getenv("CNES_PASSWORD", "cnes#2015public")

            client = Client(
                wsdl=CNESService._CNES_WSDL_URL,
                wsse=UsernameToken(cnes_user, cnes_pass),
                settings=settings,
                transport=transport,
                plugins=[history]
            )
            
            service = client.bind('CnesService', 'CnesServicePort')
            
            logger.debug(f"[SOA-CNES-DEBUG] Chamando consultarEstabelecimentoSaudePorMunicipio...")
            response = service.consultarEstabelecimentoSaudePorMunicipio(
                Municipio={'codigoMunicipio': ibge_6}
            )
            
            if history.last_sent:
                xml_sent = etree.tostring(history.last_sent["envelope"], pretty_print=True).decode()
                logger.debug(f"[SOA-CNES-DEBUG] XML ENVIADO:\n{xml_sent}")

            if history.last_received:
                xml_received = etree.tostring(history.last_received["envelope"], pretty_print=True).decode()
                logger.debug(f"[SOA-CNES-DEBUG] XML RECEBIDO:\n{xml_received}")

            if not response:
                logger.debug(f"[SOA-CNES-DEBUG] API retornou vazio ou None.")
                return []

            logger.debug(f"[SOA-CNES-DEBUG] Tipo da resposta: {type(response)}")
            
            ubs_names = []
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
                    tipo_unidade = getattr(estab, 'tipoUnidade', None)
                    tipo_codigo = None
                    if tipo_unidade and hasattr(tipo_unidade, 'codigo'):
                        tipo_codigo = str(tipo_unidade.codigo).strip().zfill(2)
                    
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
                        if len(ubs_names) < 3:
                            logger.debug(f"[SOA-CNES-DEBUG] Encontrada: {nome} (Tipo: {tipo_codigo})")
                        
                        if tipo_codigo in CNESService._CNES_UBS_TIPOS:
                            ubs_names.append(nome)
                        elif tipo_codigo is None:
                            nome_upper = nome.upper()
                            if any(kw in nome_upper for kw in ['UBS', 'CENTRO DE SAUDE', 'POSTO', 'UNIDADE BASICA', 'USF', 'PSF', 'FARMACIA', 'CLINICA']):
                                ubs_names.append(nome)

            logger.debug(f"[SOA-CNES-DEBUG] Total final filtrado: {len(ubs_names)} UBS")
            return ubs_names

        except Exception as e:
            logger.error(f"[SOA-CNES-DEBUG] !!! ERRO NA CHAMADA !!!", exc_info=True)
            logger.debug(f"[SOA-CNES-DEBUG] Mensagem: {str(e)}")
            
            if history.last_sent:
                try:
                    logger.error(f"[SOA-CNES-DEBUG] XML ENVIADO NO ERRO:\n{etree.tostring(history.last_sent['envelope'], pretty_print=True).decode()}")
                except Exception as parse_e:
                    logger.error(f"Erro ao ler XML enviado: {parse_e}")
            if history.last_received:
                try:
                    logger.error(f"[SOA-CNES-DEBUG] XML RECEBIDO NO ERRO:\n{etree.tostring(history.last_received['envelope'], pretty_print=True).decode()}")
                except Exception as parse_e:
                    logger.error(f"Erro ao ler XML recebido: {parse_e}")
                 
            raise e



    @staticmethod
    def check_cbo_local(cbo_code: str) -> dict:
        """
        Busca o CBO no arquivo CSV local.
        """
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        csv_path = os.path.join(base_dir, 'data', 'cbo_cnes.csv')
        
        try:
            if os.path.exists(csv_path):
                with open(csv_path, mode='r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row.get('codigo_cbo') == cbo_code:
                            return {
                                'codigo_cbo': row.get('codigo_cbo'),
                                'nome_cbo': row.get('nome_cbo')
                            }
        except Exception as e:
            logger.error(f"Erro ao ler CSV de CBO: {e}", exc_info=True)
            
        return None
