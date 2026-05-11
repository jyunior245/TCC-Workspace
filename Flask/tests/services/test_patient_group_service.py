import pytest
from app.services.patient_group_service import PatientGroupService
from app.repositories.user_repository import UserRepository
from app.models.patient_group import PatientGroup
from app.models.patient import Patient

@pytest.fixture
def service(app):
    with app.app_context():
        yield PatientGroupService()

def test_create_group_empty_name(service):
    """Testa a criação de um grupo com nome vazio."""
    with pytest.raises(ValueError, match="O nome do grupo é obrigatório."):
        service.create_group("", "Desc", "agent_123")
    with pytest.raises(ValueError, match="O nome do grupo é obrigatório."):
        service.create_group("   ", "Desc", "agent_123")

def test_create_group_success(service, mocker):
    """Testa a criação bem-sucedida de um grupo (mockando o repositório)."""
    mocker.patch.object(service.repository, 'create', return_value=PatientGroup(id="group_1", name="Hipertensos", agent_id="agent_123"))
    group = service.create_group(" Hipertensos ", "Pacientes com pressão alta", "agent_123")
    assert group.name == "Hipertensos"
    assert group.id == "group_1"

def test_get_all_groups_by_agent_success(service, mocker):
    """Testa listagem de todos os grupos do ACS."""
    groups = [
        PatientGroup(id="group_1", name="Grupo 1", agent_id="agent_123"),
        PatientGroup(id="group_2", name="Grupo 2", agent_id="agent_123")
    ]
    mocker.patch.object(service.repository, 'get_all_by_agent', return_value=groups)
    
    result = service.get_all_groups_by_agent("agent_123")
    assert len(result) == 2
    assert result[0].name == "Grupo 1"

def test_remove_patient_from_group_success(service, mocker):
    """Testa remover paciente do grupo com sucesso."""
    group = PatientGroup(id="group_1", name="Test", agent_id="agent_123")
    mocker.patch.object(service, 'get_group', return_value=group)
    
    patient = Patient(id="patient_1", agent_id="agent_123")
    mock_query = mocker.patch('app.models.patient.Patient.query')
    mock_query.get.return_value = patient
    
    mock_remove = mocker.patch.object(service.repository, 'remove_patient_from_group')
    
    service.remove_patient_from_group("group_1", "patient_1", "agent_123")
    mock_remove.assert_called_once_with(group, patient)

def test_add_patient_to_group_success(service, mocker):
    """Testa adicionar paciente ao grupo com sucesso."""
    group = PatientGroup(id="group_1", name="Test", agent_id="agent_123")
    mocker.patch.object(service, 'get_group', return_value=group)
    
    patient = Patient(id="patient_1", agent_id="agent_123")
    mock_query = mocker.patch('app.models.patient.Patient.query')
    mock_query.get.return_value = patient
    
    mock_add = mocker.patch.object(service.repository, 'add_patient_to_group')
    
    service.add_patient_to_group("group_1", "patient_1", "agent_123")
    mock_add.assert_called_once_with(group, patient)

def test_update_group_success(service, mocker):
    """Testa update_group alterando o nome do grupo."""
    group = PatientGroup(id="group_1", name="Test", agent_id="agent_123")
    mocker.patch.object(service, 'get_group', return_value=group)
    
    mock_update = mocker.patch.object(service.repository, 'update', return_value=group)
    
    service.update_group("group_1", "agent_123", name="Novo Nome", description=None)
    assert group.name == "Novo Nome"
    mock_update.assert_called_once_with(group)

def test_update_group_no_name_change(service, mocker):
    """Testa update_group sem alterar o nome do grupo."""
    group = PatientGroup(id="group_1", name="Nome Original", description="Desc original", agent_id="agent_123")
    mocker.patch.object(service, 'get_group', return_value=group)
    
    mock_update = mocker.patch.object(service.repository, 'update', return_value=group)
    
    service.update_group("group_1", "agent_123", name="   ", description="Nova desc")
    
    assert group.name == "Nome Original"
    assert group.description == "Nova desc"
    mock_update.assert_called_once_with(group)

def test_delete_group_success(service, mocker):
    """Testa delete_group com sucesso."""
    group = PatientGroup(id="group_1", name="Test", agent_id="agent_123")
    mocker.patch.object(service, 'get_group', return_value=group)
    
    mock_delete = mocker.patch.object(service.repository, 'delete')
    
    service.delete_group("group_1", "agent_123")
    mock_delete.assert_called_once_with(group)

