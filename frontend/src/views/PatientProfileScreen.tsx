import React, { useState } from 'react';
import { View, StyleSheet, ScrollView } from 'react-native';
import { TextInput, Button, Title, Switch, Text } from 'react-native-paper';
import { PatientProfileViewModel } from '../viewmodels/PatientProfileViewModel';
import { PatientProfilePayload } from '../models/patientUser';

export default function PatientProfileScreen({ route, navigation }: any) {
  const { token } = route.params as { token: string };

  const [cpf, setCpf] = useState('');
  const [birthDate, setBirthDate] = useState('');
  const [gender, setGender] = useState('');
  const [address, setAddress] = useState('');
  const [phone, setPhone] = useState('');
  const [hasChronicDiseases, setHasChronicDiseases] = useState(false);
  const [chronicDiseasesDescription, setChronicDiseasesDescription] = useState('');
  const [hasDisabilities, setHasDisabilities] = useState(false);
  const [disabilitiesDescription, setDisabilitiesDescription] = useState('');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const vm = new PatientProfileViewModel();

  const handleSubmit = async () => {
    setLoading(true);
    setError(null);
    try {
      const payload: PatientProfilePayload = {
        cpf,
        birthDate,
        gender,
        address,
        phone,
        hasChronicDiseases,
        chronicDiseasesDescription: chronicDiseasesDescription || undefined,
        hasDisabilities,
        disabilitiesDescription: disabilitiesDescription || undefined,
      };
      await vm.submitProfile(token, payload);
      navigation.replace('PatientHome');
    } catch (e: any) {
      console.error('Patient profile error:', e);
      setError('Falha ao salvar dados do paciente. Verifique as informações e tente novamente.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Title style={styles.title}>Cadastro Complementar - Paciente</Title>
      <TextInput label="CPF" value={cpf} onChangeText={setCpf} style={styles.input} />
      <TextInput
        label="Data de Nascimento (YYYY-MM-DD)"
        value={birthDate}
        onChangeText={setBirthDate}
        style={styles.input}
      />
      <TextInput label="Sexo" value={gender} onChangeText={setGender} style={styles.input} />
      <TextInput label="Endereço" value={address} onChangeText={setAddress} style={styles.input} />
      <TextInput label="Telefone" value={phone} onChangeText={setPhone} style={styles.input} />

      <View style={styles.switchRow}>
        <Text>Possui doenças crônicas?</Text>
        <Switch value={hasChronicDiseases} onValueChange={setHasChronicDiseases} />
      </View>
      {hasChronicDiseases && (
        <TextInput
          label="Descreva as doenças crônicas"
          value={chronicDiseasesDescription}
          onChangeText={setChronicDiseasesDescription}
          style={styles.input}
          multiline
        />
      )}

      <View style={styles.switchRow}>
        <Text>Possui deficiências?</Text>
        <Switch value={hasDisabilities} onValueChange={setHasDisabilities} />
      </View>
      {hasDisabilities && (
        <TextInput
          label="Descreva as deficiências"
          value={disabilitiesDescription}
          onChangeText={setDisabilitiesDescription}
          style={styles.input}
          multiline
        />
      )}

      <Button mode="contained" onPress={handleSubmit} disabled={loading} style={styles.button}>
        Salvar e continuar
      </Button>
      {error && <Title style={{ color: 'red', marginTop: 10 }}>{error}</Title>}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flexGrow: 1,
    padding: 20,
  },
  title: {
    textAlign: 'center',
    marginBottom: 20,
  },
  input: {
    marginBottom: 10,
  },
  button: {
    marginTop: 10,
  },
  switchRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginVertical: 8,
  },
});

