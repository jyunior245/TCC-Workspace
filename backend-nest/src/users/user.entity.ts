import { Entity, Column, PrimaryGeneratedColumn } from 'typeorm';

@Entity()
export class User {
  @PrimaryGeneratedColumn()
  id: number;

  @Column({ unique: true })
  email: string;

  @Column()
  password?: string;

  @Column({ type: 'varchar' })
  role: 'PATIENT' | 'ACS';

  @Column({ nullable: true })
  name: string;
}
