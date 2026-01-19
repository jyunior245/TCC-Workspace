import React, { useState } from 'react';
import { View, StyleSheet, ScrollView } from 'react-native';
import { TextInput, Button, Title, Text } from 'react-native-paper';
import { AcsProfileViewModel } from '../viewmodels/AcsProfileViewModel';
import { AcsProfilePayload } from '../models/acsUser';

export default function ACSProfileScreen({ route, navigation }: any) {
  const { token } = route.params as { token: string };

  const [cpf, setCpf] = useState('');
  const [functionalRegistration, setFunctionalRegistration] = useState('');
  const [healthUnit, setHealthUnit] = useState('');
  const [workArea, setWorkArea] = useState('');
  const [phone, setPhone] = useState('');
  const [photoUrl, setPhotoUrl] = useState('');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const vm = new AcsProfileViewModel();

  const handleGenerateRegistration = () => {
    const generated = vm.generateFunctionalRegistration();
    setFunctionalRegistration(generated);
  };

  const handleSubmit = async () => {
    setLoading(true);
    setError(null);
    try {
      const payload: AcsProfilePayload = {
        cpf,
        functionalRegistration,
        healthUnit,
        workArea,
        phone,
        photoUrl: photoUrl || undefined,
      };
      await vm.submitProfile(token, payload);
      navigation.replace('ACSHome');
    } catch (e: any) {
      console.error('ACS profile error:', e);
      setError('Falha ao salvar dados do ACS. Verifique as informações e tente novamente.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Title style={styles.title}>Cadastro Complementar - ACS</Title>
      <TextInput label="CPF" value={cpf} onChangeText={setCpf} style={styles.input} />
      <View style={styles.row}>
        <TextInput
          label="Matrícula funcional"
          value={functionalRegistration}
          onChangeText={setFunctionalRegistration}
          style={[styles.input, { flex: 1 }]}
        />
        <Button mode="outlined" onPress={handleGenerateRegistration} style={styles.generateButton}>
          Gerar
        </Button>
      </View>
      <TextInput
        label="Unidade de saúde vinculada"
        value={healthUnit}
        onChangeText={setHealthUnit}
        style={styles.input}
      />
      <TextInput
        label="Área de atuação"
        value={workArea}
        onChangeText={setWorkArea}
        style={styles.input}
      />
      <TextInput label="Telefone" value={phone} onChangeText={setPhone} style={styles.input} />
      <TextInput
        label="URL da foto (temporário)"
        value={photoUrl}
        onChangeText={setPhotoUrl}
        style={styles.input}
      />

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
  row: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  generateButton: {
    marginLeft: 8,
    marginTop: 4,
  },
});

