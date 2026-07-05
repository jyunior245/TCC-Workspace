import pytest
import json
import firebase_admin.exceptions
from app.services.auth_service import AuthService

class DummyFirebaseAdminError(firebase_admin.exceptions.FirebaseError):
    """Mock de classe para simular exceptions reais do Firebase"""
    def __init__(self, message):
        super().__init__(code="UNKNOWN", message=message)

class DummyPyrebaseError(Exception):
    """Mock de classe para simular exceptions reais do Firebase"""
    def __init__(self, json_payload):
        self.args = (None, json_payload)

def test_parse_firebase_error_admin_error():
    """Testa o parse de um erro real do Firebase Admin SDK"""
    error = DummyFirebaseAdminError("Usuário não encontrado.")
    result = AuthService._parse_firebase_error(error)
    assert "Erro Administrativo Firebase" in result
    assert "Usuário não encontrado." in result

def test_parse_firebase_error_weak_password():
    """Testa o parse de uma senha fraca do Firebase"""
    error_json = json.dumps({"error": {"message": "WEAK_PASSWORD"}})
    error = DummyPyrebaseError(error_json)
    result = AuthService._parse_firebase_error(error)
    assert result == "A senha deve ter pelo menos 6 caracteres."

def test_parse_firebase_error_email_exists():
    """Testa o parse de um e-mail já cadastrado no Firebase"""
    error_json = json.dumps({"error": {"message": "EMAIL_EXISTS"}})
    error = DummyPyrebaseError(error_json)
    result = AuthService._parse_firebase_error(error)
    assert result == "Este e-mail já está cadastrado."

def test_parse_firebase_error_invalid_email():
    """Testa o parse de um e-mail inválido do Firebase"""
    error_json = json.dumps({"error": {"message": "INVALID_EMAIL"}})
    error = DummyPyrebaseError(error_json)
    result = AuthService._parse_firebase_error(error)
    assert result == "E-mail inválido."

def test_parse_firebase_error_invalid_password():
    """Testa o parse de uma senha inválida do Firebase"""
    error_json = json.dumps({"error": {"message": "INVALID_PASSWORD"}})
    error = DummyPyrebaseError(error_json)
    result = AuthService._parse_firebase_error(error)
    assert result == "Senha incorreta."

def test_parse_firebase_error_user_not_found():
    """Testa o parse de um usuário não encontrado no Firebase"""
    error_json = json.dumps({"error": {"message": "USER_NOT_FOUND"}})
    error = DummyPyrebaseError(error_json)
    result = AuthService._parse_firebase_error(error)
    assert result == "Usuário não encontrado."

def test_parse_firebase_error_unknown_pyrebase_error():
    """Testa o parse de um erro desconhecido do Firebase"""
    error_json = json.dumps({"error": {"message": "SOME_NEW_ERROR_CODE"}})
    error = DummyPyrebaseError(error_json)
    result = AuthService._parse_firebase_error(error)
    assert "SOME_NEW_ERROR_CODE" in result

def test_parse_firebase_error_generic_exception():
    """Testa o parse de uma exceção genérica do Python"""
    error = Exception("Algo deu errado.")
    result = AuthService._parse_firebase_error(error)
    assert "Erro desconhecido:" in result
    assert "Algo deu errado." in result

def test_create_firebase_user_failure(mocker):
    """Testa a falha na criação de um usuário no Firebase e o tratamento da exceção."""
    mock_auth = mocker.patch('app.services.auth_service.auth')
    # Força a exception de email já existente simulando erro da API do Firebase
    error_json = json.dumps({"error": {"message": "EMAIL_EXISTS"}})
    mock_auth.create_user_with_email_and_password.side_effect = DummyPyrebaseError(error_json)
    
    # Desabilita o Admin SDK localmente para forçar o fluxo Pyrebase
    mocker.patch('app.services.auth_service.auth_admin', None)
    
    with pytest.raises(Exception) as excinfo:
        AuthService.create_firebase_user("test@test.com", "123456")
    
    # Verifica se o erro foi tratado e formatado corretamente pelo serviço
    assert str(excinfo.value) == "Este e-mail já está cadastrado."

def test_create_firebase_user_admin_sdk(mocker):
    """Testa a criação de usuário usando Admin SDK."""
    mock_auth_admin = mocker.patch('app.services.auth_service.auth_admin')
    mock_record = mocker.MagicMock()
    mock_record.uid = "new_uid_123"
    mock_auth_admin.create_user.return_value = mock_record
    
    result = AuthService.create_firebase_user("test@admin.com", "senhafortona")
    
    assert result == {'localId': 'new_uid_123'}
    mock_auth_admin.create_user.assert_called_once_with(email="test@admin.com", password="senhafortona")

def test_login_firebase_user_success(mocker):
    """Testa o login com sucesso usando Pyrebase."""
    mock_auth = mocker.patch('app.services.auth_service.auth')
    mock_auth.sign_in_with_email_and_password.return_value = {"idToken": "token123"}
    
    result = AuthService.login_firebase_user("test@test.com", "123456")
    
    assert result == {"idToken": "token123"}
    mock_auth.sign_in_with_email_and_password.assert_called_once()

def test_delete_firebase_user(mocker):
    """Testa exclusão de conta via idToken no Pyrebase."""
    mock_auth = mocker.patch('app.services.auth_service.auth')
    AuthService.delete_firebase_user("token123")
    mock_auth.delete_user_account.assert_called_once_with("token123")

def test_admin_update_user_email(mocker):
    """Testa atualização de e-mail via Admin SDK."""
    mock_auth_admin = mocker.patch('app.services.auth_service.auth_admin')
    
    result = AuthService.admin_update_user_email("uid_123", "novo@email.com")
    
    assert result is True
    mock_auth_admin.update_user.assert_called_once_with("uid_123", email="novo@email.com")

def test_send_verification_for_new_email(mocker):
    """Testa envio de verificação de e-mail mockando API REST do Google."""
    mock_auth_admin = mocker.patch('app.services.auth_service.auth_admin')
    mock_auth_admin.create_custom_token.return_value = b'custom_token_123'
    mocker.patch('app.services.auth_service.os.getenv', return_value="fake_api_key")
    
    mock_requests = mocker.patch('app.services.auth_service.requests')
    
    # Mock das duas respostas de requests.post
    mock_res_token = mocker.MagicMock()
    mock_res_token.status_code = 200
    mock_res_token.json.return_value = {'idToken': 'id_token_123'}
    
    mock_res_verify = mocker.MagicMock()
    mock_res_verify.status_code = 200
    
    mock_requests.post.side_effect = [mock_res_token, mock_res_verify]
    
    result = AuthService.send_verification_for_new_email("uid_123", "novo@email.com")
    
    assert result is True
    assert mock_requests.post.call_count == 2

def test_send_password_reset_email_success(mocker):
    '''Teste de envio de email de recuperação de senha com sucesso.'''
    mock_auth = mocker.patch('app.services.auth_service.auth')
    AuthService.send_password_reset_email("test@test.com")
    mock_auth.send_password_reset_email.assert_called_once_with("test@test.com")

def test_send_password_reset_email_failure(mocker):
    '''Teste de envio de email de recuperação de senha sem sucesso'''
    mock_auth = mocker.patch('app.services.auth_service.auth')
    error_json = json.dumps({"error": {"message": "USER_NOT_FOUND"}})
    mock_auth.send_password_reset_email.side_effect = DummyPyrebaseError(error_json)
    
    with pytest.raises(Exception) as excinfo:
        AuthService.send_password_reset_email("test@test.com")
    
    assert str(excinfo.value) == "Usuário não encontrado."

def test_admin_update_user_password_success(mocker):
    '''Teste de atualização de senha via Admin SDK com sucesso.'''
    mock_auth_admin = mocker.patch('app.services.auth_service.auth_admin')
    
    result = AuthService.admin_update_user_password("uid_123", "novasenha")
    
    assert result is True
    mock_auth_admin.update_user.assert_called_once_with("uid_123", password="novasenha")

def test_admin_update_user_password_no_admin_sdk(mocker):
    '''Teste de atualização de senha via Admin SDK sem Admin SDK'''
    mocker.patch('app.services.auth_service.auth_admin', None)
    
    with pytest.raises(Exception) as excinfo:
        AuthService.admin_update_user_password("uid_123", "novasenha")
        
    assert "Admin SDK not configured" in str(excinfo.value)

def test_admin_update_user_password_failure(mocker):
    '''Teste de atualização de senha via Admin SDK sem sucesso'''
    mock_auth_admin = mocker.patch('app.services.auth_service.auth_admin')
    mock_auth_admin.update_user.side_effect = DummyFirebaseAdminError("Erro ao atualizar")
    
    with pytest.raises(Exception) as excinfo:
        AuthService.admin_update_user_password("uid_123", "novasenha")
        
    assert "Erro Administrativo Firebase" in str(excinfo.value)

def test_delete_user_by_uid_success(mocker):
    '''Teste de deleção de usuário via Admin SDK com sucesso.'''    
    mock_auth_admin = mocker.patch('app.services.auth_service.auth_admin')
    AuthService.delete_user_by_uid("uid_123")
    mock_auth_admin.delete_user.assert_called_once_with("uid_123")

def test_delete_user_by_uid_no_admin_sdk(mocker):
    '''Teste de deleção de usuário sem Admin SDK'''
    mocker.patch('app.services.auth_service.auth_admin', None)
    
    with pytest.raises(Exception) as excinfo:
        AuthService.delete_user_by_uid("uid_123")
        
    assert "Admin SDK not configured" in str(excinfo.value)

def test_delete_user_by_uid_failure(mocker):
    '''Teste de deleção de usuário sem sucesso.'''
    mock_auth_admin = mocker.patch('app.services.auth_service.auth_admin')
    mock_auth_admin.delete_user.side_effect = DummyFirebaseAdminError("Usuário não existe")
    
    with pytest.raises(Exception) as excinfo:
        AuthService.delete_user_by_uid("uid_123")
        
    assert "Erro Administrativo Firebase" in str(excinfo.value)

def test_send_initial_verification_email_success(mocker):
    '''Teste de envio de email de verificação inicial.'''
    mock_auth_admin = mocker.patch('app.services.auth_service.auth_admin')
    mock_auth_admin.create_custom_token.return_value = b'custom_token_123'
    mocker.patch('app.services.auth_service.os.getenv', return_value="fake_api_key")
    
    mock_requests = mocker.patch('app.services.auth_service.requests')
    
    mock_res_token = mocker.MagicMock()
    mock_res_token.status_code = 200
    mock_res_token.json.return_value = {'idToken': 'id_token_123'}
    
    mock_res_verify = mocker.MagicMock()
    mock_res_verify.status_code = 200
    
    mock_requests.post.side_effect = [mock_res_token, mock_res_verify]
    
    result = AuthService.send_initial_verification_email("uid_123")
    
    assert result is True
    assert mock_requests.post.call_count == 2

def test_send_initial_verification_email_no_admin_sdk(mocker):
    '''Teste de envio de email de verificação inicial sem Admin SDK'''
    mocker.patch('app.services.auth_service.auth_admin', None)
    
    with pytest.raises(Exception) as excinfo:
        AuthService.send_initial_verification_email("uid_123")
        
    assert "Admin SDK not configured" in str(excinfo.value)

def test_send_initial_verification_email_no_api_key(mocker):
    '''Teste de envio de email de verificação inicial sem API KEY'''
    mock_auth_admin = mocker.patch('app.services.auth_service.auth_admin')
    mock_auth_admin.create_custom_token.return_value = b'custom_token_123'
    mocker.patch('app.services.auth_service.os.getenv', return_value=None)
    
    with pytest.raises(Exception) as excinfo:
        AuthService.send_initial_verification_email("uid_123")
        
    assert "FIREBASE_API_KEY" in str(excinfo.value)

def test_send_initial_verification_email_first_post_fails(mocker):
    '''Teste de envio de email de verificação inicial com falha no primeiro post'''
    mock_auth_admin = mocker.patch('app.services.auth_service.auth_admin')
    mock_auth_admin.create_custom_token.return_value = b'custom_token_123'
    mocker.patch('app.services.auth_service.os.getenv', return_value="fake_api_key")
    
    mock_requests = mocker.patch('app.services.auth_service.requests')
    
    mock_res_token = mocker.MagicMock()
    mock_res_token.status_code = 400
    mock_res_token.text = "Bad Request"
    
    mock_requests.post.side_effect = [mock_res_token]
    
    with pytest.raises(Exception) as excinfo:
        AuthService.send_initial_verification_email("uid_123")
        
    assert "Falha ao obter ID Token" in str(excinfo.value)

def test_send_initial_verification_email_second_post_fails(mocker):
    '''Teste de envio de email de verificação inicial com falha no segundo post'''
    mock_auth_admin = mocker.patch('app.services.auth_service.auth_admin')
    mock_auth_admin.create_custom_token.return_value = b'custom_token_123'
    mocker.patch('app.services.auth_service.os.getenv', return_value="fake_api_key")
    
    mock_requests = mocker.patch('app.services.auth_service.requests')
    
    mock_res_token = mocker.MagicMock()
    mock_res_token.status_code = 200
    mock_res_token.json.return_value = {'idToken': 'id_token_123'}
    
    mock_res_verify = mocker.MagicMock()
    mock_res_verify.status_code = 400
    mock_res_verify.text = "Error sending email"
    
    mock_requests.post.side_effect = [mock_res_token, mock_res_verify]
    
    with pytest.raises(Exception) as excinfo:
        AuthService.send_initial_verification_email("uid_123")
        
    assert "Falha ao enviar e-mail de verificação" in str(excinfo.value)

def test_login_firebase_user_failure(mocker):
    '''Teste de login via Firebase com falha.'''
    mock_auth = mocker.patch('app.services.auth_service.auth')
    error_json = json.dumps({"error": {"message": "INVALID_PASSWORD"}})
    mock_auth.sign_in_with_email_and_password.side_effect = DummyPyrebaseError(error_json)
    
    with pytest.raises(Exception) as excinfo:
        AuthService.login_firebase_user("test@test.com", "wrong_password")
        
    assert str(excinfo.value) == "Senha incorreta."

def test_create_firebase_user_admin_sdk_failure(mocker):
    '''Teste de criação de usuário via Admin SDK sem sucesso.'''
    mock_auth_admin = mocker.patch('app.services.auth_service.auth_admin')
    mock_auth_admin.create_user.side_effect = DummyFirebaseAdminError("Erro ao criar usuário")
    
    with pytest.raises(Exception) as excinfo:
        AuthService.create_firebase_user("test@test.com", "123456")
        
    assert "Erro Administrativo Firebase" in str(excinfo.value)

def test_admin_update_user_email_no_admin_sdk(mocker):
    '''Teste de atualização de e-mail via Admin SDK sem Admin SDK'''
    mocker.patch('app.services.auth_service.auth_admin', None)
    
    with pytest.raises(Exception) as excinfo:
        AuthService.admin_update_user_email("uid_123", "novo@email.com")
        
    assert "Admin SDK not configured" in str(excinfo.value)

def test_admin_update_user_email_failure(mocker):
    '''Teste de atualização de e-mail via Admin SDK sem sucesso'''
    mock_auth_admin = mocker.patch('app.services.auth_service.auth_admin')
    mock_auth_admin.update_user.side_effect = DummyFirebaseAdminError("Erro ao atualizar e-mail")
    
    with pytest.raises(Exception) as excinfo:
        AuthService.admin_update_user_email("uid_123", "novo@email.com")
        
    assert "Erro Administrativo Firebase" in str(excinfo.value)

def test_send_verification_for_new_email_no_admin_sdk(mocker):
    '''Teste de envio de verificação de e-mail sem Admin SDK'''
    mocker.patch('app.services.auth_service.auth_admin', None)
    
    with pytest.raises(Exception) as excinfo:
        AuthService.send_verification_for_new_email("uid_123", "novo@email.com")
        
    assert "Admin SDK not configured" in str(excinfo.value)

def test_send_verification_for_new_email_no_api_key(mocker):
    '''Teste de envio de verificação de e-mail sem API KEY'''
    mock_auth_admin = mocker.patch('app.services.auth_service.auth_admin')
    mock_auth_admin.create_custom_token.return_value = b'custom_token_123'
    mocker.patch('app.services.auth_service.os.getenv', return_value=None)
    
    with pytest.raises(Exception) as excinfo:
        AuthService.send_verification_for_new_email("uid_123", "novo@email.com")
        
    assert "FIREBASE_API_KEY" in str(excinfo.value)

def test_send_verification_for_new_email_first_post_fails(mocker):
    '''Teste de envio de verificação de e-mail sem sucesso no primeiro post'''
    mock_auth_admin = mocker.patch('app.services.auth_service.auth_admin')
    mock_auth_admin.create_custom_token.return_value = b'custom_token_123'
    mocker.patch('app.services.auth_service.os.getenv', return_value="fake_api_key")
    
    mock_requests = mocker.patch('app.services.auth_service.requests')
    
    mock_res_token = mocker.MagicMock()
    mock_res_token.status_code = 400
    mock_res_token.text = "Bad Request"
    
    mock_requests.post.side_effect = [mock_res_token]
    
    with pytest.raises(Exception) as excinfo:
        AuthService.send_verification_for_new_email("uid_123", "novo@email.com")
        
    assert "Falha ao obter ID Token" in str(excinfo.value)

def test_send_verification_for_new_email_second_post_fails(mocker):
    '''Teste de envio de verificação de e-mail sem sucesso no segundo post'''
    mock_auth_admin = mocker.patch('app.services.auth_service.auth_admin')
    mock_auth_admin.create_custom_token.return_value = b'custom_token_123'
    mocker.patch('app.services.auth_service.os.getenv', return_value="fake_api_key")
    
    mock_requests = mocker.patch('app.services.auth_service.requests')
    
    mock_res_token = mocker.MagicMock()
    mock_res_token.status_code = 200
    mock_res_token.json.return_value = {'idToken': 'id_token_123'}
    
    mock_res_verify = mocker.MagicMock()
    mock_res_verify.status_code = 400
    mock_res_verify.text = "Error sending email"
    
    mock_requests.post.side_effect = [mock_res_token, mock_res_verify]
    
    with pytest.raises(Exception) as excinfo:
        AuthService.send_verification_for_new_email("uid_123", "novo@email.com")
        
    assert "Falha ao enviar e-mail de verificação" in str(excinfo.value)

def test_delete_firebase_user_failure(mocker, caplog):
    '''Teste de remoção de usuário Firebase com falha.'''
    mock_auth = mocker.patch('app.services.auth_service.auth')
    mock_auth.delete_user_account.side_effect = Exception("Network Error")
    
    AuthService.delete_firebase_user("token123")
    
    assert "Failed to rollback Firebase user: Network Error" in caplog.text
