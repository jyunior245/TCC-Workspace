import { IsEmail, IsNotEmpty, IsString, IsIn } from 'class-validator';

export class RegisterDto {
  @IsEmail()
  email: string;

  @IsString()
  @IsNotEmpty()
  password: string;

  @IsString()
  name?: string;

  @IsIn(['PATIENT', 'ACS'])
  role: 'PATIENT' | 'ACS';
}
