from app.extensions.sql_alchemy import db
from app.models.patient_group import PatientGroup
from app.models.patient import Patient

class PatientGroupRepository:

    def create(self, patient_group: PatientGroup) -> PatientGroup:
        db.session.add(patient_group)
        db.session.commit()
        return patient_group

    def get_by_id(self, group_id: str) -> PatientGroup:
        return PatientGroup.query.get(group_id)

    def get_all_by_agent(self, agent_id: str) -> list[PatientGroup]:
        return PatientGroup.query.filter_by(agent_id=agent_id).all()

    def update(self, group: PatientGroup) -> PatientGroup:
        db.session.commit()
        return group

    def delete(self, group: PatientGroup) -> None:
        db.session.delete(group)
        db.session.commit()

    def add_patient_to_group(self, group: PatientGroup, patient: Patient) -> None:
        if patient not in group.patients:
            group.patients.append(patient)
            db.session.commit()

    def remove_patient_from_group(self, group: PatientGroup, patient: Patient) -> None:
        if patient in group.patients:
            group.patients.remove(patient)
            db.session.commit()
