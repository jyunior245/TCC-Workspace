import { CanActivate, ExecutionContext, Injectable } from '@nestjs/common';
import { UsersService } from '../../modules/users/services/users.service';

@Injectable()
export class ProfileCompletedGuard implements CanActivate {
  constructor(private usersService: UsersService) {}

  async canActivate(context: ExecutionContext): Promise<boolean> {
    const request = context.switchToHttp().getRequest();
    const user = request.user;
    if (!user || typeof user.userId !== 'number' || !user.role) {
      return false;
    }
    return this.usersService.hasCompletedProfile(user.userId, user.role);
  }
}

