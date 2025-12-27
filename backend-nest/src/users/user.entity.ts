import { Entity, Column, PrimaryGeneratedColumn } from 'typeorm';

@Entity()
export class User {
  @PrimaryGeneratedColumn()
  id: number;

  @Column({ unique: true })
  email: string;

  @Column()
  password?: string;

  @Column({ default: 'user' })
  role: string; // 'user' | 'acs' | 'admin'

  @Column({ nullable: true })
  name: string;
}
