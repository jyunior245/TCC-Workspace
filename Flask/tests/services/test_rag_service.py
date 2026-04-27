import pytest
from app.services.rag_service import RAGService

@pytest.fixture
def mock_rag(mocker):
    # Mock das bibliotecas pesadas de IA e VectorDB para evitar carga e erros de ambiente
    mock_client = mocker.patch('app.services.rag_service.PersistentClient')
    # Configura o count do mock para evitar erro na comparação "count > 0"
    mock_client.return_value.get_or_create_collection.return_value.count.return_value = 0
    
    mocker.patch('app.services.rag_service.SentenceTransformer')
    
    # Cria uma nova instância com os mocks injetados
    service = RAGService()
    
    import numpy as np
    # Mock do encode do sentence_transformers
    service.model.encode.return_value = np.array([0.1, 0.2, 0.3])
    return service

def test_add_protocol(mock_rag):
    """Testa a adição de um texto chunkado na collection do ChromaDB."""
    texto_longo = "Este é um texto " * 100 # Texto suficientemente grande para não ser ignorado
    mock_rag.add_protocol(texto_longo, {"source": "manual.pdf", "page": 1})
    
    # Verifica se a chamada para adicionar no banco vetorial ocorreu
    mock_rag.collection.add.assert_called()

def test_query_protocols_success(mock_rag):
    """Testa a busca simples no banco vetorial que retorna apenas o contexto em texto."""
    mock_rag.collection.query.return_value = {
        'documents': [["Tratamento para dengue com paracetamol e hidratação."]]
    }
    
    result = mock_rag.query_protocols("tratamento dengue", n_results=1)
    assert result == "Tratamento para dengue com paracetamol e hidratação."

def test_query_protocols_with_sources_success(mock_rag):
    """Testa a busca com referências bibliográficas do PDF."""
    mock_rag.collection.query.return_value = {
        'documents': [["Tratamento para diabetes."]],
        'metadatas': [[{"source": "Manual_Diabetes.pdf", "page": 15}]]
    }
    
    context, sources = mock_rag.query_protocols_with_sources("diabetes", n_results=1)
    
    assert context == "Tratamento para diabetes."
    assert "Manual_Diabetes.pdf (p.15)" in sources

def test_query_offline_mode(mock_rag):
    """Testa o fallback seguro se o modelo falhar ou rodar offline."""
    mock_rag.offline_mode = True
    
    result = mock_rag.query_protocols("covid")
    assert result == "Consulte o manual do SUS para orientações sobre: covid"
    
    context, sources = mock_rag.query_protocols_with_sources("covid")
    assert context == "Consulte o manual do SUS para orientações sobre: covid"
    assert sources == []

def test_query_exception_fallback(mock_rag, mocker):
    """Testa o fallback caso a query lance uma exceção (ex: banco corrompido)."""
    mock_rag.collection.query.side_effect = Exception("ChromaDB Error")
    
    result = mock_rag.query_protocols("vacina")
    assert result == "Consulte o manual do SUS para orientações sobre: vacina"
