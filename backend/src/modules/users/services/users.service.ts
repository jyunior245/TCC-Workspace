import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { User } from '../entities/user.entity';
import { PatientProfile } from '../entities/patient-profile.entity';
import { AcsProfile } from '../entities/acs-profile.entity';
import { CreatePatientProfileDto } from '../dto/create-patient-profile.dto';
import { CreateAcsProfileDto } from '../dto/create-acs-profile.dto';

@Injectable()
export class UsersService {
  constructor(
    @InjectRepository(User)
    private usersRepository: Repository<User>,
    @InjectRepository(PatientProfile)
    private patientProfilesRepository: Repository<PatientProfile>,
    @InjectRepository(AcsProfile)
    private acsProfilesRepository: Repository<AcsProfile>,
  ) {}

  async findOne(email: string): Promise<User | undefined> {
    return this.usersRepository.findOne({ where: { email } });
  }

  async findById(id: number): Promise<User | undefined> {
    return this.usersRepository.findOne({ where: { id } });
  }

  async findByFirebaseUid(firebaseUid: string): Promise<User | undefined> {
    return this.usersRepository.findOne({ where: { firebaseUid } });
  }

  async create(userData: Partial<User>): Promise<User> {
    const user = this.usersRepository.create(userData);
    return this.usersRepository.save(user);
  }

  async hasCompletedProfile(userId: number, role: 'PATIENT' | 'ACS'): Promise<boolean> {
    if (role === 'PATIENT') {
      const profile = await this.patientProfilesRepository.findOne({
        where: { user: { id: userId } },
      });
      return !!profile;
    }
    if (role === 'ACS') {
      const profile = await this.acsProfilesRepository.findOne({
        where: { user: { id: userId } },
      });
      return !!profile;
    }
    return false;
  }

  async createPatientProfile(user: User, data: CreatePatientProfileDto): Promise<PatientProfile> {
    const profile = this.patientProfilesRepository.create({
      user,
      cpf: data.cpf,
      birthDate: new Date(data.birthDate),
      gender: data.gender,
      address: data.address,
      phone: data.phone,
      hasChronicDiseases: data.hasChronicDiseases,
      chronicDiseasesDescription: data.chronicDiseasesDescription,
      hasDisabilities: data.hasDisabilities,
      disabilitiesDescription: data.disabilitiesDescription,
    });
    return this.patientProfilesRepository.save(profile);
  }

  async createAcsProfile(user: User, data: CreateAcsProfileDto): Promise<AcsProfile> {
    const profile = this.acsProfilesRepository.create({
      user,
      cpf: data.cpf,
      functionalRegistration: data.functionalRegistration,
      healthUnit: data.healthUnit,
      workArea: data.workArea,
      phone: data.phone,
      photoUrl: data.photoUrl,
    });
    return this.acsProfilesRepository.save(profile);
  }

  async remove(id: number): Promise<void> {
    await this.usersRepository.delete(id);
  }
}
