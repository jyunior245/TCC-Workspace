import { Module } from '@nestjs/common';
import { ConfigModule, ConfigService } from '@nestjs/config';
import { TypeOrmModule } from '@nestjs/typeorm';
import { UsersModule } from './modules/users/users.module';
import { AuthModule } from './modules/auth/auth.module';
import { FirebaseModule } from './infrastructure/firebase/firebase.module';
import { GatewayModule } from './modules/gateway/gateway.module';
import { User } from './modules/users/entities/user.entity';
import { PatientProfile } from './modules/users/entities/patient-profile.entity';
import { AcsProfile } from './modules/users/entities/acs-profile.entity';

@Module({
  imports: [
    ConfigModule.forRoot({
      isGlobal: true,
    }),
    TypeOrmModule.forRootAsync({
      imports: [ConfigModule],
      useFactory: (configService: ConfigService) => ({
        type: 'postgres',
        host: configService.get<string>('DB_HOST'),
        port: parseInt(configService.get<string>('DB_PORT'), 10),
        username: configService.get<string>('DB_USER'),
        password: configService.get<string>('DB_PASSWORD'),
        database: configService.get<string>('DB_NAME'),
        entities: [User, PatientProfile, AcsProfile],
        synchronize: true,
      }),
      inject: [ConfigService],
    }),
    UsersModule,
    AuthModule,
    FirebaseModule,
    GatewayModule,
  ],
  controllers: [],
  providers: [],
})
export class AppModule {}
