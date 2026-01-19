import { Injectable, Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { initializeApp, cert, ServiceAccount } from 'firebase-admin/app';
import { getAuth } from 'firebase-admin/auth';
import { readFileSync } from 'fs';

@Injectable()
export class FirebaseService {
  private logger = new Logger(FirebaseService.name);

  constructor(private config: ConfigService) {
    const credsPath = this.config.get<string>('FIREBASE_ADMIN_CREDENTIALS_PATH');
    if (!credsPath) {
      this.logger.warn('FIREBASE_ADMIN_CREDENTIALS_PATH not set');
      return;
    }
    const json = readFileSync(credsPath, 'utf-8');
    const serviceAccount = JSON.parse(json) as ServiceAccount;
    initializeApp({ credential: cert(serviceAccount) });
    this.logger.log('Firebase Admin initialized');
  }

  auth() {
    return getAuth();
  }

  async createUser(email: string, password: string, displayName?: string) {
    return this.auth().createUser({ email, password, displayName });
  }

  async sendEmailVerification(uid: string) {
    // Gera link de verificação de email para ser enviado ao usuário
    const auth = this.auth();
    const user = await auth.getUser(uid);
    if (user.email) {
      return auth.generateEmailVerificationLink(user.email);
    }
    return null;
  }
}
