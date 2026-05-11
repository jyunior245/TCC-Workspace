from app.repositories.patient_group_repository import PatientGroupRepository
from app.models.patient_group import PatientGroup
from app.models.patient import Patient

class PatientGroupService:
    def __init__(self):
        self.repository = PatientGroupRepository()

    def create_group(self, name: str, description: str, agent_id: str) -> PatientGroup:
        # Pela regra de negócio, não há impedimento de nomes repetidos, mas podemos validar se o nome não é vazio.
        if not name or not name.strip():
            raise ValueError("O nome do grupo é obrigatório.")
        
        new_group = PatientGroup(
            name=name.strip(),
            description=description.strip() if description else None,
            agent_id=agent_id
        )
        return self.repository.create(new_group)

    def get_group(self, group_id: str, agent_id: str) -> PatientGroup:
        group = self.repository.get_by_id(group_id)
        if not group:
            raise ValueError("Grupo não encontrado.")
        if group.agent_id != agent_id:
            raise PermissionError("Acesso negado. Este grupo pertence a outro agente.")
        return group

    def get_all_groups_by_agent(self, agent_id: str) -> list[PatientGroup]:
        return self.repository.get_all_by_agent(agent_id)

    def update_group(self, group_id: str, agent_id: str, name: str, description: str) -> PatientGroup:
        group = self.get_group(group_id, agent_id)
        if name and name.strip():
            group.name = name.strip()
        if description is not None:
            group.description = description.strip()
        
        return self.repository.update(group)

    def delete_group(self, group_id: str, agent_id: str) -> None:
        group = self.get_group(group_id, agent_id)
        self.repository.delete(group)

    def add_patient_to_group(self, group_id: str, patient_id: str, agent_id: str) -> None:
        group = self.get_group(group_id, agent_id)
        patient = Patient.query.get(patient_id)
        
        if not patient:
            raise ValueError("Paciente não encontrado.")
        
        if patient.agent_id != agent_id:
            raise PermissionError("Não é possível adicionar um paciente que não está vinculado a você.")
            
        self.repository.add_patient_to_group(group, patient)

    def remove_patient_from_group(self, group_id: str, patient_id: str, agent_id: str) -> None:
        group = self.get_group(group_id, agent_id)
        patient = Patient.query.get(patient_id)
        
        if not patient:
            raise ValueError("Paciente não encontrado.")
            
        self.repository.remove_patient_from_group(group, patient)
