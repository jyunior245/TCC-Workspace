import pytest
import base64
from unittest.mock import mock_open
from app.services.voice_service import VoiceService

@pytest.fixture
def service(mocker):
    # Mocking pygame para evitar que o ambiente de teste exija drivers de áudio/video
    mocker.patch('app.services.voice_service.pygame')
    return VoiceService(init_pygame=False)

def test_sanitize_text(service):
    """Testa se o serviço limpa corretamente prefixes de diálogo e fontes."""
    raw_text = "U: Qual é o sintoma?\nA: É febre.\n\nFontes: Protocolo X\nIsso é um teste real."
    cleaned = service._sanitize_text(raw_text)
    assert cleaned == "Isso é um teste real."

def test_generate_base64_audio_empty_text(service):
    """Testa a geração com texto vazio ou que fica vazio após sanitização."""
    assert service.generate_base64_audio("") is None
    assert service.generate_base64_audio(None) is None
    assert service.generate_base64_audio("U: \nA: \nFontes:") is None

def test_generate_base64_audio_success(service, mocker):
    """Testa o fluxo feliz da geração de áudio, mockando a parte async e arquivos temporários."""
    # Mock do asyncio para não invocar o edge-tts
    mocker.patch('app.services.voice_service.asyncio.run')
    
    # Mock da leitura de arquivo binário para fingir que um mp3 foi gerado
    mock_file = mocker.patch('builtins.open', mock_open(read_data=b"dummy_audio_data"))
    
    # Mock da exclusão do arquivo
    mocker.patch('app.services.voice_service.os.path.exists', return_value=True)
    mock_remove = mocker.patch('app.services.voice_service.os.remove')
    
    result = service.generate_base64_audio("Olá mundo")
    
    expected_b64 = base64.b64encode(b"dummy_audio_data").decode('utf-8')
    assert result == expected_b64
    mock_file.assert_called_once()
    mock_remove.assert_called_once()

def test_generate_base64_audio_exception(service, mocker):
    """Testa se o método lida de forma segura com exceções durante o processo."""
    mocker.patch('app.services.voice_service.asyncio.run', side_effect=Exception("Edge-tts falhou"))
    
    result = service.generate_base64_audio("Olá mundo")
    
    assert result is None
