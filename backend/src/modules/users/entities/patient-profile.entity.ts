import { Column, Entity, JoinColumn, OneToOne, PrimaryGeneratedColumn } from 'typeorm';
import { User } from './user.entity';

@Entity('patient_profiles')
export class PatientProfile {
  @PrimaryGeneratedColumn()
  id: number;

  @OneToOne(() => User)
  @JoinColumn()
  user: User;

  @Column({ unique: true })
  cpf: string;

  @Column({ type: 'date' })
  birthDate: Date;

  @Column()
  gender: string;

  @Column()
  address: string;

  @Column()
  phone: string;

  @Column({ default: false })
  hasChronicDiseases: boolean;

  @Column({ nullable: true })
  chronicDiseasesDescription?: string;

  @Column({ default: false })
  hasDisabilities: boolean;

  @Column({ nullable: true })
  disabilitiesDescription?: string;
}

