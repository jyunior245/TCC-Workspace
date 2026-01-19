import { api } from '../services/api';
import { AcsProfilePayload } from '../models/acsUser';

export class AcsProfileViewModel {
  async submitProfile(token: string, payload: AcsProfilePayload) {
    await api.post('/users/acs/profile', payload, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
  }

  generateFunctionalRegistration(): string {
    const random = Math.random().toString(36).substring(2, 8).toUpperCase();
    return `ACS-${random}`;
  }
}

