import pytest
import json
from app.services.ai_service import HealthAgent
import app.services.ai_service

def test_classify_intent_fast_path():
    """Testa se o metodo fast path está funcionando"""
    agent = HealthAgent()
    # Mock para garantir que o metodo fast path está funcionando
    # Não precisamos mockar pois o fast path retorna imediatamente
    intent = agent._classify_intent("oi")
    assert intent == "GREETING"
    
    intent = agent._classify_intent("olá tudo bem")
    assert intent == "GREETING"

def test_classify_intent_emergency_fallback():
    """Testa se o metodo fallback pega emergencias corretamente."""
    agent = HealthAgent()
    # Mock para garantir que o metodo fallback pega emergencias corretamente
    # Não precisamos mockar pois o fallback retorna imediatamente
    app.services.ai_service.rag_service.model = None
    
    intent = agent._classify_intent("Eu estou sentindo uma dor no peito muito forte e acho que vou infartar, socorro!")
    assert intent == "EMERGENCY"

def test_classify_intent_health_query_fallback():
    """Testa se o metodo fallback pega duvidas sobre saude corretamente."""
    agent = HealthAgent()
    # Mock para garantir que o metodo fallback pega duvidas sobre saude corretamente
    # Não precisamos mockar pois o fallback retorna imediatamente
    app.services.ai_service.rag_service.model = None
    
    intent = agent._classify_intent("quais são os sintomas de dengue e como tratar a febre alta?")
    assert intent == "HEALTH_QUERY"

def test_classify_intent_other_fallback():
    """Testa se o metodo fallback pega outras intencoes corretamente."""
    agent = HealthAgent()
    app.services.ai_service.rag_service.model = None
    
    intent = agent._classify_intent("me ensine a fazer um bolo de cenoura com chocolate.")
    assert intent == "OTHER"

def test_analyze_patient_triage_valid_json(mocker):
    """Testa o metodo triage analyzer parsing a valid JSON response from the LLM."""
    agent = HealthAgent()
    
    # Mock para garantir que o metodo triage analyzer parsing a valid JSON response from the LLM
    mock_llm_response = '{"nivel": "ALTA", "justificativa": "Paciente relata dor aguda no peito."}'
    mocker.patch.object(agent, '_call_llama', return_value=mock_llm_response)
    
    result = agent.analyze_patient_triage("Dor aguda no peito ontem")
    assert result['nivel'] == "ALTA"
    assert "dor aguda no peito" in result['justificativa'].lower()

def test_analyze_patient_triage_invalid_json(mocker):
    """Testa o metodo triage analyzer handling an invalid JSON response gracefully."""
    agent = HealthAgent()
    
    # Mock para garantir que o metodo triage analyzer handling an invalid JSON response gracefully
    mock_llm_response = 'Aqui está a triagem: {"nivel": "ALTA", "justificativa": "Sem fechar aspas}'
    mocker.patch.object(agent, '_call_llama', return_value=mock_llm_response)
    
    result = agent.analyze_patient_triage("Dor no joelho")
    assert result['nivel'] == "BAIXA"
    assert "Erro ao tentar ler o formato devolvido" in result['justificativa']

def test_analyze_patient_triage_missing_keys(mocker):
    """Testa o metodo triage analyzer handling valid JSON but missing required keys."""
    agent = HealthAgent()
    
    # Mock para garantir que o metodo triage analyzer handling valid JSON but missing required keys
    mock_llm_response = '{"level_priority": "MEDIA", "reason": "Tosse seca."}'
    mocker.patch.object(agent, '_call_llama', return_value=mock_llm_response)
    
    result = agent.analyze_patient_triage("Tosse")
    assert result['nivel'] == "BAIXA"
    assert "Erro interno no processamento com a Inteligência Artificial." in result['justificativa']

def test_analyze_patient_triage_api_failure(mocker):
    """Testa o método triage analyzer lidando com uma falha na API (Exceção)."""
    agent = HealthAgent()
    
    # Mock para simular uma falha de rede/API (Exception disparada pelo LLM)
    mocker.patch.object(agent, '_call_llama', side_effect=Exception("API offline"))
    
    result = agent.analyze_patient_triage("Dor aguda no peito ontem")
    # O fallback heurístico deve tratar o erro e retornar BAIXA com justificativa padrão de erro
    assert result['nivel'] == "BAIXA"
    assert "Erro interno no processamento com a Inteligência Artificial." in result['justificativa']

def test_generate_daily_report_no_chats(mocker):
    """Testa a geração de relatório quando não há interações no dia."""
    agent = HealthAgent()
    mocker.patch('app.services.ai_service.ChatHistoryRepository.get_chats_for_report', return_value=[])
    mocker.patch('app.services.ai_service.DailyReportRepository.get_by_patient_and_date', return_value=None)
    
    mocker.patch('app.services.ai_service.DailyReportRepository.create_report')
    result = agent.generate_daily_report("pat123")
    assert result[0] is None

def test_generate_daily_report_success(mocker):
    """Testa a geração de relatório diário novo."""
    agent = HealthAgent()
    
    mock_chat1 = mocker.MagicMock(message="Dor de cabeça", response="Tome água")
    mocker.patch('app.services.ai_service.ChatHistoryRepository.get_chats_for_report', return_value=[mock_chat1])
    mocker.patch('app.services.ai_service.DailyReportRepository.get_by_patient_and_date', return_value=None)
    mocker.patch('app.services.ai_service.DailyReportRepository.create_report')
    mocker.patch('app.services.ai_service.DailyReportRepository.update_report')
    
    mock_json = '{"resumo_dia": "Paciente relatou dor", "alertas_acs": "Nenhum", "sintomas_chaves": ["dor"], "orientacoes_dadas": ["água"]}'
    mocker.patch.object(agent, '_call_llama', return_value=mock_json)
    
    mock_repo = mocker.patch('app.services.ai_service.DailyReportRepository.create_report')
    
    result = agent.generate_daily_report("pat123")
    
    assert "Paciente relatou dor" in result[0]
    mock_repo.assert_called_once()

def test_update_patient_context_no_chats(mocker):
    """Testa atualização de contexto quando não há chats recentes."""
    agent = HealthAgent()
    mocker.patch('app.services.ai_service.ChatHistoryRepository.get_chats_for_context', return_value=[])
    mock_context = mocker.MagicMock()
    mocker.patch('app.services.ai_service.PatientContextRepository.get_context_by_patient', return_value=mock_context)
    
    result = agent.update_patient_context("pat123")
    assert result == mock_context.context_data

def test_update_patient_context_success(mocker):
    """Testa atualização de contexto clínico do paciente."""
    agent = HealthAgent()
    mock_chat1 = mocker.MagicMock(message="Dor", response="A")
    mocker.patch('app.services.ai_service.ChatHistoryRepository.get_chats_for_context', return_value=[mock_chat1])
    mocker.patch('app.services.ai_service.PatientContextRepository.get_context_by_patient', return_value=None)
    
    mock_json = '{"nome_do_paciente": "João", "sintomas_relatados": ["Dor"], "medicacoes_relatadas": [], "acoes_recomendadas_pela_ia": [], "observacoes_adicionais": ""}'
    mocker.patch.object(agent, '_call_llama', return_value=mock_json)
    
    mock_repo = mocker.patch('app.services.ai_service.PatientContextRepository.create_context')
    
    result = agent.update_patient_context("pat123")
    assert "nome_do_paciente" in result
    mock_repo.assert_called_once()
