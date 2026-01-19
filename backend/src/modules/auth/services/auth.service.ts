import { ConflictException, Injectable, InternalServerErrorException, Logger } from '@nestjs/common';
import { UsersService } from '../../users/services/users.service';
import { JwtService } from '@nestjs/jwt';
import { FirebaseService } from '../../../infrastructure/firebase/firebase.service';
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

  private logger = new Logger(AuthService.name);
  private readonly REGISTRATION_TIMEOUT_MINUTES = 30;

  private isRegistrationExpired(createdAt?: Date): boolean {
    if (!createdAt) {
      return false;
    }
    const now = Date.now();
    const created = createdAt instanceof Date ? createdAt.getTime() : new Date(createdAt).getTime();
    const diffMinutes = (now - created) / (1000 * 60);
    return diffMinutes > this.REGISTRATION_TIMEOUT_MINUTES;
  }

  async validateUser(email: string, password: string): Promise<any> {
    const apiKey = this.config.get<string>('FIREBASE_API_KEY');
    const url = `https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=${apiKey}`;
    try {
      const { data } = await axios.post(url, { email, password, returnSecureToken: true });
      const user = await this.usersService.findOne(email);
      if (!user) return null;
      const profileCompleted = await this.usersService.hasCompletedProfile(user.id, user.role);

      if (!profileCompleted && this.isRegistrationExpired((user as any).createdAt)) {
        this.logger.warn(`Incomplete registration expired for email ${email}. Cleaning up user.`);
        if ((user as any).firebaseUid) {
          try {
            await this.firebase.auth().deleteUser((user as any).firebaseUid);
          } catch (err: any) {
            this.logger.error(`Failed to delete expired Firebase user for ${email}: ${err.message}`);
          }
        }
        await this.usersService.remove(user.id);
        return null;
      }

      return { id: user.id, email: user.email, role: user.role, firebaseUid: data.localId, profileCompleted };
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
    const existing = await this.usersService.findOne(userData.email);
    if (existing) {
      const profileCompleted = await this.usersService.hasCompletedProfile(existing.id, existing.role);
      const expired = this.isRegistrationExpired((existing as any).createdAt);

      if (!profileCompleted && expired) {
        this.logger.warn(`Expired incomplete registration found for ${userData.email}. Cleaning up before new registration.`);
        if (existing.firebaseUid) {
          try {
            await this.firebase.auth().deleteUser(existing.firebaseUid);
          } catch (err: any) {
            this.logger.error(`Failed to delete expired Firebase user for ${userData.email}: ${err.message}`);
          }
        }
        await this.usersService.remove(existing.id);
      } else {
        let isZombie = false;
        if (existing.firebaseUid) {
          try {
            await this.firebase.auth().getUser(existing.firebaseUid);
          } catch (error: any) {
            if (error.code === 'auth/user-not-found') {
              isZombie = true;
            }
          }
        } else {
          isZombie = true;
        }

        if (isZombie) {
          this.logger.log(`Zombie user detected for email ${userData.email}. Cleaning up Postgres record.`);
          await this.usersService.remove(existing.id);
        } else {
          throw new ConflictException('Email already in use');
        }
      }
    }

    let fbUser: any;
    try {
      fbUser = await this.firebase.createUser(userData.email, userData.password, userData.name);
      await this.firebase.sendEmailVerification(fbUser.uid);

      return await this.usersService.create({
        email: userData.email,
        name: userData.name,
        role: userData.role,
        firebaseUid: fbUser.uid,
      });
    } catch (error: any) {
      if (fbUser && fbUser.uid && error.code !== 'auth/email-already-exists') {
        try {
          await this.firebase.auth().deleteUser(fbUser.uid);
        } catch {
        }
      }
      if (error.code === 'auth/email-already-exists') {
        throw new ConflictException('Email already in use');
      }
      throw new InternalServerErrorException(error.message);
    }
  }
}

