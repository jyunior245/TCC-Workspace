import { api } from '../services/api';
import { PatientProfilePayload } from '../models/patientUser';

export class PatientProfileViewModel {
  async submitProfile(token: string, payload: PatientProfilePayload) {
    await api.post('/users/patient/profile', payload, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
  }
}

