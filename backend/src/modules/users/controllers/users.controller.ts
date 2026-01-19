import { Body, Controller, NotFoundException, Post, UseGuards } from '@nestjs/common';
import { UsersService } from '../services/users.service';
import { JwtAuthGuard } from '../../../common/guards/jwt-auth.guard';
import { RolesGuard } from '../../../common/guards/roles.guard';
import { Roles } from '../../../common/decorators/roles.decorator';
import { CurrentUser } from '../../../common/decorators/user.decorator';
import { CreatePatientProfileDto } from '../dto/create-patient-profile.dto';
import { CreateAcsProfileDto } from '../dto/create-acs-profile.dto';

@Controller('users')
export class UsersController {
  constructor(private usersService: UsersService) {}

  @Post('patient/profile')
  @UseGuards(JwtAuthGuard, RolesGuard)
  @Roles('PATIENT')
  async completePatientProfile(
    @CurrentUser() user: { userId: number },
    @Body() data: CreatePatientProfileDto,
  ) {
    const baseUser = await this.usersService.findById(user.userId);
    if (!baseUser) {
      throw new NotFoundException('User not found');
    }
    return this.usersService.createPatientProfile(baseUser, data);
  }

  @Post('acs/profile')
  @UseGuards(JwtAuthGuard, RolesGuard)
  @Roles('ACS')
  async completeAcsProfile(
    @CurrentUser() user: { userId: number },
    @Body() data: CreateAcsProfileDto,
  ) {
    const baseUser = await this.usersService.findById(user.userId);
    if (!baseUser) {
      throw new NotFoundException('User not found');
    }
    return this.usersService.createAcsProfile(baseUser, data);
  }
}

