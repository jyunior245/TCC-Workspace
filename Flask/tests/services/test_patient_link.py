import pytest
from app.repositories.user_repository import UserRepository
from app.models.patient import Patient

@pytest.fixture(autouse=True)
def app_ctx(app):
    with app.app_context():
        yield

def test_link_patient_to_agent_success(mocker):
    """Testa vincular paciente a um ACS com sucesso."""
    patient = Patient(id="patient_1", patient_code="ABCDEF", agent_id=None)
    mock_query = mocker.patch('app.models.patient.Patient.query')
    mock_query.filter_by.return_value.first.return_value = patient
    
    mock_commit = mocker.patch('app.extensions.sql_alchemy.db.session.commit')
    
    success, message = UserRepository.link_patient_to_agent("agent_123", "ABCDEF")
    
    assert success is True
    assert message == "Paciente vinculado com sucesso."
    assert patient.agent_id == "agent_123"
    mock_commit.assert_called_once()

def test_link_patient_to_agent_invalid_code(mocker):
    """Testa vincular paciente com código inválido."""
    mock_query = mocker.patch('app.models.patient.Patient.query')
    mock_query.filter_by.return_value.first.return_value = None
    
    success, message = UserRepository.link_patient_to_agent("agent_123", "INVALID")
    
    assert success is False
    assert message == "Código de paciente inválido ou não encontrado."

def test_link_patient_to_agent_already_linked(mocker):
    """Testa vincular paciente que já está vinculado a outro ACS."""
    patient = Patient(id="patient_1", patient_code="ABCDEF", agent_id="other_agent")
    mock_query = mocker.patch('app.models.patient.Patient.query')
    mock_query.filter_by.return_value.first.return_value = patient
    
    success, message = UserRepository.link_patient_to_agent("agent_123", "ABCDEF")
    
    assert success is False
    assert message == "Paciente já está vinculado a outro ACS."

def test_link_patient_to_agent_already_linked_to_me(mocker):
    """Testa vincular paciente que já está vinculado ao próprio ACS."""
    patient = Patient(id="patient_1", patient_code="ABCDEF", agent_id="agent_123")
    mock_query = mocker.patch('app.models.patient.Patient.query')
    mock_query.filter_by.return_value.first.return_value = patient
    
    success, message = UserRepository.link_patient_to_agent("agent_123", "ABCDEF")
    
    assert success is False
    assert message == "Paciente já está vinculado a você."
