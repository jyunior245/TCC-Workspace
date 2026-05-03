import pytest
import json
from datetime import datetime
import numpy as np
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

def test_classify_intent_embeddings_success(mocker):
    """Testa a classificação de intenção via Embeddings (RAG model ativo)."""
    # Mock do rag_service para ter um modelo de embeddings fake
    class FakeModel:
        def encode(self, texts):
            return [np.array([1.0, 0.0, 0.0]) for _ in texts]
            
    agent = HealthAgent()
    if hasattr(agent, '_intent_embeddings_cache'):
        delattr(agent, '_intent_embeddings_cache')
        
    mocker.patch('app.services.ai_service.rag_service.model', FakeModel())
    
    mock_dot = mocker.patch('app.services.ai_service.np.dot')
    mock_dot.side_effect = [0.9, 0.1, 0.1] # EMERGENCY ganha
    
    intent = agent._classify_intent("dor no peito")
    assert intent == "EMERGENCY"

def test_generate_daily_report_update_existing_no_new_chats(mocker):
    """Testa a atualização incremental de relatório diário sem novas interações."""
    agent = HealthAgent()
    
    mock_report = mocker.MagicMock(updated_at=datetime.utcnow(), content="Relatório antigo")
    mocker.patch('app.services.ai_service.DailyReportRepository.get_by_patient_and_date', return_value=mock_report)
    mocker.patch('app.services.ai_service.ChatHistoryRepository.get_chats_for_report', return_value=[])
    
    result = agent.generate_daily_report("pat123", update_existing=True)
    assert result[0] == "Relatório antigo"
    assert "Não há novas mensagens" in result[1]

def test_generate_daily_report_update_existing_success(mocker):
    """Testa a atualização incremental de relatório diário com novas interações."""
    agent = HealthAgent()
    
    mock_report = mocker.MagicMock(updated_at=datetime.utcnow(), content="Relatório antigo")
    mock_chat = mocker.MagicMock(message="Nova dor", response="Tomar remédio", intent="HEALTH_QUERY")
    mock_chat.timestamp.strftime.return_value = "10:00"
    
    mocker.patch('app.services.ai_service.DailyReportRepository.get_by_patient_and_date', return_value=mock_report)
    mocker.patch('app.services.ai_service.ChatHistoryRepository.get_chats_for_report', return_value=[mock_chat])
    
    mock_json = 'Relatório Antigo atualizado com nova dor'
    mocker.patch.object(agent, '_call_llama', return_value=mock_json)
    mock_update = mocker.patch('app.services.ai_service.DailyReportRepository.update_report')
    
    result = agent.generate_daily_report("pat123", update_existing=True)
    assert "Relatório Antigo" in result[0]
    mock_update.assert_called_once()

def test_get_response_success(mocker):
    """Testa o fluxo principal de get_response."""
    agent = HealthAgent()
    
    mocker.patch.object(agent, '_classify_intent', return_value="HEALTH_QUERY")
    mocker.patch('app.services.ai_service.ChatHistoryRepository.get_recent_chats', return_value=[])
    mocker.patch('app.services.ai_service.rag_service.query_protocols_with_sources', return_value=("Contexto", ["Fonte 1"]))
    mocker.patch.object(agent, '_call_llama_chat', return_value="Resposta da IA")
    mock_save = mocker.patch('app.services.ai_service.ChatHistoryRepository.save_chat')
    
    response = agent.get_response("Estou com dor de cabeça", user_id="user1")
    
    assert response == "Resposta da IA"
    mock_save.assert_called_once_with("user1", "Estou com dor de cabeça", "Resposta da IA", "HEALTH_QUERY")

def test_get_response_greeting_intent(mocker):
    """Testa get_response com intent GREETING — RAG não deve ser acionado."""
    agent = HealthAgent()

    mocker.patch.object(agent, '_classify_intent', return_value="GREETING")
    mocker.patch('app.services.ai_service.ChatHistoryRepository.get_recent_chats', return_value=[])
    mock_rag = mocker.patch('app.services.ai_service.rag_service.query_protocols_with_sources')
    mocker.patch.object(agent, '_call_llama_chat', return_value="Olá! Como posso te ajudar hoje?")
    mock_save = mocker.patch('app.services.ai_service.ChatHistoryRepository.save_chat')

    response = agent.get_response("oi", user_id="user1")

    assert response == "Olá! Como posso te ajudar hoje?"
    mock_rag.assert_not_called()
    mock_save.assert_called_once_with("user1", "oi", "Olá! Como posso te ajudar hoje?", "GREETING")

def test_get_response_emergency_intent(mocker):
    """Testa get_response com intent EMERGENCY — RAG deve ser acionado e chat persistido."""
    agent = HealthAgent()

    mocker.patch.object(agent, '_classify_intent', return_value="EMERGENCY")
    mocker.patch('app.services.ai_service.ChatHistoryRepository.get_recent_chats', return_value=[])
    mock_rag = mocker.patch(
        'app.services.ai_service.rag_service.query_protocols_with_sources',
        return_value=("Protocolo de emergência cardíaca.", ["Manual_SUS.pdf"])
    )
    mocker.patch.object(agent, '_call_llama_chat', return_value="Ligue imediatamente para o SAMU: 192.")
    mock_save = mocker.patch('app.services.ai_service.ChatHistoryRepository.save_chat')

    response = agent.get_response("estou com dor no peito", user_id="user1")

    assert response == "Ligue imediatamente para o SAMU: 192."
    mock_rag.assert_called_once()
    mock_save.assert_called_once_with("user1", "estou com dor no peito", "Ligue imediatamente para o SAMU: 192.", "EMERGENCY")

def test_get_response_no_user_id(mocker):
    """Testa get_response sem user_id — chat não deve ser persistido no banco."""
    agent = HealthAgent()

    mocker.patch.object(agent, '_classify_intent', return_value="HEALTH_QUERY")
    mocker.patch(
        'app.services.ai_service.rag_service.query_protocols_with_sources',
        return_value=("Contexto SUS", [])
    )
    mocker.patch.object(agent, '_call_llama_chat', return_value="Resposta sem usuário identificado")
    mock_save = mocker.patch('app.services.ai_service.ChatHistoryRepository.save_chat')

    response = agent.get_response("estou com febre")  # Sem user_id

    assert response == "Resposta sem usuário identificado"
    mock_save.assert_not_called()

def test_update_patient_context_updates_existing(mocker):
    """Testa que update_patient_context aciona update_context (e não create_context) quando já há contexto salvo."""
    agent = HealthAgent()
    mock_chat = mocker.MagicMock(message="Febre alta", response="Tome paracetamol")
    mocker.patch('app.services.ai_service.ChatHistoryRepository.get_chats_for_context', return_value=[mock_chat])

    mock_existing_context = mocker.MagicMock()
    mock_existing_context.updated_at = None
    mock_existing_context.context_data = {"nome_do_paciente": "João"}
    mocker.patch('app.services.ai_service.PatientContextRepository.get_context_by_patient', return_value=mock_existing_context)

    mock_json = '{"nome_do_paciente": "João", "sintomas_relatados": ["Febre"], "medicacoes_relatadas": [], "acoes_recomendadas_pela_ia": [], "observacoes_adicionais": ""}'
    mocker.patch.object(agent, '_call_llama', return_value=mock_json)

    mock_user = mocker.MagicMock()
    mock_user.name = "João"
    mocker.patch('app.services.ai_service.UserRepository.get_user_by_id', return_value=mock_user)

    mock_update = mocker.patch('app.services.ai_service.PatientContextRepository.update_context')
    mock_create = mocker.patch('app.services.ai_service.PatientContextRepository.create_context')

    result = agent.update_patient_context("pat123")

    assert result is not None
    assert "nome_do_paciente" in result
    mock_update.assert_called_once()
    mock_create.assert_not_called()

def test_update_patient_context_invalid_json(mocker):
    """Testa que update_patient_context retorna None com segurança quando o LLM retorna JSON inválido."""
    agent = HealthAgent()
    mock_chat = mocker.MagicMock(message="Tosse", response="Beba água")
    mocker.patch('app.services.ai_service.ChatHistoryRepository.get_chats_for_context', return_value=[mock_chat])
    mocker.patch('app.services.ai_service.PatientContextRepository.get_context_by_patient', return_value=None)

    mocker.patch.object(agent, '_call_llama', return_value="Não consigo responder agora.")

    result = agent.update_patient_context("pat123")

    assert result is None  # Fallback seguro: sem contexto anterior e JSON inválido retorna None

def test_generate_daily_report_db_save_error(mocker):
    """Testa que o serviço retorna o conteúdo gerado mesmo quando o banco falha ao salvar."""
    agent = HealthAgent()

    mock_chat = mocker.MagicMock(message="Dor de cabeça", response="Tome água")
    mocker.patch('app.services.ai_service.ChatHistoryRepository.get_chats_for_report', return_value=[mock_chat])
    mocker.patch('app.services.ai_service.DailyReportRepository.get_by_patient_and_date', return_value=None)
    mocker.patch.object(agent, '_call_llama', return_value="Relatório gerado com sucesso pelo LLM")
    mocker.patch(
        'app.services.ai_service.DailyReportRepository.create_report',
        side_effect=Exception("DB Connection Error")
    )

    result_content, result_message = agent.generate_daily_report("pat123")

    assert result_content == "Relatório gerado com sucesso pelo LLM"
    assert "erro ao salvar no banco" in result_message.lower()
