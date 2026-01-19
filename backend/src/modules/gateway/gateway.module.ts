import { Module } from '@nestjs/common';
import { HttpModule } from '@nestjs/axios';
import { GatewayService } from './services/gateway.service';
import { GatewayController } from './controllers/gateway.controller';

@Module({
  imports: [HttpModule],
  controllers: [GatewayController],
  providers: [GatewayService],
})
export class GatewayModule {}
