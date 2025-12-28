import { Injectable } from '@nestjs/common';
import { UsersService } from '../users/users.service';
import { JwtService } from '@nestjs/jwt';
import { FirebaseService } from '../firebase/firebase.service';
import { ConfigService } from '@nestjs/config';
import axios from 'axios';

@Injectable()
export class AuthService {
  constructor(
    private usersService: UsersService,
    private jwtService: JwtService,
    private firebase: FirebaseService,
    private config: ConfigService,
  ) {}

  async validateUser(email: string, password: string): Promise<any> {
    const apiKey = this.config.get<string>('FIREBASE_API_KEY');
    const url = `https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=${apiKey}`;
    try {
      const { data } = await axios.post(url, { email, password, returnSecureToken: true });
      const user = await this.usersService.findOne(email);
      if (!user) return null;
      return { id: user.id, email: user.email, role: user.role, firebaseUid: data.localId };
    } catch (e) {
      return null;
    }
  }

  async login(user: any) {
    const payload = { email: user.email, sub: user.id, role: user.role };
    return {
      access_token: this.jwtService.sign(payload),
    };
  }

  async register(userData: any) {
    const fbUser = await this.firebase.createUser(userData.email, userData.password, userData.name);
    return this.usersService.create({
      email: userData.email,
      name: userData.name,
      role: userData.role,
      firebaseUid: fbUser.uid,
    });
  }
}
