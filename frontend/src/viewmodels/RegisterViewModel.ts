import { api } from '../services/api';

export class RegisterViewModel {
  async register(email: string, password: string, name: string, role: 'PATIENT' | 'ACS')
  {
    const res = await api.post('/auth/register', { email, password, name, role });
    return res.data;
  }
}
