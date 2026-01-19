export interface PatientProfilePayload {
  cpf: string;
  birthDate: string;
  gender: string;
  address: string;
  phone: string;
  hasChronicDiseases: boolean;
  chronicDiseasesDescription?: string;
  hasDisabilities: boolean;
  disabilitiesDescription?: string;
}
