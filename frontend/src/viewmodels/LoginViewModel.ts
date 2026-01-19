import { api } from '../services/api';

export class LoginViewModel {
  async loginAndRoute(
    email: string,
    password: string,
  ): Promise<{ token: string; role: 'PATIENT' | 'ACS'; profileCompleted: boolean }> {
    const res = await api.post('/auth/login', { email, password });
    const { access_token, user } = res.data;
    return { token: access_token, role: user.role, profileCompleted: user.profileCompleted };
  }
}

