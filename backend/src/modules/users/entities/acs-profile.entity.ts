import { Column, Entity, JoinColumn, OneToOne, PrimaryGeneratedColumn } from 'typeorm';
import { User } from './user.entity';

@Entity('acs_profiles')
export class AcsProfile {
  @PrimaryGeneratedColumn()
  id: number;

  @OneToOne(() => User)
  @JoinColumn()
  user: User;

  @Column({ unique: true })
  cpf: string;

  @Column({ unique: true })
  functionalRegistration: string;

  @Column()
  healthUnit: string;

  @Column()
  workArea: string;

  @Column()
  phone: string;

  @Column({ nullable: true })
  photoUrl?: string;
}

