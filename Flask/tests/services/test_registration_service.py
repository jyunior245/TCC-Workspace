import pytest
from unittest.mock import MagicMock
from app.services.registration_service import RegistrationService

def test_check_and_activate_user_pseudo_email(mocker, mock_db_session):
    "Testa usuário com email de teste @tcchealth.com"
    # Setup mocks
    mock_fb_user = MagicMock()
    mock_fb_user.email = "test@tcchealth.com"
    mock_fb_user.email_verified = False #Não devera importa por ser um pseudo email
    
    mock_auth_admin_local = mocker.patch('app.services.registration_service.auth_admin')
    mock_auth_admin_local.get_user.return_value = mock_fb_user
    
    mock_user = MagicMock()
    mock_user.is_active = False
    
    mocker.patch('app.services.registration_service.UserRepository.get_user_by_id', return_value=mock_user)
    
    # Executar
    is_active, redirect_dest = RegistrationService.check_and_activate_user("user123")
    
    # Verificar se os retornos foram os esperados
    assert is_active is True
    assert redirect_dest == "dashboard"
    assert mock_user.is_active is True
    mock_db_session.commit.assert_called_once()

def test_check_and_activate_user_verified_email(mocker, mock_db_session):
    """Testa usuário com email de teste @gmail.com"""
    # Setup mocks
    mock_fb_user = MagicMock()
    mock_fb_user.email = "test@gmail.com"
    mock_fb_user.email_verified = True
    
    mock_auth_admin_local = mocker.patch('app.services.registration_service.auth_admin')
    mock_auth_admin_local.get_user.return_value = mock_fb_user
    
    mock_user = MagicMock()
    mock_user.is_active = False
    
    mocker.patch('app.services.registration_service.UserRepository.get_user_by_id', return_value=mock_user)
    
    # Execute
    is_active, redirect_dest = RegistrationService.check_and_activate_user("user123")
    
    # Assert
    assert is_active is True
    assert redirect_dest == "dashboard"
    assert mock_user.is_active is True
    mock_db_session.commit.assert_called_once()

def test_check_and_activate_user_unverified_email(mocker, mock_db_session):
    """Testa usuário com email de teste @gmail.com não verificado"""
    # Setup mocks
    mock_fb_user = MagicMock()
    mock_fb_user.email = "test@gmail.com"
    mock_fb_user.email_verified = False
    
    mock_auth_admin_local = mocker.patch('app.services.registration_service.auth_admin')
    mock_auth_admin_local.get_user.return_value = mock_fb_user
    
    mock_user = MagicMock()
    mock_user.is_active = True
    
    mocker.patch('app.services.registration_service.UserRepository.get_user_by_id', return_value=mock_user)
    
    # Execute
    is_active, redirect_dest = RegistrationService.check_and_activate_user("user123")
    
    # Assert
    assert is_active is False
    assert redirect_dest == "verify_pending"
    assert mock_user.is_active is False # Rolled back to False
    mock_db_session.commit.assert_called_once()

def test_has_completed_profile_no_user(mocker):
    """Testa usuário que não existe no banco de dados"""
    mocker.patch('app.services.registration_service.UserRepository.get_user_by_id', return_value=None)
    
    has_profile, is_active = RegistrationService.has_completed_profile("non_existent_id", "patient")
    assert has_profile is False
    assert is_active is False

def test_has_completed_profile_patient_with_profile(mocker):
    """Testa paciente com perfil completo"""
    mock_user = MagicMock()
    mock_user.patient_profile = True
    mock_user.is_active = True
    
    mocker.patch('app.services.registration_service.UserRepository.get_user_by_id', return_value=mock_user)
    
    has_profile, is_active = RegistrationService.has_completed_profile("user123", "patient")
    assert has_profile is True
    assert is_active is True

def test_has_completed_profile_agent_without_profile(mocker):
    """Testa agente sem perfil completo"""
    mock_user = MagicMock()
    mock_user.agent_profile = None
    mock_user.is_active = True
    
    mocker.patch('app.services.registration_service.UserRepository.get_user_by_id', return_value=mock_user)
    
    has_profile, is_active = RegistrationService.has_completed_profile("user123", "health_agent")
    assert has_profile is False
    assert is_active is True

def test_verify_pending_status_verified(mocker, mock_db_session):
    """Testa quando o e-mail finalmente foi verificado via link."""
    mock_auth_admin = mocker.patch('app.services.registration_service.auth_admin')
    mock_fb_user = MagicMock()
    mock_fb_user.email = "test@real.com"
    mock_fb_user.email_verified = True
    mock_auth_admin.get_user.return_value = mock_fb_user
    
    mock_user = MagicMock()
    mocker.patch('app.services.registration_service.UserRepository.get_user_by_id', return_value=mock_user)
    
    success, email = RegistrationService.verify_pending_status("uid123")
    
    assert success is True
    assert email == "test@real.com"
    assert mock_user.is_active is True
    mock_db_session.commit.assert_called_once()

def test_verify_pending_status_unverified(mocker, mock_db_session):
    """Testa quando o e-mail ainda não foi verificado."""
    mock_auth_admin = mocker.patch('app.services.registration_service.auth_admin')
    mock_fb_user = MagicMock()
    mock_fb_user.email = "test@real.com"
    mock_fb_user.email_verified = False
    mock_auth_admin.get_user.return_value = mock_fb_user
    
    mock_user = MagicMock()
    mocker.patch('app.services.registration_service.UserRepository.get_user_by_id', return_value=mock_user)
    
    success, email = RegistrationService.verify_pending_status("uid123")
    
    assert success is False
    assert email == "test@real.com"
    mock_db_session.commit.assert_not_called()

def test_process_patient_completion(mocker):
    """Testa se os dados do formulário de paciente são mapeados corretamente."""
    mock_form = MagicMock()
    # Simula o .get() e o .getlist() do Flask request.form
    def get_mock(key):
        if key == 'has_potable_water': return 'yes'
        if key == 'num_residents': return '3'
        return None
    mock_form.get.side_effect = get_mock
    mock_form.getlist.return_value = ["Diabete", "Hipertensão"]
    
    mock_repo = mocker.patch('app.services.registration_service.UserRepository.create_patient_profile')
    
    RegistrationService.process_patient_completion("uid123", mock_form)
    
    mock_repo.assert_called_once()
    args, kwargs = mock_repo.call_args
    assert args[0] == "uid123"
    assert args[1]['has_potable_water'] is True
    assert args[1]['num_residents'] == 3
    assert args[1]['chronic_conditions'] == "Diabete,Hipertensão"

def test_process_agent_completion(mocker):
    """Testa se os dados do formulário do agente são mapeados corretamente."""
    mock_form = MagicMock()
    def get_mock(key):
        if key == 'state': return 'SP'
        if key == 'ubs': return 'UBS Centro'
        return None
    mock_form.get.side_effect = get_mock
    
    mock_repo = mocker.patch('app.services.registration_service.UserRepository.create_agent_profile')
    
    RegistrationService.process_agent_completion("uid123", mock_form)
    
    mock_repo.assert_called_once()
    args, kwargs = mock_repo.call_args
    assert args[0] == "uid123"
    assert args[1]['state'] == "SP"
    assert args[1]['ubs'] == "UBS Centro"
