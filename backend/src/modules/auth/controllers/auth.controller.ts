import { Controller, Post, Body, UnauthorizedException } from '@nestjs/common';
import { AuthService } from '../services/auth.service';
import { LoginDto } from '../dto/login.dto';
import { RegisterDto } from '../dto/register.dto';

@Controller('auth')
export class AuthController {
  constructor(private authService: AuthService) {}

  @Post('login')
  async login(@Body() body: LoginDto) {
    const user = await this.authService.validateUser(body.email, body.password);
    if (!user) {
      throw new UnauthorizedException();
    }
    const token = await this.authService.login(user);
    return {
      access_token: token.access_token,
      user: {
        id: user.id,
        email: user.email,
        role: user.role,
      },
    };
  }

  @Post('register')
  async register(@Body() body: RegisterDto) {
    const created = await this.authService.register(body);
    return {
      id: created.id,
      email: created.email,
      role: created.role,
    };
  }
}

