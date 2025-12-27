import { Controller, Post, Body, UseGuards } from '@nestjs/common';
import { GatewayService } from './gateway.service';
// import { JwtAuthGuard } from '../auth/jwt-auth.guard'; // Uncomment when Auth is fully integrated

@Controller('api/voice')
export class GatewayController {
  constructor(private gatewayService: GatewayService) {}

  @Post('process')
  // @UseGuards(JwtAuthGuard) // Protect this endpoint later
  async processVoice(@Body('text') text: string) {
    return this.gatewayService.processVoice(text);
  }
}
