import { IsNotEmpty, IsOptional, IsString } from 'class-validator';

export class CreateAcsProfileDto {
  @IsString()
  @IsNotEmpty()
  cpf: string;

  @IsString()
  @IsNotEmpty()
  functionalRegistration: string;

  @IsString()
  @IsNotEmpty()
  healthUnit: string;

  @IsString()
  @IsNotEmpty()
  workArea: string;

  @IsString()
  @IsNotEmpty()
  phone: string;

  @IsOptional()
  @IsString()
  photoUrl?: string;
}

