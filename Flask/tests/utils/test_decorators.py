import pytest
from unittest.mock import MagicMock
from flask import json
from app.utils.decorators import login_required, agent_required, patient_required
import firebase_admin._auth_utils

@pytest.fixture
def mock_flask_env(mocker, app):
    """Mocks de requisição e sessão do Flask."""
    mocker.patch('app.utils.decorators.session', {'user_id': 'user123', 'user_type': 'patient'})
    
    # Adicionando mocks base para passar pelo login_required
    mocker.patch('app.utils.decorators.UserRepository.get_user_by_id_forced', return_value=MagicMock())
    mock_auth = mocker.patch('app.utils.decorators.auth_admin')
    mock_auth.get_user.return_value = True

    req_context = app.test_request_context(json={})
    req_context.push()
    yield
    req_context.pop()

def test_login_required_no_session(mocker, mock_flask_env):
    """Testa login_required quando não há sessão"""
    mocker.patch('app.utils.decorators.session', {})
    
    @login_required
    def dummy_route():
        return "sucesso"
        
    response, status_code = dummy_route()
    assert status_code == 401
    assert b"N\xc3\xa3o autenticado" in response.data or b"autenticado" in response.data

def test_login_required_valid_sync(mocker, mock_flask_env):
    """Testa login_required quando o usuário existe no banco e no Firebase."""
    mock_user = MagicMock()
    mocker.patch('app.utils.decorators.UserRepository.get_user_by_id_forced', return_value=mock_user)
    
    mock_auth_admin = mocker.patch('app.utils.decorators.auth_admin')
    mock_auth_admin.get_user.return_value = True
    
    @login_required
    def dummy_route():
        return "sucesso"
        
    result = dummy_route()
    assert result == "sucesso"

def test_login_required_missing_in_firebase(mocker, mock_flask_env):
    """Testa login_required quando o usuário existe no banco mas foi deletado do Firebase."""
    mock_user = MagicMock()
    mocker.patch('app.utils.decorators.UserRepository.get_user_by_id_forced', return_value=mock_user)
    
    
    class UserNotFoundError(Exception): pass
    firebase_admin._auth_utils.UserNotFoundError = UserNotFoundError
    
    mock_auth_admin = mocker.patch('app.utils.decorators.auth_admin')
    mock_auth_admin.get_user.side_effect = UserNotFoundError("User not found")
    
    mock_delete_local = mocker.patch('app.utils.decorators.UserRepository.delete_user_completely')
    
    @login_required
    def dummy_route():
        return "sucesso"
        
    response, status_code = dummy_route()
    assert status_code == 401
    mock_delete_local.assert_called_once_with('user123')

def test_login_required_missing_in_db(mocker, mock_flask_env):
    """Testa login_required quando o usuário foi deletado do banco mas ainda existe no Firebase."""
    mocker.patch('app.utils.decorators.UserRepository.get_user_by_id_forced', return_value=None)
    
    mock_auth_admin = mocker.patch('app.utils.decorators.auth_admin')
    mock_auth_admin.get_user.return_value = True
    
    mock_delete_firebase = mocker.patch('app.utils.decorators.AuthService.delete_user_by_uid')
    
    @login_required
    def dummy_route():
        return "success"
        
    response, status_code = dummy_route()
    assert status_code == 401
    mock_delete_firebase.assert_called_once_with('user123')

def test_agent_required_forbidden(mocker, mock_flask_env):
    """Testa agent_required negando acesso a um patient."""
    mocker.patch('app.utils.decorators.session', {'user_id': 'user123', 'user_type': 'patient'})
    
    @agent_required
    def dummy_route():
        return "sucesso"
        
    response, status_code = dummy_route()
    assert status_code == 403

def test_patient_required_forbidden(mocker, mock_flask_env):
    """Testa patient_required negando acesso a um health_agent."""
    mocker.patch('app.utils.decorators.session', {'user_id': 'user123', 'user_type': 'health_agent'})
    
    @patient_required
    def dummy_route():
        return "sucesso"
        
    response, status_code = dummy_route()
    assert status_code == 403
