import { api } from '../services/api';

export class LoginViewModel {
  async loginAndRoute(email: string, password: string): Promise<{ route: string; token: string; role: 'PATIENT' | 'ACS'; }>
  {
    const res = await api.post('/auth/login', { email, password });
    const { access_token, user } = res.data;
    const route = user.role === 'ACS' ? 'ACSHome' : 'PatientHome';
    return { route, token: access_token, role: user.role };
  }
}

