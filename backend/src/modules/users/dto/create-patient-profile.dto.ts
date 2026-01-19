import { IsBoolean, IsDateString, IsNotEmpty, IsOptional, IsString } from 'class-validator';

export class CreatePatientProfileDto {
  @IsString()
  @IsNotEmpty()
  cpf: string;

  @IsDateString()
  birthDate: string;

  @IsString()
  @IsNotEmpty()
  gender: string;

  @IsString()
  @IsNotEmpty()
  address: string;

  @IsString()
  @IsNotEmpty()
  phone: string;

  @IsBoolean()
  hasChronicDiseases: boolean;

  @IsOptional()
  @IsString()
  chronicDiseasesDescription?: string;

  @IsBoolean()
  hasDisabilities: boolean;

  @IsOptional()
  @IsString()
  disabilitiesDescription?: string;
}

