import { IsEmail, IsNotEmpty, IsString, IsIn, Matches } from 'class-validator';

export class RegisterDto {
  @IsEmail()
  email: string;

  @IsString()
  @IsNotEmpty()
  @Matches(/^(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$/, {
    message: 'Password too weak',
  })
  password: string;

  @IsString()
  name?: string;

  @IsIn(['PATIENT', 'ACS'])
  role: 'PATIENT' | 'ACS';
}
