import pytest
import json
from unittest.mock import MagicMock
from app.services.cnes_service import CNESService

def test_fetch_ubs_redis_hit(mocker):
    """Testa quando o IBGE já está em cache no Redis."""
    mock_redis = mocker.patch.object(CNESService, '_get_redis')
    mock_redis.return_value.get.return_value = '["UBS Teste Redis"]'
    
    ubs_list, source = CNESService.fetch_ubs("123456")
    assert ubs_list == ["UBS Teste Redis"]
    assert source == 'cache_redis'

def test_fetch_ubs_soap_success(mocker):
    """Testa a chamada bem-sucedida para o SOAP (API CNES) salvando no cache."""
    mock_redis = mocker.patch.object(CNESService, '_get_redis')
    mock_redis.return_value.get.return_value = None
    
    mocker.patch.dict('app.services.cnes_service.CNESService._ubs_cache', {}, clear=True)
    mocker.patch('app.services.cnes_service.CNESService._fetch_from_soap', return_value=["UBS Teste SOAP"])
    
    ubs_list, source = CNESService.fetch_ubs("123456")
    
    assert ubs_list == ["UBS Teste SOAP"]
    assert source == 'api_cnes'
    mock_redis.return_value.setex.assert_called_once()

def test_fetch_ubs_csv_fallback(mocker):
    """Testa fallback para o arquivo CSV quando a API CNES cai/falha."""
    mock_redis = mocker.patch.object(CNESService, '_get_redis')
    mock_redis.return_value.get.return_value = None
    mocker.patch('app.services.cnes_service.CNESService._fetch_from_soap', side_effect=Exception("SOAP Down"))
    
    mocker.patch('app.services.cnes_service.os.path.exists', return_value=True)
    mock_csv_data = "codigo_ibge,nome_ubs\n123456,UBS Teste CSV\n"
    mocker.patch('builtins.open', mocker.mock_open(read_data=mock_csv_data))
    
    ubs_list, source = CNESService.fetch_ubs("123456")
    
    assert ubs_list == ["UBS Teste CSV"]
    assert source == 'csv_fallback'

def test_check_cbo_local_success(mocker):
    """Testa busca de CBO local com sucesso."""
    mocker.patch('app.services.cnes_service.os.path.exists', return_value=True)
    mock_csv_data = "codigo_cbo,nome_cbo\n5151-05,Agente comunitário de saúde\n"
    mocker.patch('builtins.open', mocker.mock_open(read_data=mock_csv_data))
    
    result = CNESService.check_cbo_local("5151-05")
    
    assert result is not None
    assert result['codigo_cbo'] == "5151-05"
    assert result['nome_cbo'] == "Agente comunitário de saúde"

def test_check_cbo_local_not_found(mocker):
    """Testa busca de CBO local quando não encontra o código."""
    mocker.patch('app.services.cnes_service.os.path.exists', return_value=True)
    mock_csv_data = "codigo_cbo,nome_cbo\n5151-05,Agente comunitário de saúde\n"
    mocker.patch('builtins.open', mocker.mock_open(read_data=mock_csv_data))
    
    result = CNESService.check_cbo_local("9999-99")
    
    assert result is None

def test_check_cbo_local_file_not_found(mocker):
    """Testa busca de CBO local quando arquivo CSV não existe."""
    mocker.patch('app.services.cnes_service.os.path.exists', return_value=False)
    
    result = CNESService.check_cbo_local("5151-05")
    
    assert result is None

